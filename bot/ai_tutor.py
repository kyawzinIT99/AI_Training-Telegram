"""
Claude AI Tutor — Cost-effective, digest-style answers.

- Knows today's lesson (from current_lesson.json)
- Knows ALL available Drive videos (indexed as course catalog)
- Short answers only (max 150 tokens) — controls API cost
- Maintains per-user conversation history (max 6 messages)
"""
import json
from pathlib import Path
import anthropic
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LESSON_FILE = DATA_DIR / "current_lesson.json"

# ── Cost control ──────────────────────────────────────────
MAX_TOKENS    = 180   # Short, digest answers — saves API cost
MAX_HISTORY   = 6     # 3 exchanges per user — keeps context small


def _load_current_lesson() -> tuple[str, str]:
    """Returns (title, url) of today's active lesson."""
    try:
        if LESSON_FILE.exists():
            with open(LESSON_FILE) as f:
                d = json.load(f)
                return d.get("current_lesson", ""), d.get("current_video_url", "")
    except Exception:
        pass
    return "", ""


def _load_drive_catalog() -> str:
    """
    Index all video titles from Google Drive for AI context.
    Returns a compact list string for the system prompt.
    """
    context_string = ""
    
    # 1. Load Services & Pricing if available
    try:
        import json
        with open("data/services.json", "r", encoding="utf-8") as f:
            services = json.load(f)
            if services:
                context_string += "AVAILABLE CONSULTING & SERVICES (WITH PRICING):\n"
                for s in services:
                    context_string += f"• {s['service_name']} - ${s['price_usd']}: {s['description']}\n"
                context_string += "\n"
    except Exception:
        pass

    # 2. Load Drive Lessons
    try:
        from bot.drive_service import DriveService
        drive = DriveService()
        if drive.is_available():
            videos = drive.get_latest_videos(limit=50)
            if videos:
                titles = [
                    v["name"].replace(".mov","").replace(".mp4","")
                             .replace(".avi","").replace(".mkv","").strip()
                    for v in videos
                ]
                context_string += "AVAILABLE LESSONS IN COURSE:\n" + "\n".join(
                    f"• {t}" for t in titles
                )
    except Exception:
        pass
        
    return context_string


def _build_system_prompt(lesson_title: str, video_url: str, catalog: str) -> str:
    """Compact, cost-efficient system prompt."""
    today = f"TODAY: '{lesson_title}' — {video_url}" if lesson_title else ""
    return f"""You are the professional AI Assistant and Master AI Tutor for the AI Training course on Telegram.

ABOUT THE FOUNDER & CONSULTING:
- The founder of this course is Mr. Kyaw Zin Tun (Expertise: AI automation, Cloud, Network).
- If a client discusses consulting, projects (AI, Network, Cloud), or needs professional services, you MUST automatically list the available services and their prices from your provided knowledge. Pitch the services directly to them without human effort!
- After providing the service list and prices, offer a Google Meet discussion to finalize their project.
- If the user explicitly AGREES to schedule a Google Meet or asks to proceed with a service, you MUST include the exact string "[LEAD_GENERATED]" at the very end of your response. This is a secret system trigger.
- If they ask for direct contact or human support, provide his info:
  * Email: itsolutions.mm@gmail.com
  * Phone/WhatsApp: +66949567820
  * Viber: +9595043252
- If a user asks for our AI GitHub link, source code, or repository, you must provide this exact link: https://github.com/kyawzinIT99/AI-Training.git

RESPONSE FORMATTING & COST EFFICIENCY:
- You MUST answer all questions in a highly condensed "digest" format.
- Do NOT write long paragraphs. Use brief bullet points.
- Keep your entire response under 3-4 sentences to aggressively save API tokens and minimize costs.
- Do not repeat the user's question or offer unnecessary pleasantries. Just give the exact answer.
{today}
{catalog}

RULES:
- Answer in 2-3 sentences MAX. Be direct and digest.
- Bullet points only when listing steps.
- Reply in same language as student (English or Burmese).
- Reference lesson titles by name when relevant.
- DO NOT list or mention the available lessons when a user just says "hi" or greets you. Only list the lessons if they explicitly ask what lessons are available.
- Never hallucinate. Say "I don't know" if unsure.
- No filler words. Save tokens. Every word must add value."""


class AITutor:
    """Cost-efficient Claude tutor — knows all course content."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model  = CLAUDE_MODEL
        self.conversations: dict[int, list[dict]] = {}
        # Cache catalog to avoid hitting Drive API every message
        self._catalog_cache: str = ""

    def _get_history(self, user_id: int) -> list[dict]:
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        return self.conversations[user_id]

    def _trim_history(self, user_id: int):
        h = self.conversations.get(user_id, [])
        if len(h) > MAX_HISTORY:
            self.conversations[user_id] = h[-MAX_HISTORY:]

    def clear_history(self, user_id: int):
        self.conversations.pop(user_id, None)

    def refresh_catalog(self):
        """Call once at startup to cache the Drive video catalog."""
        self._catalog_cache = _load_drive_catalog()

    async def ask(self, user_id: int, question: str) -> str:
        """
        Short, digest answer — minimal tokens, max clarity.
        Auto-loads today's lesson + full course catalog for context.
        """
        # Load catalog once if not cached
        if not self._catalog_cache:
            self._catalog_cache = _load_drive_catalog()

        lesson_title, video_url = _load_current_lesson()
        system = _build_system_prompt(lesson_title, video_url, self._catalog_cache)

        history = self._get_history(user_id)
        history.append({"role": "user", "content": question})

        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=history,
            )
            reply = resp.content[0].text
            history.append({"role": "assistant", "content": reply})
            self._trim_history(user_id)
            return reply

        except anthropic.AuthenticationError:
            return "❌ API key error — contact admin."
        except anthropic.RateLimitError:
            return "⏳ Too many requests — try again shortly."
        except Exception as e:
            return f"⚠️ {str(e)[:80]}"
