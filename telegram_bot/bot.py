import os
import sys
# pyrefly: ignore [missing-import]
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
# pyrefly: ignore [missing-import]
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.main_agent import MentorAgent

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Dict to store agent instances per user
user_agents = {}

def get_agent(user_id):
    if user_id not in user_agents:
        user_agents[user_id] = MentorAgent(user_id)
    return user_agents[user_id]

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agent = get_agent(user_id)
    
    response = await agent.process_message("/start") 
    
    welcome_text = (
        "Hello 👋\n"
        "I am your <b>AI Industry Mentor</b>.\n\n"
        "I have two modes:\n"
        "1. <b>Knowledge Mode</b> (/quiz): Real-world tasks and code reviews.\n"
        "2. <b>Communication Mode</b> (/chat): Free-form discussion and debugging help.\n\n"
    )
    
    # Persistent keyboard for modes
    mode_keyboard = [["/quiz", "/chat"]]
    reply_markup = ReplyKeyboardMarkup(mode_keyboard, resize_keyboard=True)

    if isinstance(response, dict):
        text = welcome_text + response.get("text", "")
        options = response.get("options", [])
        keyboard = [options[i:i + 2] for i in range(0, len(options), 2)]
        # Combine onboarding options with mode keyboard for this step
        keyboard.extend(mode_keyboard)
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_html(text, reply_markup=reply_markup)
    else:
        await update.message.reply_html(welcome_text + response, reply_markup=reply_markup)

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agent = get_agent(user_id)
    response = await agent.process_message("/quiz")
    await update.message.reply_html(response)

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agent = get_agent(user_id)
    response = await agent.process_message("/chat")
    await update.message.reply_html(response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>Available Commands:</b>\n"
        "/quiz - Switch to Knowledge Mode\n"
        "/chat - Switch to Communication Mode\n"
        "/report - Performance Review\n"
        "/reset - Start fresh\n"
        "/help - Show this help"
    )

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agent = get_agent(user_id)
    
    status_msg = await update.message.reply_text("📊 Compiling your Performance Review...")
    try:
        report = await agent.generate_report()
        await status_msg.edit_text(report, parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error compiling review: {str(e)}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agent = get_agent(user_id)
    response = await agent.reset_state()
    # Remove keyboard and then show start keyboard
    await update.message.reply_html(response, reply_markup=ReplyKeyboardRemove())
    await start_command(update, context)

import html

from llm.llm import transcribe_audio

async def process_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
    user_id = update.effective_user.id
    agent = get_agent(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("💭 <i>Mentor is thinking...</i>", parse_mode="HTML")

    try:
        response = await agent.process_message(user_message)
        
        mode_keyboard = [["/quiz", "/chat"]]
        
        if isinstance(response, dict):
            text = response.get("text", "")
            options = response.get("options", [])
            keyboard = [options[i:i + 2] for i in range(0, len(options), 2)]
            keyboard.extend(mode_keyboard)
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await status_msg.delete() 
            await update.message.reply_html(text, reply_markup=reply_markup)
        else:
            await status_msg.edit_text(response, parse_mode="HTML")
            await update.message.reply_text("Options:", reply_markup=ReplyKeyboardMarkup(mode_keyboard, resize_keyboard=True))

    except Exception as e:
        error_msg = html.escape(str(e))
        await status_msg.edit_text(f"⚠️ <b>An error occurred:</b>\n<code>{error_msg}</code>", parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_and_respond(update, context, update.message.text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🎤 <i>Listening to your voice note...</i>", parse_mode="HTML")
    
    try:
        # Download the voice file
        voice_file = await update.message.voice.get_file()
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{update.message.voice.file_id}.ogg"
        await voice_file.download_to_drive(file_path)
        
        # Transcribe
        transcribed_text = await transcribe_audio(file_path)
        
        # Cleanup
        os.remove(file_path)
        
        await status_msg.edit_text(f"📝 <b>Transcribed:</b>\n<i>\"{transcribed_text}\"</i>", parse_mode="HTML")
        
        # Process as a normal message
        await process_and_respond(update, context, transcribed_text)
        
    except Exception as e:
        error_msg = html.escape(str(e))
        await status_msg.edit_text(f"⚠️ <b>Voice Error:</b>\n<code>{error_msg}</code>", parse_mode="HTML")

def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("chat", chat_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("reset", reset_command))

    # Text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Voice handler
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("Mentor Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
