"""
Telegram Bot Handlers — All commands and message handlers (Phase 2).

Commands:
    /start          — Welcome + registration check
    /register       — Get the Google Form registration link
    /help           — Show available commands
    /video          — Get latest video from Google Drive folder
    /latest         — List recent files from Drive
    /clear          — Clear conversation history

Admin only:
    /pending        — List pending approvals
    /approve <id>   — Approve and broadcast content
    /reject <id>    — Reject content
    /users          — List all registered users
    /unmute <id>    — Reset user strikes
    /broadcast <msg>— Send message to all users
    /sync           — Sync registrations from Google Sheet
    /adduser <id> <name> — Manually approve a user
"""
from telegram import Update
from telegram.ext import ContextTypes

from bot.ai_tutor import AITutor
from bot.drive_service import DriveService
from bot.sentiment_filter import is_toxic, record_strike, is_muted
from bot.auth import is_registered, register_user_locally, sync_from_sheet
from bot.admin import (
    is_admin,
    pending_handler, approve_handler, reject_handler,
    users_handler, unmute_handler, broadcast_handler,
)
from config.settings import GOOGLE_FORM_URL

# Initialize services
tutor = AITutor()
drive = DriveService()


# ── Auth Gate Decorator ───────────────────────────────────

async def _check_access(update: Update) -> bool:
    """
    Returns True if user can proceed.
    Blocks muted users and unregistered users.
    Admins always pass.
    """
    user = update.effective_user
    user_id = user.id

    # Admin always has access
    if is_admin(user_id):
        return True

    # Check if muted
    if is_muted(user_id):
        await update.message.reply_text(
            "🚫 You have been muted due to repeated violations.\n"
            "Contact the admin for assistance."
        )
        return False

    # Check if registered. If not, register automatically!
    if not is_registered(user_id):
        register_user_locally(user_id, user.first_name)

    return True


# ── /start ────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if is_admin(user.id):
        await update.message.reply_text(
            f"👑 Welcome Admin!\n\n"
            "Admin commands:\n"
            "`/pending` `/approve` `/reject`\n"
            "`/users` `/unmute` `/broadcast` `/sync`",
            parse_mode="Markdown"
        )
        return

    # Auto-register user in local store
    if not is_registered(user.id):
        register_user_locally(user.id, user.first_name)

    await update.message.reply_text(
        f"👋 Welcome back, {user.first_name}! 🧠\n\n"
        "**Commands:**\n"
        "`/video` — Get today's training video\n"
        "`/latest` — See recent videos\n"
        "`/clear` — Reset conversation\n"
        "`/help` — Help\n\n"
        "Or just type any question! 🚀",
        parse_mode="Markdown"
    )


# ── /register ─────────────────────────────────────────────

async def register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_registered(user.id):
        register_user_locally(user.id, user.first_name)
    await update.message.reply_text("✅ You are registered and have full access to the AI Training bot!")


# ── /help ─────────────────────────────────────────────────

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    await update.message.reply_text(
        "🤖 **Commands:**\n\n"
        "`/video` — Today's training video\n"
        "`/latest` — Recent videos\n"
        "`/clear` — Reset conversation\n"
        "`/register` — Registration link\n\n"
        "💬 Type any question to ask the AI Tutor!",
        parse_mode="Markdown"
    )


# ── /video ────────────────────────────────────────────────

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return

    if not drive.is_available():
        await update.message.reply_text("⚠️ Video service not configured.")
        return

    await update.message.reply_text("🔍 Fetching video from Google Drive...")

    # Get the single/latest video from the folder
    videos = drive.get_latest_videos(limit=1)
    if not videos:
        await update.message.reply_text("📭 No videos found in the folder yet.")
        return

    v = videos[0]
    size = DriveService.format_size(v.get("size", "0"))
    name = v['name'].replace("<", "&lt;").replace(">", "&gt;")
    response = (
        f"🎥 <b>{name}</b>\n\n"
        f"📦 {size}\n"
        f'🔗 <a href="{v["view_link"]}">Watch Video</a>\n\n'
        "💬 Have questions? Just ask!"
    )
    await update.message.reply_text(response, parse_mode="HTML")


# ── /latest ───────────────────────────────────────────────

async def latest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return

    if not drive.is_available():
        await update.message.reply_text("⚠️ Google Drive not configured.")
        return

    await update.message.reply_text("🔍 Fetching latest files...")

    videos = drive.get_latest_videos(limit=5)
    if not videos:
        await update.message.reply_text("📭 No files found.")
        return

    response = "📚 **Latest Training Content:**\n\n"
    for i, v in enumerate(videos, 1):
        date = v["created"][:10] if v.get("created") else "—"
        response += f"**{i}.** [{v['name']}]({v['view_link']}) — {date}\n"

    response += "\n💬 Ask me anything about these!"
    await update.message.reply_text(response, parse_mode="Markdown")


# ── /clear ────────────────────────────────────────────────

async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    tutor.clear_history(update.effective_user.id)
    await update.message.reply_text("🧹 Conversation cleared! Ask me anything.")


# ── /sync (admin) ─────────────────────────────────────────

async def sync_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    await update.message.reply_text("🔄 Syncing registrations from Google Sheet...")
    new_users = sync_from_sheet()
    await update.message.reply_text(
        f"✅ Sync complete! {new_users} new user(s) added."
    )


# ── /adduser (admin) ──────────────────────────────────────

async def adduser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually register a user: /adduser <telegram_id> <name>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/adduser <telegram_id> <name>`", parse_mode="Markdown")
        return

    uid = int(context.args[0])
    name = " ".join(context.args[1:])
    register_user_locally(uid, name)
    await update.message.reply_text(f"✅ User `{uid}` ({name}) manually registered.", parse_mode="Markdown")

    # Notify the user they now have access
    try:
        await context.bot.send_message(
            chat_id=uid,
            text=(
                f"🎉 **Welcome, {name}!**\n\n"
                "You have been approved by the admin.\n"
                "You can now use the AI Training Bot!\n\n"
                "Send /start to begin. 🚀"
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass


# ── /addvideo (admin) — queue YouTube video ───────────────

async def addvideo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Queue a YouTube video for next daily broadcast: /addvideo <url> <title>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/addvideo <youtube_url> <lesson title>`\n\n"
            "Example:\n`/addvideo https://youtu.be/abc123 Lesson 2 - Python Basics`",
            parse_mode="Markdown"
        )
        return

    url = context.args[0]
    title = " ".join(context.args[1:])

    from bot.scheduler import add_to_queue
    position = add_to_queue(url, title)
    await update.message.reply_text(
        f"✅ Video queued at position #{position}\n\n"
        f"🎬 *{title}*\n"
        f"🔗 {url}\n\n"
        f"It will be sent at 6:00 AM tomorrow. Use `/sendvideo` to send now.",
        parse_mode="Markdown"
    )


async def queue_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current video queue."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    from bot.scheduler import _load_queue
    videos = _load_queue()

    if not videos:
        await update.message.reply_text("📭 No videos in queue.\nUse `/addvideo <url> <title>` to add one.", parse_mode="Markdown")
        return

    text = "📋 *Video Queue:*\n\n"
    for i, v in enumerate(videos, 1):
        status = "✅ Sent" if v.get("sent") else "⏳ Pending"
        text += f"*{i}.* {v['title']}\n{status} | {v['url']}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ── /sendvideo (admin) — manual trigger ──────────────────

async def sendvideo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: manually trigger the daily video broadcast right now."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    await update.message.reply_text("📡 Triggering daily video broadcast now...")
    from bot.scheduler import daily_video_job
    await daily_video_job(context)
    await update.message.reply_text("✅ Broadcast complete! Check the report above.")


# ── /uploadvideo (admin) — Drive → YouTube → Telegram ────

async def uploadvideo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Full pipeline: Download latest Drive video → Upload to YouTube → Broadcast to users.
    Usage: /uploadvideo [lesson title]
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    title = " ".join(context.args) if context.args else None

    msg = await update.message.reply_text("🔍 Finding latest video in Google Drive...")

    if not drive.is_available():
        await msg.edit_text("❌ Google Drive not configured.")
        return

    videos = drive.get_latest_videos(limit=5)
    if not videos:
        await msg.edit_text("📭 No videos found in Drive folder.")
        return

    from bot.scheduler import _load_processed, _save_processed, _broadcast_youtube_video
    sent_ids = _load_processed()
    
    # Reverse to process oldest first (e.g. Lesson 2 before Lesson 5)
    videos.reverse()
    unsent = next((v for v in videos if v["id"] not in sent_ids), None)

    if not unsent:
        await msg.edit_text("✅ All Drive videos already uploaded. No new video found.")
        return

    video_title = title or unsent["name"].replace(".mov", "").replace(".mp4", "").strip()
    await msg.edit_text(
        f"📥 Downloading: <b>{unsent['name']}</b>\n"
        f"⏳ This may take a few minutes for large files...",
        parse_mode="HTML"
    )

    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    downloaded = drive.download_file(unsent["id"], tmp_path)
    if not downloaded:
        await msg.edit_text("❌ Download from Google Drive failed.")
        os.unlink(tmp_path)
        return

    await msg.edit_text(
        f"✅ Downloaded!\n"
        f"📤 Uploading to YouTube as <b>Unlisted</b>...\n"
        f"⏳ Please wait...",
        parse_mode="HTML"
    )

    from bot.youtube_service import YouTubeService
    yt = YouTubeService()

    if not yt.is_available():
        os.unlink(tmp_path)
        await msg.edit_text(
            "⚠️ YouTube not authorized yet.\n\n"
            "Please restart the bot — it will open a browser to authorize YouTube access."
        )
        return

    result = yt.upload_video(
        file_path=tmp_path,
        title=video_title,
        description=f"AI Training Lesson: {video_title}\n\nWatch and learn with @Kyawzin_AIAutomation",
        privacy="unlisted",
    )
    os.unlink(tmp_path)

    if not result:
        await msg.edit_text("❌ YouTube upload failed. Check logs.")
        return

    # Mark as processed
    sent_ids.append(unsent["id"])
    _save_processed(sent_ids)

    await msg.edit_text("✅ YouTube upload complete. Broadcasting to Telegram...")
    
    sent_count = await _broadcast_youtube_video(context, video_title, result["url"])

    await msg.edit_text(
        f"🎉 <b>Broadcast Complete!</b>\n\n"
        f"🎬 {video_title}\n"
        f"🔗 {result['url']}\n"
        f"👁 Visibility: Unlisted\n\n"
        f"👥 Sent to {sent_count} students!",
        parse_mode="HTML"
    )


# ── Text Messages (AI Tutor + Sentiment Filter) ───────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""

    # ── Media & Link Guard (Skip for Admin) ──
    if not is_admin(user.id):
        # Guard against Videos, Media, or Document uploads
        if update.message.video or update.message.document or update.message.photo:
            await update.message.reply_text("🚫 Sending media or videos is not allowed. Please ask text questions only.")
            return
            
        # Guard against URLs and links
        has_url = any(ent.type in ("url", "text_link") for ent in update.message.entities or [])
        if has_url or "http://" in text or "https://" in text:
            await update.message.reply_text("🚫 Sending links is restricted to admins only.")
            return

    if not text:
        return

    # ── Command Guard: Do not process random commands ──
    if text.startswith("/"):
        # Ignore unknown commands so we don't waste API tokens
        return

    # ── Spam & API Cost Guard: Limit message length (skip for admin) ──
    if not is_admin(user.id) and len(text) > 500:
        await update.message.reply_text(
            "⚠️ Your message is too long (over 500 characters).\n"
            "Please summarize your question and keep it short!"
        )
        return

    # ── Sentiment check (skip for admin) ──
    if not is_admin(user.id) and is_toxic(text):
        strikes = record_strike(user.id)
        if strikes >= 3:
            await update.message.reply_text(
                "🚫 You have been muted for repeated violations.\n"
                "Contact the admin for help."
            )
        else:
            remaining = 3 - strikes
            await update.message.reply_text(
                f"⚠️ Please keep messages respectful.\n"
                f"Warning {strikes}/3 — {remaining} warning(s) remaining."
            )
        return

    # ── Access check ──
    if not await _check_access(update):
        return

    # ── AI Tutor response ──
    await update.message.chat.send_action("typing")
    response = await tutor.ask(user.id, text)

    # Check for secret lead generation flag
    if "[LEAD_GENERATED]" in response:
        response = response.replace("[LEAD_GENERATED]", "").strip()
        from config.settings import ADMIN_TELEGRAM_ID
        if ADMIN_TELEGRAM_ID:
            try:
                await context.bot.send_message(
                    chat_id=int(ADMIN_TELEGRAM_ID),
                    text=f"🚨 <b>NEW CONSULTING LEAD!</b>\n\n"
                         f"👤 <b>User:</b> {user.full_name} (@{user.username or 'N/A'})\n"
                         f"🆔 <b>ID:</b> {user.id}\n\n"
                         f"They just agreed to schedule a Google Meet or proceed with a service!\n\n"
                         f"<b>Their message:</b> <i>\"{text}\"</i>",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Error sending admin lead alert: {e}")

    if len(response) <= 4096:
        await update.message.reply_text(response)
    else:
        for i in range(0, len(response), 4096):
            await update.message.reply_text(response[i:i + 4096])
