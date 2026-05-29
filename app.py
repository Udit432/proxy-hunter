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
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
app           = Flask(__name__)
ALL_ALIVE     = []
CURRENT_ALIVE = []
IS_RUNNING    = False
LAST_RUN      = "Never"
STATS         = {}
OUTPUT_ALL    = "alive_proxies.txt"
def save_proxies(proxies):
    with open(OUTPUT_ALL, "w") as f:
        f.write("\n".join(proxies))
    logging.info(f"💾 Saved {len(proxies)} proxies")
def run_hunt():
    global ALL_ALIVE, CURRENT_ALIVE, IS_RUNNING, LAST_RUN, STATS
    if IS_RUNNING:
        logging.info("Hunt already running, skip.")
        return
    IS_RUNNING    = True
    CURRENT_ALIVE = []
    t0            = datetime.now()
    send_msg("🚀 <b>Proxy Hunt Started!</b>\n⏳ Scraping from 150+ sources...")
    try:
        raw = asyncio.run(scrape_all(SOURCES))
        send_msg(f"📦 <b>Scraped:</b> {len(raw):,} raw proxies\n⚡ Checking (HTTP+SOCKS verified)...")
        def progress_cb(done, total, alive_count):
            if done % 10000 == 0:
                pct = (done / total) * 100
                save_proxies(list(set(ALL_ALIVE + CURRENT_ALIVE)))
                send_msg(
                    f"⏳ Progress: {done:,}/{total:,} ({pct:.0f}%)\n"
                    f"✅ Verified alive: {alive_count:,}"
                )
        alive = asyncio.run(
            check_proxies(raw, progress_callback=progress_cb, shared_list=CURRENT_ALIVE)
        )
        ALL_ALIVE     = list(set(ALL_ALIVE + alive))
        CURRENT_ALIVE = []
        save_proxies(ALL_ALIVE)
        elapsed  = int((datetime.now() - t0).total_seconds())
        LAST_RUN = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATS    = {"raw": len(raw), "alive_this_run": len(alive),
                    "total_accumulated": len(ALL_ALIVE), "elapsed_sec": elapsed}
        send_msg(
            f"✅ <b>Hunt Complete!</b>\n\n"
            f"🔍 Scraped: {len(raw):,}\n"
            f"✅ Verified alive: {len(alive):,}\n"
            f"📦 Total accumulated: {len(ALL_ALIVE):,}\n"
            f"⏱ Time: {elapsed}s"
        )
        if len(alive) >= 100:
            send_file(OUTPUT_ALL, f"🟢 {len(ALL_ALIVE):,} VERIFIED alive proxies")
    except Exception as e:
        send_msg(f"❌ Hunt error: {e}")
        logging.error(f"Hunt error: {e}")
    finally:
        IS_RUNNING = False
def stop_hunt():
    global IS_RUNNING
    IS_RUNNING = False
    send_msg("⏹ Hunt stopped.")
def get_status():
    total = len(set(ALL_ALIVE + CURRENT_ALIVE))
    return (f"📊 <b>Status</b>\n\n🔄 Running: {'Yes' if IS_RUNNING else 'No'}\n"
            f"✅ Verified alive: {total:,}\n🕐 Last run: {LAST_RUN}\n📈 {STATS}")
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
    return jsonify({"status": "alive", "proxies": len(set(ALL_ALIVE + CURRENT_ALIVE)),
                    "running": IS_RUNNING, "last_run": LAST_RUN}), 200
@app.route("/start")
def web_start():
    threading.Thread(target=run_hunt, daemon=True).start()
    return jsonify({"msg": "Hunt started"}), 200
@app.route("/stop")
def web_stop():
    stop_hunt()
    return jsonify({"msg": "Stopped"}), 200
@app.route("/status")
def web_status():
    return jsonify({"running": IS_RUNNING, "total_alive": len(set(ALL_ALIVE + CURRENT_ALIVE)),
                    "last_run": LAST_RUN, "stats": STATS}), 200
@app.route("/proxies")
def web_proxies():
    return "\n".join(set(ALL_ALIVE + CURRENT_ALIVE)), 200, {"Content-Type": "text/plain"}
if __name__ == "__main__":
    set_alive_getter(lambda: list(set(ALL_ALIVE + CURRENT_ALIVE)))
    threading.Thread(target=start_bot,
        args=(lambda: threading.Thread(target=run_hunt, daemon=True).start(),
              stop_hunt, get_status), daemon=True).start()
    threading.Thread(target=_auto_scheduler, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
