import os
import logging
import requests
import threading

TOKEN   = os.environ.get("8612747382:AAGaAPhsNeagH5RD0kZQHAHnH9Tm7c-V39M", "")
CHAT_ID = os.environ.get("5081251584", "")

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        logging.warning("Telegram not configured")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        logging.error(f"Telegram send error: {e}")

def send_file(filepath, caption=""):
    if not TOKEN or not CHAT_ID:
        return
    try:
        with open(filepath, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": f},
                timeout=30
            )
    except Exception as e:
        logging.error(f"Telegram file error: {e}")

def start_bot(start_job_fn, stop_job_fn, status_fn):
    """
    Long-polling bot using raw HTTP — no python-telegram-bot library needed.
    Supports: /start, /hunt, /stop, /status, /getfile
    """
    if not TOKEN:
        logging.warning("No TELEGRAM_TOKEN set — bot disabled")
        return

    logging.info("🤖 Telegram bot started (raw polling)")
    offset = 0

    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35
            )
            updates = r.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message") or update.get("callback_query", {}).get("message")
                if not msg:
                    continue

                chat_id = str(msg["chat"]["id"])
                text    = msg.get("text", "")

                # Only respond to authorized chat
                if CHAT_ID and chat_id != str(CHAT_ID):
                    continue

                if "/start" in text or "/help" in text:
                    send_msg(
                        "🤖 <b>Proxy Hunter Bot</b>\n\n"
                        "/hunt — Start proxy hunt\n"
                        "/stop — Stop hunt\n"
                        "/status — Show status\n"
                        "/getfile — Get alive proxies file"
                    )
                elif "/hunt" in text:
                    threading.Thread(target=start_job_fn, daemon=True).start()
                    send_msg("🚀 Hunt started!")
                elif "/stop" in text:
                    stop_job_fn()
                    send_msg("⏹ Hunt stopped.")
                elif "/status" in text:
                    send_msg(status_fn())
                elif "/getfile" in text:
                    if os.path.exists("alive_proxies.txt"):
                        send_file("alive_proxies.txt", "🟢 Latest alive proxies")
                    else:
                        send_msg("❌ No file yet. Run /hunt first.")

        except Exception as e:
            logging.error(f"Bot polling error: {e}")
            import time
            time.sleep(5)
