"""
Google Drive Service — OAuth 2.0 authentication for retrieving training videos.

Uses OAuth client credentials (client_secret JSON) to authenticate.
On first run, opens a browser for Google login. After that, uses saved token.json.

Videos are uploaded daily by the instructor to Google Drive.
This module fetches video metadata and generates shareable links
for delivery via Telegram.
"""
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config.settings import GOOGLE_CREDENTIALS_JSON, GOOGLE_DRIVE_FOLDER_ID, GOOGLE_TOKEN_FILE

# Scopes: Drive read + Sheets read + YouTube upload (all covered by one token)
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class DriveService:
    """Google Drive video retrieval service using OAuth 2.0."""

    def __init__(self):
        self.folder_id = GOOGLE_DRIVE_FOLDER_ID
        self.service = None
        self._init_service()

    def _init_service(self):
        """Initialize Google Drive API client with OAuth 2.0."""
        if not GOOGLE_CREDENTIALS_JSON or not os.path.exists(GOOGLE_CREDENTIALS_JSON):
            print("[Drive] ⚠️  No credentials JSON found — video features disabled.")
            return

        creds = None

        # Check for existing token (saved from previous login)
        if os.path.exists(GOOGLE_TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
            except Exception:
                creds = None

        # If no valid creds, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GOOGLE_CREDENTIALS_JSON, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"[Drive] ❌ OAuth flow failed: {e}")
                    return

            # Save token for future runs
            with open(GOOGLE_TOKEN_FILE, "w") as token_file:
                token_file.write(creds.to_json())
            print("[Drive] ✅ Token saved to token.json")

        try:
            self.service = build("drive", "v3", credentials=creds)
            print("[Drive] ✅ Google Drive service initialized")
        except Exception as e:
            print(f"[Drive] ❌ Failed to build service: {e}")
            self.service = None

    def is_available(self) -> bool:
        """Check if Drive service is properly configured."""
        return self.service is not None

    def get_video_by_id(self, file_id: str) -> dict | None:
        """
        Get video info and download link by Google Drive file ID.

        Args:
            file_id: Google Drive file ID

        Returns:
            Dict with name, link, mimeType, size — or None on error
        """
        if not self.is_available():
            return None

        try:
            file_meta = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, webViewLink, webContentLink",
                supportsAllDrives=True,
            ).execute()

            return {
                "id": file_meta.get("id"),
                "name": file_meta.get("name", "Unknown"),
                "mime_type": file_meta.get("mimeType", ""),
                "size": file_meta.get("size", "0"),
                "view_link": file_meta.get("webViewLink", ""),
                "download_link": file_meta.get("webContentLink", ""),
            }
        except HttpError as e:
            print(f"[Drive Error] get_video_by_id({file_id}): {e}")
            return None

    def get_latest_videos(self, limit: int = 5) -> list[dict]:
        """
        Get the most recently added files from the configured folder.

        Args:
            limit: Number of recent files to return

        Returns:
            List of dicts with video info
        """
        if not self.is_available() or not self.folder_id:
            return []

        try:
            query = (
                f"'{self.folder_id}' in parents "
                "and trashed = false"
            )

            results = self.service.files().list(
                q=query,
                pageSize=limit,
                fields="files(id, name, mimeType, size, webViewLink, createdTime)",
                orderBy="createdTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            ).execute()

            files = results.get("files", [])
            return [
                {
                    "id": f.get("id"),
                    "name": f.get("name", "Unknown"),
                    "mime_type": f.get("mimeType", ""),
                    "size": f.get("size", "0"),
                    "view_link": f.get("webViewLink", ""),
                    "created": f.get("createdTime", ""),
                }
                for f in files
            ]
        except HttpError as e:
            print(f"[Drive Error] get_latest_videos: {e}")
            return []

    def download_file(self, file_id: str, dest_path: str) -> bool:
        """
        Download a file from Google Drive to a local path.

        Args:
            file_id: Google Drive file ID
            dest_path: Local path to save the file

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False

        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io

            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(dest_path, "wb")
            downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"[Drive] Download {int(status.progress() * 100)}%")

            fh.close()
            print(f"[Drive] ✅ Downloaded to {dest_path}")
            return True

        except Exception as e:
            print(f"[Drive] ❌ Download failed: {e}")
            return False

    @staticmethod
    def format_size(size_bytes: str) -> str:
        """Convert bytes string to human-readable format."""
        try:
            size = int(size_bytes)
        except (ValueError, TypeError):
            return "Unknown size"

        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
