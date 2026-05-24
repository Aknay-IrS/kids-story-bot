"""voice_generator.py - Gentle TTS for kids stories using edge-tts"""
import asyncio
import logging
import os
import re
import config

log = logging.getLogger(__name__)

async def _generate_async(text, output_path):
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=config.VOICE_NAME,
                                        rate=config.VOICE_RATE, pitch=config.VOICE_PITCH)
    audio_chunks = []
    timings = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            timings.append({
                "word": chunk["text"],
                "start_ms": chunk["offset"] // 10000,
                "end_ms": (chunk["offset"] + chunk.get("duration", 200000)) // 10000,
            })
    with open(output_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)
    log.info(f"Voice saved: {output_path} | Words: {len(timings)}")
    return timings

def generate_voice(text, output_path):
    clean = _clean_text(text)
    log.info(f"Generating voice for {len(clean.split())} words...")
    return asyncio.run(_generate_async(clean, output_path))

def _clean_text(text):
    replacements = {"&": "and", "%": "percent", "vs": "versus"}
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def build_caption_groups(timings, words_per_group=5):
    if not timings:
        return []
    groups = []
    for i in range(0, len(timings), words_per_group):
        chunk = timings[i:i+words_per_group]
        groups.append({
            "text": " ".join(w["word"] for w in chunk),
            "start_ms": chunk[0]["start_ms"],
            "end_ms": chunk[-1]["end_ms"],
        })
    return groups

def get_audio_duration(audio_path):
    try:
        from mutagen.mp3 import MP3
        return MP3(audio_path).info.length
    except Exception:
        return float(os.path.getsize(audio_path)) / 16000
