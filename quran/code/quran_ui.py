from pathlib import Path
import subprocess
import requests
import os
import gradio as gr
import json
import quran_engine

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
DB_PATH = os.path.join(
    BASE_DIR, "quran", "quran_database.json"
)

with open(DB_PATH, "r", encoding="utf-8") as f:
    quran_db = json.load(f)

# ربط قاعدة القرآن بالمحرك.
# المفاتيح تُحمّل لاحقًا من البيئة/Colab Secrets ولا تُحفظ في الملف.

_qf_client_id = os.environ.get("QF_CLIENT_ID")
_qf_client_secret = os.environ.get("QF_CLIENT_SECRET")

quran_engine.configure(
    _qf_client_id,
    _qf_client_secret,
    quran_db
)


BASMALA_URL = (
    "https://mirrors.quranicaudio.com/"
    "everyayah/Husary_64kbps/001001.mp3"
)

HUSARY_BASE_URL = (
    "https://download.quranicaudio.com/"
    "qdc/khalil_al_husary/murattal"
)

QURAN_CACHE = Path("/tmp/fadl_quran_basmala")
QURAN_CACHE.mkdir(parents=True, exist_ok=True)


def _download_quran_audio(url, path):
    if path.exists() and path.stat().st_size > 0:
        return path

    temp = path.with_suffix(path.suffix + ".part")

    with requests.get(
        url,
        stream=True,
        timeout=(20, 300)
    ) as response:
        response.raise_for_status()

        with open(temp, "wb") as f:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

    temp.replace(path)
    return path


def _get_surah_with_basmala(surah_number):
    final = QURAN_CACHE / f"surah_{surah_number:03d}_with_basmala.mp3"

    if final.exists() and final.stat().st_size > 0:
        print("[QURAN] ✅ موجود في Cache:", final)
        return str(final)

    basmala = QURAN_CACHE / "basmala.mp3"
    surah = QURAN_CACHE / f"surah_{surah_number:03d}.mp3"

    _download_quran_audio(BASMALA_URL, basmala)
    _download_quran_audio(
        f"{HUSARY_BASE_URL}/{surah_number}.mp3",
        surah
    )

    concat_file = QURAN_CACHE / f"concat_{surah_number:03d}.txt"

    concat_file.write_text(
        f"file '{basmala}'\n"
        f"file '{surah}'\n",
        encoding="utf-8"
    )

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(final)
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 or not final.exists():
        raise RuntimeError(
            "فشل دمج البسملة مع السورة: "
            + result.stderr[-500:]
        )

    print("[QURAN] ✅ بسملة + سورة:", surah_number)
    return str(final)


def prepare_surah(choice):
    surah_number = int(choice.split(" - ")[0])
    surah = quran_db[str(surah_number)]

    lines = [
        f'سورة {surah["name"]}',
        ""
    ]

    for ayah in surah["ayahs"]:
        lines.append(
            f'{ayah["ayah"]} - {ayah["text"]}'
        )

    # الفاتحة فيها البسملة، والتوبة لا تبدأ بالبسملة.
    if surah_number in (1, 9):
        audio_value = (
            f"{HUSARY_BASE_URL}/{surah_number}.mp3"
        )
        print(
            f"[QURAN] سورة {surah_number:03d} "
            "تعمل مباشرة"
        )
    else:
        audio_value = _get_surah_with_basmala(
            surah_number
        )

    return "\n".join(lines), audio_value


def create_quran_ui():
    surah_choices = [
        f'{num} - {quran_db[str(num)]["name"]}'
        for num in range(1, 115)
    ]

    with gr.Blocks() as app:
        gr.Markdown("# فضل AI - القرآن الكريم")

        surah_menu = gr.Dropdown(
            choices=surah_choices,
            value="1 - الفاتحة",
            label="اختر السورة"
        )

        play_button = gr.Button(
            "عرض السورة وتشغيل التلاوة"
        )

        quran_text = gr.Textbox(
            label="نص السورة",
            lines=16,
            interactive=False
        )

        quran_audio = gr.Audio(
            label="التلاوة",
            type="filepath"
        )

        play_button.click(
            fn=prepare_surah,
            inputs=surah_menu,
            outputs=[
                quran_text,
                quran_audio
            ]
        )

    return app
