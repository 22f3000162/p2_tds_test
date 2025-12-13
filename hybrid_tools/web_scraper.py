"""
Enhanced web scraper with async support, caching, and context extraction.
Uses Playwright for JS-rendered pages with HTTP fallback.
Integrated with persistent EventLoopManager (NO asyncio.run hacks).
"""

from langchain_core.tools import tool
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import asyncio


# --------------------------------------------------
# INTERNAL ASYNC IMPLEMENTATION
# --------------------------------------------------
async def _get_rendered_html_async(url: str) -> str:
    from hybrid_tools.cache_manager import get_html_cache
    from hybrid_tools.http_client import get_with_retry

    cache = get_html_cache()
    cached = cache.get(url)
    if cached:
        print(f"[WEB_SCRAPER] ⚡ Cache hit")
        return cached

    print(f"\n[WEB_SCRAPER] 🌐 Rendering: {url}")

    # --------------------------------------------------
    # PLAYWRIGHT RENDER
    # --------------------------------------------------
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            html = await page.content()

            # ---------------- LINKS ----------------
            links = []
            for a in await page.query_selector_all("a"):
                href = await a.get_attribute("href")
                try:
                    text = await a.inner_text()
                except Exception:
                    text = ""
                if href:
                    links.append({
                        "url": urljoin(url, href),
                        "text": text[:80]
                    })

            # ---------------- FORMS ----------------
            forms = []
            for form in await page.query_selector_all("form"):
                action = await form.get_attribute("action")
                method = (await form.get_attribute("method")) or "GET"
                if action:
                    forms.append({
                        "action": urljoin(url, action),
                        "method": method.upper()
                    })

            await browser.close()

        # ---------------- API URL EXTRACTION ----------------
        soup = BeautifulSoup(html, "html.parser")
        api_urls = []

        for script in soup.find_all("script"):
            txt = script.string or ""
            matches = re.findall(r'["\']https?://[^"\']+["\']', txt)
            for m in matches:
                clean = m.strip('"\'')
                if "api" in clean.lower() or clean.endswith(".json"):
                    api_urls.append(clean)

        # ---------------- CONTEXT METADATA ----------------
        meta = "\n\n<!-- CONTEXT_METADATA\n"
        meta += f"Links: {len(links)}, Forms: {len(forms)}, APIs: {len(api_urls)}\n"

        if links[:5]:
            meta += "Top links:\n"
            for l in links[:5]:
                meta += f"  - {l['text']}: {l['url']}\n"

        if forms:
            meta += "Forms:\n"
            for f in forms[:5]:
                meta += f"  - {f['method']} {f['action']}\n"

        if api_urls:
            meta += "APIs:\n"
            for api in api_urls[:5]:
                meta += f"  - {api}\n"

        meta += "-->\n"

        result = html + meta
        cache.set(url, result, ttl=3600)

        print(f"[WEB_SCRAPER] ✅ Rendered via Playwright")
        return result

    # --------------------------------------------------
    # FALLBACK: SIMPLE HTTP
    # --------------------------------------------------
    except Exception as e:
        print(f"[WEB_SCRAPER] ⚠️ Playwright failed: {e}")
        print("[WEB_SCRAPER] 🔄 Falling back to HTTP")

        try:
            resp = await get_with_retry(url)
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            links = []
            for a in soup.find_all("a", href=True):
                links.append({
                    "url": urljoin(url, a["href"]),
                    "text": a.get_text(strip=True)[:80]
                })

            forms = []
            for f in soup.find_all("form"):
                action = f.get("action")
                method = f.get("method", "GET").upper()
                if action:
                    forms.append({
                        "action": urljoin(url, action),
                        "method": method
                    })

            meta = "\n\n<!-- CONTEXT_METADATA (HTTP FALLBACK)\n"
            meta += f"Links: {len(links)}, Forms: {len(forms)}\n"

            if links[:5]:
                meta += "Top links:\n"
                for l in links[:5]:
                    meta += f"  - {l['text']}: {l['url']}\n"

            if forms:
                meta += "Forms:\n"
                for f in forms[:5]:
                    meta += f"  - {f['method']} {f['action']}\n"

            meta += "-->\n"

            result = html + meta
            cache.set(url, result, ttl=3600)

            print(f"[WEB_SCRAPER] ✅ Loaded via HTTP fallback")
            return result

        except Exception as e2:
            error = f"[WEB_SCRAPER ERROR] {e} | {e2}"
            print(error)
            return error


# --------------------------------------------------
# LANGCHAIN TOOL WRAPPER
# --------------------------------------------------
@tool
def get_rendered_html(url: str) -> str:
    """
    Fetch fully rendered HTML with JS execution and rich context.

    MUST be used only for HTML pages.
    DO NOT use for direct files (.pdf, .csv, .png).
    """
    from hybrid_tools.event_loop_manager import run_async
    return run_async(_get_rendered_html_async(url))
