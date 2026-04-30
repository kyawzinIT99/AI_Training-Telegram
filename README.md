# AI Training Telegram Bot - High-End Learning Platform 🤖🧠

A fully autonomous, premium Telegram Bot that serves as a **Master AI Tutor**. It delivers progressive training lessons from YouTube and provides cost-effective, personalized AI tutoring using Anthropic's Claude API.

## 🚀 System Architecture & Flow

### 1. Registration (Zero-Friction)
- **No Google Forms needed.** 
- The moment a user searches the bot and sends `/start` or any text message, they are **automatically registered** and added to the `data/users.json` database.

### 2. Daily Progressive Delivery (Set-and-Forget)
- **Schedule:** Triggers daily at exactly **6:00 PM SE Asia Time**.
- **Logic:** The bot polls the connected YouTube channel. It looks for videos with **"lesson"** in the title.
- **Progressive Sharing:** It selects exactly **ONE** unshared video (the oldest available) and broadcasts it to all registered students.
- **History Retention:** The bot *does not* delete previous messages. Students have a scrollable, permanent timeline of Lesson 1, Lesson 2, Lesson 3, etc.

### 3. Master AI Tutor (Claude Sonnet)
- **Course Awareness:** The bot caches the entire Google Drive catalog in its system prompt but is strictly instructed **not to spam** the curriculum unless explicitly asked.
- **Founder Authority:** It recognizes the founder as **Mr. Kyaw Zin Tun**. If a student demands human support, it provides the official contact details:
  - Email: `itsolutions.mm@gmail.com`
  - Phone/WhatsApp: `+66949567820`
  - Viber: `+9595043252`

---

## 🛡️ Security & Reputation Guards

The bot acts as an impenetrable shield for both API costs and brand reputation:

1. **Media & Link Guard:** Students are physically blocked from sending links (`http`), videos, photos, or documents. (Only the Admin is immune to this rule).
2. **Text Length Armor (Cost Guard):** Student messages cannot exceed **500 characters** (approx. 80 words). Massive walls of text are instantly rejected to protect the Anthropic API bill.
3. **Sentiment / Toxicity Filter (3-Strike System):**
   - Strike 1 & 2: Issues a professional warning to keep messages respectful.
   - Strike 3: The user is automatically muted and locked out of the platform until the Admin intervenes.
4. **Strict Token Limits:** The AI is hard-capped at 180 output tokens and a memory depth of 6 messages (3 interactions). This guarantees API costs remain extremely low (approx. $0.003 per question).

---

## 🛠️ Admin Commands

The platform is managed completely inside Telegram by the Admin (defined in `.env`).

* `/users` — List all registered students and their status.
* `/unmute <id>` — Restore access to a student who received 3 strikes.
* `/broadcast <msg>` — Send an instant text announcement to all students.
* `/addvideo <url> <title>` — Manually queue a video for the next 6:00 PM broadcast.
* `/queue` — View all manually queued videos.
* `/sendvideo` — Force an immediate broadcast of the next queued video.

## 💻 Technical Setup

**To start the bot permanently on macOS:**
```bash
bash start_bot.sh --install
```
*The bot runs as a background Launch Agent and will auto-restart if the Mac reboots.*

**To view logs:**
```bash
tail -f logs/bot.log
```
