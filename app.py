import asyncio
import threading
import logging
import os
from datetime import datetime
from flask import Flask, jsonify

from sources import SOURCES
from scraper import scrape_all
from checker import check_proxies
from bot     import send_msg, send_file, start_bot, set_alive_getter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app        = Flask(__name__)
ALL_ALIVE  = []
IS_RUNNING = False
LAST_RUN   = "Never"
STATS      = {}

OUTPUT_ALL = "alive_proxies.txt"

def save_proxies(proxies):
    with open(OUTPUT_ALL, "w") as f:
        f.write("\n".join(proxies))
    logging.info(f"💾 Saved {len(proxies)} proxies to {OUTPUT_ALL}")

def run_hunt():
    global ALL_ALIVE, IS_RUNNING, LAST_RUN, STATS
    if IS_RUNNING:
        logging.info("Hunt already running, skip.")
        return
    IS_RUNNING = True
    t0    = datetime.now()
    alive = []
    send_msg("🚀 <b>Proxy Hunt Started!</b>\n⏳ Scraping from 150+ sources...")

    try:
        raw = asyncio.run(scrape_all(SOURCES))
        send_msg(
            f"📦 <b>Scraped:</b> {len(raw):,} raw proxies\n"
            f"⚡ Checking alive status (500 concurrent)..."
        )

        def progress_cb(done, total, alive_count):
            if done % 10000 == 0:
                pct = (done / total) * 100
                save_proxies(list(set(ALL_ALIVE + alive)))
                send_msg(
                    f"⏳ Progress: {done:,}/{total:,} ({pct:.0f}%)\n"
                    f"✅ Alive so far: {alive_count:,}"
                )

        alive = asyncio.run(check_proxies(raw, progress_callback=progress_cb))

        ALL_ALIVE = list(set(ALL_ALIVE + alive))
        save_proxies(ALL_ALIVE)

        elapsed  = int((datetime.now() - t0).total_seconds())
        LAST_RUN = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATS    = {
            "raw": len(raw),
            "alive_this_run": len(alive),
            "total_accumulated": len(ALL_ALIVE),
            "elapsed_sec": elapsed
        }

        summary = (
            f"✅ <b>Hunt Complete!</b>\n\n"
            f"🔍 Scraped: {len(raw):,}\n"
            f"✅ Alive (this run): {len(alive):,}\n"
            f"📦 Total accumulated: {len(ALL_ALIVE):,}\n"
            f"⏱ Time: {elapsed}s\n"
            f"🕐 Run at: {LAST_RUN}"
        )
        send_msg(summary)

        if len(alive) >= 500:
            send_file(OUTPUT_ALL, f"🟢 {len(ALL_ALIVE):,} accumulated alive proxies")

    except Exception as e:
        send_msg(f"❌ Hunt error: {e}")
        logging.error(f"Hunt error: {e}")
    finally:
        IS_RUNNING = False

def stop_hunt():
    global IS_RUNNING
    IS_RUNNING = False
    send_msg("⏹ Hunt stopped by user.")

def get_status():
    return (
        f"📊 <b>Status</b>\n\n"
        f"🔄 Running: {'Yes' if IS_RUNNING else 'No'}\n"
        f"✅ Total alive: {len(ALL_ALIVE):,}\n"
        f"🕐 Last run: {LAST_RUN}\n"
        f"📈 Stats: {STATS}"
    )

def _auto_scheduler():
    import time
    time.sleep(10)
    while True:
        try:
            run_hunt()
        except Exception as e:
            logging.error(f"Scheduler error: {e}")
        logging.info("⏰ Next hunt in 90 minutes...")
        time.sleep(90 * 60)

@app.route("/")
@app.route("/ping")
def ping():
    return jsonify({
        "status": "alive",
        "proxies": len(ALL_ALIVE),
        "running": IS_RUNNING,
        "last_run": LAST_RUN
    }), 200

@app.route("/start")
def web_start():
    t = threading.Thread(target=run_hunt, daemon=True)
    t.start()
    return jsonify({"msg": "Hunt started"}), 200

@app.route("/stop")
def web_stop():
    stop_hunt()
    return jsonify({"msg": "Stop flag set"}), 200

@app.route("/status")
def web_status():
    return jsonify({
        "running": IS_RUNNING,
        "total_alive": len(ALL_ALIVE),
        "last_run": LAST_RUN,
        "stats": STATS
    }), 200

@app.route("/proxies")
def web_proxies():
    return "\n".join(ALL_ALIVE), 200, {"Content-Type": "text/plain"}

if __name__ == "__main__":
    # Memory getter register karo — /getfile mid-hunt bhi kaam karega
    set_alive_getter(lambda: list(ALL_ALIVE))

    bot_thread = threading.Thread(
        target=start_bot,
        args=(
            lambda: threading.Thread(target=run_hunt, daemon=True).start(),
            stop_hunt,
            get_status
        ),
        daemon=True
    )
    bot_thread.start()

    sched_thread = threading.Thread(target=_auto_scheduler, daemon=True)
    sched_thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
