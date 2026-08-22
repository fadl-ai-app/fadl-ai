
import os
import json
import uuid
import shutil
import importlib
from pathlib import Path

import gradio as gr


# =========================================================
# PATHS
# =========================================================

THIS_FILE = Path(__file__).resolve()
LITE_ROOT = THIS_FILE.parents[1]
PROJECT_ROOT = THIS_FILE.parents[2]

INPUT_DIR = LITE_ROOT / "input_images"
OUTPUT_DIR = LITE_ROOT / "outputs"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONFIRMATIONS_FILE = LITE_ROOT / "used_confirmations.json"


# =========================================================
# SAFE CONFIRMATION STORE
# =========================================================

def _load_used_confirmations():
    if not CONFIRMATIONS_FILE.exists():
        return []

    try:
        data = json.loads(
            CONFIRMATIONS_FILE.read_text(encoding="utf-8")
        )
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _consume_confirmation(token):
    used = _load_used_confirmations()

    if token in used:
        return False

    used.append(token)

    CONFIRMATIONS_FILE.write_text(
        json.dumps(
            used,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return True


# =========================================================
# PREPARE
# =========================================================

def prepare_image_video(
    image_path,
    motion_text
):
    if not image_path:
        return (
            "✗ ارفعي صورة أولًا",
            ""
        )

    motion_text = (motion_text or "").strip()

    if not motion_text:
        return (
            "✗ اكتبي وصف الحركة",
            ""
        )

    job_id = str(uuid.uuid4())[:8]

    source = Path(image_path)

    if not source.exists():
        return (
            "✗ الصورة غير موجودة",
            ""
        )

    ext = source.suffix.lower() or ".jpg"

    saved_image = (
        INPUT_DIR
        / f"{job_id}_image{ext}"
    )

    shutil.copy2(
        source,
        saved_image
    )

    request = {
        "job_id": job_id,
        "type": "image_to_video",
        "mode": "motion_only",

        "image": str(saved_image),

        "motion_text": motion_text,
        "prompt": motion_text,

        "duration_seconds": 5,
        "ratio": "16:9",

        "model": "gen4_turbo",

        "estimated_credits": 25,

        "confirmed_for_paid_generation": False
    }

    request_file = (
        LITE_ROOT
        / f"{job_id}_request.json"
    )

    request_file.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    token = str(uuid.uuid4())

    confirmation = {
        "confirm_token": token,
        "job_id": job_id,
        "estimated_credits": 25
    }

    message = (
        "=== معاينة قبل التوليد ===\n"
        f"رقم المهمة: {job_id}\n"
        "المدة: 5 ثوانٍ\n"
        "المحرك: Runway / gen4_turbo\n"
        "التكلفة المتوقعة: 25 Credits\n\n"
        "🔒 لم يتم إرسال الطلب بعد"
    )

    return (
        message,
        json.dumps(
            confirmation,
            ensure_ascii=False
        )
    )


# =========================================================
# CONFIRM + SEND
# =========================================================

def confirm_image_video(
    confirmation_json
):
    if not confirmation_json:
        return (
            "✗ اعملي معاينة التكلفة أولًا",
            None,
            None,
            ""
        )

    try:
        confirmation = json.loads(
            confirmation_json
        )
    except Exception:
        return (
            "✗ بيانات التأكيد غير صالحة",
            None,
            None,
            ""
        )

    token = confirmation.get(
        "confirm_token"
    )

    job_id = confirmation.get(
        "job_id"
    )

    if not token or not job_id:
        return (
            "✗ بيانات التأكيد ناقصة",
            None,
            None,
            ""
        )

    if not _consume_confirmation(token):
        return (
            "🔒 تم منع التوليد المكرر",
            None,
            None,
            ""
        )

    request_file = (
        LITE_ROOT
        / f"{job_id}_request.json"
    )

    if not request_file.exists():
        return (
            "✗ ملف الطلب غير موجود",
            None,
            None,
            ""
        )

    request = json.loads(
        request_file.read_text(
            encoding="utf-8"
        )
    )

    request[
        "confirmed_for_paid_generation"
    ] = True

    request_file.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # -----------------------------------------------------
    # Register job in shared jobs.json
    # -----------------------------------------------------

    jobs_file = (
        PROJECT_ROOT
        / "video_engine"
        / "jobs.json"
    )

    try:
        jobs = json.loads(
            jobs_file.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(jobs, list):
            jobs = []

    except Exception:
        jobs = []

    jobs = [
        j for j in jobs
        if j.get("job_id") != job_id
    ]

    jobs.append({
        "job_id": job_id,
        "type": "image_to_video",
        "request_file": str(
            request_file
        ),
        "status": "prepared"
    })

    jobs_file.write_text(
        json.dumps(
            jobs,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    # -----------------------------------------------------
    # Runway
    # -----------------------------------------------------

    from video_engine.providers import (
        runway_provider
    )

    runway_provider = importlib.reload(
        runway_provider
    )

    runway_provider.ALLOWED_PAID_JOB_ID = (
        job_id
    )

    runway_provider.PAID_ENGINE_ENABLED = True

    # فتح Web Trial لهذه المهمة فقط
    old_trial_mode = getattr(
        runway_provider,
        "FADL_WEB_TRIAL_MODE",
        True
    )

    old_paid_enabled = getattr(
        runway_provider,
        "FADL_WEB_PAID_GENERATION_ENABLED",
        False
    )

    runway_provider.FADL_WEB_TRIAL_MODE = False
    runway_provider.FADL_WEB_PAID_GENERATION_ENABLED = True

    try:
        result = (
            runway_provider.send_to_runway(
                job_id
            )
        )
    finally:
        # إرجاع كل الأقفال كما كانت
        runway_provider.PAID_ENGINE_ENABLED = False
        runway_provider.ALLOWED_PAID_JOB_ID = None

        runway_provider.FADL_WEB_TRIAL_MODE = old_trial_mode
        runway_provider.FADL_WEB_PAID_GENERATION_ENABLED = old_paid_enabled

    if not result.get("sent"):
        return (
            "✗ Runway لم يقبل المهمة\n"
            + str(
                result.get(
                    "message",
                    result
                )
            ),
            None,
            None,
            ""
        )

    task_id = result.get(
        "task_id"
    )

    if not task_id:
        return (
            "✗ لم يرجع Task ID",
            None,
            None,
            ""
        )

    return (
        "✅ تم إرسال المهمة إلى Runway\n"
        f"job_id: {job_id}\n"
        f"Task ID: {task_id}\n"
        "🔒 تم إغلاق Runway بعد الإرسال\n"
        "🔒 لا يمكن إعادة نفس التأكيد",
        None,
        None,
        ""
    )


# =========================================================
# UI
# =========================================================

def create_image_to_video_lite_ui():

    with gr.Blocks() as app:

        gr.Markdown(
            "## صورة → فيديو Lite"
        )

        image_input = gr.Image(
            type="filepath",
            label="ارفع صورة"
        )

        motion_input = gr.Textbox(
            label="وصف الحركة",
            placeholder=(
                "مثال: الرجل ينظر "
                "للكاميرا ويحرك رأسه "
                "بهدوء"
            )
        )

        prepare_button = gr.Button(
            "معاينة التكلفة"
        )

        cost_preview = gr.Textbox(
            label="معاينة التكلفة",
            lines=7,
            interactive=False
        )

        confirmation_data = (
            gr.Textbox(
                visible=False
            )
        )

        confirm_button = gr.Button(
            "✅ تأكيد التوليد"
        )

        status = gr.Textbox(
            label="حالة التوليد",
            lines=8,
            interactive=False
        )

        final_video = gr.Video(
            label="الفيديو النهائي"
        )

        download_video = gr.File(
            label="تحميل الفيديو"
        )

        prepare_button.click(
            fn=prepare_image_video,
            inputs=[
                image_input,
                motion_input
            ],
            outputs=[
                cost_preview,
                confirmation_data
            ]
        )

        confirm_button.click(
            fn=confirm_image_video,
            inputs=confirmation_data,
            outputs=[
                status,
                final_video,
                download_video,
                confirmation_data
            ]
        )

    return app


# =========================================================
# EMBED INSIDE FADL AI MAIN APP
# =========================================================

def add_image_to_video_ui():

    gr.Markdown(
        "## صورة → فيديو"
    )

    image_input = gr.Image(
        type="filepath",
        label="ارفع صورة"
    )

    motion_input = gr.Textbox(
        label="وصف الحركة",
        placeholder=(
            "مثال: الرجل ينظر للكاميرا "
            "ويحرك رأسه بهدوء"
        )
    )

    prepare_button = gr.Button(
        "معاينة التكلفة"
    )

    cost_preview = gr.Textbox(
        label="معاينة التكلفة",
        lines=7,
        interactive=False
    )

    confirmation_data = gr.Textbox(
        visible=False
    )

    confirm_button = gr.Button(
        "✅ تأكيد التوليد"
    )

    status = gr.Textbox(
        label="حالة التوليد",
        lines=8,
        interactive=False
    )

    final_video = gr.Video(
        label="الفيديو النهائي"
    )

    download_video = gr.File(
        label="تحميل الفيديو"
    )

    prepare_button.click(
        fn=prepare_image_video,
        inputs=[
            image_input,
            motion_input
        ],
        outputs=[
            cost_preview,
            confirmation_data
        ]
    )

    confirm_button.click(
        fn=confirm_image_video,
        inputs=confirmation_data,
        outputs=[
            status,
            final_video,
            download_video,
            confirmation_data
        ]
    )
