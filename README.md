---
title: Hybrid Quiz Solver
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 🤖 Hybrid Quiz Solver Agent

> **An enterprise-grade, autonomous AI agent for solving multi-step quiz questions using LangGraph with intelligent LLM orchestration.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Powered-green.svg)](https://langchain-ai.github.io/langgraph/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

---

## 🎯 Overview

The Hybrid Quiz Solver is a production-ready AI agent that autonomously navigates and solves multi-step quiz workflows. It combines the power of **Google Gemini** and **OpenAI GPT** with intelligent fallback mechanisms, API key rotation, and comprehensive tooling for web scraping, code execution, and multimedia processing.

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🧠 Intelligent LLM Orchestration

- **Primary**: Gemini 2.5 Flash (fast, free tier)
- **Fallback**: OpenAI GPT-4o-mini
- **Auto-rotation**: Cycles through multiple API keys
- **Quota handling**: Seamless fallback on rate limits

</td>
<td width="50%">

### 🛠️ Comprehensive Toolset

- **Web Scraping**: Playwright + HTTP fallback
- **Code Execution**: Sandboxed Python runner
- **Image Analysis**: Gemini Vision API
- **Audio Transcription**: Multi-provider fallback
- **Data Visualization**: Matplotlib/Seaborn charts

</td>
</tr>
<tr>
<td>

### 📊 Built-in Tracking

- Real-time progress monitoring
- Correct/wrong answer tracking
- Automatic retry on failures
- Question chain navigation

</td>
<td>

### 🔒 Production Ready

- Docker containerization
- Remote logging (GitHub Gist)
- Graceful shutdown handling
- Request caching for efficiency

</td>
</tr>
</table>

---

## 🏗️ System Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │         External Services           │
                                    │  ┌─────────┐  ┌─────────┐          │
                                    │  │ Gemini  │  │ OpenAI  │          │
                                    │  │   API   │  │   API   │          │
                                    │  └────┬────┘  └────┬────┘          │
                                    └───────┼────────────┼───────────────┘
                                            │            │
                    ┌───────────────────────┴────────────┴───────────────────────┐
                    │                                                             │
                    │                    API Key Rotator                          │
                    │              (Automatic Quota Management)                   │
                    │                                                             │
                    └─────────────────────────┬───────────────────────────────────┘
                                              │
┌─────────────────────────────────────────────┴─────────────────────────────────────────────┐
│                                                                                           │
│                                   HYBRID AGENT CORE                                       │
│                                                                                           │
│  ┌─────────────┐    ┌─────────────────────────────────────────────────┐                  │
│  │   FastAPI   │    │                  LangGraph Agent                 │                  │
│  │   Server    │───▶│                                                  │                  │
│  │  :8000      │    │   ┌────────┐    ┌────────┐    ┌────────────┐    │                  │
│  └─────────────┘    │   │ Agent  │───▶│ Tools  │───▶│  Process   │────│──▶ Loop         │
│                     │   │  Node  │    │  Node  │    │   Output   │    │                  │
│                     │   └────────┘    └────────┘    └────────────┘    │                  │
│                     │                      │                           │                  │
│                     └──────────────────────┼───────────────────────────┘                  │
│                                            │                                              │
│  ┌─────────────────────────────────────────┴─────────────────────────────────────────┐   │
│  │                              TOOL LAYER (14 Operations)                            │   │
│  │                                                                                    │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                │   │
│  │  │   Web Scraper    │  │  Code Executor   │  │  Context Extract │                │   │
│  │  │  (Playwright)    │  │  (uv sandbox)    │  │  (HTML Parser)   │                │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘                │   │
│  │                                                                                    │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                │   │
│  │  │  Image Analyzer  │  │  Audio Transcrib │  │  Data Visualizer │                │   │
│  │  │ (Gemini Vision)  │  │  (Multi-fallback)│  │  (Matplotlib)    │                │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘                │   │
│  │                                                                                    │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                │   │
│  │  │  File Download   │  │  HTTP Client     │  │  Cache Manager   │                │   │
│  │  │  (Atomic Write)  │  │  (Connection Pool)│  │  (In-Memory)     │                │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘                │   │
│  │                                                                                    │   │
│  └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │       Quiz Server API         │
                              │   (Submit answers, get next)  │
                              └───────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** package manager (recommended)
- **API Keys**: Gemini and/or OpenAI

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd sharing_new_hybrid_folder

# Create virtual environment & install dependencies
uv venv && source .venv/bin/activate
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

### Run Server

```bash
uv run hybrid_main.py
```

🎉 Server running at `http://localhost:8000`

---

## ⚙️ Environment Configuration

```env
# ============================================================
# LLM CONFIGURATION
# ============================================================

# Use Gemini as primary (recommended: true)
USE_GEMINI=true

# Gemini model selection
GEMINI_MODEL=gemini-2.5-flash

# ============================================================
# GEMINI API KEYS (Auto-rotation supported)
# ============================================================
# Get keys from: https://aistudio.google.com/app/apikey

GOOGLE_API_KEY=your_primary_gemini_key
GOOGLE_API_KEY_2=your_second_gemini_key      # Optional
GOOGLE_API_KEY_3=your_third_gemini_key       # Optional
# Add more: GOOGLE_API_KEY_4, _5, _6, etc.

# ============================================================
# OPENAI CONFIGURATION (Fallback)
# ============================================================
# Get key from: https://platform.openai.com/api-keys

OPENAI_API_KEY=your_openai_key
FALLBACK_OPENAI_MODEL=gpt-4o-mini
PRIMARY_OPENAI_MODEL=gpt-4o-mini              # Optional
OPENAI_BASE_URL=                              # Optional (for proxies)

# ============================================================
# QUIZ CREDENTIALS
# ============================================================

TDS_EMAIL=your_email@example.com
TDS_SECRET=your_secret_key

# ============================================================
# OPTIONAL: REMOTE LOGGING
# ============================================================
# Auto-upload logs to GitHub Gist on shutdown
# Create token at: https://github.com/settings/tokens (scope: gist)

GITHUB_TOKEN=your_github_token
```

---

## 📡 API Reference

### Start Quiz Solving

```bash
POST /quiz
```

**Request:**

```json
{
  "email": "your_email@example.com",
  "secret": "your_secret",
  "url": "https://quiz-server.com/q1.html"
}
```

**Response:**

```json
{
  "status": "accepted",
  "message": "Quiz solving started"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/quiz \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@test.com","secret":"abc123","url":"https://quiz.example.com/q1.html"}'
```

### Health Check

```bash
GET /health
```

---

## 🐳 Docker Deployment

### Build & Run

```bash
# Build image
docker build -t hybrid-agent .

# Run container
docker run -d \
  --name hybrid-agent \
  -p 8000:8000 \
  --env-file .env \
  hybrid-agent
```

### Docker Compose

```yaml
version: "3.8"
services:
  hybrid-agent:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

```bash
docker-compose up -d
```

---

## 🔄 LLM Fallback Flow

```
┌─────────────────────┐
│   Incoming Request  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     Success     ┌─────────────────────┐
│  Gemini Key #1      │────────────────▶│   Return Response   │
└──────────┬──────────┘                 └─────────────────────┘
           │ 429/Quota
           ▼
┌─────────────────────┐     Success     ┌─────────────────────┐
│  Gemini Key #2      │────────────────▶│   Return Response   │
└──────────┬──────────┘                 └─────────────────────┘
           │ 429/Quota
           ▼
┌─────────────────────┐     Success     ┌─────────────────────┐
│  OpenAI Fallback    │────────────────▶│   Return Response   │
└──────────┬──────────┘                 └─────────────────────┘
           │ Failure
           ▼
┌─────────────────────┐
│   END (Graceful)    │
└─────────────────────┘
```

---

## 📁 Project Structure

```
sharing_new_hybrid_folder/
├── hybrid_agent.py          # Core LangGraph agent logic
├── hybrid_main.py           # FastAPI server & endpoints
├── api_key_rotator.py       # Multi-key rotation manager
├── remote_logger.py         # GitHub Gist log uploader
├── pyproject.toml           # Dependencies & metadata
├── Dockerfile               # Container configuration
├── .env.example             # Environment template
├── .gitignore               # Git exclusions
├── README.md                # Documentation (this file)
│
└── hybrid_tools/            # Agent tool implementations
    ├── __init__.py          # Tool exports
    ├── web_scraper.py       # Playwright + HTTP scraping
    ├── context_extractor.py # HTML/API parsing
    ├── code_executor.py     # Python sandbox execution
    ├── send_request.py      # Answer submission
    ├── download_file.py     # Atomic file downloads
    ├── audio_transcriber.py # Audio → text conversion
    ├── image_analyzer.py    # Gemini Vision analysis
    ├── data_visualizer.py   # Chart generation
    ├── cache_manager.py     # Request caching
    ├── http_client.py       # Shared HTTP client
    ├── event_loop_manager.py# Async loop management
    ├── error_utils.py       # Error handling utilities
    └── add_dependencies.py  # Runtime package installer
```

---

## 🔧 Troubleshooting

| Issue                | Solution                                                           |
| -------------------- | ------------------------------------------------------------------ |
| **429 Rate Limit**   | Add more Gemini keys (`GOOGLE_API_KEY_2`, `_3`, etc.)              |
| **Playwright Error** | Run `uv run playwright install chromium`                           |
| **Event Loop Error** | Restart server: `pkill -f hybrid_main.py && uv run hybrid_main.py` |
| **OpenAI Quota**     | Check billing at platform.openai.com                               |
| **Empty Response**   | Agent auto-retries with fallback LLM                               |

---

## 📄 License

MIT License - Free for personal and commercial use.

---

<p align="center">
  <b>Built with LangGraph • Gemini • OpenAI • FastAPI</b>
  <br>
  <sub>Made with ❤️</sub>
</p>
