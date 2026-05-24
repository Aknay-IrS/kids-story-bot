"""
video_assembler.py - Illustrated slideshow with Ken Burns + crossfades
Always finds images - never uses solid color background
"""
import logging
import os
import random
import subprocess
import requests
import config

log = logging.getLogger(__name__)
W = config.VIDEO_WIDTH   # 1920
H = config.VIDEO_HEIGHT  # 1080

PIXABAY_KEY = "55951851-7282cb13bfe0431ff6400f2a0"

# Large pool of guaranteed-to-work fallback queries
GUARANTEED_QUERIES = [
    "forest nature", "castle medieval", "fairy tale", "garden flowers",
    "animals wildlife", "sunset landscape", "mountains river", "ocean beach",
    "children playing", "meadow grass", "autumn leaves", "village countryside",
    "birds trees", "lake reflection", "colorful flowers", "green nature",
    "countryside road", "waterfall river", "butterfly garden", "starry night",
]

def get_pixabay_key():
    return os.environ.get("PIXABAY_API_KEY") or config.PIXABAY_API_KEY or PIXABAY_KEY

def download_image(query, output_path, key):
    """Download one image for a query. Returns True if successful."""
    try:
        r = requests.get("https://pixabay.com/api/", params={
            "key": key, "q": query, "image_type": "photo",
            "orientation": "horizontal", "per_page": 10,
            "safesearch": "true", "order": "popular", "min_width": 800
        }, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            return False
        hit = random.choice(hits[:5])
        img_url = hit.get("largeImageURL") or hit.get("webformatURL")
        if not img_url:
            return False
        img_r = requests.get(img_url, timeout=30)
        img_r.raise_for_status()
        if len(img_r.content) < 5000:  # too small = error page
            return False
        with open(output_path, 'wb') as f:
            f.write(img_r.content)
        return True
    except Exception as e:
        log.debug(f"Download failed for '{query}': {e}")
        return False

def download_scene_images(visual_query, chapters, output_dir, num_images=8):
    """Download images for each scene. Keeps trying until all images found."""
    os.makedirs(output_dir, exist_ok=True)
    key = get_pixabay_key()
    image_paths = []

    # Build query list: story-specific + chapter titles + guaranteed fallbacks
    queries = [visual_query]
    for ch in chapters:
        title = ch.get("title", "")
        clean = " ".join(w for w in title.split() if w.isalpha())[:30]
        if clean:
            queries.append(clean)
    queries.extend(GUARANTEED_QUERIES)  # always enough fallbacks

    log.info(f"Downloading {num_images} scene images (key: {key[:8]}...)...")

    downloaded = 0
    query_idx = 0

    while downloaded < num_images and query_idx < len(queries):
        img_path = os.path.join(output_dir, f"scene_{downloaded:02d}.jpg")
        q = queries[query_idx]
        query_idx += 1

        success = download_image(q, img_path, key)
        if success:
            image_paths.append(img_path)
            downloaded += 1
            log.info(f"✅ Scene {downloaded}/{num_images}: '{q}'")
        else:
            log.debug(f"❌ No result for '{q}', trying next...")

    if not image_paths:
        # Last resort: try very generic queries one more time
        for q in ["nature", "forest", "sky", "water", "flowers"]:
            img_path = os.path.join(output_dir, f"scene_last_{q}.jpg")
            if download_image(q, img_path, key):
                image_paths.append(img_path)
                log.info(f"✅ Last resort image found: '{q}'")
            if len(image_paths) >= 3:
                break

    log.info(f"Total images downloaded: {len(image_paths)}")
    return image_paths

def get_audio_duration_ffprobe(audio_path):
    try:
        r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                           '-of','default=noprint_wrappers=1:nokey=1', audio_path],
                          capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        try:
            from mutagen.mp3 import MP3
            return MP3(audio_path).info.length
        except Exception:
            return 540.0

def create_ken_burns_clip(image_path, duration, output_path, index):
    """Apply Ken Burns effect. Multiple motion styles for variety."""
    motions = [
        f"scale=iw*2:ih*2,zoompan=z='min(zoom+0.0008,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        f"scale=iw*2:ih*2,zoompan=z='1.2':x='if(lte(on,1),0,min(x+2,iw))':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        f"scale=iw*2:ih*2,zoompan=z='1.2':x='if(lte(on,1),iw,max(x-2,0))':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        f"scale=iw*2:ih*2,zoompan=z='if(lte(on,1),1.3,max(zoom-0.0008,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        f"scale=iw*2:ih*2,zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),ih,max(y-2,0))':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
    ]
    vf = motions[index % len(motions)]
    cmd = ['ffmpeg','-y','-loop','1','-i', image_path,
           '-t', str(duration + 1),
           '-vf', vf,
           '-c:v','libx264','-preset','fast','-crf','23',
           '-pix_fmt','yuv420p','-an', output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        log.warning(f"Ken Burns failed scene {index}, using static zoom")
        cmd2 = ['ffmpeg','-y','-loop','1','-i', image_path,
                '-t', str(duration + 1),
                '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}',
                '-c:v','libx264','-preset','fast','-crf','23',
                '-pix_fmt','yuv420p','-an', output_path]
        result2 = subprocess.run(cmd2, capture_output=True, timeout=300)
        if result2.returncode != 0:
            return None
    return output_path

def crossfade_clips(clip_paths, output_path, fade_duration=1.5):
    """Concatenate clips with crossfade transitions."""
    if len(clip_paths) == 1:
        import shutil
        shutil.copy(clip_paths[0], output_path)
        return output_path

    durations = []
    for cp in clip_paths:
        try:
            r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                               '-of','default=noprint_wrappers=1:nokey=1', cp],
                              capture_output=True, text=True, timeout=15)
            durations.append(float(r.stdout.strip()))
        except:
            durations.append(15.0)

    inputs = []
    for cp in clip_paths:
        inputs.extend(['-i', cp])

    transitions = ['fade','dissolve','fadeblack','fadegrays','smoothleft','smoothright']
    filter_parts = []
    offset = 0
    prev_label = '[0:v]'

    for i in range(1, len(clip_paths)):
        offset += durations[i-1] - fade_duration
        t = transitions[i % len(transitions)]
        curr_label = '[vout]' if i == len(clip_paths)-1 else f'[v{i}]'
        filter_parts.append(f"{prev_label}[{i}:v]xfade=transition={t}:duration={fade_duration}:offset={offset:.2f}{curr_label}")
        prev_label = f'[v{i}]'

    cmd = ['ffmpeg','-y'] + inputs + [
        '-filter_complex', ';'.join(filter_parts),
        '-map','[vout]','-c:v','libx264','-preset','fast','-crf','23',
        '-pix_fmt','yuv420p','-an', output_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    if result.returncode != 0:
        log.warning("Crossfade failed, using simple concat")
        concat_file = output_path + '_concat.txt'
        with open(concat_file, 'w') as f:
            for cp in clip_paths:
                f.write(f"file '{os.path.abspath(cp)}'\n")
        cmd2 = ['ffmpeg','-y','-f','concat','-safe','0','-i',concat_file,
                '-c:v','libx264','-preset','fast','-crf','23',
                '-pix_fmt','yuv420p','-an', output_path]
        subprocess.run(cmd2, capture_output=True, timeout=600)
        if os.path.exists(concat_file):
            os.remove(concat_file)
    return output_path

def add_text_and_audio(bg_video, audio_path, title, captions, chapters, total_duration, output_path):
    filters = []
    filters.append(f'drawbox=x=0:y={H-160}:w={W}:h=160:color=black@0.6:t=fill')

    clean_title = ''.join(c if ord(c) < 128 else ' ' for c in title).strip()[:55]
    filters.append(f"drawbox=x=0:y=0:w={W}:h=100:color=black@0.7:t=fill:enable='between(t,0,5)'")
    filters.append(f"drawtext=text='{clean_title}':fontsize=54:fontcolor=yellow:borderw=3:bordercolor=black:x=(w-text_w)/2:y=22:enable='between(t,0,5)'")

    for ch in chapters[:6]:
        ch_title = ''.join(c if ord(c) < 128 else ' ' for c in ch.get("title","")).strip()
        if not ch_title:
            continue
        start_t = (ch.get("start_word", 0) / 130) * 60
        end_t = start_t + 4
        if 5 < start_t < total_duration:
            filters.append(f"drawbox=x=0:y=0:w={W}:h=80:color=black@0.7:t=fill:enable='between(t,{start_t:.1f},{end_t:.1f})'")
            filters.append(f"drawtext=text='{ch_title}':fontsize=46:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=18:enable='between(t,{start_t:.1f},{end_t:.1f})'")

    for cap in captions[:400]:
        start = cap['start_ms'] / 1000
        end = cap['end_ms'] / 1000
        if end <= start: end = start + 0.5
        text = ''.join(c if ord(c) < 128 else ' ' for c in cap['text']).strip()
        if not text or len(text) < 2: continue
        text = text[:45].replace("'","")
        filters.append(f"drawtext=text='{text}':fontsize=50:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y={H-120}:enable='between(t,{start:.2f},{end:.2f})'")

    sub_start = max(0, total_duration - 8)
    filters.append(f"drawbox=x=(w-520)/2:y={H-220}:w=520:h=60:color=red@0.85:t=fill:enable='between(t,{sub_start:.1f},{total_duration:.1f})'")
    filters.append(f"drawtext=text='Subscribe for more stories!':fontsize=38:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y={H-208}:enable='between(t,{sub_start:.1f},{total_duration:.1f})'")

    vf = ','.join(filters)
    cmd = ['ffmpeg','-y','-i', bg_video,'-i', audio_path,
           '-vf', vf, '-c:v','libx264','-preset','fast','-crf','22',
           '-c:a','aac','-b:a','192k',
           '-t', str(total_duration),'-shortest', output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError(f"Final render failed: {result.stderr.decode()[:400]}")
    return output_path

def assemble_video(clip_paths, audio_path, captions, title, chapters, output_path):
    log.info("Assembling illustrated slideshow with Ken Burns...")
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    total_dur = get_audio_duration_ffprobe(audio_path)
    log.info(f"Duration: {total_dur:.1f}s ({total_dur/60:.1f} min)")

    scenes_dir = output_path.replace('.mp4', '_scenes')
    num_scenes = max(6, int(total_dur / 60))  # ~1 scene per minute

    # Get visual query from story context
    visual_query = "fairy tale magical forest"
    # Try to extract from title
    clean = ''.join(c if ord(c) < 128 else ' ' for c in title).strip()
    if clean:
        words = [w for w in clean.split() if len(w) > 3 and w.isalpha()][:3]
        if words:
            visual_query = ' '.join(words)

    image_paths = download_scene_images(visual_query, chapters, scenes_dir, num_images=num_scenes)

    if not image_paths:
        raise RuntimeError("Could not download ANY images from Pixabay. Check API key.")

    scene_dur = (total_dur + 5) / len(image_paths)
    ken_burns_clips = []

    for i, img_path in enumerate(image_paths):
        kb_path = os.path.join(scenes_dir, f"kb_{i:02d}.mp4")
        log.info(f"Ken Burns scene {i+1}/{len(image_paths)}...")
        result = create_ken_burns_clip(img_path, scene_dur, kb_path, i)
        if result and os.path.exists(kb_path):
            ken_burns_clips.append(kb_path)

    if not ken_burns_clips:
        raise RuntimeError("All Ken Burns clips failed - check FFmpeg installation")

    log.info(f"Crossfading {len(ken_burns_clips)} scenes...")
    bg_path = output_path.replace('.mp4', '_bg.mp4')
    crossfade_clips(ken_burns_clips, bg_path)

    log.info("Adding captions and audio...")
    add_text_and_audio(bg_path, audio_path, title, captions, chapters, total_dur, output_path)

    if os.path.exists(bg_path):
        os.remove(bg_path)

    log.info(f"Video ready: {output_path}")
    return output_path
