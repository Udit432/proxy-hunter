import os
import logging
import requests
import threading
import io

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

_get_alive_fn = None

def set_alive_getter(fn):
    global _get_alive_fn
    _get_alive_fn = fn

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
                timeout=60
            )
    except Exception as e:
        logging.error(f"Telegram file error: {e}")

def _send_from_memory(proxies):
    """Disk file ki zaroorat nahi — memory se seedha bhejo"""
    if not TOKEN or not CHAT_ID:
        return
    try:
        content = "\n".join(proxies).encode("utf-8")
        buf = io.BytesIO(content)
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendDocument",
            data={
                "chat_id": CHAT_ID,
                "caption": f"🟢 {len(proxies):,} alive proxies (live snapshot)"
            },
            files={"document": ("alive_proxies.txt", buf)},
            timeout=60
        )
        logging.info(f"Sent {len(proxies)} proxies from memory")
    except Exception as e:
        logging.error(f"Memory send error: {e}")

def start_bot(start_job_fn, stop_job_fn, status_fn):
    if not TOKEN:
        logging.warning("No TELEGRAM_TOKEN — bot disabled")
        return
    logging.info("🤖 Telegram bot started")
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
                    proxies = _get_alive_fn() if _get_alive_fn else []
                    if proxies:
                        send_msg(f"📤 Sending {len(proxies):,} proxies... wait karo")
                        threading.Thread(
                            target=_send_from_memory,
                            args=(proxies,),
                            daemon=True
                        ).start()
                    else:
                        send_msg("❌ Abhi koi proxy nahi. /hunt karo pehle.")

        except Exception as e:
            logging.error(f"Bot polling error: {e}")
            import time
            time.sleep(5)
