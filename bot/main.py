"""
AI Training Telegram Bot — Entry Point

Usage:
    python -m bot.main              # Start the bot
    python -m bot.main --verify     # Verify configuration only (dry run)
"""
import sys
import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config.settings import TELEGRAM_BOT_TOKEN, validate_config
from bot.handlers import (
    start_handler,
    register_handler,
    help_handler,
    video_handler,
    latest_handler,
    clear_handler,
    message_handler,
    sync_handler,
    adduser_handler,
    sendvideo_handler,
    addvideo_handler,
    queue_handler,
    uploadvideo_handler,
)
from bot.admin import (
    pending_handler,
    approve_handler,
    reject_handler,
    users_handler,
    unmute_handler,
    broadcast_handler,
)
from bot.scheduler import daily_video_job, auto_upload_job, DAILY_SEND_TIME, HOURLY_INTERVAL

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def verify_mode():
    """Check all configuration without starting the bot."""
    print("\n🔍 Verifying configuration...\n")
    errors = validate_config()

    if errors:
        for err in errors:
            print(f"  {err}")
        print()
        has_critical = any("❌" in e for e in errors)
        if has_critical:
            print("🚫 Critical errors found. Fix them in .env before starting the bot.\n")
            sys.exit(1)
        else:
            print("⚠️  Some optional features are disabled. Bot can still start.\n")
    else:
        print("  ✅ TELEGRAM_BOT_TOKEN is set")
        print("  ✅ ANTHROPIC_API_KEY is set")
        print("  ✅ GOOGLE_DRIVE_API_KEY is set")
        print()
        print("🎉 All configuration is valid! Run without --verify to start the bot.\n")

    sys.exit(0)


def main():
    """Initialize and start the Telegram bot."""

    # ── Handle --verify flag ──
    if "--verify" in sys.argv:
        verify_mode()

    # ── Validate config ──
    errors = validate_config()
    critical_errors = [e for e in errors if "❌" in e]

    if critical_errors:
        print("\n🚫 Cannot start bot — critical configuration errors:\n")
        for err in critical_errors:
            print(f"  {err}")
        print("\n👉 Fix your .env file and try again.\n")
        sys.exit(1)

    for warning in [e for e in errors if "⚠️" in e]:
        logger.warning(warning)

    # ── Build the bot application ──
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Pre-load Drive video catalog for AI Tutor ──
    from bot.handlers import tutor
    tutor.refresh_catalog()
    logger.info("📚 Drive video catalog loaded for AI Tutor")

    # ── Register command handlers ──
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("register", register_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("video", video_handler))
    app.add_handler(CommandHandler("latest", latest_handler))
    app.add_handler(CommandHandler("clear", clear_handler))

    # ── Admin commands ──
    app.add_handler(CommandHandler("pending", pending_handler))
    app.add_handler(CommandHandler("approve", approve_handler))
    app.add_handler(CommandHandler("reject", reject_handler))
    app.add_handler(CommandHandler("users", users_handler))
    app.add_handler(CommandHandler("unmute", unmute_handler))
    app.add_handler(CommandHandler("broadcast", broadcast_handler))
    app.add_handler(CommandHandler("sync", sync_handler))
    app.add_handler(CommandHandler("adduser", adduser_handler))
    app.add_handler(CommandHandler("sendvideo", sendvideo_handler))
    app.add_handler(CommandHandler("addvideo", addvideo_handler))
    app.add_handler(CommandHandler("queue", queue_handler))
    app.add_handler(CommandHandler("uploadvideo", uploadvideo_handler))

    # ── Register text message handler (AI Tutor) ──
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # ── Daily video broadcast (Mon-Thu only) ──
    app.job_queue.run_daily(
        daily_video_job,
        time=DAILY_SEND_TIME,
        days=(0, 1, 2, 3),  # Mon=0, Tue=1, Wed=2, Thu=3
        name="daily_video_broadcast",
    )
    logger.info("⏰ Daily broadcast scheduled — Mon-Thu @ 06:00 PM SE Asia")

    # Removed Google Form auto-sync (direct Telegram registration is now active)

    # ── Start polling ──
    logger.info("🚀 AI Training Telegram Bot is starting...")
    logger.info("📡 Polling for messages... (Ctrl+C to stop)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
