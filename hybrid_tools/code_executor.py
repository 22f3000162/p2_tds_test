"""
Enhanced code executor with safety checks, timeout handling,
and structured error feedback.

IMPORTANT:
- Code is executed with cwd = hybrid_llm_files/
- Therefore, DO NOT prefix paths with 'hybrid_llm_files/'
"""

from langchain_core.tools import tool
import subprocess
import os
import re
from typing import Dict, Any


@tool
def run_code(code: str) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed working directory.

    CONTRACT FOR LLM:
    - All files are already in the current directory
    - Use filenames directly: "data.csv", "file.pdf"
    - Assign final result to variable named `answer`
    - Print the answer as the LAST non-empty line
    - Do NOT perform submissions or installs inside code

    Returns a structured dict for agent reasoning.
    """

    print(f"\n[CODE_EXECUTOR] ▶ Executing code ({len(code)} chars)")

    exec_dir = "hybrid_llm_files"
    os.makedirs(exec_dir, exist_ok=True)

    runner_path = os.path.join(exec_dir, "runner.py")

    # --------------------------------------------------
    # BASIC SAFETY CHECKS (heuristic)
    # --------------------------------------------------
    forbidden_patterns = [
        r"os\.system",
        r"subprocess\.call",
        r"subprocess\.popen",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
    ]

    lowered = code.lower()
    for pattern in forbidden_patterns:
        if re.search(pattern, lowered):
            print(f"[CODE_EXECUTOR] ⚠️ Warning: risky pattern detected → {pattern}")

    # --------------------------------------------------
    # WRITE CODE
    # --------------------------------------------------
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"[CODE_EXECUTOR] 📄 Written runner.py")
    print(f"[CODE_EXECUTOR] 🚀 Running with uv (timeout = 90s)")

    # --------------------------------------------------
    # EXECUTE
    # --------------------------------------------------
    try:
        proc = subprocess.Popen(
            ["uv", "run", "runner.py"],   # runner.py is in cwd
            cwd=exec_dir,                # IMPORTANT
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = proc.communicate(timeout=90)
        return_code = proc.returncode

    except subprocess.TimeoutExpired:
        proc.kill()
        return {
            "code_executed": code[:1000],
            "stdout": "",
            "stderr": "Execution timed out after 90 seconds",
            "return_code": -1,
            "answer": None,
            "error_analysis": {
                "type": "timeout",
                "suggestion": "Optimize logic, reduce data size, or simplify computation",
            },
        }

    # --------------------------------------------------
    # ANSWER EXTRACTION
    # --------------------------------------------------
    answer = None
    stdout_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if stdout_lines:
        answer = stdout_lines[-1]

    # --------------------------------------------------
    # BASE64 IMAGE DETECTION
    # --------------------------------------------------
    is_base64 = False
    if isinstance(answer, str) and len(answer) > 500:
        if answer.startswith("iVBORw0KG") or answer.startswith("data:image"):
            is_base64 = True

    # --------------------------------------------------
    # RESULT STRUCTURE
    # --------------------------------------------------
    result: Dict[str, Any] = {
        "code_executed": code[:1000] + ("… (truncated)" if len(code) > 1000 else ""),
        "stdout": stdout[:800] + ("… (truncated)" if len(stdout) > 800 else ""),
        "stderr": stderr[:800] + ("… (truncated)" if len(stderr) > 800 else ""),
        "return_code": return_code,
        "answer": answer,
    }

    # --------------------------------------------------
    # ERROR ANALYSIS
    # --------------------------------------------------
    if return_code != 0:
        try:
            from hybrid_tools.error_utils import analyze_code_error
            analysis = analyze_code_error(stderr)
        except Exception:
            analysis = {
                "type": "execution_error",
                "message": stderr,
                "suggestion": "Read traceback carefully and fix logic or imports",
            }

        result["error_analysis"] = analysis
        result["suggestion"] = analysis.get(
            "suggestion", "Fix the error and retry with a different approach"
        )

        print(f"[CODE_EXECUTOR] ❌ Failed (code={return_code})")
        print(f"[CODE_EXECUTOR] ❌ {stderr[:300]}")

    else:
        print("[CODE_EXECUTOR] ✅ Execution successful")
        if answer:
            if is_base64:
                print(f"[CODE_EXECUTOR] 🖼 Base64 image output ({len(answer)} chars)")
            else:
                print(f"[CODE_EXECUTOR] 🔢 Answer extracted: {answer}")

    return result
