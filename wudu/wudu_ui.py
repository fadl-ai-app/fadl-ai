
import gradio as gr
import json

SEQUENCE_PATH = os.path.join(os.path.dirname(__file__), "wudu_sequence.json")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")

with open(SEQUENCE_PATH, "r", encoding="utf-8") as f:
    wudu_sequence = json.load(f)


def render_step(index):
    index = int(index)
    index = max(0, min(index, len(wudu_sequence) - 1))

    item = wudu_sequence[index]

    body_part_ar = {
        "hands": "الكفان",
        "mouth": "الفم",
        "nose": "الأنف",
        "face": "الوجه",
        "right_arm": "الذراع اليمنى",
        "left_arm": "الذراع اليسرى",
        "head": "الرأس",
        "ears": "الأذنان",
        "right_foot": "القدم اليمنى",
        "left_foot": "القدم اليسرى"
    }

    side_ar = {
        "both": "كلا الجانبين",
        "right": "اليمنى",
        "left": "اليسرى"
    }

    endpoint_ar = {
        "elbow": "المرفق",
        "ankle": "الكعب",
        "back_of_head": "مؤخرة الرأس"
    }

    body_part = body_part_ar.get(
        item.get("body_part"),
        item.get("body_part", "")
    )

    side = side_ar.get(
        item.get("side"),
        item.get("side", "")
    )

    details = [
        f'العضو: {body_part}',
        f'الجهة: {side}',
        f'عدد التكرارات: {item.get("repetition_count", "")}',
        f'الوصف: {item.get("movement_note", "")}'
    ]

    if item.get("endpoint"):
        endpoint = endpoint_ar.get(
            item.get("endpoint"),
            item.get("endpoint")
        )

        details.append(
            f'نقطة النهاية: {endpoint}'
        )

    import os

    image_path = os.path.join(
        IMAGES_DIR,
        item.get("image", "")
    )

    return (
        index,
        f"{index + 1} / {len(wudu_sequence)}",
        item["action"],
        "\n".join(details),
        image_path if os.path.exists(image_path) else None
    )


def next_step(index):
    return render_step(
        min(int(index) + 1, len(wudu_sequence) - 1)
    )


def previous_step(index):
    return render_step(
        max(int(index) - 1, 0)
    )


def start_wudu():
    return render_step(0)


def add_wudu_ui():

    first = render_step(0)

    step_state = gr.Number(
        value=first[0],
        visible=False
    )

    counter = gr.Textbox(
        value=first[1],
        label="رقم الخطوة",
        interactive=False
    )

    action_box = gr.Textbox(
        value=first[2],
        label="الخطوة",
        interactive=False
    )

    details_box = gr.Textbox(
        value=first[3],
        label="تفاصيل الحركة",
        lines=8,
        interactive=False
    )

    image_box = gr.Image(
        value=first[4],
        label="صورة توضيحية للوضوء",
        type="filepath"
    )

    start_button = gr.Button(
        "ابدأ الوضوء من البداية"
    )

    with gr.Row():
        previous_button = gr.Button("السابق")
        next_button = gr.Button("التالي")

    start_button.click(
        start_wudu,
        inputs=None,
        outputs=[
            step_state,
            counter,
            action_box,
            details_box,
            image_box
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
            image_box
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
            image_box
        ]
    )

    return (
        step_state,
        counter,
        action_box,
        details_box,
        image_box
    )
