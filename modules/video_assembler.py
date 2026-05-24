"""
video_assembler.py - Illustrated slideshow with Ken Burns effect + crossfades
Each scene gets its own image that slowly pans/zooms for a cinematic feel
"""
import logging
import os
import subprocess
import random
import requests
import config

log = logging.getLogger(__name__)
W = config.VIDEO_WIDTH   # 1920
H = config.VIDEO_HEIGHT  # 1080

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

def download_scene_images(visual_query, chapters, output_dir, pixabay_key):
    """Download one illustration per chapter/scene from Pixabay."""
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []

    # Generate search queries per chapter
    queries = []
    queries.append(visual_query)  # main query
    for ch in chapters:
        title = ch.get("title", "")
        clean = ''.join(c for c in title if c.isalpha() or c.isspace()).strip()
        if clean:
            queries.append(clean[:30])

    # Add generic fallbacks
    fallbacks = ["fairy tale castle", "magical forest", "storybook village",
                 "enchanted garden", "mystical landscape", "children adventure"]
    queries.extend(fallbacks)

    log.info(f"Downloading {len(chapters)+2} scene images...")

    for i, query in enumerate(queries[:len(chapters)+2]):
        try:
            r = requests.get("https://pixabay.com/api/", params={
                "key": pixabay_key,
                "q": query,
                "image_type": "illustration,photo",
                "orientation": "horizontal",
                "per_page": 5,
                "safesearch": "true",
                "min_width": 1280,
                "order": "popular"
            }, timeout=15)
            hits = r.json().get("hits", [])
            if not hits:
                # fallback to photo
                r2 = requests.get("https://pixabay.com/api/", params={
                    "key": pixabay_key, "q": fallbacks[i % len(fallbacks)],
                    "image_type": "photo", "orientation": "horizontal",
                    "per_page": 5, "safesearch": "true", "min_width": 1280
                }, timeout=15)
                hits = r2.json().get("hits", [])

            if hits:
                # Pick a random one from top 5
                hit = random.choice(hits[:5])
                img_url = hit.get("largeImageURL") or hit.get("webformatURL")
                img_r = requests.get(img_url, timeout=30)
                img_path = os.path.join(output_dir, f"scene_{i:02d}.jpg")
                with open(img_path, 'wb') as f:
                    f.write(img_r.content)
                image_paths.append(img_path)
                log.info(f"Scene {i}: downloaded for '{query}'")
            else:
                log.warning(f"No image for '{query}'")
        except Exception as e:
            log.warning(f"Scene {i} download failed: {e}")

    return image_paths

def create_ken_burns_clip(image_path, duration, output_path, index):
    """Apply Ken Burns (slow zoom/pan) effect to a single image."""
    # Different motion for variety
    motions = [
        # Zoom in from center
        f"scale=iw*2:ih*2,zoompan=z='min(zoom+0.0008,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        # Pan left to right
        f"scale=iw*2:ih*2,zoompan=z='1.2':x='if(lte(on,1),0,x+1)':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        # Pan right to left
        f"scale=iw*2:ih*2,zoompan=z='1.2':x='if(lte(on,1),iw,x-1)':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        # Zoom out
        f"scale=iw*2:ih*2,zoompan=z='if(lte(on,1),1.3,max(zoom-0.0008,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
        # Pan up
        f"scale=iw*2:ih*2,zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='if(lte(on,1),ih,y-1)':d={int(duration*config.VIDEO_FPS)}:s={W}x{H}:fps={config.VIDEO_FPS}",
    ]
    vf = motions[index % len(motions)]

    cmd = ['ffmpeg', '-y', '-loop', '1', '-i', image_path,
           '-t', str(duration + 0.5),
           '-vf', vf,
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
           '-pix_fmt', 'yuv420p', '-an', output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        log.warning(f"Ken Burns failed for scene {index}, using static: {result.stderr.decode()[:200]}")
        # Fallback: static image
        cmd2 = ['ffmpeg', '-y', '-loop', '1', '-i', image_path,
                '-t', str(duration + 0.5),
                '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-pix_fmt', 'yuv420p', '-an', output_path]
        subprocess.run(cmd2, capture_output=True, timeout=300)
    return output_path

def crossfade_clips(clip_paths, output_path, fade_duration=1.0):
    """Concatenate clips with crossfade transitions."""
    if len(clip_paths) == 1:
        import shutil
        shutil.copy(clip_paths[0], output_path)
        return output_path

    if len(clip_paths) == 0:
        return None

    # Build complex filtergraph for crossfades
    # Use xfade filter for smooth transitions
    n = len(clip_paths)

    # Get duration of each clip
    durations = []
    for cp in clip_paths:
        try:
            r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                               '-of','default=noprint_wrappers=1:nokey=1', cp],
                              capture_output=True, text=True, timeout=15)
            durations.append(float(r.stdout.strip()))
        except:
            durations.append(15.0)

    # Simple concat with xfade
    inputs = []
    for cp in clip_paths:
        inputs.extend(['-i', cp])

    # Build xfade filtergraph
    filter_parts = []
    offset = 0
    prev_label = '[0:v]'

    transitions = ['fade', 'dissolve', 'slideright', 'slideleft',
                   'circlecrop', 'fadeblack', 'fadegrays']

    for i in range(1, n):
        offset += durations[i-1] - fade_duration
        transition = transitions[i % len(transitions)]
        curr_label = f'[v{i}]' if i < n-1 else '[vout]'
        filter_parts.append(
            f"{prev_label}[{i}:v]xfade=transition={transition}:duration={fade_duration}:offset={offset:.2f}{curr_label}"
        )
        prev_label = f'[v{i}]'

    filter_complex = ';'.join(filter_parts)

    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', filter_complex,
        '-map', '[vout]',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-pix_fmt', 'yuv420p', '-an', output_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    if result.returncode != 0:
        log.warning(f"Crossfade failed, using simple concat: {result.stderr.decode()[:300]}")
        # Fallback: simple concat
        concat_file = output_path + '_concat.txt'
        with open(concat_file, 'w') as f:
            for cp in clip_paths:
                f.write(f"file '{os.path.abspath(cp)}'\n")
        cmd2 = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-pix_fmt', 'yuv420p', '-an', output_path]
        subprocess.run(cmd2, capture_output=True, timeout=600)
        if os.path.exists(concat_file):
            os.remove(concat_file)
    return output_path

def add_text_and_audio(bg_video, audio_path, title, captions, chapters, total_duration, output_path):
    """Add captions, chapter titles and audio to the slideshow video."""
    filters = []

    # Semi-transparent dark bar at bottom for captions
    filters.append(
        f"drawbox=x=0:y={H-160}:w={W}:h=160:color=black@0.6:t=fill"
    )

    # Title overlay (first 5 seconds) - large and centered
    clean_title = ''.join(c if ord(c) < 128 else ' ' for c in title).strip()[:50]
    filters.append(
        f"drawbox=x=0:y=0:w={W}:h=100:color=black@0.7:t=fill:enable='between(t,0,5)'"
    )
    filters.append(
        f"drawtext=text='{clean_title}':fontsize=56:fontcolor=yellow:"
        f"borderw=3:bordercolor=black:x=(w-text_w)/2:y=22:enable='between(t,0,5)'"
    )

    # Chapter titles
    for i, ch in enumerate(chapters[:6]):
        ch_title = ''.join(c if ord(c) < 128 else ' ' for c in ch.get("title","")).strip()
        if not ch_title:
            continue
        start_word = ch.get("start_word", 0)
        start_t = (start_word / 130) * 60
        end_t = start_t + 4
        if start_t > 5 and start_t < total_duration:
            filters.append(
                f"drawbox=x=0:y=0:w={W}:h=80:color=black@0.7:t=fill:"
                f"enable='between(t,{start_t:.1f},{end_t:.1f})'"
            )
            filters.append(
                f"drawtext=text='{ch_title}':fontsize=48:fontcolor=white:"
                f"borderw=3:bordercolor=black:x=(w-text_w)/2:y=18:"
                f"enable='between(t,{start_t:.1f},{end_t:.1f})'"
            )

    # Captions at bottom
    for cap in captions[:300]:
        start = cap['start_ms'] / 1000
        end = cap['end_ms'] / 1000
        if end <= start:
            end = start + 0.5
        text = ''.join(c if ord(c) < 128 else ' ' for c in cap['text']).strip()
        if not text or len(text) < 2:
            continue
        text = text[:45].replace("'", "")
        filters.append(
            f"drawtext=text='{text}':fontsize=52:fontcolor=white:"
            f"borderw=4:bordercolor=black:x=(w-text_w)/2:y={H-120}:"
            f"enable='between(t,{start:.2f},{end:.2f})'"
        )

    # Subscribe reminder last 8 seconds
    sub_start = max(0, total_duration - 8)
    filters.append(
        f"drawbox=x=(w-500)/2:y={H-220}:w=500:h=60:color=red@0.85:t=fill:"
        f"enable='between(t,{sub_start:.1f},{total_duration:.1f})'"
    )
    filters.append(
        f"drawtext=text='Subscribe for more stories!':fontsize=38:fontcolor=white:"
        f"borderw=2:bordercolor=black:x=(w-text_w)/2:y={H-208}:"
        f"enable='between(t,{sub_start:.1f},{total_duration:.1f})'"
    )

    vf = ','.join(filters)
    cmd = ['ffmpeg', '-y',
           '-i', bg_video, '-i', audio_path,
           '-vf', vf,
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
           '-c:a', 'aac', '-b:a', '192k',
           '-t', str(total_duration), '-shortest', output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError(f"Final render failed: {result.stderr.decode()[:400]}")
    return output_path

def assemble_video(clip_paths, audio_path, captions, title, chapters, output_path):
    """Main assembly: illustrated slideshow with Ken Burns + crossfades."""
    log.info("Assembling illustrated slideshow video...")
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    total_dur = get_audio_duration_ffprobe(audio_path)
    log.info(f"Story duration: {total_dur:.1f}s ({total_dur/60:.1f} min)")

    # Download scene illustrations
    pixabay_key = os.environ.get("PIXABAY_API_KEY", config.PIXABAY_API_KEY)
    scenes_dir = output_path.replace('.mp4', '_scenes')

    # Use visual query from clip_paths context or fallback
    visual_query = "fairy tale magical forest"
    if clip_paths:  # clip_paths here contains image paths or empty
        pass

    # Actually download images based on chapters
    image_paths = download_scene_images(
        visual_query, chapters, scenes_dir, pixabay_key
    )

    if not image_paths:
        # Emergency fallback - solid color background
        log.warning("No images downloaded, using colored background")
        cmd = ['ffmpeg', '-y', '-f', 'lavfi',
               '-i', f'color=c=0x1a0a2e:size={W}x{H}:duration={total_dur}:rate={config.VIDEO_FPS}',
               '-c:v', 'libx264', '-preset', 'fast', output_path.replace('.mp4', '_bg.mp4')]
        subprocess.run(cmd, capture_output=True, timeout=120)
        image_paths = []

    # Calculate duration per scene
    n_scenes = max(len(image_paths), 1)
    scene_dur = (total_dur + 5) / n_scenes  # slight overlap for crossfades

    # Apply Ken Burns to each image
    ken_burns_clips = []
    for i, img_path in enumerate(image_paths):
        kb_path = os.path.join(scenes_dir, f"kb_{i:02d}.mp4")
        log.info(f"Applying Ken Burns to scene {i+1}/{n_scenes}...")
        create_ken_burns_clip(img_path, scene_dur, kb_path, i)
        if os.path.exists(kb_path):
            ken_burns_clips.append(kb_path)

    if not ken_burns_clips:
        log.error("No Ken Burns clips created")
        raise RuntimeError("Ken Burns clip creation failed")

    # Crossfade all scenes together
    log.info(f"Crossfading {len(ken_burns_clips)} scenes...")
    bg_path = output_path.replace('.mp4', '_bg.mp4')
    crossfade_clips(ken_burns_clips, bg_path, fade_duration=1.5)

    # Add captions and audio
    log.info("Adding captions and audio...")
    add_text_and_audio(bg_path, audio_path, title, captions, chapters, total_dur, output_path)

    # Cleanup
    if os.path.exists(bg_path):
        os.remove(bg_path)

    log.info(f"✅ Video ready: {output_path}")
    return output_path
