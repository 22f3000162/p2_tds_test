"""
Dependency installer tool using uv.
Installs Python packages ONLY when required.
"""

from langchain_core.tools import tool
from typing import List
import subprocess
import importlib


@tool
def add_dependencies(dependencies: List[str]) -> str:
    """
    Install Python packages dynamically using uv.

    STRICT RULES (for LLM):
    - Call this ONLY after an ImportError
    - Do NOT pre-install packages
    - Pass real pip package names (not aliases)

    Parameters
    ----------
    dependencies : List[str]
        Example: ["pandas", "numpy", "matplotlib"]

    Returns
    -------
    str
        Human-readable status message (success or failure)
    """

    if not dependencies:
        return "No dependencies provided."

    print(f"\n[DEPENDENCIES] 🔍 Checking: {', '.join(dependencies)}")

    already_installed = []
    to_install = []

    # --------------------------------------------------
    # CHECK INSTALLED PACKAGES
    # --------------------------------------------------
    for dep in dependencies:
        module_name = dep.replace("-", "_")
        try:
            importlib.import_module(module_name)
            already_installed.append(dep)
            print(f"[DEPENDENCIES] ✓ Already installed: {dep}")
        except ImportError:
            to_install.append(dep)

    # --------------------------------------------------
    # NOTHING TO INSTALL
    # --------------------------------------------------
    if not to_install:
        msg = f"All dependencies already installed: {', '.join(already_installed)}"
        print(f"[DEPENDENCIES] ✓ {msg}")
        return msg

    # --------------------------------------------------
    # INSTALL WITH UV
    # --------------------------------------------------
    print(f"[DEPENDENCIES] ⬇️ Installing: {', '.join(to_install)}")

    try:
        proc = subprocess.run(
            ["uv", "add", *to_install],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        msg = f"Successfully installed: {', '.join(to_install)}"
        if already_installed:
            msg += f" (already present: {', '.join(already_installed)})"

        print(f"[DEPENDENCIES] ✓ {msg}")
        return msg

    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Dependency installation failed.\n"
            f"Exit code: {e.returncode}\n"
            f"stderr: {e.stderr.strip() if e.stderr else 'No error output.'}"
        )
        print(f"[DEPENDENCIES] ❌ {error_msg}")
        return error_msg

    except Exception as e:
        error_msg = f"Unexpected error during dependency installation: {str(e)}"
        print(f"[DEPENDENCIES] ❌ {error_msg}")
        return error_msg
