
import gradio as gr
import json
import os

STEPS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "wudu_steps.json")
IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))

with open(STEPS_PATH, "r", encoding="utf-8") as f:
    wudu_steps = json.load(f)


def render_step(index):
    index = int(index)
    index = max(0, min(index, len(wudu_steps) - 1))

    item = wudu_steps[index]

    image_name = item["image"].replace(".jpg", ".jpeg")
    image_path = os.path.join(IMAGES_DIR, image_name)

    return (
        index,
        f"{index + 1} / {len(wudu_steps)}",
        item["name"],
        image_path if os.path.exists(image_path) else None
    )


def next_step(index):
    return render_step(
        min(int(index) + 1, len(wudu_steps) - 1)
    )


def previous_step(index):
    return render_step(
        max(int(index) - 1, 0)
    )


def add_wudu_ui():

    step_state = gr.Number(
        value=0,
        visible=False
    )

    counter = gr.Textbox(
        label="رقم الخطوة",
        interactive=False
    )

    step_name = gr.Textbox(
        label="خطوة الوضوء",
        interactive=False
    )

    image_box = gr.Image(
        label="الحركة",
        type="filepath"
    )

    with gr.Row():
        previous_button = gr.Button("السابق")
        next_button = gr.Button("التالي")

    next_button.click(
        fn=next_step,
        inputs=step_state,
        outputs=[
            step_state,
            counter,
            step_name,
            image_box
        ]
    )

    previous_button.click(
        fn=previous_step,
        inputs=step_state,
        outputs=[
            step_state,
            counter,
            step_name,
            image_box
        ]
    )

    return (
        step_state,
        counter,
        step_name,
        image_box
    )
