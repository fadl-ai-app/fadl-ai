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

    print(f"[QURAN] طلب تشغيل السورة: {surah_number}")
    print("[QURAN] QF_CLIENT_ID موجود:", bool(os.environ.get("QF_CLIENT_ID")))
    print("[QURAN] QF_CLIENT_SECRET موجود:", bool(os.environ.get("QF_CLIENT_SECRET")))

    try:
        audio_path = quran_engine.get_surah_audio(
            surah_number
        )

        print("[QURAN] audio_path:", audio_path)

        if audio_path and os.path.exists(audio_path):
            print("[QURAN] الملف موجود:", True)
            print("[QURAN] الحجم:", os.path.getsize(audio_path))
            return "\n".join(lines), audio_path

        print("[QURAN] ❌ لم يتم إنشاء ملف صوت")
        return "\n".join(lines), None

    except Exception as e:
        print("[QURAN] ❌ خطأ:", type(e).__name__, str(e))
        raise


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
