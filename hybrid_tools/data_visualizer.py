"""
Data visualization tool for generating charts and graphs.
Supports matplotlib and seaborn.
Returns base64-encoded images via marker mechanism.
"""

from langchain_core.tools import tool
import base64
from typing import Optional

# --------------------------------------------------
# GLOBAL BASE64 STORAGE
# --------------------------------------------------
_last_base64_image: Optional[str] = None


# --------------------------------------------------
# SIMPLE VISUALIZATION
# --------------------------------------------------
@tool
def create_visualization(code: str, chart_type: str = "auto", title: str = "") -> str:
    """
    Create a visualization and store base64 image internally.
    Returns a preview message ONLY.
    """

    print(f"\n[VISUALIZER] Creating visualization ({chart_type})")

    try:
        viz_code = f"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import base64
from io import BytesIO

sns.set_style("whitegrid")
plt.figure(figsize=(10, 6))

# ---------------- USER CODE ----------------
{code}
# -------------------------------------------

{"plt.title(" + repr(title) + ")" if title else ""}

buffer = BytesIO()
plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
buffer.seek(0)
answer = base64.b64encode(buffer.read()).decode("utf-8")
plt.close()

print(answer)
"""

        from hybrid_tools.code_executor import run_code
        result = run_code.invoke({"code": viz_code})

        if result.get("return_code") == 0 and result.get("answer"):
            global _last_base64_image
            _last_base64_image = result["answer"]

            preview = (
                _last_base64_image[:100]
                + "..."
                + _last_base64_image[-50:]
            )

            print(f"[VISUALIZER] ✓ Image generated ({len(_last_base64_image)} chars)")
            return (
                f"SUCCESS! Chart created ({len(_last_base64_image)} chars)\n"
                f"Preview: {preview}\n\n"
                f"IMPORTANT: Call get_last_base64() next."
            )

        return f"Error creating visualization: {result.get('stderr', 'Unknown error')}"

    except Exception as e:
        return f"Error: {str(e)}"


# --------------------------------------------------
# CUSTOM DATA + CHART
# --------------------------------------------------
@tool
def create_chart_from_data(data_code: str, chart_config: str) -> str:
    """
    Create a chart using custom data preparation and plotting logic.
    """

    print(f"\n[VISUALIZER] Creating custom chart")

    try:
        full_code = f"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import base64
from io import BytesIO

sns.set_style("whitegrid")

# ---------------- DATA ----------------
{data_code}
# -------------------------------------

plt.figure(figsize=(10, 6))

# ---------------- CHART ----------------
{chart_config}
# --------------------------------------

buffer = BytesIO()
plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
buffer.seek(0)
answer = base64.b64encode(buffer.read()).decode("utf-8")
plt.close()

print(answer)
"""

        from hybrid_tools.code_executor import run_code
        result = run_code.invoke({"code": full_code})

        if result.get("return_code") == 0 and result.get("answer"):
            global _last_base64_image
            _last_base64_image = result["answer"]

            preview = (
                _last_base64_image[:100]
                + "..."
                + _last_base64_image[-50:]
            )

            print(f"[VISUALIZER] ✓ Image generated ({len(_last_base64_image)} chars)")
            return (
                f"SUCCESS! Chart created ({len(_last_base64_image)} chars)\n"
                f"Preview: {preview}\n\n"
                f"IMPORTANT: Call get_last_base64() next."
            )

        return f"Error creating chart: {result.get('stderr', 'Unknown error')}"

    except Exception as e:
        return f"Error: {str(e)}"


# --------------------------------------------------
# BASE64 MARKER
# --------------------------------------------------
@tool
def get_last_base64() -> str:
    """
    Return marker for last generated base64 image.
    post_request will automatically attach the stored image.
    """

    global _last_base64_image

    if not _last_base64_image:
        return "Error: No visualization available."

    print(f"[VISUALIZER] Base64 ready ({len(_last_base64_image)} chars)")
    return "USE_LAST_BASE64"
