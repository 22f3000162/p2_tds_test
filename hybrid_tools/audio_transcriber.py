"""
Multi-fallback audio transcription tool.
PRIMARY: Gemini 2.5 Flash
Fallbacks: SpeechRecognition → OpenAI Whisper
"""

from langchain_core.tools import tool
import os
import base64


@tool
def transcribe_audio(audio_url: str) -> str:
    """
    Transcribe an audio file.

    ORDER OF EXECUTION (STRICT):
    1. Gemini 2.5 Flash (PRIMARY, always attempted first)
    2. SpeechRecognition (local, if installed)
    3. OpenAI Whisper (last resort)

    Returns:
    - Pure transcription text
    - OR error string
    """

    print(f"\n[AUDIO] 🎧 Transcribing: {audio_url}")

    try:
        # --------------------------------------------------
        # DOWNLOAD AUDIO
        # --------------------------------------------------
        from hybrid_tools.download_file import download_file

        audio_path_info = download_file.invoke({"url": audio_url})

        if "ERROR" in audio_path_info.upper():
            return f"Failed to download audio: {audio_path_info}"

        audio_path = audio_path_info.split("|")[0].strip()
        print(f"[AUDIO] 📥 Downloaded to: {audio_path}")

        # --------------------------------------------------
        # METHOD 1 — GEMINI 2.5 FLASH (PRIMARY)
        # --------------------------------------------------
        try:
            from openai import OpenAI

            try:
                from api_key_rotator import get_api_key_rotator
                rotator = get_api_key_rotator()
                api_key = rotator.get_next_key()
                print("[AUDIO] 🔄 Using Gemini API key rotation")
            except Exception:
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise RuntimeError("GOOGLE_API_KEY not set")
                print("[AUDIO] 🔑 Using primary Gemini API key")


            print("[AUDIO] 🚀 Trying Gemini 2.5 Flash (PRIMARY)")

            client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )

            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")

            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Transcribe this audio EXACTLY. "
                                    "Return ONLY the transcription text. "
                                    "Do NOT add explanations."
                                )
                            },
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": encoded_audio,
                                    "format": "wav"
                                }
                            }
                        ]
                    }
                ],
            )

            text = response.choices[0].message.content.strip()
            if text:
                print(f"[AUDIO] ✅ Gemini transcription success")
                return text

        except Exception as e:
            print(f"[AUDIO] ⚠ Gemini failed: {e}")

        # --------------------------------------------------
        # METHOD 2 — SPEECHRECOGNITION (LOCAL FALLBACK)
        # --------------------------------------------------
        try:
            print("[AUDIO] 🔁 Trying SpeechRecognition fallback")
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)

            print("[AUDIO] ✅ SpeechRecognition success")
            return text

        except Exception as e:
            print(f"[AUDIO] ⚠ SpeechRecognition failed: {e}")

        # --------------------------------------------------
        # METHOD 3 — OPENAI WHISPER (LAST RESORT)
        # --------------------------------------------------
        try:
            print("[AUDIO] 🔁 Trying OpenAI Whisper fallback")
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )

            text = transcript.text.strip()
            print("[AUDIO] ✅ Whisper transcription success")
            return text

        except Exception as e:
            print(f"[AUDIO] ❌ Whisper failed: {e}")

        return "Error: All transcription methods failed"

    except Exception as e:
        err = f"Error during transcription: {str(e)}"
        print(f"[AUDIO] ❌ {err}")
        return err
