
import gradio as gr
import json
import os
from pydub import AudioSegment

SEQUENCE_PATH = os.path.join(os.path.dirname(__file__), "two_rakah", "two_rakah_sequence.json")
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

IMAGES_DIR = os.path.join(
    BASE_DIR, "two_rakah", "images"
)

TEMP_AUDIO_DIR = os.path.join(
    BASE_DIR, "audio", "temp"
)

os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

with open(SEQUENCE_PATH, "r", encoding="utf-8") as f:
    prayer_sequence = json.load(f)


def get_step_audio(item):

    if item.get("quran_audio"):
        return item["quran_audio"]

    if item.get("audio"):
        return item["audio"]

    if item.get("audio_1") and item.get("audio_2"):
        audio1 = AudioSegment.from_file(item["audio_1"])
        audio2 = AudioSegment.from_file(item["audio_2"])

        pause = AudioSegment.silent(duration=400)
        combined = audio1 + pause + audio2

        output = os.path.join(
            TEMP_AUDIO_DIR,
            f"step_{item['order']}_combined.mp3"
        )

        combined.export(output, format="mp3")
        return output

    return None


def render_step(index):

    index = int(index)
    index = max(0, min(index, len(prayer_sequence) - 1))

    item = prayer_sequence[index]

    image_path = os.path.join(
        IMAGES_DIR,
        item.get("image", "")
    )

    details = []

    if item.get("reading_text"):
        details.append(
            "القراءة: " + item["reading_text"]
        )

    if item.get("spoken_text"):
        details.append(
            "الذكر: " + item["spoken_text"]
        )

    audio_path = get_step_audio(item)

    video_path = item.get("video")

    if video_path and os.path.exists(video_path):
        # إذا وُجد فيديو جاهز، نعرضه بدل الصورة والصوت المنفصل
        display_image = None
        display_video = video_path
        display_audio = None
    else:
        # Fallback لبقية خطوات الصلاة
        display_image = (
            image_path
            if os.path.exists(image_path)
            else None
        )
        display_video = None
        display_audio = (
            audio_path
            if audio_path and os.path.exists(audio_path)
            else None
        )

    return (
        index,
        f"{index + 1} / {len(prayer_sequence)}",
        item["action"],
        "\n".join(details),
        display_image,
        display_video,
        display_audio
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

    # تجهيز الخطوة الأولى قبل إنشاء عناصر الواجهة
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
        label="فيديو الصلاة"
    )

    audio_box = gr.Audio(
        value=first_step[6],
        label="صوت الحركة",
        type="filepath",
        autoplay=True
    )

    start_button = gr.Button(
        "ابدأ الصلاة من البداية"
    )

    with gr.Row():
        previous_button = gr.Button("السابق")
        next_button = gr.Button("التالي")

    start_button.click(
        lambda: render_step(0),
        inputs=None,
        outputs=[
            step_state,
            counter,
            action_box,
            details_box,
            image_box,
            video_box,
            audio_box
        ]
    )

    next_button.click(
        next_step,
        inputs=step_state,
        outputs=[
            step_state,
            counter,
            action_box,
            details_box,
            image_box,
            video_box,
            audio_box
        ]
    )

    previous_button.click(
        previous_step,
        inputs=step_state,
        outputs=[
            step_state,
            counter,
            action_box,
            details_box,
            image_box,
            video_box,
            audio_box
        ]
    )

    return (
        step_state,
        counter,
        action_box,
        details_box,
        image_box,
        video_box,
        audio_box
    )
