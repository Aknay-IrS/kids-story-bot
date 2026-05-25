"""thumbnail_generator.py - AI cartoon thumbnail using Pollinations.ai"""
import logging
import os
import textwrap
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from io import BytesIO
import config

log = logging.getLogger(__name__)
W, H = 1280, 720

def _get_font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()

def generate_ai_background(title, visual_query):
    """Generate cartoon thumbnail background via Pollinations.ai."""
    words = [w for w in title.split() if w.isalpha()][:5]
    short_title = " ".join(words)
    query_clean = visual_query[:30] if visual_query else "fairy tale"
    
    # Keep prompt SHORT to avoid 402 errors
    prompt = f"{query_clean} {short_title} cartoon children illustration colorful magical"
    encoded = urllib.parse.quote(prompt[:200])
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&model=flux&nologo=true&seed=42"
    
    try:
        log.info(f"Generating AI thumbnail: '{prompt[:60]}'")
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        if len(r.content) > 10000:
            img = Image.open(BytesIO(r.content)).convert("RGB").resize((W, H), Image.LANCZOS)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.5)
            log.info("AI thumbnail background ready!")
            return img
    except Exception as e:
        log.warning(f"Pollinations thumbnail failed: {e}")
    
    # Fallback: purple-blue gradient (no numpy needed)
    img = Image.new("RGB", (W, H), (30, 10, 80))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        ratio = y / H
        r_val = int(30 + 50 * ratio)
        g_val = int(10 + 30 * ratio)
        b_val = int(80 + 40 * ratio)
        draw.line([(0, y), (W, y)], fill=(r_val, g_val, b_val))
    return img

def generate_thumbnail(title, hook, output_path, visual_query="fairy tale", moral=""):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    bg = generate_ai_background(title, visual_query)
    draw = ImageDraw.Draw(bg)
    
    # Dark overlay at top
    for y in range(220):
        alpha = int(0.75 * (1 - y/220) * 255)
        r, g, b = bg.getpixel((W//2, y))
        nr = max(0, r - int(alpha * r / 255))
        ng = max(0, g - int(alpha * g / 255))
        nb = max(0, b - int(alpha * b / 255))
        draw.line([(0,y),(W,y)], fill=(nr,ng,nb))
    
    # Title text
    clean = ''.join(c if ord(c) < 128 else ' ' for c in title).strip()
    parts = clean.split('|')
    main_title = parts[0].strip()[:35]
    lines = textwrap.wrap(main_title, width=18)[:2]
    
    title_font = _get_font(88)
    y = 25
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        # Glow
        for offset in [5, 3]:
            draw.text((x-offset, y-offset), line, font=title_font, fill=(255,200,0))
            draw.text((x+offset, y+offset), line, font=title_font, fill=(255,150,0))
        # Border
        for dx, dy in [(-3,0),(3,0),(0,-3),(0,3)]:
            draw.text((x+dx, y+dy), line, font=title_font, fill=(0,0,0))
        # Main
        draw.text((x, y), line, font=title_font, fill=(255,255,255))
        y += (bbox[3]-bbox[1]) + 6
    
    # Bottom orange banner
    banner_y = H - 105
    draw.rectangle([(0, banner_y), (W, H)], fill=(220, 100, 0))
    draw.rectangle([(0, banner_y), (W, banner_y+4)], fill=(255,180,0))
    
    sub_font = _get_font(48)
    sub_text = "BEDTIME STORY FOR KIDS"
    bbox = draw.textbbox((0,0), sub_text, font=sub_font)
    sx = (W - (bbox[2]-bbox[0])) // 2
    draw.text((sx+2, banner_y+15), sub_text, font=sub_font, fill=(0,0,0))
    draw.text((sx, banner_y+13), sub_text, font=sub_font, fill=(255,255,255))
    
    moral_font = _get_font(36)
    moral_clean = ''.join(c if ord(c) < 128 else ' ' for c in (moral or hook)).strip()[:55]
    bbox2 = draw.textbbox((0,0), moral_clean, font=moral_font)
    mx = (W - (bbox2[2]-bbox2[0])) // 2
    draw.text((mx, banner_y+65), moral_clean, font=moral_font, fill=(255,230,150))
    
    bg.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path
