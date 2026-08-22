from pathlib import Path

import os
import json
import requests

VOICE_ROUTER = str(
    Path(__file__).resolve().parents[1]
    / "image_to_video"
    / "config"
    / "voice_router.json"
)

def get_voice(voice_type):
    with open(VOICE_ROUTER, "r", encoding="utf-8") as f:
        config = json.load(f)

    voices = config.get("approved_voices", {})

    if voice_type not in voices:
        raise ValueError(f"نوع الصوت غير موجود: {voice_type}")

    voice = voices[voice_type]

    if not voice.get("approved"):
        raise ValueError("هذا الصوت غير معتمد")

    return voice


def generate_speech(text, voice_type, output_path):
    text = (text or "").strip()

    if not text:
        raise ValueError("النص فارغ")

    api_key = os.environ.get("ELEVENLABS_API_KEY")

    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY غير موجود")

    voice = get_voice(voice_type)
    voice_id = voice["voice_id"]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path
