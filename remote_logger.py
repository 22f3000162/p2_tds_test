"""
Remote logging utility.
Uploads full session logs to GitHub Gist on shutdown or completion.
"""

import requests
import os
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def upload_to_github_gist(content: str, description="Hybrid Quiz Solver Log"):
    if not GITHUB_TOKEN:
        print("[LOGGER] No GITHUB_TOKEN found, skipping upload")
        return None

    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quiz_logs_{timestamp}.txt"

        payload = {
            "description": description,
            "public": False,
            "files": {
                filename: {"content": content}
            },
        }

        res = requests.post(
            "https://api.github.com/gists",
            json=payload,
            headers=headers,
            timeout=15,
        )

        if res.status_code == 201:
            gist_url = res.json().get("html_url")
            print(f"[LOGGER] ✓ Logs uploaded to GitHub Gist")
            print(f"[LOGGER] 🔗 {gist_url}")
            return gist_url

        print(f"[LOGGER] ✗ Upload failed: {res.status_code}")
        return None

    except Exception as e:
        print(f"[LOGGER] ✗ Exception while uploading logs: {e}")
        return None


def upload_log_file(log_path: str, description="Hybrid Quiz Solver – Full Session"):
    if not os.path.exists(log_path):
        print("[LOGGER] Log file not found, skipping upload")
        return None

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if not content.strip():
            print("[LOGGER] Log file empty, skipping upload")
            return None

        return upload_to_github_gist(content, description)

    except Exception as e:
        print(f"[LOGGER] ✗ Failed to read/upload log file: {e}")
        return None
