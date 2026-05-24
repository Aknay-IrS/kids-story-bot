"""thumbnail_generator.py - YouTube thumbnail 1280x720"""
import logging
import os
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont
import config

log = logging.getLogger(__name__)
W, H = 1280, 720

def _get_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def _get_bg(query):
    try:
        key = os.environ.get("PIXABAY_API_KEY", config.PIXABAY_API_KEY)
        r = requests.get("https://pixabay.com/api/", params={"key": key, "q": query,
            "image_type": "photo", "orientation": "horizontal", "per_page": 3,
            "safesearch": "true"}, timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            from io import BytesIO
            img_r = requests.get(hits[0]["webformatURL"], timeout=15)
            return Image.open(BytesIO(img_r.content)).convert("RGB")
    except Exception as e:
        log.warning(f"BG image failed: {e}")
    return None

def generate_thumbnail(title, hook, output_path, visual_query="fairy tale"):
    bg = _get_bg(visual_query)
    if bg:
        bg = bg.resize((W, H), Image.LANCZOS)
    else:
        bg = Image.new("RGB", (W, H), (30, 10, 60))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    bg = bg.convert("RGBA")
    bg.paste(overlay, (0, 0), overlay)
    bg = bg.convert("RGB")
    draw = ImageDraw.Draw(bg)

    # Title
    clean = ''.join(c if ord(c) < 128 else ' ' for c in title).strip()[:50]
    lines = textwrap.wrap(clean, width=22)
    font = _get_font(72)
    y = 80
    for line in lines[:3]:
        bbox = draw.textbbox((0,0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (W - w) // 2
        draw.text((x+3, y+3), line, font=font, fill=(0,0,0))
        draw.text((x, y), line, font=font, fill=(255, 220, 50))
        y += bbox[3] - bbox[1] + 8

    # Gold banner
    banner_y = H - 120
    draw.rectangle([(0, banner_y), (W, H)], fill=(255, 193, 7))
    hook_font = _get_font(42)
    hook_clean = ''.join(c if ord(c) < 128 else ' ' for c in hook).strip()[:55]
    bbox = draw.textbbox((0,0), hook_clean, font=hook_font)
    x = (W - (bbox[2]-bbox[0])) // 2
    draw.text((x, banner_y + 35), hook_clean, font=hook_font, fill=(20, 20, 20))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    bg.save(output_path, "JPEG", quality=92)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path
