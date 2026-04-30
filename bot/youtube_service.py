"""
YouTube Service — Upload videos to @Kyawzin_AIAutomation channel.

Uses the same OAuth2 token as Google Drive (token.json).
The token must have youtube.upload scope (added to drive_service.py SCOPES).

Flow:
    1. Admin runs /uploadvideo in Telegram
    2. Bot downloads video from Google Drive
    3. Bot uploads to YouTube as Unlisted
    4. Bot sends YouTube link to all users (plays inline in Telegram)
    5. Students watch inside Telegram — no download button

YouTube API reference:
    https://developers.google.com/youtube/v3/guides/uploading_a_video
"""
import os
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config.settings import GOOGLE_CREDENTIALS_JSON, GOOGLE_TOKEN_FILE, YOUTUBE_CHANNEL_ID

logger = logging.getLogger(__name__)

# OAuth scopes must include youtube.upload (set in drive_service.py SCOPES)
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeService:
    """YouTube upload service using OAuth2 (same token as Drive)."""

    def __init__(self):
        self.service = None
        self.enabled = False
        self._init_service()

    def _init_service(self):
        """Initialize YouTube API client using the shared OAuth token."""
        if not os.path.exists(GOOGLE_TOKEN_FILE):
            logger.warning("[YouTube] No token.json found — run bot once to authorize")
            return

        try:
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
            self.service = build("youtube", "v3", credentials=creds)
            self.enabled = True
            logger.info("[YouTube] ✅ YouTube service initialized")
        except Exception as e:
            logger.warning(f"[YouTube] ⚠️ Could not initialize: {e}")
            self.service = None
            self.enabled = False

    def is_available(self) -> bool:
        return self.enabled and self.service is not None

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: list[str] = None,
        privacy: str = "unlisted",
        category_id: str = "27",  # 27 = Education
    ) -> dict | None:
        """
        Upload a video file to YouTube.

        Args:
            file_path: Local path to the video file
            title: YouTube video title
            description: Video description
            tags: List of tags
            privacy: 'public', 'unlisted' (default), or 'private'
            category_id: YouTube category (27 = Education)

        Returns:
            dict with 'id' and 'url' if successful, None otherwise
        """
        if not self.is_available():
            logger.error("[YouTube] Service not available")
            return None

        if not os.path.exists(file_path):
            logger.error(f"[YouTube] File not found: {file_path}")
            return None

        body = {
            "snippet": {
                "title": title,
                "description": description or f"AI Training Lesson: {title}",
                "tags": tags or ["AI", "training", "automation", "education"],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        # Detect MIME type
        ext = Path(file_path).suffix.lower()
        mime_map = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
        }
        mime_type = mime_map.get(ext, "video/mp4")

        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10MB chunks
        )

        try:
            logger.info(f"[YouTube] Starting upload: {title}")
            request = self.service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"[YouTube] Upload progress: {progress}%")

            video_id = response["id"]
            video_url = f"https://youtu.be/{video_id}"
            logger.info(f"[YouTube] ✅ Upload complete: {video_url}")

            return {
                "id": video_id,
                "url": video_url,
                "title": title,
                "privacy": privacy,
            }

        except HttpError as e:
            logger.error(f"[YouTube] Upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"[YouTube] Unexpected error: {e}")
            return None

    def get_channel_videos(self, max_results: int = 10) -> list[dict]:
        """
        Get recent videos from the configured YouTube channel.

        Returns list of dicts with id, title, url, published_at
        """
        if not self.is_available() or not YOUTUBE_CHANNEL_ID:
            return []

        try:
            response = self.service.search().list(
                part="snippet",
                channelId=YOUTUBE_CHANNEL_ID,
                type="video",
                order="date",
                maxResults=max_results,
            ).execute()

            videos = []
            for item in response.get("items", []):
                vid_id = item["id"]["videoId"]
                videos.append({
                    "id": vid_id,
                    "title": item["snippet"]["title"],
                    "url": f"https://youtu.be/{vid_id}",
                    "published_at": item["snippet"]["publishedAt"],
                    "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
                })
            return videos

        except Exception as e:
            logger.error(f"[YouTube] get_channel_videos error: {e}")
            return []
