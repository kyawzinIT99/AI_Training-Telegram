"""
Admin system — admin-only commands for approving content and managing users.

Commands (admin only):
    /pending          — list all pending video/URL approvals
    /approve <id>     — approve an item and broadcast to all users
    /reject <id>      — reject an item
    /users            — list all registered users
    /unmute <user_id> — reset strikes for a muted user
    /broadcast <msg>  — send a message to all registered users
"""
import json
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import ADMIN_TELEGRAM_ID

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PENDING_FILE = DATA_DIR / "pending.json"
USERS_FILE = DATA_DIR / "users.json"


def is_admin(user_id: int) -> bool:
    return str(user_id) == str(ADMIN_TELEGRAM_ID)


def _load_pending() -> dict:
    if PENDING_FILE.exists():
        with open(PENDING_FILE) as f:
            return json.load(f)
    return {"pending": []}


def _save_pending(data: dict):
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            return json.load(f)
    return {"registered_users": {}}


def add_pending(item_type: str, content: str, submitted_by: int) -> str:
    """Add a video/URL to the pending approval queue. Returns item ID."""
    data = _load_pending()
    item_id = str(len(data["pending"]) + 1)
    data["pending"].append({
        "id": item_id,
        "type": item_type,
        "content": content,
        "submitted_by": submitted_by,
        "status": "pending",
    })
    _save_pending(data)
    return item_id


def get_approved_content() -> list:
    """Return all approved items."""
    data = _load_pending()
    return [i for i in data["pending"] if i["status"] == "approved"]


# ── Admin Handlers ─────────────────────────────────────────

async def pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all pending approvals."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    data = _load_pending()
    items = [i for i in data["pending"] if i["status"] == "pending"]

    if not items:
        await update.message.reply_text("✅ No pending approvals.")
        return

    text = "📋 **Pending Approvals:**\n\n"
    for item in items:
        text += (
            f"ID: `{item['id']}` | Type: {item['type']}\n"
            f"Content: {item['content'][:80]}\n"
            f"From user: {item['submitted_by']}\n\n"
        )
    text += "Use `/approve <id>` or `/reject <id>`"
    await update.message.reply_text(text, parse_mode="Markdown")


async def approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a pending item."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/approve <id>`", parse_mode="Markdown")
        return

    item_id = context.args[0]
    data = _load_pending()
    approved = None

    for item in data["pending"]:
        if item["id"] == item_id:
            item["status"] = "approved"
            approved = item
            break

    if not approved:
        await update.message.reply_text(f"❌ Item `{item_id}` not found.", parse_mode="Markdown")
        return

    _save_pending(data)

    # Notify admin
    await update.message.reply_text(
        f"✅ Approved item `{item_id}`\n\n"
        f"Content will be available to all registered users.",
        parse_mode="Markdown"
    )

    # Broadcast to all registered users
    users_data = _load_users()
    broadcast_text = (
        f"📢 **New Content Released!**\n\n"
        f"🎥 {approved['content']}\n\n"
        f"Approved by Admin ✅"
    )

    sent = 0
    for uid, info in users_data.get("registered_users", {}).items():
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=broadcast_text,
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(f"📡 Broadcast sent to {sent} users.")


async def reject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending item."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/reject <id>`", parse_mode="Markdown")
        return

    item_id = context.args[0]
    data = _load_pending()

    for item in data["pending"]:
        if item["id"] == item_id:
            item["status"] = "rejected"
            _save_pending(data)
            await update.message.reply_text(f"🚫 Item `{item_id}` rejected.", parse_mode="Markdown")
            return

    await update.message.reply_text(f"❌ Item `{item_id}` not found.", parse_mode="Markdown")


async def users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered users."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    data = _load_users()
    users = data.get("registered_users", {})

    if not users:
        await update.message.reply_text("📭 No registered users yet.")
        return

    text = f"👥 **Registered Users ({len(users)}):**\n\n"
    for uid, info in users.items():
        strikes = info.get("strikes", 0)
        name = info.get("name", "Unknown")
        text += f"• {name} (ID: `{uid}`) — ⚡ {strikes} strikes\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def unmute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset strikes for a muted user."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/unmute <user_id>`", parse_mode="Markdown")
        return

    from bot.sentiment_filter import reset_strikes
    target_id = int(context.args[0])
    reset_strikes(target_id)
    await update.message.reply_text(f"✅ Strikes reset for user `{target_id}`.", parse_mode="Markdown")


async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a message to all registered users."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/broadcast Your message here`", parse_mode="Markdown")
        return

    message = " ".join(context.args)
    users_data = _load_users()
    sent = 0

    for uid in users_data.get("registered_users", {}):
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 **Admin Message:**\n\n{message}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(f"📡 Broadcast sent to {sent} users.")
