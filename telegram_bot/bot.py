import os
import sys
import logging
import html
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove
)
# pyrefly: ignore [missing-import]
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.main_agent import MentorAgent
from llm.llm import transcribe_audio
from utils.storage import init_db

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
        "🏆 <b>AI Industry Mentor</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Welcome to your professional growth journey. I help you build industry-standard skills through real-world tasks.\n\n"
        "<b>Choose your mode to begin:</b>"
    )
    
    # Inline buttons for a more premium feel
    keyboard = [
        [
            InlineKeyboardButton("📊 Knowledge Mode", callback_data="mode_quiz"),
            InlineKeyboardButton("💬 Comm Mode", callback_data="mode_chat")
        ],
        [InlineKeyboardButton("📈 Performance Review", callback_data="show_report")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(response, dict):
        text = response.get("text", "")
        options = response.get("options", [])
        
        # Create interactive onboarding buttons
        onboarding_keyboard = [[InlineKeyboardButton(opt, callback_data=f"onboarding_{opt}")] for opt in options]
        markup = InlineKeyboardMarkup(onboarding_keyboard)
        
        await update.message.reply_html(f"👋 {text}", reply_markup=markup)
    else:
        await update.message.reply_html(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    agent = get_agent(user_id)
    
    await query.answer() # Acknowledge the click
    
    data = query.data
    
    if data == "mode_quiz":
        response = await agent.process_message("/quiz")
        await query.edit_message_text(response, parse_mode="HTML")
    elif data == "mode_chat":
        response = await agent.process_message("/chat")
        await query.edit_message_text(response, parse_mode="HTML")
    elif data == "show_report":
        report = await agent.generate_report()
        await query.message.reply_html(report)
    elif data.startswith("onboarding_"):
        choice = data.replace("onboarding_", "")
        response = await agent.process_message(choice)
        
        if isinstance(response, dict):
            options = response.get("options", [])
            keyboard = [[InlineKeyboardButton(opt, callback_data=f"onboarding_{opt}")] for opt in options]
            await query.edit_message_text(response.get("text", ""), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            await query.edit_message_text(response, parse_mode="HTML")

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
        voice_file = await update.message.voice.get_file()
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{update.message.voice.file_id}.ogg"
        await voice_file.download_to_drive(file_path)
        
        transcribed_text = await transcribe_audio(file_path)
        os.remove(file_path)
        
        await status_msg.edit_text(f"📝 <b>Transcribed:</b>\n<i>\"{transcribed_text}\"</i>", parse_mode="HTML")
        await process_and_respond(update, context, transcribed_text)
        
    except Exception as e:
        error_msg = html.escape(str(e))
        await status_msg.edit_text(f"⚠️ <b>Voice Error:</b>\n<code>{error_msg}</code>", parse_mode="HTML")

async def process_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
    user_id = update.effective_user.id
    agent = get_agent(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("💭 <i>Mentor is thinking...</i>", parse_mode="HTML")

    try:
        response = await agent.process_message(user_message)
        
        mode_keyboard = [
            [
                InlineKeyboardButton("📊 Knowledge", callback_data="mode_quiz"),
                InlineKeyboardButton("💬 Chat", callback_data="mode_chat")
            ]
        ]
        
        if isinstance(response, dict):
            text = response.get("text", "")
            options = response.get("options", [])
            keyboard = [[InlineKeyboardButton(opt, callback_data=f"onboarding_{opt}")] for opt in options]
            await status_msg.delete() 
            await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await status_msg.edit_text(response, parse_mode="HTML")
            await update.message.reply_html("<b>Quick Actions:</b>", reply_markup=InlineKeyboardMarkup(mode_keyboard))

    except Exception as e:
        error_msg = html.escape(str(e))
        await status_msg.edit_text(f"⚠️ <b>An error occurred:</b>\n<code>{error_msg}</code>", parse_mode="HTML")

def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env")
        return

    # Initialize Database
    init_db()
    logger.info("Database initialized successfully.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("chat", chat_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("reset", reset_command))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Mentor Bot is starting polling...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
