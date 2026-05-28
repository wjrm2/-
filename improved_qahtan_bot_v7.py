import logging
import os
import time
import asyncio
import json
from threading import Thread
from collections import defaultdict
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Improved Libraries for Performance
import uvloop

load_dotenv()
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

uvloop.install()

# ================= Enhanced Bot Settings =================
BOT_NAME = "Qahtan"
BOT_VERSION = "7.0"
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 8080))
MODEL = "gpt-4"

MAX_MSG_LEN = 4096
RATE_LIMIT_COUNT = 10
RATE_LIMIT_SECONDS = 60
USER_HISTORY_LIMIT = 50

flask_app = Flask(__name__)
bot_start_time = time.time()

# ================= Enhanced Memories via Redis/SQLite =================
# In production, Redis or PostgreSQL can be plugged here for real scaling
conversation_history = defaultdict(list)
user_rate_limits = defaultdict(list)
user_settings = defaultdict(lambda: {"personality": "default"})  # Personalized settings

# ================= Personalities =================
PERSONALITIES = {
    "default": "You are Qahtan, a smart AI bot in version 7.0 that is friendly, helpful, and intuitive.",
    "educator": "You are Qahtan, a teaching-focused AI capable of clear and detailed explanations.",
    "sarcastic": "You are Qahtan, a witty AI with a sarcastic edge while maintaining helpfulness.",
    "philosopher": "You are Qahtan, a thoughtful and wise philosopher bot that ponders deeply."
}

# ================= Flask Routes =================
@flask_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running", "version": BOT_VERSION, "uptime": int(time.time() - bot_start_time)})

@flask_app.route("/stats", methods=["GET"])
def stats():
    return jsonify({
        "total_users": len(conversation_history),
        "start_time": bot_start_time,
        "active_sessions": len([h for h in conversation_history.values() if h])
    })

def start_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False)

# ================= Helper Functions =================
def enforce_rate_limit(user_id):
    now = time.time()
    user_rate_limits[user_id] = [t for t in user_rate_limits[user_id] if now - t < RATE_LIMIT_SECONDS]
    if len(user_rate_limits[user_id]) >= RATE_LIMIT_COUNT:
        return False
    user_rate_limits[user_id].append(now)
    return True

def split_message(message):
    chunks = [message[i:i + MAX_MSG_LEN] for i in range(0, len(message), MAX_MSG_LEN)]
    return chunks

async def fetch_gpt_response(query, personality):
    # Placeholder GPT handler for OpenAI
    try:
        # Mocked response can eventually call: `openai.ChatCompletion.create`
        return f"[{personality}] Response: {query[:50]}... answered with extension."
    except Exception as error:
        logger.error(f"GPT API Failure:: {error}")
        return "Failed GPT Processing. Try Later."

# Command: Start Bot
async def start_command(update: Update, context):
    keyboard = [[InlineKeyboardButton("Chat 🚀", callback_data="start_chat")],
                [InlineKeyboardButton("Preferences ⚙️", callback_data="settings_menu")]]
    welcome = f"Welcome to {BOT_NAME} v{BOT_VERSION}! Your advanced all-rounded assistant."
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))

# Command: Rate-limiting-friendly Chat System
async def message_handler(update, context):
    content, uid = update.message.text.strip(), update.effective_user.id

    if not enforce_rate_limit(uid):
        await update.message.reply_text("⚠️ Too Fast! You are rate limited.")
        return

    # Manage Personality Mid-conversation
    user_persona = user_settings[uid]["personality"]
    full_history = conversation_history[uid][-USER_HISTORY_LIMIT:] + [content]

    response = await fetch_gpt_response(content, user_persona)

    for submsg in split_message(response):
        await update.message.reply_text(submsg)

if __name__ == "__main__":
    flask_thread = Thread(target=start_flask)
    flask_thread.daemon, flask_thread.start()

    telegram_app = Application.builder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start"))
    telegram_app.run_polling()