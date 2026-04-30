"""
Scheduler — Fully automated daily AI training delivery.

Jobs:
    1. auto_upload_job  — runs every hour
       • Checks YouTube channel for new videos
       • Sends immediately to all registered Telegram users
       • Uses processed_ids to NEVER send the same video twice

    2. daily_video_job  — runs every day at 6:00 AM SE Asia (23:00 UTC)
       • Same check — catches anything missed by hourly watcher
       • Acts as a safety net for reliable delivery

Both jobs share the same processed_ids store — zero conflicts guaranteed.
"""
import json
import logging
from pathlib import Path
from datetime import time

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LAST_MESSAGES_FILE = DATA_DIR / "last_messages.json"


def _load_last_messages() -> dict:
    if LAST_MESSAGES_FILE.exists():
        with open(LAST_MESSAGES_FILE) as f:
            return json.load(f).get("last_message_ids", {})
    return {}


def _save_last_messages(ids: dict):
    with open(LAST_MESSAGES_FILE, "w") as f:
        json.dump({"last_message_ids": ids}, f, indent=2)
SENT_FILE     = DATA_DIR / "sent_videos.json"
USERS_FILE    = DATA_DIR / "users.json"
PROCESSED_FILE = DATA_DIR / "auto_processed.json"

# 6:00 PM SE Asia (UTC+7) = 11:00 UTC
DAILY_SEND_TIME = time(hour=11, minute=0, second=0)
HOURLY_INTERVAL = 3600  # seconds


# ── Data helpers ──────────────────────────────────────────

def _load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            return json.load(f)
    return {"registered_users": {}}


def _load_processed() -> list:
    """Single source of truth — video IDs already sent to Telegram."""
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return json.load(f).get("processed", [])
    return []


def _save_processed(ids: list):
    with open(PROCESSED_FILE, "w") as f:
        json.dump({"processed": ids}, f, indent=2)


def _save_current_lesson(title: str, url: str):
    """Let the AI tutor know what today's lesson is."""
    lesson_file = DATA_DIR / "current_lesson.json"
    with open(lesson_file, "w") as f:
        json.dump({"current_lesson": title, "current_video_url": url}, f, indent=2)


# ── Core broadcast helper ─────────────────────────────────

async def _broadcast_youtube_video(context, title: str, url: str) -> int:
    """
    Send latest YouTube video to all users.
    Retains chat history so users can scroll back to old lessons.
    """
    users_data = _load_users()
    registered = users_data.get("registered_users", {})
    if not registered:
        return 0

    message = (
        f"🎬 <b>{title}</b>\n"
        f"──────────────────────\n"
        f"{url}\n\n"
        f"💬 Ask me any questions about this lesson!"
    )

    sent = 0
    for uid in registered:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=message,
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to send to {uid}: {e}")

    return sent


async def _check_and_send_new_youtube(context, job_name: str):
    """
    Shared logic for both jobs:
    1. Get latest videos from YouTube channel
    2. Find any not yet in processed_ids
    3. Send to all Telegram users
    4. Mark as processed — prevents ALL future duplicates
    """
    from config.settings import YOUTUBE_CHANNEL_ID, ADMIN_TELEGRAM_ID
    from bot.youtube_service import YouTubeService

    if not YOUTUBE_CHANNEL_ID or "xxxx" in YOUTUBE_CHANNEL_ID:
        logger.warning(f"[{job_name}] YouTube channel ID not configured")
        return

    yt = YouTubeService()
    if not yt.is_available():
        logger.warning(f"[{job_name}] YouTube service unavailable")
        return

    processed_ids = _load_processed()
    videos = yt.get_channel_videos(max_results=10)

    new_videos = [
        v for v in videos
        if f"yt_{v['id']}" not in processed_ids and "lesson" in v["title"].lower()
    ]

    if not new_videos:
        logger.info(f"[{job_name}] No new videos — nothing to send")
        return

    # To share progressively, pick the OLDEST unshared video
    # YouTube returns newest first, so we reverse it to get oldest first
    new_videos.reverse()
    
    # Select only ONE video per schedule trigger
    v = new_videos[0]

    key = f"yt_{v['id']}"
    title = v["title"]
    url   = v["url"]

    logger.info(f"[{job_name}] New video found: {title} (Sending 1 progressively)")

    # Mark FIRST to prevent race condition
    processed_ids.append(key)
    _save_processed(processed_ids)
    _save_current_lesson(title, url)

    sent_count = await _broadcast_youtube_video(context, title, url)
    logger.info(f"[{job_name}] ✅ '{title}' → sent to {sent_count} users")

    # Brief admin confirmation
    if ADMIN_TELEGRAM_ID:
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_TELEGRAM_ID),
                text=(
                    f"✅ <b>{title}</b>\n"
                    f"🔗 {url}\n"
                    f"👥 Sent to {sent_count} students"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass


# ── Job 1: Hourly watcher ─────────────────────────────────

async def auto_upload_job(context):
    """Runs every hour — auto-downloads from Drive, uploads to YouTube, and broadcasts."""
    import datetime
    # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    today = datetime.datetime.now().weekday()
    if today in [4, 5, 6]:
        logger.info("⏸️ [AutoUpload] Skipped: Today is Friday/Weekend. Auto-upload disabled.")
        return
        
    logger.info("🔍 [AutoUpload] Checking Google Drive for new videos...")
    
    from bot.drive_service import DriveService
    from bot.youtube_service import YouTubeService
    from config.settings import ADMIN_TELEGRAM_ID
    import tempfile, os

    drive = DriveService()
    if not drive.is_available():
        logger.warning("[AutoUpload] Drive not configured.")
        return

    videos = drive.get_latest_videos(limit=5)
    if not videos:
        return

    processed_ids = _load_processed()
    videos.reverse()  # Process oldest first
    unsent = next((v for v in videos if v["id"] not in processed_ids), None)

    if not unsent:
        return

    logger.info(f"[AutoUpload] Downloading new video: {unsent['name']}")
    video_title = unsent["name"].replace(".mov", "").replace(".mp4", "").strip()

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    downloaded = drive.download_file(unsent["id"], tmp_path)
    if not downloaded:
        logger.error("[AutoUpload] Drive download failed.")
        os.unlink(tmp_path)
        return

    yt = YouTubeService()
    if not yt.is_available():
        logger.error("[AutoUpload] YouTube not authorized.")
        os.unlink(tmp_path)
        return

    logger.info(f"[AutoUpload] Uploading to YouTube: {video_title}")
    result = yt.upload_video(
        file_path=tmp_path,
        title=video_title,
        description=f"AI Training Lesson: {video_title}\n\nWatch and learn with @Kyawzin_AIAutomation",
        privacy="unlisted",
    )
    os.unlink(tmp_path)

    if not result:
        logger.error("[AutoUpload] YouTube upload failed.")
        return

    # Mark as processed in Drive so it doesn't upload again
    processed_ids.append(unsent["id"])
    _save_processed(processed_ids)

    logger.info("[AutoUpload] 🤫 Uploaded to YouTube silently. Waiting for 6:00 PM schedule to broadcast.")
    
    if ADMIN_TELEGRAM_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=f"🤫 <b>Auto-Upload Complete!</b>\n\n🎬 {video_title}\n🔗 {result['url']}\n\n<i>This video is now queued and will be sent to students at exactly 6:00 PM based on schedule.</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass


# ── Job 2: Daily 6AM broadcast ────────────────────────────

async def daily_video_job(context):
    """Runs at 6:00 AM SE Asia — safety net delivery."""
    logger.info("⏰ [Daily] 6AM job triggered")
    await _check_and_send_new_youtube(context, "Daily")
