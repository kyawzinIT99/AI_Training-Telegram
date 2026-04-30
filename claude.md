# AI Training Telegram Bot — Project Architecture

## Overview

This is a **Telegram Bot** that serves as a **Master AI Tutor** for AI training courses.
It uses **Claude 3.5 Haiku** (Anthropic) for cost-effective AI-powered tutoring and
retrieves training videos from **Google Drive** for delivery to students.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Telegram Users (Students)           │
│              Ask questions / Request videos       │
└───────────────┬─────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│           Telegram Bot (python-telegram-bot)     │
│                                                   │
│  Commands:                                        │
│    /start   — Welcome message                     │
│    /video   — Fetch video from Google Drive       │
│    /latest  — Show newest training videos         │
│    /clear   — Reset conversation history          │
│    /help    — Show commands                       │
│    [text]   — Forward to AI Tutor                 │
└──────┬──────────────────────────┬───────────────┘
       │                          │
       ▼                          ▼
┌──────────────┐        ┌─────────────────┐
│  Claude      │        │  Google Drive    │
│  3.5 Haiku   │        │  API v3         │
│              │        │                  │
│  AI Tutor    │        │  Video Retrieval │
│  Responses   │        │  by ID / Folder  │
└──────────────┘        └─────────────────┘
```

## File Structure

| File | Purpose |
|------|---------|
| `.env` | API keys (Telegram, Anthropic, Google Drive) |
| `requirements.txt` | All Python dependencies |
| `config/settings.py` | Centralized config loader from `.env` |
| `bot/main.py` | Entry point — starts the bot |
| `bot/handlers.py` | Telegram command & message handlers |
| `bot/ai_tutor.py` | Claude Haiku integration with per-user memory |
| `bot/drive_service.py` | Google Drive video retrieval |

## How It Works

### 1. Student sends a question
```
Student → Telegram → handlers.py → ai_tutor.py → Claude Haiku → response → Telegram → Student
```

### 2. Student requests a video
```
Student → /video <id> → handlers.py → drive_service.py → Google Drive API → video link → Telegram → Student
```

### 3. You upload daily videos
```
You → Upload to Google Drive folder → Students use /latest → Bot lists newest videos
```

## Cost Estimation (Claude 3.5 Haiku)

| Metric | Cost |
|--------|------|
| Input tokens | ~$0.25 per million tokens |
| Output tokens | ~$1.25 per million tokens |
| Avg. question (500 tokens in, 300 out) | ~$0.0005 per question |
| 100 questions/day | ~$0.05/day (~$1.50/month) |

## Commands Quick Reference

```
/start          — Welcome & introduction
/video <id>     — Get video by Google Drive file ID
/latest         — List newest training videos
/clear          — Reset conversation memory
/help           — Show all commands
```

## Running the Bot

```bash
# 1. Fill in your API keys
nano .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify configuration
python -m bot.main --verify

# 4. Start the bot
python -m bot.main
```
