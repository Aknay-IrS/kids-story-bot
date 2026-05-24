"""video_assembler.py - Assembles 16:9 landscape story video using FFmpeg"""
import logging
import os
import subprocess
import textwrap
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

def build_background(clip_paths, total_duration, output_path):
    if not clip_paths:
        cmd = ['ffmpeg','-y','-f','lavfi',
               '-i', f'color=c=0x1a0a2e:size={W}x{H}:duration={total_duration}:rate={config.VIDEO_FPS}',
               '-c:v','libx264','-preset','fast','-crf','28', output_path]
        subprocess.run(cmd, capture_output=True, timeout=120)
        return output_path

    concat_file = output_path + '_concat.txt'
    with open(concat_file, 'w') as f:
        repeats = int(total_duration / 8) + 5
        for _ in range(repeats):
            for clip in clip_paths:
                f.write(f"file '{os.path.abspath(clip)}'\n")

    # Scale to fill 1920x1080 properly from any source aspect ratio
    vf = (f"scale='if(gt(iw/ih,{W}/{H}),{W},{H}*iw/ih)':"
          f"'if(gt(iw/ih,{W}/{H}),{W}*ih/iw,{H})',"
          f"crop={W}:{H},fps={config.VIDEO_FPS}")

    cmd = ['ffmpeg','-y','-f','concat','-safe','0','-i',concat_file,
           '-t', str(total_duration), '-vf', vf,
           '-c:v','libx264','-preset','fast','-crf','23','-an', output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    if os.path.exists(concat_file):
        os.remove(concat_file)
    if result.returncode != 0:
        log.error(f"Background failed: {result.stderr.decode()[:300]}")
        return build_background([], total_duration, output_path)
    return output_path

def add_overlays_and_audio(bg_video, audio_path, title, captions, chapters, total_duration, output_path):
    filters = []

    # Semi-dark overlay for readability
    filters.append(f'drawbox=x=0:y=0:w={W}:h={H}:color=black@0.4:t=fill')

    # Title at top (first 4 seconds)
    clean_title = ''.join(c if ord(c) < 128 else ' ' for c in title).strip()
    short_title = clean_title[:60]
    filters.append(
        f"drawtext=text='{short_title}':fontsize=52:fontcolor=white:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=60:enable='between(t,0,4)'"
    )

    # Chapter markers
    for ch in chapters[:4]:
        start_word = ch.get("start_word", 0)
        ch_title = ''.join(c if ord(c) < 128 else ' ' for c in ch.get("title","")).strip()
        if not ch_title:
            continue
        # Approximate timing from word count (130 wpm)
        start_t = (start_word / 130) * 60
        end_t = start_t + 3
        if start_t < total_duration:
            filters.append(
                f"drawtext=text='{ch_title}':fontsize=44:fontcolor=yellow:borderw=3:bordercolor=black:"
                f"x=(w-text_w)/2:y=120:enable='between(t,{start_t:.1f},{end_t:.1f})'"
            )

    # Captions - bottom third
    for cap in captions[:200]:
        start = cap['start_ms'] / 1000
        end = cap['end_ms'] / 1000
        if end <= start:
            end = start + 0.5
        text = ''.join(c if ord(c) < 128 else ' ' for c in cap['text']).strip()
        if not text:
            continue
        text = text[:40]
        filters.append(
            f"drawtext=text='{text}':fontsize=48:fontcolor=white:borderw=4:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h*0.82):enable='between(t,{start:.2f},{end:.2f})'"
        )

    # Subscribe reminder at end
    sub_start = max(0, total_duration - 10)
    filters.append(
        f"drawtext=text='Subscribe for more stories!':fontsize=44:fontcolor=yellow:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=(h-80):enable='between(t,{sub_start:.1f},{total_duration:.1f})'"
    )

    vf = ','.join(filters)
    cmd = ['ffmpeg','-y','-i', bg_video,'-i', audio_path,
           '-vf', vf,
           '-c:v','libx264','-preset','fast','-crf','23',
           '-c:a','aac','-b:a','192k',
           '-t', str(total_duration), '-shortest', output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=900)
    if result.returncode != 0:
        log.error(f"Overlay failed: {result.stderr.decode()[:500]}")
        raise RuntimeError(f"FFmpeg overlay failed")
    return output_path

def assemble_video(clip_paths, audio_path, captions, title, chapters, output_path):
    log.info("Assembling story video with FFmpeg...")
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    total_dur = get_audio_duration_ffprobe(audio_path)
    log.info(f"Story duration: {total_dur:.1f}s ({total_dur/60:.1f} minutes)")
    bg_path = output_path.replace('.mp4', '_bg.mp4')
    log.info("Building background...")
    build_background(clip_paths, total_dur + 1, bg_path)
    log.info("Adding overlays and audio...")
    add_overlays_and_audio(bg_path, audio_path, title, captions, chapters, total_dur, output_path)
    if os.path.exists(bg_path):
        os.remove(bg_path)
    log.info(f"Video ready: {output_path}")
    return output_path
