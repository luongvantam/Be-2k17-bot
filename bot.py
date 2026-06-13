# -*- coding: utf-8 -*-
from flask import Flask
import threading
import os
import datetime
import difflib
import aiohttp
import discord
import firebase_admin
import asyncio
import random
from firebase_admin import credentials, firestore
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Initialize Firebase (Safe check to avoid re-initialization)
if not firebase_admin._apps:
    # Kiểm tra xem có đang chạy trên môi trường Cloud (Render) không
    firebase_creds_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    
    if firebase_creds_json:
        # Nếu có biến môi trường, parse chuỗi JSON trực tiếp
        import json
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
    else:
        # Fallback chạy ở máy cá nhân (Local) nếu có file sẵn
        if os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
        else:
            print("❌ Error: Firebase credentials not found neither in Env nor in File.")
            import sys
            sys.exit(1)
            
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Configure Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Be2k17(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vietnamese_words = set() # Dùng để check từ tồn tại
        self.word_list = []          # Dùng để bốc random nhanh
        self.word_map = {}           # {tiếng_đầu: set(các_từ)} để tìm từ nối
        self.db = db
        self.start_time = None
        self.blocked_user_ids = set()

    async def load_blacklist(self):
        """Fetch blocked user IDs from Firebase"""
        try:
            docs = await asyncio.to_thread(lambda: list(self.db.collection("blocked_users").stream()))
            self.blocked_user_ids = {int(doc.id) for doc in docs}
            print(f"✅ Loaded {len(self.blocked_user_ids)} users into blacklist.")
        except Exception as e:
            print(f"❌ Error loading blacklist: {e}")

    async def download_dict(self):
        """Download the Vietnamese dictionary from GitHub"""
        url = "https://raw.githubusercontent.com/luongvantam/Vietnamese-Word-Chain-Dict/refs/heads/main/tudien.txt"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        text = await response.text()
                        self.vietnamese_words = set()
                        self.word_list = []
                        self.word_map = {}
                        
                        for line in text.splitlines():
                            word = line.strip().lower()
                            parts = word.split()
                            if len(parts) == 2:
                                self.vietnamese_words.add(word)
                                self.word_list.append(word)
                                first = parts[0]
                                if first not in self.word_map:
                                    self.word_map[first] = set()
                                self.word_map[first].add(word)
                        
                        print(f"✅ Dictionary loaded: {len(self.word_list)} words from GitHub.")
        except Exception as e:
            print(f"❌ Error downloading dictionary: {e}")

    def get_random_word(self):
        """Bốc ngẫu nhiên một từ từ GitHub và kiểm tra xem có nối tiếp được không"""
        if not self.word_list:
            return None
        
        # Loop bốc cho đến khi tìm được từ có thể nối tiếp
        for _ in range(500): # Thử tối đa 500 lần
            word = random.choice(self.word_list)
            last_part = word.split()[-1]
            
            # Kiểm tra xem có từ nào bắt đầu bằng tiếng cuối của từ này không
            if last_part in self.word_map and len(self.word_map[last_part]) > 0:
                return word
                
        # Fallback (hầu như không xảy ra)
        return random.choice(self.word_list)

    async def setup_hook(self):
        # 1. Load Data
        await self.download_dict()
        await self.load_blacklist()
        
        # 2. Load Extensions (Cogs)
        cogs_dir = "./cogs"
        if os.path.isdir(cogs_dir):
            for filename in os.listdir(cogs_dir):
                if filename.endswith(".py"):
                    try:
                        await self.load_extension(f"cogs.{filename[:-3]}")
                        print(f"✅ Loaded extension: {filename}")
                    except Exception as e:
                        print(f"❌ Failed to load {filename}: {e}")
        
        # 3. Sync Slash Commands
        await self.tree.sync()

bot = Be2k17(command_prefix="o!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    if not bot.start_time:
        bot.start_time = datetime.datetime.now(datetime.UTC)
    print(f"🚀 Bot logged in as {bot.user}")
    print(f"⏰ Start time: {bot.start_time}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.HTTPException):
        if getattr(error, 'status', 0) == 429:
            print(f"🛑 Rate Limited! Retry after {getattr(error, 'retry_after', 60)}s.")
            return

    if isinstance(error, commands.CommandOnCooldown):
        try: await ctx.reply(f"⏱️ Cooldown: {error.retry_after:.1f}s", delete_after=5)
        except: pass
        return

    if isinstance(error, (commands.CheckFailure, discord.Forbidden)):
        return

    if isinstance(error, commands.CommandNotFound):
        command_name = ctx.message.content.split()[0].strip()
        all_commands = [c.name for c in bot.commands]
        cmd_input = command_name.lstrip("o!").lower()
        suggestions = difflib.get_close_matches(cmd_input, all_commands, n=3, cutoff=0.6)
        
        msg = f"```ansi\n\u001b[1;31mError:\u001b[0m Command '\u001b[1;33m{command_name}\u001b[0m' not found.\n"
        if suggestions:
            msg += f"\n\u001b[1;37mDid you mean:\u001b[0m\n" + "\n".join(f"    \u001b[36m{s}\u001b[0m" for s in suggestions)
        msg += f"\n```"
        try: await ctx.reply(msg, delete_after=10)
        except: pass
    else:
        print(f"❌ System Error: {error}")

@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.author.id in bot.blocked_user_ids: return
    await bot.process_commands(message)

@bot.command()
@commands.is_owner()
async def reload_cogs(ctx):
    """Developer command to hot-reload all extensions"""
    cogs_dir = "./cogs"
    success, failed = [], []
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            try:
                await bot.reload_extension(f"cogs.{filename[:-3]}")
                success.append(filename)
            except Exception as e: failed.append(f"{filename} ({e})")
    
    msg = f"✅ Reloaded: {', '.join(success)}"
    if failed: msg += f"\n❌ Failed: {', '.join(failed)}"
    await ctx.reply(msg)
    
# ===== Web Server (for Railway/Render) =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Be 2k17 Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)