"""
Image analysis tool using Gemini Vision API.
Used for OCR, chart reading, diagram understanding, and visual Q&A.
LangChain tool compatible.
"""

from langchain_core.tools import tool
import os
import base64
import mimetypes


@tool
def analyze_image(
    image_url: str,
    question: str = "Describe this image in detail"
) -> str:
    """
    Analyze an image using Gemini Vision (gemini-2.5-flash).

    Parameters
    ----------
    image_url : str
        Image URL or local file path
    question : str
        Question to ask about the image

    Returns
    -------
    str
        Extracted or analyzed information from the image
    """

    print(f"\n[IMAGE_ANALYZER] 🖼️ Image: {image_url}")
    print(f"[IMAGE_ANALYZER] ❓ Question: {question}")

    try:
        from openai import OpenAI

        # --------------------------------------------------
        # API KEY (WITH ROTATION IF AVAILABLE)
        # --------------------------------------------------
        try:
            from api_key_rotator import get_api_key_rotator
            rotator = get_api_key_rotator()
            api_key = rotator.get_next_key()
            print("[IMAGE_ANALYZER] 🔄 Using Gemini API key rotation")
        except Exception:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return "Error: GOOGLE_API_KEY not set"
            print("[IMAGE_ANALYZER] 🔑 Using primary Gemini API key")

        # --------------------------------------------------
        # DOWNLOAD IMAGE IF URL
        # --------------------------------------------------
        if image_url.startswith("http"):
            from hybrid_tools.download_file import download_file
            local_path = download_file.invoke({"url": image_url})
            if "ERROR" in local_path.upper():
                return f"Failed to download image: {local_path}"
            image_path = local_path.split(" | ")[0]
        else:
            image_path = image_url

        print(f"[IMAGE_ANALYZER] 📂 Using file: {image_path}")

        # --------------------------------------------------
        # MIME TYPE
        # --------------------------------------------------
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/png"

        # --------------------------------------------------
        # READ + BASE64
        # --------------------------------------------------
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        print(f"[IMAGE_ANALYZER] 📦 Encoded image ({len(image_b64)} chars)")

        # --------------------------------------------------
        # GEMINI VISION CALL (OPENAI-COMPAT)
        # --------------------------------------------------
        client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

        model = "gemini-2.5-flash"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=600,
            temperature=0.1,
        )

        answer = response.choices[0].message.content
        print("[IMAGE_ANALYZER] ✅ Analysis complete")

        return answer or "No response from vision model"

    except Exception as e:
        error = f"[IMAGE_ANALYZER ERROR] {type(e).__name__}: {e}"
        print(error)
        return error
