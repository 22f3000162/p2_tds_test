"""
Hybrid FastAPI Server – Minimal & Clean
Compatible with your Hybrid LangGraph Quiz Agent
"""

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
import uvicorn
import os
import time
import sys
import signal
import atexit
import threading
import requests

from hybrid_agent import run_agent  # your compiled LangGraph agent

# =====================================================
# ENV & LOGGING SETUP
# =====================================================
load_dotenv()

EMAIL = os.getenv("TDS_EMAIL") or os.getenv("EMAIL")
SECRET = os.getenv("TDS_SECRET") or os.getenv("SECRET")

START_TIME = time.time()

# Timestamped log file
log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"hybrid_logs_{log_timestamp}.txt"
log_file = open(log_filename, "w", buffering=1)

class Tee:
    """Write logs to both console and file."""
    def __init__(self, *files):
        self.files = files

    def write(self, data):
        for f in self.files:
            f.write(data)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()

# Redirect stdout / stderr
sys.stdout = Tee(sys.stdout, log_file)
sys.stderr = Tee(sys.stderr, log_file)

print(f"[LOGGING] Logs → {log_filename}")
# =====================================================
# GITHUB GIST LOG UPLOADER (SHUTDOWN SAFE)
# =====================================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
_gist_uploaded = False
_gist_lock = threading.Lock()

def upload_logs_to_gist():
    global _gist_uploaded

    if not GITHUB_TOKEN:
        print("[LOGGER] No GITHUB_TOKEN found, skipping Gist upload")
        return

    with _gist_lock:
        if _gist_uploaded:
            return
        _gist_uploaded = True

    try:
        # Flush everything
        log_file.flush()

        with open(log_filename, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hybrid_session_{timestamp}.txt"

        payload = {
            "description": "Hybrid Quiz Solver – Full Session Log",
            "public": False,
            "files": {
                filename: {"content": content}
            }
        }

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        response = requests.post(
            "https://api.github.com/gists",
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code == 201:
            print(f"[LOGGER] ✅ Logs uploaded to Gist: {response.json()['html_url']}")
        else:
            print(f"[LOGGER] ❌ Gist upload failed: {response.status_code}")

    except Exception as e:
        print(f"[LOGGER] ❌ Error uploading logs: {e}")
# =====================================================
# SHUTDOWN HANDLERS (CRITICAL)
# =====================================================
def _on_shutdown(signum=None, frame=None):
    print("\n[SHUTDOWN] Saving logs before exit...")
    upload_logs_to_gist()

# Hugging Face / Docker stop
signal.signal(signal.SIGTERM, _on_shutdown)

# Ctrl+C
signal.signal(signal.SIGINT, _on_shutdown)

# Normal Python exit
atexit.register(upload_logs_to_gist)


# =====================================================
# FASTAPI APP
# =====================================================
app = FastAPI(title="Hybrid Quiz Solver", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# HEALTH CHECK
# =====================================================
@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "email": EMAIL,
        "version": "hybrid-v1.0",
    }

# =====================================================
# CORE ENDPOINTS
# =====================================================
@app.post("/quiz")
async def quiz_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Start solving a quiz.

    Body:
    {
        "url": "QUIZ_URL",
        "secret": "YOUR_SECRET"
    }
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    url = data.get("url")
    secret = data.get("secret")

    if not url or not secret:
        raise HTTPException(status_code=400, detail="Missing 'url' or 'secret'")

    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    print(f"[SERVER] ✅ Accepted quiz: {url}")

    background_tasks.add_task(run_agent, url)

    return JSONResponse(
        status_code=200,
        content={"status": "accepted", "message": "Quiz solving started"},
    )


@app.post("/solve")
async def solve_endpoint(request: Request, background_tasks: BackgroundTasks):

    return await quiz_endpoint(request, background_tasks)

# =====================================================
# ENTRY POINT
# =====================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Hybrid Quiz Solver Server")
    print("=" * 60)
    print(f"Email  : {EMAIL}")
    print(f"Secret : {'*' * len(SECRET) if SECRET else 'NOT SET'}")
    print("=" * 60 + "\n")

    # Disable uvicorn default logging (we use Tee)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
    )
