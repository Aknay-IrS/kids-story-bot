"""youtube_uploader.py - Uploads story videos to YouTube"""
import json
import logging
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import config

log = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]

def _find_token():
    for p in ["token.json",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "token.json"),
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "token.json")]:
        p = os.path.normpath(p)
        if os.path.exists(p):
            return p
    return "token.json"

def get_service():
    token_path = _find_token()
    with open(token_path) as f:
        data = json.load(f)
    if "web" in data: data = data["web"]
    if "installed" in data: data = data["installed"]
    creds = Credentials(
        token=data.get("token") or data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", SCOPES)
    )
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        updated = {"token": creds.token, "refresh_token": creds.refresh_token,
                   "token_uri": creds.token_uri, "client_id": creds.client_id,
                   "client_secret": creds.client_secret, "scopes": list(creds.scopes or SCOPES)}
        with open(token_path, "w") as f:
            json.dump(updated, f, indent=2)
    return build("youtube", "v3", credentials=creds)

def upload_video(video_path, title, description, tags):
    try:
        youtube = get_service()
        full_desc = (f"{description}\n\n{'─'*30}\n"
                     "🌟 New kids story every day!\n"
                     "🔔 Subscribe for magical bedtime stories\n"
                     "👨‍👩‍👧 Perfect for family story time\n\n"
                     "#KidsStories #BedtimeStories #StoriesForKids #MoralStories #FairyTales")
        body = {
            "snippet": {"title": title[:100], "description": full_desc[:5000],
                        "tags": tags, "categoryId": "27",  # Education
                        "defaultLanguage": "en"},
            "status": {"privacyStatus": "public",
                       "selfDeclaredMadeForKids": config.YT_MADE_FOR_KIDS}
        }
        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5*1024*1024)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                log.info(f"Upload: {int(status.progress()*100)}%")
        video_id = response.get("id", "")
        log.info(f"✅ Uploaded! https://youtube.com/watch?v={video_id}")
        return video_id
    except Exception as e:
        log.error(f"Upload failed: {e}")
        return None

def set_thumbnail(video_id, thumbnail_path):
    try:
        youtube = get_service()
        youtube.thumbnails().set(videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")).execute()
        log.info(f"Thumbnail set for {video_id}")
    except Exception as e:
        log.warning(f"Thumbnail failed: {e}")
