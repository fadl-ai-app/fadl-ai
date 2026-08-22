from pathlib import Path

import gradio as gr
import json
import quran_engine

DB_PATH = str(
    Path(__file__).resolve().parents[1]
    / "quran_database.json"
)

with open(DB_PATH, "r", encoding="utf-8") as f:
    quran_db = json.load(f)

# ربط قاعدة القرآن بالمحرك.
# المفاتيح تُحمّل لاحقًا من البيئة/Colab Secrets ولا تُحفظ في الملف.
import os

_qf_client_id = os.environ.get("QF_CLIENT_ID")
_qf_client_secret = os.environ.get("QF_CLIENT_SECRET")

quran_engine.configure(
    _qf_client_id,
    _qf_client_secret,
    quran_db
)

def prepare_surah(choice):
    surah_number = int(choice.split(" - ")[0])
    surah = quran_db[str(surah_number)]

    lines = [
        f'سورة {surah["name"]}',
        f'عدد الآيات: {surah["ayah_count"]}',
        ""
    ]

    for ayah in surah["ayahs"]:
        lines.append(
            f'{ayah["ayah"]} - {ayah["text"]}'
        )

    audio_path = quran_engine.get_surah_audio(
        surah_number
    )

    return "\n".join(lines), audio_path


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
