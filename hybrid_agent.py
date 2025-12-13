"""
Hybrid LangGraph Quiz Agent (Optimized)
Author: You
"""

# =========================
# IMPORTS
# =========================
from api_key_rotator import get_api_key_rotator

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain.chat_models import init_chat_model

from typing import TypedDict, Annotated, List, Dict, Any
from dotenv import load_dotenv
import os, time, json

# =========================
# ENV SETUP
# =========================
load_dotenv()

EMAIL = os.getenv("TDS_EMAIL") or os.getenv("EMAIL")
SECRET = os.getenv("TDS_SECRET") or os.getenv("SECRET")

USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() in ("1", "true", "yes")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

PRIMARY_OPENAI_MODEL = os.getenv("PRIMARY_OPENAI_MODEL", "gpt-4o-mini")
FALLBACK_OPENAI_MODEL = os.getenv("FALLBACK_OPENAI_MODEL", PRIMARY_OPENAI_MODEL)

RECURSION_LIMIT = 5000
MAX_ATTEMPTS_PER_QUESTION = 15


if USE_GEMINI:
    print(f"Gemini Model: {GEMINI_MODEL}")
else:
    print(f"Primary OpenAI Model: {PRIMARY_OPENAI_MODEL}")
print(f"Fallback OpenAI Model: {FALLBACK_OPENAI_MODEL}")

# =========================
# TOOLS
# =========================
from hybrid_tools import (
    get_rendered_html,
    extract_context,
    run_code,
    download_file,
    post_request,
    analyze_image,
    transcribe_audio,
    create_visualization,
    create_chart_from_data,
    get_last_base64,
)

TOOLS = [
    get_rendered_html,
    extract_context,
    run_code,
    download_file,
    post_request,
    analyze_image,
    transcribe_audio,
    create_visualization,
    create_chart_from_data,
    get_last_base64,
]

# =========================
# STATE
# =========================
class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    context: Dict[str, Any]
    error_history: List[Dict[str, Any]]
    attempt_count: int
    current_url: str
    start_time: float

# =========================
# DYNAMIC RATE LIMITER (auto-scales based on API keys)
# =========================
BASE_REQUESTS_PER_KEY = 15  # 15 requests/min per key (Gemini free tier is ~60/min)

def create_rate_limiter(key_count: int) -> InMemoryRateLimiter:
    """Create rate limiter based on available keys."""
    total_rpm = BASE_REQUESTS_PER_KEY * max(key_count, 1)
    print(f"[RATE_LIMIT] {key_count} key(s) → {total_rpm} requests/min")
    return InMemoryRateLimiter(
        requests_per_second=total_rpm / 60,
        check_every_n_seconds=0.1,
        max_bucket_size=total_rpm,
    )

# Initialize with rotator key count
_rotator = get_api_key_rotator()
rate_limiter = create_rate_limiter(_rotator.key_count)

# =========================
# LLM FACTORY
# =========================
def gemini_llm():
    """Create Gemini LLM with current rotated key."""
    rotator = get_api_key_rotator()
    api_key = rotator.get_next_key()

    return init_chat_model(
        model_provider="google_genai",
        model=GEMINI_MODEL,
        api_key=api_key,
        rate_limiter=rate_limiter,
    ).bind_tools(TOOLS)


def openai_llm(fallback=False):
    model = FALLBACK_OPENAI_MODEL if fallback else PRIMARY_OPENAI_MODEL
    return init_chat_model(
        model_provider="openai",
        model=model,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    ).bind_tools(TOOLS)

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = f"""
You are an autonomous problem-solving agent operating in a multi-step quiz environment.

Your objective is to solve each question correctly by strictly following the page instructions
and interacting with the system exactly as required.

MANDATORY WORKFLOW (DO NOT SKIP OR REORDER):
1. Load the page using get_rendered_html(url)
2. Immediately extract rules and instructions using extract_context(html, base_url)
3. Read and understand all instructions before reasoning
4. Compute the answer carefully (use run_code for non-trivial reasoning)
5. Submit the answer using post_request
6. Continue only if a next_url is returned
7. Stop only when no next_url exists

GENERAL REASONING RULES:
- Never assume missing information
- Never invent endpoints, parameters, or rules
- Never reuse a previously submitted answer
- Treat every question independently unless explicitly told otherwise
- When retrying a question, discard all previous reasoning and start fresh

PROCESS-DEPENDENT QUESTIONS:
If the correct answer depends on how actions unfold over time or steps:
- Do NOT compress the logic into a single formula
- Do NOT guess the outcome
- Explicitly simulate the process step by step
- Apply rules continuously as the process evolves
- Produce the final result only after the process fully completes

ERROR HANDLING & RETRIES:
- A rejected answer indicates flawed reasoning
- Change the reasoning approach before retrying
- Do not retry the same logic or method
- Limit retries per question; reset the counter when the question changes

SUBMISSION RULES:
- If no explicit submit URL is provided, construct it as: base_url + "/submit"
- The answer must contain ONLY the final value
- No explanations, labels, or formatting text

DATA & FILE SAFETY:
- Do not reference absolute or internal file paths
- Use only relative filenames when handling files
- Verify all paths before executing code

SPECIAL HANDLING:
- Apply rounding rules exactly as stated
- Include any required personalization adjustments only if explicitly mentioned
- For visual outputs, retrieve the final encoded result before submission

CREDENTIALS (USE EXACTLY AS PROVIDED):
- email = {EMAIL}
- secret = {SECRET}

TERMINATION:
- Return END only when there is no next_url and no pending question to solve
"""

BASE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("messages"),
    ]
)

# =========================
# AGENT NODE
# =========================
def agent_node(state: AgentState):
    print(f"\n[AGENT] Thinking | Attempt {state['attempt_count']}")

    if state["attempt_count"] >= MAX_ATTEMPTS_PER_QUESTION:
        print("[AGENT] Max attempts reached for this question → END")
        return {"messages": state["messages"] + [{"role": "assistant", "content": "END"}]}

    def is_valid_response(result):
        """Check if LLM response has content or tool calls."""
        has_content = hasattr(result, "content") and result.content
        has_tools = hasattr(result, "tool_calls") and result.tool_calls
        return has_content or has_tools

    def is_quota_error(error_msg: str) -> bool:
        """Check if error is a quota/rate limit error."""
        keywords = ["RESOURCE_EXHAUSTED", "429", "quota", "rate limit"]
        return any(k in error_msg for k in keywords)

    # Try Gemini with key rotation
    if USE_GEMINI:
        rotator = get_api_key_rotator()
        
        for attempt in range(rotator.key_count):
            try:
                llm = gemini_llm()
                result = (BASE_PROMPT | llm).invoke({"messages": state["messages"]})
                
                if not is_valid_response(result):
                    raise ValueError("Empty LLM response")
                
                return {"messages": state["messages"] + [result]}
                
            except Exception as e:
                error_msg = str(e)
                if is_quota_error(error_msg):
                    print(f"[AGENT] 🔥 Gemini key exhausted → rotating ({attempt + 1}/{rotator.key_count})")
                    rotator.mark_key_exhausted()
                    rotator.rotate_to_next_key()
                    continue
                else:
                    print(f"[AGENT] Gemini error (not quota): {error_msg[:100]}")
                    break  # Non-quota error, go to fallback
        
        print("[AGENT] All Gemini keys exhausted → OpenAI fallback")

    # Fallback to OpenAI
    try:
        llm = openai_llm(fallback=True)
        result = (BASE_PROMPT | llm).invoke({"messages": state["messages"]})
        
        if not is_valid_response(result):
            print("[AGENT] ⚠️ OpenAI returned empty → END")
            return {"messages": state["messages"] + [{"role": "assistant", "content": "END"}]}
        
        return {"messages": state["messages"] + [result]}
        
    except Exception as e:
        print(f"[AGENT] ❌ OpenAI failed: {e} → END")
        return {"messages": state["messages"] + [{"role": "assistant", "content": "END"}]}

# =========================
# ROUTER
# =========================
def route(state: AgentState):
    last = state["messages"][-1]

    # If LLM wants to use tools → allow it
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"

    content = getattr(last, "content", "")

    # End ONLY if LLM explicitly says END
    if isinstance(content, str) and content.strip().upper() == "END":
        return END

    # Otherwise keep thinking
    return "agent"


# =========================
# TOOL OUTPUT PROCESSOR
# =========================
def process_tool_output(state: AgentState):
    context = state["context"]
    attempts = state["attempt_count"]
    current_url = state["current_url"]

    msg = state["messages"][-1]
    name = getattr(msg, "name", None)
    content = getattr(msg, "content", None)

    if name == "extract_context":
        try:
            context = content if isinstance(content, dict) else json.loads(content)
        except Exception:
            pass

    if name == "post_request":
        try:
            res = json.loads(content)

            if res.get("correct") is False:
                attempts += 1

            if res.get("next_url"):
                current_url = res["next_url"]
                attempts = 0   # ✅ RESET PER QUESTION

        except Exception:
            pass

    return {
        "context": context,
        "attempt_count": attempts,
        "current_url": current_url,
    }

# =========================
# GRAPH
# =========================
graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(TOOLS))
graph.add_node("process", process_tool_output)

graph.add_edge(START, "agent")
graph.add_edge("tools", "process")
graph.add_edge("process", "agent")

graph.add_conditional_edges(
    "agent",
    route,
    {
        "tools": "tools",
        "agent": "agent",
        END: END,
    },
)

app = graph.compile()

# =========================
# RUNNER (CLEAN RETRY LOGIC)
# =========================
def run_agent(url: str):
    from hybrid_tools.send_request import (
        reset_submission_tracking,
        get_wrong_questions,
        get_quiz_summary,
    )

    print("\n========== START ==========")
    reset_submission_tracking()

    state: AgentState = {
        "messages": [{"role": "user", "content": url}],
        "context": {},
        "error_history": [],
        "attempt_count": 0,
        "current_url": url,
        "start_time": time.time(),
    }

    # -------- First pass --------
    app.invoke(state, config={"recursion_limit": RECURSION_LIMIT})

    # -------- Retry unsolved --------
    prev_correct = -1

    while True:
        summary = get_quiz_summary()
        wrong_urls = summary["wrong_urls"]

        if not wrong_urls:
            break

        if summary["correct"] == prev_correct:
            print("[AGENT] No progress in retry → stopping")
            break

        prev_correct = summary["correct"]

        for wrong_url in wrong_urls:
            retry_state: AgentState = {
                "messages": [{
                    "role": "user",
                    "content": f"Retry this question from scratch:\n{wrong_url}"
                }],
                "context": {},
                "error_history": [],
                "attempt_count": 0,
                "current_url": wrong_url,
                "start_time": time.time(),
            }
            app.invoke(retry_state, config={"recursion_limit": 500})

    final = get_quiz_summary()
    print("\n========== FINAL ==========")
    print(final)
    print("========== END ==========")
