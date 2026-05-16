# 🚀 AI Industry Mentor Bot

An advanced Telegram bot designed to bridge the gap between students and the tech industry. It acts as a **Senior Industry Mentor**, providing real-world tasks, professional code reviews, and career guidance.

## ✨ Key Features
- **Industry Mentor Persona**: 15+ years of experience packed into an AI.
- **Dual Modes**: 
  - 📊 **Knowledge Mode**: Technical quizzes and professional sprint-style tasks.
  - 💬 **Communication Mode**: Free-form chat for debugging and career advice.
- **Voice Support**: Send voice notes for a natural mentoring experience (via Groq Whisper).
- **Web Intelligence**: Uses Google and Wikipedia to stay up-to-date with latest tech trends.
- **Premium UI**: Sleek Inline Buttons and real-time interactive feedback.
- **Performance Reviews**: Track your progress with detailed industry-standard reports.

## 🛠️ Tech Stack
- **AI**: Groq (Llama 3.3 70B & Whisper-v3)
- **Framework**: LangChain & python-telegram-bot
- **Database**: SQLite
- **Tools**: Google Search, Wikipedia API

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- A Groq API Key (from [Groq Console](https://console.groq.com/))

### 2. Installation
```bash
git clone https://github.com/Manish-sen-98/code-coach.git
cd code-coach
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 4. Run the Bot
```bash
python telegram_bot/bot.py
```

## 📈 Deployment
This project is ready for deployment on platforms like **Render**, **Railway**, or **Heroku**.
- **Procfile** included for worker deployment.
- **Logging** enabled for production monitoring.
- **Database** auto-migration handles updates automatically.

## 📝 License
MIT
