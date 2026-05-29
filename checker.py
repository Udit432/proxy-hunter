import asyncio
import aiohttp
import logging
import re

try:
    from aiohttp_socks import ProxyConnector, ProxyType
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    logging.warning("aiohttp-socks not available — socks proxies will be skipped")

CHECK_URL    = "http://httpbin.org/ip"
TIMEOUT_SEC  = 8
CONCURRENCY  = 200
IP_REGEX     = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

def _detect_type(proxy):
    """Port range se proxy type guess karo"""
    try:
        port = int(proxy.split(":")[1])
    except:
        return "http"
    # Common socks5 ports
    if port in (1080, 1081, 4145, 9050, 9150, 10800, 10801):
        return "socks5"
    # Common socks4 ports  
    if port in (4153, 4154, 1085, 1086):
        return "socks4"
    return "http"

async def _check_http(session, proxy, alive):
    """HTTP/HTTPS proxy check"""
    try:
        async with session.get(
            CHECK_URL,
            proxy=f"http://{proxy}",
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SEC),
            allow_redirects=False,
            ssl=False
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                # Genuine check: response mein IP hona chahiye
                if '"origin"' in text and IP_REGEX.search(text):
                    alive.append(proxy)
    except:
        pass

async def _check_socks(proxy, proto, alive):
    """SOCKS4/SOCKS5 proxy check"""
    if not SOCKS_AVAILABLE:
        return
    try:
        ip, port = proxy.split(":")
        ptype = ProxyType.SOCKS5 if proto == "socks5" else ProxyType.SOCKS4
        connector = ProxyConnector(
            proxy_type=ptype,
            host=ip,
            port=int(port),
            rdns=True
        )
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SEC)
        ) as s:
            async with s.get(CHECK_URL, allow_redirects=False, ssl=False) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if '"origin"' in text and IP_REGEX.search(text):
                        alive.append(proxy)
    except:
        pass

async def check_proxies(proxy_list, progress_callback=None, shared_list=None):
    alive = shared_list if shared_list is not None else []
    sem   = asyncio.Semaphore(CONCURRENCY)

    async def _guarded(proxy):
        async with sem:
            ptype = _detect_type(proxy)
            if ptype in ("socks4", "socks5"):
                await _check_socks(proxy, ptype, alive)
            else:
                await _check_http(session, proxy, alive)

    connector = aiohttp.TCPConnector(
        limit=CONCURRENCY, ssl=False,
        ttl_dns_cache=300,
        enable_cleanup_closed=True
    )
    async with aiohttp.ClientSession(connector=connector) as session:
        total, checked = len(proxy_list), 0
        for i in range(0, total, 1000):
            chunk = proxy_list[i:i+1000]
            await asyncio.gather(*[_guarded(p) for p in chunk])
            checked += len(chunk)
            pct = (checked / total) * 100
            logging.info(f"Progress: {checked}/{total} ({pct:.1f}%) | Alive: {len(alive)}")
            if progress_callback:
                progress_callback(checked, total, len(alive))

    return alive
