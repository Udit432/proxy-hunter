import asyncio
import aiohttp
import logging

CHECK_URLS  = [
    "http://www.google.com",
    "http://www.bing.com", 
    "http://example.com",
]
TIMEOUT_SEC = 10
CONCURRENCY = 300

async def _check(session, proxy, alive):
    for url in CHECK_URLS:
        try:
            async with session.get(
                url,
                proxy=f"http://{proxy}",
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SEC),
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                }
            ) as resp:
                if resp.status in [200, 301, 302]:
                    alive.append(proxy)
                    return
        except:
            continue

async def check_proxies(proxy_list, progress_callback=None):
    alive = []
    sem   = asyncio.Semaphore(CONCURRENCY)
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
