# -*- coding: utf-8 -*-
from discord.ext import commands
import discord
from discord import app_commands
import os, asyncio
import datetime
import random
from firebase_admin import firestore

os.environ["PYTHONIOENCODING"] = "utf-8"
OWNER_ID = 1193095716730585102

class WordChain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # RAM Cache Database - TỐC ĐỘ ÁNH SÁNG ⚡
        self.last_word = {}         # {guild_id: "từ hiện tại"}
        self.last_player_id = {}    # {guild_id: user_id}
        self.used_words_cache = {}  # {guild_id: set(tất cả từ đã dùng)}
        self.channel_configs = {}   # {guild_id: channel_id}
        self.game_mutes = {}        # {user_id: datetime_hết_hạn}
        
        if not hasattr(bot, 'word_map'):
            bot.word_map = {}

    # =========================================================================
    # --- CÁC HÀM HỖ TRỢ (HELPER FUNCTIONS) ---
    # =========================================================================

    async def get_config(self, guild_id):
        """Lấy channel_id từ RAM hoặc Firestore"""
        if guild_id in self.channel_configs:
            return self.channel_configs[guild_id]
        doc_ref = self.bot.db.collection("channels").document(str(guild_id))
        doc = await asyncio.to_thread(doc_ref.get)
        if doc.exists:
            cid = doc.to_dict().get("channel_id")
            self.channel_configs[guild_id] = cid
            return cid
        return None

    async def check_money(self, guild_id, user_id, amount):
        """Kiểm tra tiền (Firestore)"""
        doc_ref = self.bot.db.collection("ranks").document(f"{guild_id}_{user_id}")
        doc = await asyncio.to_thread(doc_ref.get)
        return doc.to_dict().get("money", 0) >= amount if doc.exists else False

    async def sync_game_state(self, guild_id):
        """Đồng bộ từ Firestore vào RAM (Chỉ chạy khi khởi động hoặc reset)"""
        def _fetch():
            return list(self.bot.db.collection("used_words")\
                .where(filter=firestore.FieldFilter("guild_id", "==", str(guild_id)))\
                .stream())
        docs = await asyncio.to_thread(_fetch)
        if not docs: return False
        
        data = [d.to_dict() for d in docs]
        sorted_data = sorted(data, key=lambda d: d.get("added_at", 0), reverse=True)
        self.last_word[guild_id] = sorted_data[0]["word"]
        self.used_words_cache[guild_id] = {d["word"] for d in data}
        return True

    # =========================================================================
    # --- QUẢN TRỊ (ADMIN) ---
    # =========================================================================

    @app_commands.command(name="set-channel", description="Cài đặt kênh chơi nối từ (Admin)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await asyncio.to_thread(self.bot.db.collection("channels").document(str(interaction.guild_id)).set, {"channel_id": channel.id}, merge=True)
        self.channel_configs[interaction.guild_id] = channel.id
        await interaction.followup.send(f"✅ Kênh chơi nối từ: {channel.mention}")

    @commands.command(name="start")
    @commands.has_permissions(administrator=True)
    async def start(self, ctx):
        if not self.bot.word_map: return await ctx.send("❌ Từ điển chưa tải xong!")
        cid = await self.get_config(ctx.guild.id)
        if ctx.channel.id != cid: return await ctx.send(f"❌ Dùng tại <#{cid}>")

        start_word = self.bot.get_random_word()
        def _reset():
            batch = self.bot.db.batch()
            old = self.bot.db.collection("used_words").where(filter=firestore.FieldFilter("guild_id", "==", str(ctx.guild.id))).get()
            for d in old: batch.delete(d.reference)
            batch.commit()
            self.bot.db.collection("used_words").add({"guild_id": str(ctx.guild.id), "word": start_word, "added_at": firestore.SERVER_TIMESTAMP})
        
        await asyncio.to_thread(_reset)
        self.last_word[ctx.guild.id] = start_word
        self.used_words_cache[ctx.guild.id] = {start_word}
        self.last_player_id[ctx.guild.id] = None
        await ctx.send(f"🎮 **BẮT ĐẦU!** Từ đầu tiên: **{start_word}**")

    @commands.command(name="stop")
    @commands.has_permissions(administrator=True)
    async def stop(self, ctx):
        def _del():
            batch = self.bot.db.batch()
            old = self.bot.db.collection("used_words").where(filter=firestore.FieldFilter("guild_id", "==", str(ctx.guild.id))).get()
            for d in old: batch.delete(d.reference)
            batch.commit()
        await asyncio.to_thread(_del)
        self.last_word.pop(ctx.guild.id, None)
        self.used_words_cache.pop(ctx.guild.id, None)
        await ctx.send("🛑 Đã dừng game và xoá dữ liệu.")

    # =========================================================================
    # --- VẬT PHẨM & TIỆN ÍCH ---
    # =========================================================================

    @app_commands.command(name="w-undo", description="Quay lại lượt trước ($500)")
    async def w_undo(self, interaction: discord.Interaction):
        await interaction.response.defer()
        gid = interaction.guild_id
        if gid not in self.last_word and not await self.sync_game_state(gid): return await interaction.followup.send("Game chưa chạy!")
        if not await self.check_money(gid, interaction.user.id, 500): return await interaction.followup.send("❌ Thiếu $500!")

        def _undo():
            docs = sorted(list(self.bot.db.collection("used_words").where(filter=firestore.FieldFilter("guild_id", "==", str(gid))).stream()), key=lambda d: d.to_dict().get("added_at", 0), reverse=True)
            if len(docs) < 2: return None
            cur = docs[0]
            prev_word = docs[1].to_dict()["word"]
            cur.reference.delete()
            self.bot.db.collection("ranks").document(f"{gid}_{interaction.user.id}").update({"money": firestore.Increment(-500)})
            return prev_word

        prev = await asyncio.to_thread(_undo)
        if not prev: return await interaction.followup.send("Không thể Undo!")
        self.last_word[gid] = prev
        self.used_words_cache[gid].discard(prev) # Sẽ sync lại ở lượt sau
        self.last_player_id[gid] = None
        await interaction.followup.send(f"⏪ **{interaction.user.display_name}** Undo! Từ hiện tại: **{prev}**")

    @app_commands.command(name="w-mute", description="Chặn người chơi (Game: $50k, Chat: $1M)")
    @app_commands.choices(loai=[app_commands.Choice(name="Game ($50k)", value="game"), app_commands.Choice(name="Chat ($1M)", value="chat")])
    async def w_mute(self, interaction: discord.Interaction, user: discord.Member, loai: str, seconds: int = 60):
        await interaction.response.defer()
        cost = 1000000 if loai == "chat" else 50000
        seconds = min(seconds, 60)
        if user.id == interaction.user.id: return await interaction.followup.send("Không thể tự chặn mình!")
        if not await self.check_money(interaction.guild_id, interaction.user.id, cost): return await interaction.followup.send(f"❌ Thiếu ${cost:,}!")

        if loai == "chat":
            try:
                await user.timeout(datetime.timedelta(seconds=seconds))
            except: return await interaction.followup.send("Bot thiếu quyền Timeout!")
        else:
            self.game_mutes[user.id] = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)

        await asyncio.to_thread(self.bot.db.collection("ranks").document(f"{interaction.guild_id}_{interaction.user.id}").update, {"money": firestore.Increment(-cost)})
        await interaction.followup.send(f"🤐 **{interaction.user.name}** đã chặn **{user.name}** ({loai}) trong {seconds}s!")

    @app_commands.command(name="w-skip", description="Bỏ qua từ ($750)")
    async def w_skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        gid = interaction.guild_id
        if gid not in self.last_word and not await self.sync_game_state(gid): return await interaction.followup.send("Game chưa chạy!")
        if not await self.check_money(gid, interaction.user.id, 750): return await interaction.followup.send("❌ Thiếu $750!")

        last_char = self.last_word[gid].split()[-1]
        used = self.used_words_cache.get(gid, set())
        possible = [w for w in self.bot.word_map.get(last_char, []) if w not in used]
        if not possible: return await interaction.followup.send("Bot cũng chịu, không skip được!")

        new_word = random.choice(possible)
        self.last_word[gid] = new_word
        self.used_words_cache[gid].add(new_word)
        self.last_player_id[gid] = None
        
        asyncio.create_task(asyncio.to_thread(lambda: self.bot.db.collection("used_words").add({"guild_id": str(gid), "word": new_word, "added_at": firestore.SERVER_TIMESTAMP})))
        asyncio.create_task(asyncio.to_thread(lambda: self.bot.db.collection("ranks").document(f"{gid}_{interaction.user.id}").update({"money": firestore.Increment(-750)})))
        await interaction.followup.send(f"⏭️ Bot nối: **{new_word}**. Mời tiếp tục!")

    @app_commands.command(name="w-hint", description="Gợi ý từ ($250-$450)")
    async def hint(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gid = interaction.guild_id
        if gid not in self.last_word and not await self.sync_game_state(gid): return await interaction.followup.send("Game chưa chạy!")
        
        last_char = self.last_word[gid].split()[-1]
        used = self.used_words_cache.get(gid, set())
        possible = [w for w in self.bot.word_map.get(last_char, []) if w not in used]
        if not possible: return await interaction.followup.send("Không còn từ nào để nối!")

        winning = [w for w in possible if not any(nxt not in used for nxt in self.bot.word_map.get(w.split()[-1], []))]
        
        if winning:
            if not await self.check_money(gid, interaction.user.id, 450): return await interaction.followup.send("Thiếu $450 cho từ chí mạng!")
            hint_word, fee = random.choice(winning), 450
            msg = f"💀 **TỪ CHÍ MẠNG:** ||**{hint_word}**|| (Đối thủ sẽ không thể nối!)"
        else:
            if not await self.check_money(gid, interaction.user.id, 250): return await interaction.followup.send("Thiếu $250 cho gợi ý!")
            hint_word, fee = random.choice(possible), 250
            msg = f"💡 Gợi ý: **{hint_word}**"

        await asyncio.to_thread(self.bot.db.collection("ranks").document(f"{gid}_{interaction.user.id}").update, {"money": firestore.Increment(-fee)})
        await interaction.followup.send(f"{msg} (-${fee})")

    # =========================================================================
    # --- THỐNG KÊ (STATS) ---
    # =========================================================================

    @app_commands.command(name="rank", description="Xem BXH Server")
    async def rank(self, interaction: discord.Interaction):
        await interaction.response.defer()
        docs = await asyncio.to_thread(lambda: list(self.bot.db.collection("ranks").where(filter=firestore.FieldFilter("guild_id", "==", str(interaction.guild_id))).stream()))
        if not docs: return await interaction.followup.send("Chưa có dữ liệu.")
        top = sorted(docs, key=lambda d: (d.to_dict().get("wins", 0), d.to_dict().get("score", 0)), reverse=True)[:10]
        desc = "\n".join([f"**#{i+1}** <@{d.id.split('_')[-1]}>: `{d.to_dict().get('wins',0)}` thắng | `${d.to_dict().get('money',0):,}`" for i, d in enumerate(top)])
        await interaction.followup.send(embed=discord.Embed(title="🏆 BXH Nối Từ", description=desc, color=0xFFAA00))

    @app_commands.command(name="me", description="Thống kê cá nhân")
    async def me(self, interaction: discord.Interaction):
        doc = await asyncio.to_thread(self.bot.db.collection("ranks").document(f"{interaction.guild_id}_{interaction.user.id}").get)
        data = doc.to_dict() if doc.exists else {"score":0, "wins":0, "money":0}
        emb = discord.Embed(title=f"📊 {interaction.user.display_name}", color=0x3498db)
        emb.add_field(name="Số từ", value=f"`{data.get('score',0)}`").add_field(name="Thắng", value=f"`{data.get('wins',0)}`").add_field(name="Tiền", value=f"`${data.get('money',0):,}`")
        await interaction.response.send_message(embed=emb)

    @app_commands.command(name="donate", description="Chuyển tiền ($)")
    async def donate(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0 or user.bot or user.id == interaction.user.id: return await interaction.response.send_message("Giao dịch không hợp lệ!")
        if not await self.check_money(interaction.guild_id, interaction.user.id, amount): return await interaction.response.send_message("❌ Thiếu tiền!")
        
        def _xfer():
            b = self.bot.db.batch()
            b.update(self.bot.db.collection("ranks").document(f"{interaction.guild_id}_{interaction.user.id}"), {"money": firestore.Increment(-amount)})
            b.set(self.bot.db.collection("ranks").document(f"{interaction.guild_id}_{user.id}"), {"guild_id": str(interaction.guild_id), "money": firestore.Increment(amount)}, merge=True)
            b.commit()
        await asyncio.to_thread(_xfer)
        await interaction.response.send_message(f"✅ Đã chuyển **${amount:,}** cho **{user.name}**!")

    @app_commands.command(name="report", description="Báo lỗi game")
    async def report(self, interaction: discord.Interaction, tu: str, ly_do: str):
        owner = self.bot.get_user(OWNER_ID)
        if owner: await owner.send(f"🚩 **REPORT**: {interaction.user} báo lỗi từ `{tu}`: {ly_do}")
        await interaction.response.send_message("✅ Đã gửi báo cáo!", ephemeral=True)

    @app_commands.command(name="stats", description="Thống kê toàn hệ thống")
    async def stats(self, interaction: discord.Interaction):
        doc = await asyncio.to_thread(self.bot.db.collection("stats").document("total_words").get)
        total = doc.to_dict().get("value", 0) if doc.exists else 0
        await interaction.response.send_message(f"📊 Hệ thống đã nối được `{total:,}` từ!")

    # =========================================================================
    # --- CORE GAME LOGIC ---
    # =========================================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        cnt = message.content.strip().lower()
        if cnt.startswith(("!", "/", "o!", "t!")): return
        
        gid = message.guild.id
        if gid not in self.channel_configs: await self.get_config(gid)
        if message.channel.id != self.channel_configs.get(gid): return

        if gid not in self.last_word and not await self.sync_game_state(gid): return

        if message.author.id in self.game_mutes:
            if datetime.datetime.utcnow() < self.game_mutes[message.author.id]:
                try: await message.add_reaction("🔇")
                except: pass
                return
            else: del self.game_mutes[message.author.id]

        words = cnt.split()
        if len(words) != 2: return
        
        if self.last_player_id.get(gid) == message.author.id:
             return await self._err(message, "⏳")

        required = self.last_word[gid].split()[-1]
        if words[0] != required: return await self._err(message, "❌")
        if words[0] not in self.bot.word_map or cnt not in self.bot.word_map[words[0]]: return await self._err(message, "❓")
        if cnt in self.used_words_cache.get(gid, set()): return await self._err(message, "🚫")

        # OK -> Phản hồi tức thì
        try: await message.add_reaction("✅")
        except: pass
        self.last_word[gid] = cnt
        self.last_player_id[gid] = message.author.id
        self.used_words_cache[gid].add(cnt)

        # Xử lý background
        asyncio.create_task(self._process(message, cnt))

    async def _err(self, msg, emoji):
        """Thay thế gửi tin nhắn phản hồi bằng cách thả emoji trực tiếp"""
        try: await msg.add_reaction(emoji)
        except: pass

    async def _process(self, message, cnt):
        gid, uid = message.guild.id, message.author.id
        await asyncio.to_thread(lambda: self.bot.db.collection("used_words").add({"guild_id": str(gid), "word": cnt, "added_at": firestore.SERVER_TIMESTAMP}))
        await asyncio.to_thread(lambda: self.bot.db.collection("ranks").document(f"{gid}_{uid}").set({"guild_id": str(gid), "score": firestore.Increment(1), "money": firestore.Increment(50)}, merge=True))
        await asyncio.to_thread(lambda: self.bot.db.collection("stats").document("total_words").set({"value": firestore.Increment(1)}, merge=True))

        # Check Win
        last_tkn = cnt.split()[-1]
        can_cont = any(w not in self.used_words_cache[gid] for w in self.bot.word_map.get(last_tkn, []))
        
        if not can_cont:
            await asyncio.to_thread(lambda: self.bot.db.collection("ranks").document(f"{gid}_{uid}").update({"wins": firestore.Increment(1), "money": firestore.Increment(500)}))
            await message.channel.send(embed=discord.Embed(title="🏆 CHIẾN THẮNG!", description=f"Không còn từ nối cho **{last_tkn}**!\nThưởng: **$500** cho <@{uid}>", color=0xFFD700))
            await asyncio.sleep(5)
            await self._new_round(message.channel)

    async def _new_round(self, channel):
        gid = channel.guild.id
        nw = self.bot.get_random_word()
        def _c():
            b = self.bot.db.batch()
            for d in self.bot.db.collection("used_words").where(filter=firestore.FieldFilter("guild_id", "==", str(gid))).get(): b.delete(d.reference)
            b.commit()
            self.bot.db.collection("used_words").add({"guild_id": str(gid), "word": nw, "added_at": firestore.SERVER_TIMESTAMP})
        await asyncio.to_thread(_c)
        self.last_word[gid], self.used_words_cache[gid], self.last_player_id[gid] = nw, {nw}, None
        await channel.send(f"🎮 **Vòng mới bắt đầu!** Từ đầu tiên: **{nw}**")

async def setup(bot):
    await bot.add_cog(WordChain(bot))