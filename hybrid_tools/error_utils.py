"""
Centralized error handling utilities for hybrid agent tools.
Provides standardized, actionable error responses for the LLM.
"""

from typing import Optional, Dict, Any


# --------------------------------------------------
# HTTP ERROR SUGGESTIONS
# --------------------------------------------------
def get_http_error_suggestion(status_code: int) -> str:
    hints = {
        400: "Bad request - payload MUST include email, secret, full url, and answer.",
        401: "Authentication failed - verify email and secret are correct.",
        403: "Forbidden - you do not have permission for this resource.",
        404: "Endpoint not found - use extract_context to find the correct submit URL.",
        405: "Method not allowed - check whether POST or GET is required.",
        408: "Request timeout - retry the request.",
        429: "Rate limited - wait 30 seconds before retrying.",
        500: "Server error - retry after a short delay.",
        502: "Bad gateway - server may be down, retry after 10 seconds.",
        503: "Service unavailable - retry after 30 seconds.",
        504: "Gateway timeout - server took too long to respond."
    }
    return hints.get(status_code, f"HTTP {status_code} error occurred.")


# --------------------------------------------------
# ERROR TYPE CLASSIFICATION
# --------------------------------------------------
def get_error_type(error: Exception) -> str:
    error_str = str(error).lower()

    if "404" in error_str:
        return "endpoint_not_found"
    if "401" in error_str or "403" in error_str:
        return "authentication_error"
    if "429" in error_str or "rate" in error_str:
        return "rate_limit"
    if "timeout" in error_str:
        return "timeout"
    if "connection" in error_str or "network" in error_str:
        return "network_error"
    if "json" in error_str:
        return "json_parse_error"
    if "import" in error_str:
        return "import_error"
    if "syntax" in error_str:
        return "syntax_error"
    if "not defined" in error_str:
        return "name_error"

    return type(error).__name__.lower()


# --------------------------------------------------
# STANDARDIZED ERROR RESPONSE
# --------------------------------------------------
def create_error_response(
    error: Exception,
    context: Optional[str] = None,
    retryable: bool = True,
    suggestion: Optional[str] = None
) -> Dict[str, Any]:

    error_type = get_error_type(error)

    if suggestion is None:
        suggestion = get_default_suggestion(error_type)

    return {
        "success": False,
        "error": str(error),
        "error_type": error_type,
        "suggestion": suggestion,
        "retryable": retryable,
        "context": context,
    }


# --------------------------------------------------
# DEFAULT SUGGESTIONS
# --------------------------------------------------
def get_default_suggestion(error_type: str) -> str:
    suggestions = {
        "endpoint_not_found": "Use extract_context to locate the correct submit URL.",
        "authentication_error": "Verify email and secret credentials.",
        "rate_limit": "Wait before retrying.",
        "timeout": "Retry the request after a short delay.",
        "network_error": "Check network connectivity and retry.",
        "json_parse_error": "Inspect API response format before parsing.",
        "import_error": "Use add_dependencies to install the missing package.",
        "syntax_error": "Fix Python syntax errors.",
        "name_error": "Ensure all variables/functions are defined.",
    }
    return suggestions.get(error_type, "Analyze the error and try a different approach.")


# --------------------------------------------------
# CODE EXECUTION ERROR ANALYSIS
# --------------------------------------------------
def analyze_code_error(stderr: str) -> Dict[str, Any]:
    import re

    info = {
        "type": "runtime_error",
        "message": "",
        "line": None,
        "suggestion": "Inspect the error and fix the code logic.",
    }

    lower = stderr.lower()

    if "importerror" in lower or "modulenotfounderror" in lower:
        info["type"] = "import_error"
        match = re.search(r"no module named ['\"]?([\w_]+)", lower)
        if match:
            module = match.group(1)
            info["message"] = f"Missing module: {module}"
            info["suggestion"] = f"Use add_dependencies to install '{module}'."
        else:
            info["suggestion"] = "Use add_dependencies to install missing packages."

    elif "syntaxerror" in lower:
        info["type"] = "syntax_error"
        info["suggestion"] = "Fix Python syntax (colons, brackets, quotes)."

    elif "nameerror" in lower:
        info["type"] = "name_error"
        match = re.search(r"name ['\"]?([\w_]+)['\"]? is not defined", stderr)
        if match:
            name = match.group(1)
            info["message"] = f"Undefined name: {name}"
            info["suggestion"] = f"Define '{name}' before use."

    elif "typeerror" in lower:
        info["type"] = "type_error"
        info["suggestion"] = "Check variable types used in operations."

    elif "keyerror" in lower:
        info["type"] = "key_error"
        match = re.search(r"keyerror:? ['\"]?([^'\"]+)", lower)
        if match:
            key = match.group(1)
            info["message"] = f"Missing key: {key}"
            info["suggestion"] = "Inspect dictionary keys before accessing."

    elif "filenotfounderror" in lower:
        info["type"] = "file_not_found"
        info["suggestion"] = "Ensure the file exists or download it first."

    # Extract line number if present
    line_match = re.search(r"line (\d+)", stderr)
    if line_match:
        info["line"] = int(line_match.group(1))

    # Extract error message
    lines = stderr.strip().splitlines()
    if lines:
        info["message"] = info["message"] or lines[-1][:200]

    return info
