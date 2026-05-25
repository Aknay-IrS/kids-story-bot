"""
thumbnail_generator.py - Eye-catching AI cartoon thumbnails using Pollinations.ai
YouTube thumbnail: 1280x720
"""
import logging
import os
import textwrap
import urllib.parse
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO
import config

log = logging.getLogger(__name__)
W, H = 1280, 720

def _get_font(size):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()

def generate_ai_background(title, visual_query, story_type="fairy tale"):
    """Generate a stunning cartoon thumbnail background using Pollinations.ai."""
    # Build an eye-catching prompt for thumbnail
    clean_title = ' '.join(w for w in title.split() if w.isalpha())[:40]
    
    prompt = (
        f"{visual_query} scene, {clean_title}, "
        f"children book illustration thumbnail, "
        f"extremely colorful and vibrant, magical fairy tale art, "
        f"cute cartoon characters, glowing effects, sparkles, "
        f"professional YouTube thumbnail style, "
        f"high contrast bright colors, enchanting atmosphere, "
        f"wide angle establishing shot, "
        f"no text, no letters, illustration only"
    )
    
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&model=flux&nologo=true&enhance=true&seed=777"
    
    try:
        log.info("Generating AI cartoon thumbnail background...")
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        if len(r.content) > 10000:
            img = Image.open(BytesIO(r.content)).convert("RGB")
            img = img.resize((W, H), Image.LANCZOS)
            # Enhance colors to make it more vibrant
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.4)
            enhancer2 = ImageEnhance.Contrast(img)
            img = enhancer2.enhance(1.1)
            log.info("AI thumbnail background generated!")
            return img
    except Exception as e:
        log.warning(f"Pollinations thumbnail failed: {e}")
    return None

def add_text_overlays(img, title, moral):
    """Add professional title text with glowing effect."""
    draw = ImageDraw.Draw(img)
    
    # Clean title for display
    clean = ''.join(c if ord(c) < 128 else ' ' for c in title).strip()
    # Remove emoji and extra parts
    parts = clean.split('|')
    main_title = parts[0].strip()[:40]
    
    # Wrap title into max 2 lines
    lines = textwrap.wrap(main_title, width=18)[:2]
    
    title_font = _get_font(96)
    subtitle_font = _get_font(52)
    moral_font = _get_font(42)
    
    # Dark gradient overlay at top for title readability
    overlay = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(200):
        alpha = int(180 * (1 - y/200))
        overlay_draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    img.paste(Image.fromarray(
        __import__('numpy').array(overlay)[:,:,:3], 'RGB'
    ), (0, 0), overlay)
    
    # Draw title lines with glow effect
    y = 30
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        
        # Glow layers (yellow/orange)
        for offset in [6, 4, 2]:
            draw.text((x-offset, y-offset), line, font=title_font, fill=(255, 200, 0, 180))
            draw.text((x+offset, y+offset), line, font=title_font, fill=(255, 150, 0, 180))
        
        # Black border
        for dx, dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,-2),(-2,2),(2,2)]:
            draw.text((x+dx, y+dy), line, font=title_font, fill=(0, 0, 0))
        
        # White main text
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255))
        y += bbox[3] - bbox[1] + 8
    
    # Bottom banner with moral/tagline
    banner_h = 110
    banner_y = H - banner_h
    
    # Gradient banner
    banner = Image.new("RGBA", (W, banner_h), (0, 0, 0, 0))
    banner_draw = ImageDraw.Draw(banner)
    colors = [(255, 100, 0), (255, 180, 0)]  # orange to yellow gradient
    for x in range(W):
        ratio = x / W
        r_val = int(colors[0][0] * (1-ratio) + colors[1][0] * ratio)
        g_val = int(colors[0][1] * (1-ratio) + colors[1][1] * ratio)
        b_val = int(colors[0][2] * (1-ratio) + colors[1][2] * ratio)
        banner_draw.line([(x, 0), (x, banner_h)], fill=(r_val, g_val, b_val, 220))
    
    img.paste(Image.fromarray(
        __import__('numpy').array(banner)[:,:,:3], 'RGB'
    ), (0, banner_y), banner)
    
    # Story type badge
    badge_text = "BEDTIME STORY"
    bbox = draw.textbbox((0, 0), badge_text, font=subtitle_font)
    bw = bbox[2] - bbox[0]
    bx = (W - bw) // 2
    draw.text((bx+2, banner_y+12), badge_text, font=subtitle_font, fill=(0, 0, 0))
    draw.text((bx, banner_y+10), badge_text, font=subtitle_font, fill=(255, 255, 255))
    
    # Moral text
    clean_moral = ''.join(c if ord(c) < 128 else ' ' for c in moral).strip()[:55]
    bbox2 = draw.textbbox((0, 0), clean_moral, font=moral_font)
    mx = (W - (bbox2[2]-bbox2[0])) // 2
    draw.text((mx+1, banner_y+62), clean_moral, font=moral_font, fill=(0, 0, 0))
    draw.text((mx, banner_y+60), clean_moral, font=moral_font, fill=(50, 0, 0))
    
    # Star decorations
    star_font = _get_font(60)
    for pos, star in [(20, banner_y+20, "⭐"), (W-80, banner_y+20, "⭐")]:
        pass  # skip emoji - ASCII only
    
    # Corner sparkle dots
    for cx, cy, col in [(30,30,(255,255,0)), (W-30,30,(255,200,0)),
                         (50,60,(255,255,255)), (W-50,60,(255,255,255))]:
        draw.ellipse([(cx-8,cy-8),(cx+8,cy+8)], fill=col)
        draw.ellipse([(cx-4,cy-4),(cx+4,cy+4)], fill=(255,255,255))
    
    return img

def generate_thumbnail(title, hook, output_path, visual_query="fairy tale", moral=""):
    """Generate a stunning AI cartoon thumbnail."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # Generate AI cartoon background
    bg = generate_ai_background(title, visual_query)
    
    if bg is None:
        # Fallback: vibrant gradient background
        import numpy as np
        bg_arr = np.zeros((H, W, 3), dtype=np.uint8)
        for y in range(H):
            ratio = y / H
            bg_arr[y, :, 0] = int(30 * (1-ratio) + 80 * ratio)   # R
            bg_arr[y, :, 1] = int(10 * (1-ratio) + 20 * ratio)   # G
            bg_arr[y, :, 2] = int(100 * (1-ratio) + 60 * ratio)  # B
        bg = Image.fromarray(bg_arr, 'RGB')
    
    # Add text overlays
    bg = add_text_overlays(bg, title, moral or hook[:55])
    
    bg.save(output_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {output_path}")
    return output_path
