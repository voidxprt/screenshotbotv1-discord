import os
import io
import json
import uuid
import textwrap
import re
import requests
import emoji
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

import discord
from discord.ext import commands
from discord import app_commands, Activity, ActivityType

# Optional: load .env automatically when present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional for runtime; environment variables still work
    pass

# ---------------- CONFIG ----------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set. Copy .env.example -> .env and add your token.")

CONFIG_FILE = "config.json"
FONTS_DIR = "fonts"
TWEMOJI_DIR = "twemoji"
WORD_LIMIT = 200
MAX_CHARS = 2000  # Discord-like char cap

os.makedirs(TWEMOJI_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)  # ensure fonts dir exists for user to drop files

FONT_PATHS = {
    "regular": os.path.join(FONTS_DIR, "whitneybook.otf"),
    "bold": os.path.join(FONTS_DIR, "whitneysemibold.otf"),
    "italic": os.path.join(FONTS_DIR, "whitneybookitalic.otf")
}

# ---------------- HELPERS ----------------
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Backwards-compat: convert string entries to dict(mode=...)
            for k, v in list(data.items()):
                if isinstance(v, str):
                    data[k] = {"mode": v}
            return data
    except Exception:
        return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def fetch_url_bytes(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None

def fetch_twemoji(char):
    """
    Returns a PIL Image for the emoji (RGBA) or None if not found.
    Caches PNGs under TWEMOJI_DIR by codepoint.
    """
    codepoint = "-".join(f"{ord(c):x}" for c in char)
    local_path = os.path.join(TWEMOJI_DIR, f"{codepoint}.png")
    if os.path.exists(local_path):
        try:
            return Image.open(local_path).convert("RGBA")
        except Exception:
            pass
    url = f"https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/{codepoint}.png"
    b = fetch_url_bytes(url)
    if b:
        try:
            with open(local_path, "wb") as f:
                f.write(b)
            return Image.open(io.BytesIO(b)).convert("RGBA")
        except Exception:
            pass
    return None

def load_font(style="regular", size=22):
    path = FONT_PATHS.get(style, FONT_PATHS["regular"])
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        # Fallback to a default PIL font with approximate metrics
        return ImageFont.load_default()

def circle_crop_image(pil_img, size=(64,64)):
    pil_img = pil_img.convert("RGBA").resize(size)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0,0,size[0],size[1]), fill=255)
    out = Image.new("RGBA", size, (0,0,0,0))
    out.paste(pil_img, (0,0), mask)
    return out

def get_member_role_color(member: discord.Member):
    """
    Return an (r,g,b) tuple for the member's top role color (if present), else None.
    """
    try:
        top = getattr(member, "top_role", None)
        if top and hasattr(top, "color"):
            color = top.color
            # color might be default (0) or a Colour object
            try:
                if color.value != 0:
                    return color.to_rgb()
            except Exception:
                v = getattr(color, "value", 0)
                if v:
                    return ((v >> 16) & 255, (v >> 8) & 255, v & 255)
    except Exception:
        pass
    return None

# ---------------- MENTION PREPROCESS ----------------
def preprocess_mentions(content: str, msg: discord.Message, guild: discord.Guild):
    out = content
    try:
        for role in msg.role_mentions:
            raw = f"<@&{role.id}>"
            replacement = f"{{{{ROLE:{role.id}:{role.name}}}}}"
            out = out.replace(raw, replacement)
    except Exception:
        pass
    try:
        for user in msg.mentions:
            raw1 = f"<@!{user.id}>"
            raw2 = f"<@{user.id}>"
            replacement = f"{{{{USER:{user.id}:{user.display_name}}}}}"
            out = out.replace(raw1, replacement).replace(raw2, replacement)
    except Exception:
        pass
    out = out.replace("@everyone", "{{EVERYONE}}").replace("@here", "{{HERE}}")
    return out

# ---------------- RENDERING ----------------
def _render_line_with_tokens(img, draw, line, x, y, max_width, font, default_color, guild):
    tokens = re.split(r"(\{\{.*?\}\})", line)
    cur_x = x
    for t in tokens:
        if not t:
            continue
        if t.startswith("{{ROLE:"):
            try:
                _, rid, name = t.strip("{}").split(":", 2)
                role = guild.get_role(int(rid))
                color = (88, 101, 242) if (not role or getattr(role.color, "value", 0) == 0) else role.color.to_rgb()
                draw.text((cur_x, y), f"@{name}", font=font, fill=color)
                cur_x += draw.textlength(f"@{name}", font=font)
            except Exception:
                draw.text((cur_x, y), t, font=font, fill=default_color)
                cur_x += draw.textlength(t, font=font)
        elif t.startswith("{{USER:"):
            try:
                _, uid, name = t.strip("{}").split(":", 2)
                draw.text((cur_x, y), f"@{name}", font=font, fill=(88,101,242))
                cur_x += draw.textlength(f"@{name}", font=font)
            except Exception:
                draw.text((cur_x, y), t, font=font, fill=default_color)
                cur_x += draw.textlength(t, font=font)
        elif t == "{{EVERYONE}}":
            draw.text((cur_x, y), "@everyone", font=font, fill=(250,166,26))
            cur_x += draw.textlength("@everyone", font=font)
        elif t == "{{HERE}}":
            draw.text((cur_x, y), "@here", font=font, fill=(250,166,26))
            cur_x += draw.textlength("@here", font=font)
        else:
            # regular text that may contain emoji
            for ch in t:
                # render emoji via twemoji if available
                if ch in emoji.EMOJI_DATA:
                    em_img = fetch_twemoji(ch)
                    if em_img:
                        # size the emoji to font.size if possible
                        try:
                            font_size = getattr(font, "size", 22)
                        except Exception:
                            font_size = 22
                        em_img = em_img.resize((font_size, font_size), Image.LANCZOS)
                        img.paste(em_img, (int(cur_x), int(y)), em_img)
                        cur_x += font_size
                        continue
                draw.text((cur_x, y), ch, font=font, fill=default_color)
                cur_x += draw.textlength(ch, font=font)
    return y + getattr(font, "size", 22) + 6

def draw_wrapped_with_placeholders(img, draw, text, x, y, max_width, font, default_color, guild):
    lines = text.split("\n")
    current_y = y
    for line in lines:
        words = line.split(" ")
        cur_line = ""
        for w in words:
            if draw.textlength(w, font=font) > max_width:
                # break very long word into chunks
                chunk = ""
                for ch in w:
                    if draw.textlength(chunk + ch, font=font) <= max_width:
                        chunk += ch
                    else:
                        current_y = _render_line_with_tokens(img, draw, chunk, x, current_y, max_width, font, default_color, guild)
                        chunk = ch
                if chunk:
                    cur_line = chunk + " "
                else:
                    cur_line = ""
            else:
                test = (cur_line + w + " ").rstrip()
                if draw.textlength(test, font=font) <= max_width:
                    cur_line = (cur_line + w + " ").rstrip() + " "
                else:
                    current_y = _render_line_with_tokens(img, draw, cur_line, x, current_y, max_width, font, default_color, guild)
                    cur_line = w + " "
        if cur_line:
            current_y = _render_line_with_tokens(img, draw, cur_line, x, current_y, max_width, font, default_color, guild)
    return current_y

def render_discord_message(author, avatar_url, content, timestamp, mode, member, guild):
    bg = (54,57,63) if mode=="dark" else (255,255,255)
    text_color = (220,221,222) if mode=="dark" else (0,0,0)
    img = Image.new("RGBA", (800, 400), bg)
    draw = ImageDraw.Draw(img)
    # avatar
    av_bytes = None
    if avatar_url:
        try:
            av_bytes = fetch_url_bytes(avatar_url)
        except Exception:
            av_bytes = None
    if av_bytes:
        try:
            av_img = Image.open(io.BytesIO(av_bytes))
            av_img = circle_crop_image(av_img, (64,64))
            img.paste(av_img, (20,20), av_img)
        except Exception:
            pass
    role_color = get_member_role_color(member) or (255,255,255)
    draw.text((100,20), author, font=load_font("bold", 24), fill=role_color)
    # Format timestamp in a cross-platform way, remove leading zero
    try:
        ts = timestamp if isinstance(timestamp, str) else timestamp.strftime("%I:%M %p").lstrip("0")
    except Exception:
        ts = str(timestamp)
    draw.text((100,50), ts, font=load_font("regular", 18), fill=(150,150,150))
    y = 90
    y = draw_wrapped_with_placeholders(img, draw, content, 100, y, 680, load_font("regular", 22), text_color, guild)
    final = img.crop((0,0,800,y+20))
    path = f"screenshot_{uuid.uuid4().hex}.png"
    final.save(path)
    return path

# ---------------- BOT ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    activity = Activity(type=ActivityType.listening, name="!ss")
    await bot.change_presence(activity=activity)
    try:
        await bot.tree.sync()
    except Exception:
        # non-fatal
        pass
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("✅ Slash commands synced (if possible).")

# ---------- PREFIX COMMAND ----------
@bot.command()
async def ss(ctx):
    # Attempt to delete the command message silently (ignore errors)
    try:
        await ctx.message.delete()
    except Exception:
        pass

    target = ctx.message.reference and ctx.message.reference.resolved
    if not target:
        await ctx.send("❌ You must reply to a message to screenshot it.", delete_after=5)
        return
    if getattr(target.author, "bot", False):
        await ctx.send("😏 Nice try, but you can’t screenshot bot messages.", delete_after=5)
        return
    if len(target.content.split()) > WORD_LIMIT:
        await ctx.send(f"⚠️ Message too long (limit: {WORD_LIMIT} words).", delete_after=5)
        return
    if len(target.content) > MAX_CHARS:
        await ctx.send(f"⚠️ Message too long (limit: {MAX_CHARS} characters).", delete_after=5)
        return

    cfg = load_config()
    guild_cfg = cfg.get(str(ctx.guild.id), {"mode": "light"})
    mode = guild_cfg.get("mode", "light")

    content = preprocess_mentions(target.content, target, ctx.guild)
    # Use UTC-aware formatting (target.created_at is usually aware)
    timestamp = target.created_at.astimezone(timezone.utc).strftime("%I:%M %p").lstrip("0")
    # Resolve avatar URL safely
    avatar_attr = getattr(target.author, "display_avatar", None)
    avatar_url = None
    try:
        avatar_url = avatar_attr.url if avatar_attr else None
    except Exception:
        avatar_url = None

    img_path = render_discord_message(
        target.author.display_name,
        avatar_url,
        content,
        timestamp,
        mode,
        target.author,
        ctx.guild
    )
    try:
        await ctx.send(f"📸 Screenshot generated by {ctx.author.mention}", file=discord.File(img_path))
    finally:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except Exception:
            pass

# ---------- SLASH COMMANDS ----------
@bot.tree.command(name="setup", description="Setup screenshot mode for this server")
@app_commands.describe(mode="Choose light or dark mode")
@app_commands.choices(mode=[
    app_commands.Choice(name="Light Mode", value="light"),
    app_commands.Choice(name="Dark Mode", value="dark")
])
async def setup(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    cfg = load_config()
    cfg[str(interaction.guild.id)] = {"mode": mode.value}
    save_config(cfg)
    await interaction.response.send_message(f"✅ Setup complete! Mode set to **{mode.name}**.", delete_after=2)

@bot.tree.command(name="lightmode", description="Switch screenshots to light mode")
async def lightmode(interaction: discord.Interaction):
    cfg = load_config()
    cfg[str(interaction.guild.id)] = {"mode": "light"}
    save_config(cfg)
    await interaction.response.send_message("☀️ Switched to **light mode** for screenshots.", delete_after=2)

@bot.tree.command(name="darkmode", description="Switch screenshots to dark mode")
async def darkmode(interaction: discord.Interaction):
    cfg = load_config()
    cfg[str(interaction.guild.id)] = {"mode": "dark"}
    save_config(cfg)
    await interaction.response.send_message("🌙 Switched to **dark mode** for screenshots.", delete_after=2)

# Run
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
