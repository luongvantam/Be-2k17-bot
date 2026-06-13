# -*- coding: utf-8 -*-
from discord.ext import commands
import discord
import os, sys, asyncio, datetime, traceback, aiohttp, json
import psutil
import content
from firebase_admin import firestore

os.environ["PYTHONIOENCODING"] = "utf-8"

OWNER_ID   = 1193095716730585102
GEMINI_KEY = os.getenv("GEMINI_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"

# ANSI Color Codes
C_RESET  = "\x1b[0m"
C_GREEN  = "\x1b[1;32m"
C_RED    = "\x1b[1;31m"
C_YELLOW = "\x1b[1;33m"
C_WHITE  = "\x1b[1;37m"
C_BLUE  = "\x1b[1;34m"


class Others(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def is_owner(ctx):
        return ctx.author.id == OWNER_ID

    def format_response(self, content: str, is_error: bool = False,
                        lang: str = None, force_block: bool = False) -> str:
        content = str(content).strip()
        if is_error:
            content = f"{C_RED}Error:{C_RESET} {content}"
        elif lang == "ansi" or force_block:
            if not content.startswith(C_RED) and not content.startswith(C_YELLOW):
                content = f"{C_WHITE}{content}{C_RESET}"
        if lang is None or lang == "ansi":
            return f"```ansi\n{content}\n```"
        if content.startswith("```"):
            return content
        return f"```{lang}\n{content}\n```"

    async def cog_check(self, ctx):
        if ctx.author.id in self.bot.blocked_user_ids:
            await ctx.reply("❌ You have been blocked from using this bot.", delete_after=5)
            return False
        return True

    async def _send_long(self, ctx, text: str, file_name: str = "output.txt"):
        """Gửi text; nếu > 1900 ký tự thì đính kèm file thay vì chia nhỏ."""
        if len(text) <= 1900:
            return await ctx.reply(text)
        
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            await ctx.reply("Nội dung quá dài, mình gửi file đính kèm nhé:", file=discord.File(file_name))
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    # ──────────────────────────────────────────────
    # Commands
    # ──────────────────────────────────────────────

    @commands.command(name="help")
    async def help(self, ctx, *, args: str = None):
        if not args:
            return await self._send_general_help(ctx, lang="en")

        parts = args.split()
        first_arg = parts[0].lower()

        if first_arg in ["vi", "en"]:
            if len(parts) == 1:
                return await self._send_general_help(ctx, lang=first_arg)
            
            lang = first_arg
            cmd_name = parts[1].lower()
        else:
            lang = "en"
            cmd_name = first_arg

        is_vi = (lang == "vi")
        usage_dict = content.usage_dict_vi if is_vi else content.usage_dict_en
        block = usage_dict.get(cmd_name)

        if not block:
            return await ctx.reply(f"No usage info found for command: {cmd_name}")

        if is_vi:
            return await ctx.reply(f"## Lệnh {cmd_name} được dùng kiểu:\n{block}")
        return await ctx.reply(f"## Usage of {cmd_name}:\n{block}\n\nTip: Use `o!help vi {cmd_name}` for Vietnamese help.")

    async def _send_general_help(self, ctx, lang: str):
        text = content.help_text_vi if lang == "vi" else content.help_text_en
        try:
            await ctx.reply(text)
        except discord.Forbidden:
            await ctx.author.reply(self.format_response(
                "The bot does not have permission to send messages in this channel.", is_error=True
            ))


    @commands.command(name="talk")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def generator(self, ctx, *, prompt: str):
        """Hỏi Gemini với Google Search tích hợp (Sử dụng REST API để nhẹ máy)"""
        if not GEMINI_KEY:
            return await ctx.reply("❌ Gemini key không tồn tại!")

        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "system_instruction": {"parts": [{"text": "You are Bé 2k17-bot, a helpful assistant. Reply in the same language as the user's question."}]},
            "tools": [{"google_search": {}}]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(GEMINI_URL, json=data) as resp:
                    if resp.status != 200:
                        err_text = await resp.text()
                        return await self._send_long(ctx, f"Gemini API Error {resp.status}:\n\n{err_text}", file_name="api_error.txt")
                    
                    result = await resp.json()
                    candidates = result.get("candidates", [])
                    if not candidates:
                        return await ctx.reply("❌ Không nhận được câu trả lời từ AI (Safety block hoặc lý do khác).")
                    
                    # Trích xuất nội dung văn bản từ các parts
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply_text = "".join(p.get("text", "") for p in parts)
                    
                    if not reply_text:
                        # Kiểm tra fallback nếu text rống
                        reply_text = str(candidates[0])[:1900] 

                    await self._send_long(ctx, reply_text.strip())
        except Exception as e:
            await ctx.reply(self.format_response(str(e), is_error=True))


    @commands.command(name="info")
    @commands.is_owner()
    async def info(self, ctx):
        try:
            now     = datetime.datetime.now(datetime.timezone.utc)
            process = psutil.Process()
            uptime  = now - self.bot.start_time
            dm_users = []
            
            if hasattr(self.bot, 'private_channels'):
                for channel in self.bot.private_channels:
                    if isinstance(channel, discord.DMChannel) and channel.recipient:
                        dm_users.append(channel.recipient)
            
            for message in self.bot.cached_messages:
                if isinstance(message.channel, discord.DMChannel) and message.channel.recipient:
                    if message.channel.recipient not in dm_users:
                        dm_users.append(message.channel.recipient)
                        
            dm_users = list(set(dm_users))

            msg = (
                f"{C_WHITE}Bot Info (UTC {now}):{C_RESET}\n\n"
                f"{C_BLUE}[General]{C_RESET}\n"
                f" {C_GREEN}Name:{C_RESET} {self.bot.user.name}\n"
                f" {C_GREEN}ID:{C_RESET} {self.bot.user.id}\n"
                f" {C_GREEN}Servers:{C_RESET} {len(self.bot.guilds)}\n"
                f" {C_GREEN}Users:{C_RESET} {len(set(self.bot.get_all_members()))}\n"
                f" {C_GREEN}Python:{C_RESET} {sys.version.split()[0]}\n"
                f" {C_GREEN}RAM:{C_RESET} {process.memory_info().rss / 1024 / 1024:.2f} MB\n"
                f" {C_GREEN}CPU:{C_RESET} {psutil.cpu_percent(interval=1):.2f}%\n"
                f" {C_GREEN}Uptime:{C_RESET} {str(uptime).split('.')[0]}\n\n"
                
                f"{C_BLUE}[Direct Messages (DMs)]{C_RESET}\n"
            )
            
            if dm_users:
                msg += f" {C_GREEN}Total DM Channels Active in Cache:{C_RESET} {len(dm_users)}\n"
                for u in dm_users:
                    msg += f"  - {u.name} (ID: {u.id})\n"
            else:
                msg += "  (Không tìm thấy người dùng nào trong cache DM hiện tại)\n"
                
            msg += f"\n{C_BLUE}[Servers]{C_RESET}\n"
            for g in self.bot.guilds:
                msg += f" {C_GREEN}{g.name} (ID: {g.id}, Members: {g.member_count}){C_RESET}\n"

            if len(msg) > 1900:
                with open("bot_info.txt", "w", encoding="utf-8") as f:
                    f.write(msg)
                await ctx.reply(file=discord.File("bot_info.txt"))
                os.remove("bot_info.txt")
            else:
                await ctx.reply(self.format_response(msg, lang="ansi"))
                
        except Exception:
            await ctx.reply(self.format_response(f"Error retrieving info:\n{traceback.format_exc()}", is_error=True))


    @commands.command(name="eval")
    @commands.is_owner()
    async def eval_code(self, ctx, *, code: str):
        code = code.strip()
        if code.startswith("```"):
            lines = code.splitlines()
            if len(lines) > 1:
                first_line = lines[0].strip().lower()
                if first_line.startswith("```"):
                    lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines).strip()
        else:
            code = code.strip("` \n")

        try:
            local_vars = {
                "bot": self.bot,
                "ctx": ctx,
                "channel": ctx.channel,
                "author": ctx.author,
                "guild": ctx.guild,
                "message": ctx.message,
                "asyncio": asyncio,
                "os": os,
                "sys": sys,
                "_result": None
            }
            lines = code.splitlines()
            if lines:
                last_line = lines[-1].strip()
                if (not last_line.startswith(("return", "yield", "print", "import", "from", "assert", "raise", "global", "nonlocal")) 
                        and "=" not in last_line and last_line != ""):
                    indent = len(lines[-1]) - len(lines[-1].lstrip())
                    lines[-1] = (" " * indent) + f"_result = {lines[-1].strip()}"
            structured_code = "\n".join(lines)
            func_str = "async def __ex():\n" + "\n".join(f"    {line}" for line in structured_code.splitlines())
            exec(func_str, local_vars)
            result = await local_vars["__ex"]()
            final_output = result if result is not None else local_vars["_result"]
            
            if final_output is not None:
                await ctx.reply(self.format_response(f"{C_GREEN}Result:\n{final_output}{C_RESET}", lang="ansi"))
            else:
                await ctx.reply(self.format_response(f"{C_GREEN}Executed successfully.{C_RESET}", lang="ansi"))
                
        except Exception:
            await ctx.reply(self.format_response(f"Error:\n{traceback.format_exc()}", is_error=True))


    @commands.command(name="block")
    @commands.check(is_owner)
    async def block_user(self, ctx, user_id: int):
        if user_id in self.bot.blocked_user_ids:
            return await ctx.reply(self.format_response(f"ID {user_id} is already blocked.", lang="ansi"))
        if user_id == ctx.author.id:
            return await ctx.reply(self.format_response("You cannot block yourself!", lang="ansi"))
        self.bot.blocked_user_ids.add(user_id)
        await asyncio.to_thread(
            self.bot.db.collection("blocked_users").document(str(user_id)).set,
            {"blocked_at": firestore.SERVER_TIMESTAMP}
        )
        await ctx.reply(self.format_response(f"Successfully blocked ID {user_id}.", lang="ansi"))


    @commands.command(name="unblock")
    @commands.check(is_owner)
    async def unblock_user(self, ctx, user_id: int):
        if user_id not in self.bot.blocked_user_ids:
            return await ctx.reply(self.format_response(f"ID {user_id} is not in the block list.", lang="ansi"))
        self.bot.blocked_user_ids.remove(user_id)
        await asyncio.to_thread(self.bot.db.collection("blocked_users").document(str(user_id)).delete)
        await ctx.reply(self.format_response(f"Successfully unblocked ID {user_id}.", lang="ansi"))


    @commands.command(name="blocklist")
    @commands.check(is_owner)
    async def block_list(self, ctx):
        if not self.bot.blocked_user_ids:
            return await ctx.reply("The block list is currently empty.")
        msg = "```ansi\n\u001b[1;31m      === BLOCK LIST ===\u001b[0m\n"
        for i, user_id in enumerate(self.bot.blocked_user_ids, 1):
            user = self.bot.get_user(user_id)
            name = user.name if user else "Unknown User"
            msg += f"\u001b[1;34m{i}.\u001b[0m \u001b[1;33m{user_id}\u001b[0m | {name}\n"
        msg += f"\n\u001b[1;37mTotal:\u001b[0m {len(self.bot.blocked_user_ids)} user(s).```"
        await ctx.reply(msg)


    @commands.command(name="server")
    @commands.check(is_owner)
    async def server_info(self, ctx, guild_id: int):
        """Xem thông tin một server mà bot đang ở."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.reply(self.format_response(f"Server ID `{guild_id}` not found (bot may not be in it).", is_error=True))

        owner = guild.owner
        owner_name = owner.name if owner else "Unknown"
        owner_id   = owner.id   if owner else "Unknown"

        # Thời gian tạo server từ Discord snowflake
        created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        msg = (
            f"\x1b[1;34m[Server Info]{C_RESET}\n"
            f" {C_GREEN}Name:{C_RESET}       {guild.name}\n"
            f" {C_GREEN}ID:{C_RESET}         {guild.id}\n"
            f" {C_GREEN}Owner:{C_RESET}      {owner_name}\n"
            f" {C_GREEN}Owner ID:{C_RESET}   {owner_id}\n"
            f" {C_GREEN}Members:{C_RESET}    {guild.member_count}\n"
            f" {C_GREEN}Created:{C_RESET}    {created_at}\n"
            f" {C_GREEN}Channels:{C_RESET}   {len(guild.channels)}\n"
            f" {C_GREEN}Roles:{C_RESET}      {len(guild.roles)}\n"
        )
        await ctx.reply(self.format_response(msg, lang="ansi"))


    @commands.command(name="leave")
    @commands.check(is_owner)
    async def leave_server(self, ctx, guild_id: int, *, message: str = None):
        """Rời khỏi một server, có thể kèm tin nhắn tạm biệt."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.reply(self.format_response(f"Server ID `{guild_id}` not found (bot may not be in it).", is_error=True))

        # Gửi tin nhắn tạm biệt vào system channel hoặc channel đầu tiên có thể gửi được
        farewell = message or "The bot is leaving this server. Goodbye!"
        target_channel = guild.system_channel or next(
            (ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages),
            None
        )
        if target_channel:
            try:
                await target_channel.send(farewell)
            except Exception:
                pass  # Bỏ qua nếu không gửi được

        await guild.leave()
        await ctx.reply(self.format_response(
            f"{C_GREEN}Successfully left server:{C_RESET} {guild.name} (`{guild_id}`)", lang="ansi"
        ))

    @commands.command(name="say", description="Make the bot speak in a channel or send a DM to a specific user")
    @commands.is_owner()
    async def say(self, ctx, target: str, *, message: str = ""):
        """
        Syntax: 
        - Speak in a channel: !say <Channel_ID_or_Tag> <content>
        - DM a user:          !say <User_ID_or_Tag> <content>
        Supports attachments to forward files/images through the bot.
        """
        files = []
        if ctx.message.attachments:
            for att in ctx.message.attachments:
                try:
                    files.append(await att.to_file())
                except Exception as e:
                    return await ctx.reply(f"Error downloading attachment: {e}")

        if not message and not files:
            return await ctx.reply("Please provide a message content or attach a file to send!")
            
        clean_target = target.strip("<@!#>")
        try:
            target_id = int(clean_target)
        except ValueError:
            return await ctx.reply("Invalid target ID! Please enter a valid ID.")
            
        channel = self.bot.get_channel(target_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(target_id)
            except discord.HTTPException:
                channel = None

        if channel:
            if isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                try:
                    await channel.send(content=message if message else None, files=files)
                    return
                except discord.Forbidden:
                    return await ctx.reply(f"Bot lacks permission to send messages in {channel.mention}!")
                except Exception as e:
                    return await ctx.reply(f"An error occurred while sending message to channel: {e}")
            else:
                return await ctx.reply("The selected channel is not a valid text channel!")
                
        user = self.bot.get_user(target_id)
        if not user:
            try:
                user = await self.bot.fetch_user(target_id)
            except discord.HTTPException:
                user = None

        if user:
            try:
                await user.send(content=message if message else None, files=files)
                return
            except discord.Forbidden:
                return await ctx.reply(f"Failed to send DM to {user.name} (They might have closed their DMs or blocked the bot)!")
            except Exception as e:
                return await ctx.reply(f"An error occurred while sending DM to user: {e}")
                
        await ctx.reply("Could not find any channel or user with the provided ID across the bot system!")


async def setup(bot):
    await bot.add_cog(Others(bot))