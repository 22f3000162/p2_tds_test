"""
Context extraction tool.
Extracts rich, structured context from HTML pages.
"""

from langchain_core.tools import tool
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json
from typing import Dict, Any, List


@tool
def extract_context(html: str, base_url: str = "") -> Dict[str, Any]:
    """
    Extract structured context from HTML.

    Extracts:
    - submit URLs
    - API URLs
    - sampled API responses (best-effort)
    - JavaScript hints
    - form structures
    - full page text (instructions)

    Returns:
    - Dict[str, Any] (JSON serializable)
    """

    print(f"\n[CONTEXT] 🔍 Extracting context ({len(html)} chars)")

    try:
        soup = BeautifulSoup(html, "html.parser")

        context: Dict[str, Any] = {
            "submit_urls": [],
            "api_urls": [],
            "api_samples": {},
            "forms": [],
            "javascript_count": 0,
            "sample_javascript": "",
            "page_text": "",
        }

        # --------------------------------------------------
        # SUBMIT URL EXTRACTION
        # --------------------------------------------------
        submit_urls: List[str] = []

        # Forms
        for form in soup.find_all("form"):
            action = form.get("action")
            if action:
                submit_urls.append(
                    urljoin(base_url, action) if base_url else action
                )

        # Text-based hints
        page_text_raw = soup.get_text(" ", strip=True)
        submit_patterns = [
            r"(?:submit|post)\s+(?:to|at)\s+([^\s<]+)",
            r"endpoint\s*[:=]\s*([^\s<]+)",
        ]

        for pat in submit_patterns:
            for match in re.findall(pat, page_text_raw, re.IGNORECASE):
                submit_urls.append(
                    urljoin(base_url, match) if base_url else match
                )

        context["submit_urls"] = sorted(set(submit_urls))

        # --------------------------------------------------
        # API URL EXTRACTION
        # --------------------------------------------------
        api_urls: List[str] = []

        # Anchor tags
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "api" in href.lower() or href.lower().endswith(".json"):
                api_urls.append(urljoin(base_url, href) if base_url else href)

        # Script blocks
        for script in soup.find_all("script"):
            script_text = script.string or ""
            urls = re.findall(r"https?://[^\s\"']+", script_text)
            for u in urls:
                if "api" in u.lower() or u.lower().endswith(".json"):
                    api_urls.append(u)

        context["api_urls"] = sorted(set(api_urls))

        # --------------------------------------------------
        # JAVASCRIPT HINTS
        # --------------------------------------------------
        scripts = [s.string for s in soup.find_all("script") if s.string]
        context["javascript_count"] = len(scripts)
        if scripts:
            context["sample_javascript"] = scripts[0][:500]

        # --------------------------------------------------
        # API SAMPLING (BEST-EFFORT, NON-BLOCKING)
        # --------------------------------------------------
        if api_urls:
            try:
                from hybrid_tools.http_client import get_with_retry
                from hybrid_tools.event_loop_manager import run_async

                for api_url in api_urls[:3]:
                    try:
                        resp = run_async(get_with_retry(api_url))
                        if resp.status_code == 200:
                            try:
                                context["api_samples"][api_url] = resp.json()
                            except Exception:
                                context["api_samples"][api_url] = resp.text[:300]
                    except Exception:
                        continue
            except Exception:
                pass

        # --------------------------------------------------
        # FORMS
        # --------------------------------------------------
        forms: List[Dict[str, Any]] = []
        for form in soup.find_all("form"):
            form_info = {
                "action": form.get("action", ""),
                "method": form.get("method", "GET").upper(),
                "inputs": [],
            }

            for inp in form.find_all("input"):
                form_info["inputs"].append(
                    {
                        "name": inp.get("name", ""),
                        "type": inp.get("type", "text"),
                    }
                )

            forms.append(form_info)

        context["forms"] = forms

        # --------------------------------------------------
        # PAGE TEXT (CRITICAL)
        # --------------------------------------------------
        context["page_text"] = page_text_raw

        # --------------------------------------------------
        # DEBUG LOG
        # --------------------------------------------------
        print(f"[CONTEXT] ✓ submit_urls: {context['submit_urls']}")
        print(f"[CONTEXT] ✓ api_urls: {context['api_urls']}")
        print(f"[CONTEXT] ✓ api_samples: {len(context['api_samples'])}")
        print(f"[CONTEXT] ✓ forms: {len(forms)}")
        print(f"[CONTEXT] ✓ page_text length: {len(page_text_raw)}")

        return context

    except Exception as e:
        err = f"Context extraction failed: {str(e)}"
        print(f"[CONTEXT] ❌ {err}")
        return {"error": err}
