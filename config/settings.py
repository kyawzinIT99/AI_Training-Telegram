"""
Centralized configuration — loads all settings from .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ── Telegram ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")

# ── Claude AI (Anthropic) ─────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Available model on this API key

# ── Google Drive (OAuth 2.0) ──────────────────────────────
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# ── Registration ──────────────────────────────────────────
GOOGLE_FORM_URL = os.getenv("GOOGLE_FORM_URL", "https://forms.gle/your_form_here")

# ── YouTube Integration ───────────────────────────────────
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
GCP_SERVICE_ACCOUNT_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "")
if GCP_SERVICE_ACCOUNT_JSON and not os.path.isabs(GCP_SERVICE_ACCOUNT_JSON):
    GCP_SERVICE_ACCOUNT_JSON = str(PROJECT_ROOT / GCP_SERVICE_ACCOUNT_JSON)

# Resolve credentials path relative to project root
if GOOGLE_CREDENTIALS_JSON and not os.path.isabs(GOOGLE_CREDENTIALS_JSON):
    GOOGLE_CREDENTIALS_JSON = str(PROJECT_ROOT / GOOGLE_CREDENTIALS_JSON)

# Token file for storing OAuth refresh token after first login
GOOGLE_TOKEN_FILE = str(PROJECT_ROOT / "token.json")

# ── AI Tutor System Prompt ────────────────────────────────

def get_system_prompt(lesson_title: str = "", video_url: str = "") -> str:
    """
    Returns a dynamic system prompt that includes today's lesson context.
    The AI tutor can answer questions specifically about the current video.
    """
    lesson_context = ""
    if lesson_title:
        lesson_context = (
            f"\nTODAY'S LESSON: '{lesson_title}'\n"
            f"{'Video: ' + video_url if video_url else ''}\n"
            "Focus answers on this lesson topic when relevant.\n"
        )

    return f"""You are the professional AI Assistant and Master AI Tutor for the AI Training course on Telegram.
{lesson_context}
ABOUT THE FOUNDER & CONSULTING:
- The founder of this course is Mr. Kyaw Zin Tun.
- His expertise: AI automation, Cloud, Network.
- If a client discusses consulting, projects (AI, Network, Cloud), or needs professional services, you MUST automatically list the available services and their prices from your provided knowledge. Pitch the services directly to them without human effort!
- After providing the service list and prices, offer a Google Meet discussion to finalize their project.
- If they ask for direct contact or human support, provide his info:
  * Email: itsolutions.mm@gmail.com
  * Phone/WhatsApp: +66949567820
  * Viber: +9595043252
- If a user asks for our AI GitHub link, source code, or repository, you must provide this exact link: https://github.com/kyawzinIT99/AI-Training.git

YOUR ROLE:
- Personal AI assistant and expert tutor.
- Answer questions about AI, automation, Python, Cloud, Networking, and today's lesson.
- Help students understand video content they just watched.

CRITICAL RULES:
- Keep responses SHORT: 3-5 sentences max. No walls of text.
- Use bullet points instead of paragraphs.
- Only include code if specifically asked.
- Respond in the same language the student uses (English or Burmese).
- Never hallucinate. Say "I don't know" if unsure.
- Use 1-2 emoji max per response.
- If asked about today's lesson, reference '{lesson_title}' specifically.
"""

# Default system prompt (before any lesson is loaded)
SYSTEM_PROMPT = get_system_prompt()


def validate_config():
    """Check that all required environment variables are set."""
    errors = []

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("your_"):
        errors.append("❌ TELEGRAM_BOT_TOKEN is not set in .env")

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.startswith("your_"):
        errors.append("❌ ANTHROPIC_API_KEY is not set in .env")

    if not GOOGLE_CREDENTIALS_JSON or not os.path.exists(GOOGLE_CREDENTIALS_JSON):
        errors.append("⚠️  GOOGLE_CREDENTIALS_JSON not found (video features disabled)")

    if not GOOGLE_DRIVE_FOLDER_ID or GOOGLE_DRIVE_FOLDER_ID.startswith("your_"):
        errors.append("⚠️  GOOGLE_DRIVE_FOLDER_ID is not set in .env (video listing disabled)")

    return errors
