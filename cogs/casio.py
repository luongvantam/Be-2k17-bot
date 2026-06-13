# -*- coding: utf-8 -*-
from discord.ext import commands
import discord
import subprocess
import os, re

os.environ["PYTHONIOENCODING"] = "utf-8"

# ANSI Color Codes
C_RESET  = "\x1b[0m"
C_GREEN  = "\x1b[1;32m"
C_RED    = "\x1b[1;31m"
C_YELLOW = "\x1b[1;33m"
C_WHITE  = "\x1b[1;37m"
C_CYAN   = "\x1b[1;36m"


class Casio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    def format_hex_with_spaces(self, hex_string: str) -> str:
        return ' '.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))

    def cleanup_files(self, *files):
        for f in files:
            if f and os.path.exists(f):
                os.remove(f)

    def strip_codeblock(self, text: str) -> str:
        """Loại bỏ Markdown code block nếu có."""
        s = text.strip("`\"' \n")
        if s.startswith("```") and s.endswith("```"):
            lines = s.strip("`").splitlines()
            if len(lines) > 1:
                lines = lines[1:]
            s = "\n".join(lines).strip()
        return s

    def run_pixel(self, cmd: str, *args):
        return subprocess.run(
            ["python", "./commands/pixel_art.py", cmd, *args],
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="ignore"
        )

    def run_script(self, *cmd_args, shell: bool = False, stdin: str = None) -> subprocess.CompletedProcess:
        """Chạy subprocess với encoding chuẩn. Truyền stdin nếu có."""
        return subprocess.run(
            cmd_args if not shell else " ".join(cmd_args),
            input=stdin,
            capture_output=True, text=True, check=True,
            encoding="utf-8", errors="ignore", shell=shell
        )

    async def send_output(self, ctx, output: str, file_name: str = "output.txt",
                          lang: str = "ansi", extra_file: discord.File = None):
        """Gửi output; nếu quá dài thì đính kèm file."""
        if len(output) > 1900:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(output)
            files = [discord.File(file_name)]
            if extra_file:
                files.insert(0, extra_file)
            await ctx.reply(files=files)
            os.remove(file_name)
        else:
            kwargs = {"file": extra_file} if extra_file else {}
            await ctx.reply(self.format_response(output, lang=lang), **kwargs)

    async def check_send_permission(self, ctx) -> bool:
        if not ctx.channel.permissions_for(ctx.me).send_messages:
            await ctx.author.reply(
                self.format_response("The bot does not have permission to send messages in this channel.", is_error=True)
            )
            return False
        return True

    async def read_attachment_text(self, ctx, att: discord.Attachment,
                                   allowed_exts: tuple = None) -> str | None:
        """Đọc nội dung file đính kèm dạng UTF-8. Trả về None nếu lỗi."""
        if allowed_exts and not any(att.filename.lower().endswith(e) for e in allowed_exts):
            await ctx.reply(self.format_response(
                f"Only {', '.join(allowed_exts)} files are supported.", is_error=True
            ))
            return None
        try:
            return (await att.read()).decode("utf-8")
        except Exception as e:
            await ctx.reply(self.format_response(f"Failed to read the uploaded file: {e}", is_error=True))
            return None

    # ──────────────────────────────────────────────
    # Commands
    # ──────────────────────────────────────────────

    @commands.command(name="p2h")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def p2h_command(self, ctx, *, args: str = None):
        if not ctx.message.attachments:
            return await ctx.reply(self.format_response("Please attach an image file.", is_error=True))
            
        size = "192x63"
        if args and "x" in args.split()[0]:
            size = args.split()[0]

        att = ctx.message.attachments[0]
        if not att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            return await ctx.reply(self.format_response("Invalid image format.", is_error=True))

        inp = f"inp_{ctx.author.id}.tmp"
        out = f"out_{ctx.author.id}.png"
        hex_file = None

        try:
            await att.save(inp)
            res = self.run_pixel("p2h", size, inp, out)

            m = re.search(r"HEX_DATA_NEW:(.*)", res.stdout)
            if not m:
                raise Exception(f"Pixel script failed: {res.stderr or 'HEX_DATA_NEW not found'}")

            hex_fmt = self.format_hex_with_spaces(m.group(1).strip())

            if len(hex_fmt) > 1900:
                hex_file = f"hex_{ctx.author.id}.txt"
                with open(hex_file, "w", encoding="utf-8") as f:
                    f.write(hex_fmt)
                await ctx.reply(files=[discord.File(out), discord.File(hex_file)])
            else:
                await ctx.reply(file=discord.File(out), content=f"```{hex_fmt}```")

        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(
                f"Subprocess Error (p2h): {e.stderr.strip() if e.stderr else 'Unknown error'}", is_error=True
            ))
        except Exception as e:
            await ctx.reply(self.format_response(f"Processing Error (p2h): {e}", is_error=True))
        finally:
            self.cleanup_files(inp, out, hex_file)


    @commands.command(name="h2p")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def h2p_command(self, ctx, *, args: str = None):
        out  = f"out_{ctx.author.id}.png"
        temp = None
        
        size = "192x63"
        hex_input = None

        if args:
            parts = args.split(maxsplit=1)
            # Nếu cụm đầu tiên chữa 'x' (vd: 120x64), thì nó là kích thước
            if "x" in parts[0] and len(parts[0].split("x")) == 2:
                size = parts[0]
                hex_input = parts[1] if len(parts) > 1 else None
            else:
                hex_input = args

        if ctx.message.attachments:
            temp = f"hex_{ctx.author.id}.tmp"
            try:
                await ctx.message.attachments[0].save(temp)
                if os.path.getsize(temp) > 5 * 1024 * 1024:
                    raise Exception("File too large (>5MB)")
                hex_input = open(temp, 'r', encoding='utf-8').read()
            except Exception as e:
                return await ctx.reply(self.format_response(f"Error reading file: {e}", is_error=True))
        elif not hex_input:
            return await ctx.reply(self.format_response("Provide hex string or attach file.", is_error=True))

        hex_clean = "".join(c for c in hex_input.lower() if c in "0123456789abcdef")
        if not hex_clean:
            return await ctx.reply(self.format_response("Empty hex string after cleanup.", is_error=True))
        if len(hex_clean) % 2:
            return await ctx.reply(self.format_response("Odd hex length.", is_error=True))

        try:
            res = self.run_pixel("h2p", size, hex_clean, out)
            if res.stderr:
                raise Exception(res.stderr)
            await ctx.reply(
                self.format_response(f"{C_GREEN}Successfully generated image from hex.{C_RESET}", lang="ansi"),
                file=discord.File(out)
            )
        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(
                f"Subprocess Error (h2p): {e.stderr.strip() if e.stderr else 'Unknown error'}", is_error=True
            ))
        except Exception as e:
            await ctx.reply(self.format_response(f"Processing Error (h2p): {e}", is_error=True))
        finally:
            self.cleanup_files(out, temp)


    @commands.command(name="conv_hex")
    async def conv_hex_command(self, ctx, *, hex_input: str = None):
        if not hex_input and not ctx.message.attachments:
            return await ctx.reply(self.format_response(
                f"{C_YELLOW}Usage:{C_RESET} o!conv_hex <hex string or .txt file>", lang="ansi"
            ))

        if ctx.message.attachments:
            hex_input = await self.read_attachment_text(ctx, ctx.message.attachments[0])
            if hex_input is None:
                return

        s = self.strip_codeblock(hex_input).replace("\n", " ").strip()
        try:
            result = self.run_script("python", "./commands/trans_hex.py", s)
            out = result.stdout.strip() or "No output."
            await self.send_output(ctx, f"{C_GREEN}{out}{C_RESET}")
        except FileNotFoundError:
            await ctx.reply(self.format_response("conv_hex script not found.", is_error=True))
        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(
                f"conv_hex error: {e.stderr.strip() if e.stderr else 'Unknown error'}", is_error=True
            ))
        except Exception as e:
            await ctx.reply(self.format_response(e, is_error=True))


    @commands.command(name="hex_split")
    async def hex_split_command(self, ctx, *, hex_input: str = None):
        if not hex_input and not ctx.message.attachments:
            return await ctx.reply(self.format_response(
                f"{C_YELLOW}Usage:{C_RESET} o!hex_split <hex string or .txt file>", lang="ansi"
            ))

        if ctx.message.attachments:
            hex_input = await self.read_attachment_text(ctx, ctx.message.attachments[0])
            if hex_input is None:
                return

        s = self.strip_codeblock(hex_input).replace("\n", " ").strip()
        try:
            result = self.run_script("python", "./commands/hexsplit.py", s)
            out = result.stdout.strip() or "No output."
            await self.send_output(ctx, f"{C_RESET}{out}")
        except FileNotFoundError:
            await ctx.reply(self.format_response("hex_split script not found.", is_error=True))
        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(
                f"hex_split error: {e.stderr.strip() if e.stderr else 'Unknown error'}", is_error=True
            ))
        except Exception as e:
            await ctx.reply(self.format_response(e, is_error=True))


    @commands.command(name="decomp")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def decompile(self, ctx, *, hex_input: str = None):
        if not await self.check_send_permission(ctx):
            return

        if ctx.message.attachments:
            hex_input = await self.read_attachment_text(ctx, ctx.message.attachments[0], (".txt",))
            if hex_input is None:
                return
        elif hex_input is not None:
            hex_input = self.strip_codeblock(hex_input)
        else:
            return await ctx.reply(self.format_response(
                f"{C_YELLOW}Usage:{C_RESET} Please provide a HEX string or upload a .txt file.", lang="ansi"
            ))

        try:
            result = self.run_script("python", "./commands/decomp_.py", stdin=hex_input)
            output = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(f"Error from decompiler: {(e.stderr or str(e)).strip()}", is_error=True))
            return
        except FileNotFoundError:
            await ctx.reply(self.format_response("Decompiler script was not found.", is_error=True))
            return
        except Exception as e:
            await ctx.reply(self.format_response(f"Unknown error: {e}", is_error=True))
            return

        if not output:
            return await ctx.reply(self.format_response(
                "Decompiler ran but produced an empty output.", is_error=True
            ))
        await self.send_output(ctx, output, lang="")


    @commands.command(name="comp")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def compile(self, ctx, *, hex_input: str = None):
        if not await self.check_send_permission(ctx):
            return

        if ctx.message.attachments:
            hex_input = await self.read_attachment_text(ctx, ctx.message.attachments[0], (".txt", ".rsc"))
            if hex_input is None:
                return
        elif hex_input is not None:
            hex_input = self.strip_codeblock(hex_input)
        else:
            return await ctx.reply(self.format_response(
                f"{C_YELLOW}Usage:{C_RESET} Please provide a resource script or upload a .txt/.rsc file.", lang="ansi"
            ))

        try:
            result = self.run_script(
                "python", "./commands/compiler_.py", "-f", "hex", "commands/580vnx",
                shell=True, stdin=hex_input
            )
            output = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(f"Error from compiler: {(e.stderr or str(e)).strip()}", is_error=True))
            return
        except FileNotFoundError:
            await ctx.reply(self.format_response("Compiler script was not found.", is_error=True))
            return
        except Exception as e:
            await ctx.reply(self.format_response(f"Unknown error: {e}", is_error=True))
            return

        if not output:
            return await ctx.reply(self.format_response(
                "Compiler ran but produced an empty output.", is_error=True
            ))
        await self.send_output(ctx, output, lang="")


    async def _translate_command(self, ctx, src: str, dst: str, input_text: str):
        """Logic chung cho vnx2cnx và cnx2vnx."""
        if not await self.check_send_permission(ctx):
            return
        input_text = self.strip_codeblock(input_text)
        try:
            result = self.run_script("python", "./commands/trans_rop.py", src, dst, input_text)
            output = result.stdout.strip()
            if not output:
                await ctx.reply(self.format_response("Translator ran but produced an empty output.", is_error=True))
            else:
                await self.send_output(ctx, output, file_name=f"tmp_{ctx.author.id}.txt")
        except FileNotFoundError:
            await ctx.reply(self.format_response("Translator script not found.", is_error=True))
        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(
                f"Error from translator: {e.stderr.strip() if e.stderr else 'Unknown error'}", is_error=True
            ))
        except Exception as e:
            await ctx.reply(self.format_response(f"An unknown error occurred: {e}", is_error=True))

    @commands.command(name="vnx2cnx")
    async def vnx2cnx_command(self, ctx, *, input_text: str):
        await self._translate_command(ctx, "fx580vnx", "fx991cnx", input_text)

    @commands.command(name="cnx2vnx")
    async def cnx2vnx_command(self, ctx, *, input_text: str):
        await self._translate_command(ctx, "fx991cnx", "fx580vnx", input_text)


    @commands.command(name="find_gadget")
    async def find_gadget(self, ctx, *, block: str):
        if not await self.check_send_permission(ctx):
            return

        # 1. Loại bỏ markdown code blocks
        s = self.strip_codeblock(block)
        # 2. Thay thế xuống dòng băng dấu chấm phẩy để script finder_gadget nhận dạng đúng
        s = s.replace("\n", ";").strip()
        
        try:
            # Chạy script tìm kiếm
            result = self.run_script("python", "./commands/finder_gadget.py", "./commands/data/fx580vnx.txt", s)
            out = result.stdout.strip()
            if not out or "[-] Not found" in out:
                return await ctx.reply(self.format_response("[-] No gadgets found for this pattern.", lang="ansi"))
            await self.send_output(ctx, out, file_name="gadgets.txt")
        except subprocess.CalledProcessError as e:
            await ctx.reply(self.format_response(
                f"Error: {e.stderr.strip() if e.stderr else 'Unknown error'}", is_error=True
            ))
        except Exception as e:
            await ctx.reply(self.format_response(f"Unknown error: {e}", is_error=True))


async def setup(bot):
    await bot.add_cog(Casio(bot))