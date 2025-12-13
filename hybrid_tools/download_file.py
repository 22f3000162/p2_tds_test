"""
Async file downloader with retry, caching, and atomic writes.
LangChain tool compatible.
"""

from langchain_core.tools import tool
import os

# -------------------------------------------------
# INTERNAL ASYNC IMPLEMENTATION
# -------------------------------------------------
async def _download_file_async(url: str, filename: str | None = None) -> str:
    """
    Internal async downloader with retry and atomic write.
    """
    from hybrid_tools.http_client import get_with_retry

    print(f"\n[DOWNLOADER] ⬇️ Downloading: {url}")

    try:
        download_dir = "hybrid_llm_files"
        os.makedirs(download_dir, exist_ok=True)

        # -----------------------------
        # Determine filename safely
        # -----------------------------
        if not filename:
            filename = url.split("/")[-1].split("?")[0].strip()
            if not filename:
                filename = "downloaded_file"

        # Sanitize filename
        filename = filename.replace("/", "_").replace("\\", "_")

        base, ext = os.path.splitext(filename)
        filepath = os.path.join(download_dir, filename)

        # Avoid overwrite
        counter = 1
        while os.path.exists(filepath):
            filepath = os.path.join(download_dir, f"{base}_{counter}{ext}")
            counter += 1

        temp_path = filepath + ".part"

        # -----------------------------
        # Download with retry
        # -----------------------------
        response = await get_with_retry(url)

        # -----------------------------
        # Atomic write
        # -----------------------------
        with open(temp_path, "wb") as f:
            f.write(response.content)

        os.replace(temp_path, filepath)

        size = os.path.getsize(filepath)
        content_type = response.headers.get("content-type", "unknown")

        print(f"[DOWNLOADER] ✅ Saved {size} bytes → {filepath}")
        print(f"[DOWNLOADER] 📄 Content-Type: {content_type}")

        return f"{filepath} | content-type={content_type} | size={size}"

    except Exception as e:
        err = f"[DOWNLOADER ERROR] {type(e).__name__}: {str(e)}"
        print(f"[DOWNLOADER] ❌ {err}")
        return err


# -------------------------------------------------
# LANGCHAIN TOOL WRAPPER
# -------------------------------------------------
@tool
def download_file(url: str, filename: str | None = None) -> str:
    """
    Download a file from a direct URL and save it locally.

    Features:
    - Async download
    - Connection pooling
    - Automatic retry (via shared client)
    - Atomic writes (no corrupted files)
    - Filename collision safety

    DO NOT use for HTML pages.
    DO NOT use get_rendered_html for binary files.

    Parameters
    ----------
    url : str
        Direct file URL (PDF, CSV, image, audio, ZIP, etc.)
    filename : str, optional
        Optional custom filename

    Returns
    -------
    str
        "path | content-type=... | size=..."
        OR
        "[DOWNLOADER ERROR] ..."
    """
    from hybrid_tools.event_loop_manager import run_async
    return run_async(_download_file_async(url, filename))
