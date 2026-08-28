import os
import json
from pathlib import Path

import gradio as gr
from pydub import AudioSegment


# مجلد prayer نفسه — يعمل محليًا وعلى Render/GitHub
PRAYER_ROOT = Path(__file__).resolve().parent

SEQUENCE_PATH = PRAYER_ROOT / "two_rakah" / "two_rakah_sequence.json"
IMAGES_DIR = PRAYER_ROOT / "two_rakah" / "images"
TEMP_AUDIO_DIR = PRAYER_ROOT / "audio" / "temp"

TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_path(value):
    """
    يحول المسارات القديمة من Colab إلى مسارات داخل مجلد prayer الحالي.
    ويقبل أيضًا المسارات النسبية والجديدة.
    """
    if not value:
        return None

    raw = str(value).replace("\\", "/")

    old_prefixes = (
        "/content/fadl_ai/prayer/",
        "/content/fadl_ai_latest/prayer/",
    )

    for prefix in old_prefixes:
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            return str(PRAYER_ROOT / raw)

    p = Path(raw)

    if p.is_absolute():
        return str(p)

    return str(PRAYER_ROOT / raw)


with open(SEQUENCE_PATH, "r", encoding="utf-8") as f:
    prayer_sequence = json.load(f)


def get_step_audio(item):
    if item.get("quran_audio"):
        return _resolve_path(item["quran_audio"])

    if item.get("audio"):
        return _resolve_path(item["audio"])

    if item.get("audio_1") and item.get("audio_2"):
        audio1_path = _resolve_path(item["audio_1"])
        audio2_path = _resolve_path(item["audio_2"])

        if not (
            audio1_path
            and audio2_path
            and os.path.exists(audio1_path)
            and os.path.exists(audio2_path)
        ):
            return None

        audio1 = AudioSegment.from_file(audio1_path)
        audio2 = AudioSegment.from_file(audio2_path)

        pause = AudioSegment.silent(duration=400)
        combined = audio1 + pause + audio2

        output = TEMP_AUDIO_DIR / f"step_{item.get('order', 'x')}_combined.mp3"
        combined.export(str(output), format="mp3")
        return str(output)

    return None



def render_step(index):
    index = int(index)
    index = max(0, min(index, len(prayer_sequence) - 1))

    item = prayer_sequence[index]

    image_value = item.get("image")
    image_path = None

    if image_value:
        # إذا كان JSON يحتوي اسم الصورة فقط
        candidate = IMAGES_DIR / str(image_value)
        if candidate.exists():
            image_path = str(candidate)
        else:
            # وإذا احتوى مسارًا كاملًا/نسبيًا
            resolved = _resolve_path(image_value)
            if resolved and os.path.exists(resolved):
                image_path = resolved

    details = []

    if item.get("reading_text"):
        details.append("القراءة: " + item["reading_text"])

    if item.get("spoken_text"):
        details.append("الذكر: " + item["spoken_text"])

    audio_path = get_step_audio(item)
    if not (audio_path and os.path.exists(audio_path)):
        audio_path = None

    video_path = None
    action = item.get("action", "")

    if action == "القراءة":
        video_path = str(PRAYER_ROOT / "reading" / "reading_preview.mp4")
    elif action == "الجلوس بين السجدتين":
        video_path = str(PRAYER_ROOT / "rabbi_ighfir_li" / "rabbi_ighfir_li_preview.mp4")
    elif action == "التشهد":
        video_path = str(PRAYER_ROOT / "tashahhud" / "tashahhud_preview.mp4")

    if video_path and not os.path.exists(video_path):
        video_path = None

    # إذا كان لهذه الخطوة فيديو جاهز، نعرض الفيديو بدل الصورة الثابتة
    if video_path:
        image_path = None

    return (
        index,
        f"{index + 1} / {len(prayer_sequence)}",
        action,
        "\n".join(details),
        image_path,
        video_path,
        audio_path,
    )


def next_step(index):
    return render_step(
        min(int(index) + 1, len(prayer_sequence) - 1)
    )


def previous_step(index):
    return render_step(
        max(int(index) - 1, 0)
    )


def add_prayer_ui():
    first_step = render_step(0)

    step_state = gr.Number(
        value=first_step[0],
        visible=False
    )

    counter = gr.Textbox(
        value=first_step[1],
        label="رقم الخطوة",
        interactive=False
    )

    action_box = gr.Textbox(
        value=first_step[2],
        label="الحركة",
        interactive=False
    )

    details_box = gr.Textbox(
        value=first_step[3],
        label="الذكر / القراءة",
        interactive=False
    )

    image_box = gr.Image(
        value=first_step[4],
        label="وضعية الصلاة",
        type="filepath"
    )


    video_box = gr.Video(
        value=first_step[5],
        label="حركة الصلاة"
    )

    audio_box = gr.Audio(
        value=first_step[6],
        label="صوت الحركة",
        type="filepath"
    )

    with gr.Row():
        previous_button = gr.Button("السابق")
        next_button = gr.Button("التالي")

    previous_button.click(
        fn=previous_step,
        inputs=step_state,
        outputs=[
            step_state,
            counter,
            action_box,
            details_box,
            image_box,
            video_box,
            audio_box,
        ],
    )

    next_button.click(
        fn=next_step,
        inputs=step_state,
        outputs=[
            step_state,
            counter,
            action_box,
            details_box,
            image_box,
            video_box,
            audio_box,
        ],
    )

    return (
        step_state,
        counter,
        action_box,
        details_box,
        image_box,
        video_box,
        audio_box,
    )
