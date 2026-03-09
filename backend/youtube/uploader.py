import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from backend.config.settings import (
    YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN,
    OUTPUT_DIR, THUMBNAILS_DIR,
)
from backend.storage.models import Project


TOKEN_URI = "https://oauth2.googleapis.com/token"


def upload_to_youtube(db, project_id: int, privacy: str = "private"):
    """Upload video to YouTube with metadata and thumbnail."""
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    project.status = "uploading"
    db.commit()

    video_path = OUTPUT_DIR / project.video_filename
    if not video_path.exists():
        raise ValueError(f"Video file not found: {video_path}")

    # Parse metadata
    metadata = json.loads(project.metadata_json) if project.metadata_json else {}

    # Build YouTube API client
    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
    )
    youtube = build("youtube", "v3", credentials=creds)

    # Upload video
    body = {
        "snippet": {
            "title": project.title[:100],
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "categoryId": "22",  # People & Blogs (safe default)
            "defaultLanguage": project.channel.language if project.channel else "es",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=10 * 1024 * 1024, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]

    # Upload thumbnail if available
    if project.thumbnail_filename:
        thumb_path = THUMBNAILS_DIR / project.thumbnail_filename
        if thumb_path.exists():
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb_path)),
            ).execute()

    project.youtube_video_id = video_id
    project.youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    project.status = "published"
    project.current_step = 8
    db.commit()

    return {"video_id": video_id, "url": project.youtube_url}
