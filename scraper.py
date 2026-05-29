import asyncio
import aiohttp
import re
import logging

PROXY_REGEX = re.compile(r'\b(\d{1,3}\.){3}\d{1,3}:\d{2,5}\b')

async def fetch_source(session, url):
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=15),
            ssl=False
        ) as r:
            text = await r.text(errors='ignore')
            found = PROXY_REGEX.findall(text)
            # findall returns groups — fix karo
            raw = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}\b', text)
            logging.info(f"✅ {url.split('/')[-1][:40]} → {len(raw)}")
            return raw
    except Exception as e:
        logging.warning(f"❌ {url[-40:]} → {e}")
        return []

async def scrape_all(sources):
    all_proxies = set()
    connector   = aiohttp.TCPConnector(limit=50, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        results = await asyncio.gather(
            *[fetch_source(session, url) for url in sources],
            return_exceptions=True
        )
        for r in results:
            if isinstance(r, list):
                all_proxies.update(r)
    logging.info(f"📦 Total unique raw: {len(all_proxies)}")
    return list(all_proxies)
