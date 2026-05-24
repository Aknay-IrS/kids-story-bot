"""
main.py - Kids Story Bot orchestrator
Generates 8-12 minute original kids stories and uploads to YouTube daily
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import config
from modules.story_generator import generate_story
from modules.voice_generator import generate_voice, build_caption_groups, get_audio_duration
from modules.visual_sourcer import get_video_clips
from modules.video_assembler import assemble_video
from modules.thumbnail_generator import generate_thumbnail
from modules.youtube_uploader import upload_video, set_thumbnail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("pipeline.log", mode="a")]
)
log = logging.getLogger("main")


def make_story_video(topic=None, dry_run=False, no_upload=False):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = Path(f"output/{run_id}")
    work_dir.mkdir(parents=True, exist_ok=True)
    result = {"run_id": run_id, "status": "started"}

    # Step 1: Generate story
    log.info("STEP 1: Story Generation")
    story = generate_story(topic)
    (work_dir / "story.json").write_text(json.dumps(story, indent=2, ensure_ascii=False))
    result["title"] = story["title"]
    log.info(f"Title: {story['title']}")

    if dry_run:
        log.info(f"DRY RUN complete. Story:\n{story['narration'][:200]}...")
        result["status"] = "dry_run"
        return result

    # Step 2: Voice generation
    log.info("STEP 2: Voice Generation")
    audio_path = str(work_dir / "narration.mp3")
    timings = generate_voice(story["narration"], audio_path)
    captions = build_caption_groups(timings, 5)
    duration = get_audio_duration(audio_path)
    log.info(f"Audio: {duration:.1f}s | Captions: {len(captions)}")

    # Step 3: Visual sourcing
    log.info("STEP 3: Visual Sourcing")
    clips_dir = str(work_dir / "clips")
    clips = get_video_clips(story["visual_query"], clips_dir, count=8)
    log.info(f"Downloaded {len(clips)} clips")

    # Step 4: Video assembly
    log.info("STEP 4: Video Assembly")
    video_path = str(work_dir / "story.mp4")
    assemble_video(clips, audio_path, captions, story["title"], story["chapters"], video_path)

    # Step 5: Thumbnail
    log.info("STEP 5: Thumbnail")
    thumb_path = str(work_dir / "thumbnail.jpg")
    try:
        generate_thumbnail(story["title"], story["hook"], thumb_path, story["visual_query"])
    except Exception as e:
        log.warning(f"Thumbnail failed: {e}")
        thumb_path = None

    if no_upload:
        result["status"] = "ready_no_upload"
        result["video_path"] = video_path
        return result

    # Step 6: Upload
    log.info("STEP 6: Uploading to YouTube")
    video_id = upload_video(
        video_path=video_path,
        title=story["title"],
        description=story["description"],
        tags=story["tags"]
    )

    if video_id:
        if thumb_path and os.path.exists(thumb_path):
            set_thumbnail(video_id, thumb_path)
        result["video_id"] = video_id
        result["video_url"] = f"https://youtube.com/watch?v={video_id}"
        result["status"] = "uploaded"
        log.info(f"✅ Done! https://youtube.com/watch?v={video_id}")
    else:
        result["status"] = "upload_failed"

    (work_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()

    log.info("Kids Story Bot starting...")
    r = make_story_video(topic=args.topic, dry_run=args.dry_run, no_upload=args.no_upload)
    log.info(f"Status: {r['status']} | {r.get('title','N/A')} | {r.get('video_url','')}")


if __name__ == "__main__":
    main()
