"""voice_generator.py - TTS with word timing fallback"""
import asyncio
import logging
import os
import re
import config

log = logging.getLogger(__name__)

async def _generate_async(text, output_path):
    import edge_tts
    communicate = edge_tts.Communicate(
        text=text, voice=config.VOICE_NAME,
        rate=config.VOICE_RATE, pitch=config.VOICE_PITCH
    )
    audio_chunks = []
    timings = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            offset_ms = chunk["offset"] // 10000
            dur_ms = max(chunk.get("duration", 0) // 10000, 200)
            timings.append({
                "word": chunk["text"].strip(),
                "start_ms": offset_ms,
                "end_ms": offset_ms + dur_ms,
            })
    with open(output_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)
    log.info(f"Voice saved: {output_path} | Words timed: {len(timings)}")
    return timings

def generate_voice(text, output_path):
    clean = _clean_text(text)
    log.info(f"Generating voice for {len(clean.split())} words...")
    timings = asyncio.run(_generate_async(clean, output_path))
    
    # Fallback: generate approximate timings if edge-tts gave 0
    if not timings:
        log.warning("No word timings from edge-tts, generating approximate timings...")
        timings = _approximate_timings(clean, output_path)
    return timings

def _approximate_timings(text, audio_path):
    """Generate approximate word timings based on audio duration."""
    try:
        from mutagen.mp3 import MP3
        duration_ms = int(MP3(audio_path).info.length * 1000)
    except:
        duration_ms = len(text.split()) * 400  # 400ms per word estimate
    
    words = text.split()
    if not words:
        return []
    
    ms_per_word = duration_ms / len(words)
    timings = []
    for i, word in enumerate(words):
        start = int(i * ms_per_word)
        end = int((i + 1) * ms_per_word)
        timings.append({"word": word, "start_ms": start, "end_ms": end})
    
    log.info(f"Generated {len(timings)} approximate word timings")
    return timings

def _clean_text(text):
    text = text.replace("&", "and").replace("%", "percent")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def build_caption_groups(timings, words_per_group=3):
    """TikTok-style: 3 words per caption, ALL CAPS, centered."""
    if not timings:
        return []
    groups = []
    for i in range(0, len(timings), words_per_group):
        chunk = timings[i:i+words_per_group]
        if not chunk:
            continue
        groups.append({
            "text": " ".join(w["word"].upper() for w in chunk),
            "start_ms": chunk[0]["start_ms"],
            "end_ms": chunk[-1]["end_ms"],
        })
    log.info(f"Built {len(groups)} caption groups")
    return groups

def get_audio_duration(audio_path):
    try:
        from mutagen.mp3 import MP3
        return MP3(audio_path).info.length
    except:
        return float(os.path.getsize(audio_path)) / 16000
