"""visual_sourcer.py - Downloads stock videos from Pixabay"""
import logging
import os
import random
import time
import requests
import config

log = logging.getLogger(__name__)
PIXABAY_URL = "https://pixabay.com/api/videos/"
PIXABAY_KEY_HARDCODED = "55951851-7282cb13bfe0431ff6400f2a0"
FALLBACK_QUERIES = ["nature forest", "magical castle", "animals wildlife",
                    "meadow flowers", "river mountains", "sky clouds sunset"]

def get_pexels_headers():
    return {"Authorization": os.environ.get("PEXELS_API_KEY", config.PIXABAY_API_KEY)}

def search_videos(query, count=8):
    params = {"key": os.environ.get("PIXABAY_API_KEY") or config.PIXABAY_API_KEY or PIXABAY_KEY_HARDCODED,
              "q": " ".join(query.split()[:3]),
              "video_type": "film", "per_page": min(count*2, 20), "safesearch": "true"}
    try:
        r = requests.get(PIXABAY_URL, params=params, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            params["q"] = random.choice(FALLBACK_QUERIES)
            r2 = requests.get(PIXABAY_URL, params=params, timeout=15)
            hits = r2.json().get("hits", [])
        log.info(f"Pixabay: found {len(hits)} videos for '{query}'")
        return hits[:count]
    except Exception as e:
        log.error(f"Pixabay search failed: {e}")
        return []

def download_video(video, output_dir, index):
    videos = video.get("videos", {})
    for quality in ["large", "medium", "small", "tiny"]:
        url = videos.get(quality, {}).get("url", "")
        if url:
            break
    if not url:
        return None
    output_path = os.path.join(output_dir, f"clip_{index:02d}.mp4")
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        log.info(f"Downloaded clip {index}: {os.path.getsize(output_path)/1024/1024:.1f}MB")
        return output_path
    except Exception as e:
        log.error(f"Download failed clip {index}: {e}")
        return None

def get_video_clips(search_query, output_dir, count=8):
    os.makedirs(output_dir, exist_ok=True)
    videos = search_videos(search_query, count)
    if len(videos) < 3:
        videos += search_videos(random.choice(FALLBACK_QUERIES), count)
    paths = []
    for i, v in enumerate(videos[:count]):
        p = download_video(v, output_dir, i)
        if p:
            paths.append(p)
        time.sleep(0.2)
    log.info(f"Got {len(paths)} clips")
    return paths
