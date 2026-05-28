import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

TOKEN   = os.environ["8612747382:AAGaAPhsNeagH5RD0kZQHAHnH9Tm7c-V39M"]
CHAT_ID = os.environ["5081251584"]

_job_ref    = None  # scheduler job reference
_is_running = False

def send_msg(text):
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        )
    except Exception as e:
        logging.error(f"Telegram send error: {e}")

def send_file(filepath, caption=""):
    try:
        import requests
        with open(filepath, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": f}
            )
    except Exception as e:
        logging.error(f"Telegram file error: {e}")

def start_bot(start_job_fn, stop_job_fn, status_fn):
    updater = Updater(TOKEN)
    dp      = updater.dispatcher

    def cmd_start(update: Update, ctx: CallbackContext):
        keyboard = [
            [InlineKeyboardButton("▶️ Start Hunt", callback_data="start"),
             InlineKeyboardButton("⏹ Stop", callback_data="stop")],
            [InlineKeyboardButton("📊 Status", callback_data="status"),
             InlineKeyboardButton("📁 Get File", callback_data="getfile")],
        ]
        update.message.reply_text(
            "🤖 <b>Proxy Hunter Bot</b>\n\nCommands:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    def cb_handler(update: Update, ctx: CallbackContext):
        q    = update.callback_query
        data = q.data
        q.answer()
        if data == "start":
            start_job_fn()
            q.edit_message_text("🚀 Proxy hunt started!")
        elif data == "stop":
            stop_job_fn()
            q.edit_message_text("⏹ Hunt stopped.")
        elif data == "status":
            q.edit_message_text(status_fn())
        elif data == "getfile":
            if os.path.exists("alive_proxies.txt"):
                send_file("alive_proxies.txt", "🟢 Latest alive proxies")
                q.edit_message_text("📁 File sent!")
            else:
                q.edit_message_text("❌ No file yet. Run a hunt first.")

    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CallbackQueryHandler(cb_handler))
    updater.start_polling()
    logging.info("Bot started polling...")
