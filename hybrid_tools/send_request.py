"""
Async POST request tool with retry logic, connection pooling, and time tracking.
Enhanced with structured error responses for the LLM.
"""

from langchain_core.tools import tool
import json
import time
from typing import Any, Dict, Optional

# --------------------------------------------------
# SUBMISSION TRACKING
# --------------------------------------------------
_submission_history = []
_start_time = None
_correct_questions = set()
_wrong_questions = []


def reset_submission_tracking():
    """Reset submission tracking for a new quiz chain."""
    global _submission_history, _start_time, _correct_questions, _wrong_questions
    _submission_history = []
    _start_time = time.time()
    _correct_questions = set()
    _wrong_questions = []


def track_question_result(question_url: str, correct: bool):
    """Track whether a question was answered correctly or incorrectly."""
    if correct:
        _correct_questions.add(question_url)
        if question_url in _wrong_questions:
            _wrong_questions.remove(question_url)
    else:
        if question_url not in _correct_questions and question_url not in _wrong_questions:
            _wrong_questions.append(question_url)


def get_wrong_questions() -> list:
    """Return list of wrong questions still pending."""
    return [q for q in _wrong_questions if q not in _correct_questions]


def get_quiz_summary() -> dict:
    """Return quiz summary."""
    return {
        "correct": len(_correct_questions),
        "wrong": len(get_wrong_questions()),
        "total": len(_correct_questions) + len(get_wrong_questions()),
        "correct_urls": list(_correct_questions),
        "wrong_urls": get_wrong_questions(),
    }


# --------------------------------------------------
# INTERNAL ASYNC POST
# --------------------------------------------------
async def _post_request_async(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    from hybrid_tools.http_client import post_with_retry
    from hybrid_tools.error_utils import get_http_error_suggestion, get_error_type

    global _start_time

    if _start_time is None:
        _start_time = time.time()

    elapsed = time.time() - _start_time
    headers = headers or {"Content-Type": "application/json"}

    # --------------------------------------------------
    # BASE64 MARKER RESOLUTION
    # --------------------------------------------------
    if payload.get("answer") == "USE_LAST_BASE64":
        try:
            from hybrid_tools.data_visualizer import _last_base64_image
            if _last_base64_image:
                payload = payload.copy()
                payload["answer"] = _last_base64_image
                print(f"[SUBMIT] Using stored base64 ({len(_last_base64_image)} chars)")
        except Exception as e:
            print(f"[SUBMIT] ⚠️ Failed to retrieve base64: {e}")

    print(f"\n[SUBMIT] → {url}")
    display_payload = payload.copy()
    if isinstance(display_payload.get("answer"), str) and len(display_payload["answer"]) > 200:
        display_payload["answer"] = display_payload["answer"][:200] + "... (truncated)"
    print(f"[SUBMIT] Payload: {json.dumps(display_payload, indent=2)}")
    print(f"[SUBMIT] Time elapsed: {elapsed:.1f}s / 180s")

    try:
        response = await post_with_retry(url, json=payload, headers=headers)

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "correct": False,
                "error": str(e),
                "error_type": "json_parse_error",
                "suggestion": "Invalid JSON response. Use extract_context to find the correct endpoint.",
            }

        correct = data.get("correct", False)
        delay = data.get("delay", elapsed)
        next_url = data.get("url")
        reason = data.get("reason", "")
        if next_url:
            _start_time = time.time()
        question_url = payload.get("url")
        if question_url:
            track_question_result(question_url, correct)

        result = {
            "success": True,
            "correct": correct,
            "delay": delay,
            "reason": reason,
            "submitted_answer": str(payload.get("answer", ""))[:100],
        }

        if correct:
            print("[SUBMIT] ✓ Correct")
            if next_url:
                result["url"] = next_url
        else:
            print("[SUBMIT] ✗ Wrong")
            if reason:
                print(f"[SUBMIT] Reason: {reason}")

            time_remaining = 180 - delay
            if delay < 180:
                result["can_retry"] = True
                result["time_remaining"] = time_remaining
                result["suggestion"] = f"Wrong answer. Reason: {reason}"
            else:
                result["can_retry"] = False
                if next_url:
                    result["url"] = next_url

        print(f"[SUBMIT] Response: {json.dumps(result, indent=2)}")
        return result

    except Exception as e:
        error_type = get_error_type(e)
        error_msg = str(e)

        status_code = next(
            (code for code in [400, 401, 403, 404, 429, 500] if str(code) in error_msg),
            None,
        )

        suggestion = (
            get_http_error_suggestion(status_code)
            if status_code
            else "Check endpoint using extract_context."
        )

        print(f"[SUBMIT] ✗ Error: {error_msg}")
        print(f"[SUBMIT] Suggestion: {suggestion}")

        return {
            "success": False,
            "correct": False,
            "error": error_msg,
            "error_type": error_type,
            "http_status": status_code,
            "suggestion": suggestion,
            "retryable": status_code not in (401, 403),
        }


# --------------------------------------------------
# LANGCHAIN TOOL
# --------------------------------------------------
@tool
def post_request(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    """
    Submit an answer via POST with retry, tracking, and error handling.
    """
    from hybrid_tools.event_loop_manager import run_async
    return run_async(_post_request_async(url, payload, headers))
