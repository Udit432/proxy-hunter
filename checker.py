import asyncio
import aiohttp
import logging

CHECK_URL   = "http://httpbin.org/ip"
TIMEOUT_SEC = 6
CONCURRENCY = 500

async def _check(session, proxy, alive):
    try:
        async with session.get(
            CHECK_URL,
            proxy=f"http://{proxy}",
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SEC),
            allow_redirects=True
        ) as resp:
            if resp.status == 200:
                alive.append(proxy)
    except:
        pass

async def check_proxies(proxy_list, progress_callback=None, shared_list=None):
    # ✅ shared_list pass karo toh wahi use hogi — bahar se real-time visible
    alive = shared_list if shared_list is not None else []

    sem       = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False, ttl_dns_cache=300)

    async def _guarded(proxy):
        async with sem:
            await _check(session, proxy, alive)

    async with aiohttp.ClientSession(connector=connector) as session:
        total   = len(proxy_list)
        batch   = 1000
        checked = 0
        for i in range(0, total, batch):
            chunk = proxy_list[i:i+batch]
            await asyncio.gather(*[_guarded(p) for p in chunk])
            checked += len(chunk)
            pct = (checked / total) * 100
            logging.info(f"Progress: {checked}/{total} ({pct:.1f}%) | Alive: {len(alive)}")
            if progress_callback:
                progress_callback(checked, total, len(alive))

    return alive
