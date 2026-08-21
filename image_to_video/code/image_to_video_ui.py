
import gradio as gr
import os
import shutil
import uuid
import json
import sys

VIDEO_ENGINE_DIR = "/content/fadl_ai/video_engine"

if VIDEO_ENGINE_DIR not in sys.path:
    sys.path.insert(0, VIDEO_ENGINE_DIR)

import full_pipeline

BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
IMAGE_DIR = f"{BASE}/input_images"
AUDIO_DIR = f"{BASE}/input_audio"
CONFIG_PATH = f"{BASE}/config/motion_config.json"
LANGUAGES_CONFIG_PATH = f"{BASE}/config/languages_config.json"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    motion_config = json.load(f)

with open(LANGUAGES_CONFIG_PATH, "r", encoding="utf-8") as f:
    languages_config = json.load(f)

LANGUAGES = languages_config["languages"]



def on_language_change(language):
    dialects = LANGUAGES.get(
        language,
        {}
    ).get("dialects", ["عام"])

    return gr.update(
        choices=dialects,
        value=dialects[0] if dialects else "عام"
    )

def on_mode_change(mode):
    speaking = mode in ["يتكلم", "حركة + كلام"]

    return (
        gr.update(visible=speaking),  # speech_source
        gr.update(visible=speaking),  # speech_text
        gr.update(visible=speaking),  # voice_type
        gr.update(visible=speaking),  # language
        gr.update(visible=speaking),  # dialect
        gr.update(visible=False)      # audio_input
    )


def on_source_change(source):

    if source == "أكتب النص":
        return (
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=False)
        )

    if source == "أرفع تسجيل صوتي":
        return (
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True)
        )

    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False)
    )


def prepare_inputs(
    mode,
    speech_source,
    image_path,
    speech_text,
    voice_type,
    language,
    dialect,
    audio_path,
    motion_text
):

    if not image_path:
        return "✗ ارفعي صورة أولًا", ""

    mode_map = {
        "حركة فقط": "motion_only",
        "يتكلم": "talking",
        "حركة + كلام": "motion_and_talking"
    }

    mode_key = mode_map.get(mode)

    if not mode_key:
        return "✗ اختاري نوع الفيديو", ""

    motion_text = (motion_text or "").strip()
    speech_text = (speech_text or "").strip()

    if not motion_text:
        return "✗ اكتبي وصف الحركة", ""

    speaking = mode_key in [
        "talking",
        "motion_and_talking"
    ]

    if speaking:

        if speech_source == "أكتب النص":
            if not speech_text:
                return "✗ اكتبي الكلام الذي ستقوله الشخصية", ""

            if not voice_type:
                return "✗ اختاري نوع الصوت", ""

        elif speech_source == "أرفع تسجيل صوتي":
            if not audio_path:
                return "✗ ارفعي ملف الصوت", ""

        else:
            return "✗ اختاري مصدر الكلام", ""

    job_id = str(uuid.uuid4())[:8]

    image_ext = os.path.splitext(image_path)[1]

    saved_image = os.path.join(
        IMAGE_DIR,
        f"{job_id}_image{image_ext}"
    )

    shutil.copy2(image_path, saved_image)

    saved_audio = None

    if speaking and speech_source == "أرفع تسجيل صوتي":
        audio_ext = os.path.splitext(audio_path)[1]

        saved_audio = os.path.join(
            AUDIO_DIR,
            f"{job_id}_audio{audio_ext}"
        )

        shutil.copy2(audio_path, saved_audio)

    request = {
        "job_id": job_id,
        "mode": mode_key,
        "motion_text": motion_text,
        "image": saved_image,

        "speech_source": (
            "text"
            if speech_source == "أكتب النص"
            else "audio"
            if speech_source == "أرفع تسجيل صوتي"
            else None
        ),

        "speech_text": (
            speech_text
            if speaking and speech_source == "أكتب النص"
            else None
        ),

        "voice_type": (
            voice_type
            if speaking and speech_source == "أكتب النص"
            else None
        ),

        "language": (
            language
            if speaking and speech_source == "أكتب النص"
            else None
        ),

        "dialect": (
            dialect
            if speaking and speech_source == "أكتب النص"
            else None
        ),

        "audio": saved_audio,

        "lip_sync": speaking,

        "continuity_rules": motion_config.get(
            "continuity_rules", {}
        ),

        "master_generation_instruction":
            motion_config.get(
                "master_generation_instruction",
                ""
            ),

        "master_negative_instruction":
            motion_config.get(
                "master_negative_instruction",
                ""
            ),

        "style_preservation_guard":
            motion_config.get(
                "style_preservation_guard",
                ""
            ),

        "style_negative_guard":
            motion_config.get(
                "style_negative_guard",
                ""
            ),

        "animal_preservation_guard":
            motion_config.get(
                "animal_preservation_guard",
                ""
            ),

        "animal_negative_guard":
            motion_config.get(
                "animal_negative_guard",
                ""
            ),

        "islamic_modesty_guard":
            motion_config.get(
                "islamic_modesty_guard",
                ""
            ),

        "islamic_modesty_negative_guard":
            motion_config.get(
                "islamic_modesty_negative_guard",
                ""
            )
    }

    request_path = os.path.join(
        BASE,
        f"{job_id}_request.json"
    )

    with open(
        request_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            request,
            f,
            ensure_ascii=False,
            indent=2
        )

    message = [
        "✓ تم تجهيز الطلب",
        f"✓ رقم المهمة: {job_id}",
        f"✓ الوضع: {mode}",
        "✓ الصورة محفوظة",
        f"✓ وصف الحركة: {motion_text}"
    ]

    if speaking:

        if speech_source == "أكتب النص":
            message.append("✓ مصدر الكلام: نص مكتوب")
            message.append(f"✓ النص: {speech_text}")
            message.append(f"✓ نوع الصوت: {voice_type}")
            message.append(
                "⏳ سيتم تحويل النص إلى صوت قبل Lip-sync"
            )

        elif speech_source == "أرفع تسجيل صوتي":
            message.append(
                "✓ مصدر الكلام: تسجيل صوتي"
            )
            message.append("✓ الصوت محفوظ")

        message.append("✓ Lip-sync مطلوب")

    message.append(
        "⏳ التوليد النهائي ينتظر محرك الفيديو"
    )

    return "\n".join(message), job_id



def preview_full_pipeline(job_id):

    job_id = (job_id or "").strip()

    if not job_id:
        return "✗ أدخلي رقم المهمة أولًا"

    try:
        pipeline = full_pipeline.prepare_pipeline(
            job_id,
            dry_run=True
        )

        lines = [
            "✓ المهمة جاهزة للمعاينة",
            f'✓ رقم المهمة: {job_id}',
            f'✓ الوضع: {pipeline["mode"]}',
            "",
            "=== خطة التنفيذ ==="
        ]

        for step in pipeline["steps"]:
            lines.append(
                f'{step["step"]}. '
                f'{step["name"]} | '
                f'{step.get("provider", "local")}'
            )

        lines += [
            "",
            "✓ Dry Run فقط",
            "✓ لم يتم إرسال أي طلب",
            "✓ لم يتم استهلاك Credits"
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"✗ خطأ: {e}"

def add_image_to_video_ui():

    gr.Markdown("## صورة إلى فيديو")

    mode = gr.Radio(
        choices=[
            "حركة فقط",
            "يتكلم",
            "حركة + كلام"
        ],
        value="حركة فقط",
        label="نوع الفيديو"
    )

    image_input = gr.Image(
        label="صورة الشخص",
        type="filepath"
    )

    speech_source = gr.Radio(
        choices=[
            "أكتب النص",
            "أرفع تسجيل صوتي"
        ],
        value="أكتب النص",
        label="مصدر الكلام",
        visible=False
    )

    speech_text = gr.Textbox(
        label="الكلام الذي ستقوله الشخصية",
        placeholder="مثال: السلام عليكم كيف حالكم؟",
        lines=3,
        visible=False
    )

    voice_type = gr.Radio(
        choices=[
            "تلقائي",
            "امرأة",
            "رجل",
            "بنت",
            "ولد"
        ],
        value="تلقائي",
        label="نوع الصوت",
        visible=False
    )

    language = gr.Dropdown(
        choices=list(LANGUAGES.keys()),
        value=languages_config["default_language"],
        label="اللغة",
        visible=False
    )

    default_dialects = LANGUAGES[
        languages_config["default_language"]
    ]["dialects"]

    dialect = gr.Dropdown(
        choices=default_dialects,
        value=languages_config["default_dialect"],
        label="اللهجة",
        visible=False
    )

    audio_input = gr.Audio(
        label="التسجيل الصوتي",
        type="filepath",
        visible=False
    )

    motion_input = gr.Textbox(
        label="وصف الحركة",
        placeholder="مثال: يقف بثبات ويتكلم بهدوء",
        lines=3
    )

    prepare_button = gr.Button(
        "تجهيز صورة إلى فيديو"
    )

    status = gr.Textbox(
        label="حالة الطلب",
        interactive=False,
        lines=10
    )

    current_job_id = gr.Textbox(
        label="رقم المهمة الداخلي",
        visible=False
    )

    mode.change(
        fn=on_mode_change,
        inputs=mode,
        outputs=[
            speech_source,
            speech_text,
            voice_type,
            language,
            dialect,
            audio_input
        ]
    )

    language.change(
        fn=on_language_change,
        inputs=language,
        outputs=dialect
    )

    speech_source.change(
        fn=on_source_change,
        inputs=speech_source,
        outputs=[
            speech_text,
            voice_type,
            audio_input
        ]
    )

    prepare_button.click(
        fn=prepare_inputs,
        inputs=[
            mode,
            speech_source,
            image_input,
            speech_text,
            voice_type,
            language,
            dialect,
            audio_input,
            motion_input
        ],
        outputs=[
            status,
            current_job_id
        ]
    )

    gr.Markdown("---")
    gr.Markdown("### إنشاء الفيديو النهائي")

    job_id_input = current_job_id

    pipeline_button = gr.Button(
        "معاينة إنشاء الفيديو النهائي"
    )


    cost_button = gr.Button(
        "معاينة التكلفة قبل التوليد"
    )

    cost_status = gr.Textbox(
        label="معاينة التكلفة والحماية",
        lines=8,
        interactive=False
    )

    confirmation_data = gr.Textbox(
        visible=False
    )

    confirm_button = gr.Button(
        "✅ تأكيد التوليد"
    )

    pipeline_status = gr.Textbox(
        label="خطة التنفيذ",
        lines=10,
        interactive=False
    )

    final_video = gr.Video(
        label="الفيديو النهائي"
    )

    download_video = gr.File(
        label="تحميل الفيديو"
    )

    pipeline_button.click(
        fn=preview_full_pipeline,
        inputs=job_id_input,
        outputs=pipeline_status
    )


    cost_button.click(
        fn=preview_image_video_cost,
        inputs=job_id_input,
        outputs=[
            cost_status,
            confirmation_data
        ]
    )

    confirm_button.click(
        fn=confirm_image_generation,
        inputs=confirmation_data,
        outputs=[
            pipeline_status,
            final_video,
            download_video,
            confirmation_data
        ]
    )


IMAGE_CONFIRMATIONS_FILE = os.path.join(
    BASE,
    "used_image_confirmations.json"
)

def _load_used_image_confirmations():
    if not os.path.exists(IMAGE_CONFIRMATIONS_FILE):
        return []

    try:
        with open(
            IMAGE_CONFIRMATIONS_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _consume_image_confirmation(token):
    used = _load_used_image_confirmations()

    if token in used:
        return False

    used.append(token)

    with open(
        IMAGE_CONFIRMATIONS_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            used,
            f,
            ensure_ascii=False,
            indent=2
        )

    return True


def preview_image_video_cost(job_id):

    job_id = (job_id or "").strip()

    if not job_id:
        return "✗ جهزي الطلب أولًا", ""

    request_path = os.path.join(
        BASE,
        f"{job_id}_request.json"
    )

    if not os.path.exists(request_path):
        return "✗ ملف الطلب غير موجود", ""

    with open(
        request_path,
        "r",
        encoding="utf-8"
    ) as f:
        request = json.load(f)

    duration = int(
        request.get("duration_seconds", 5)
    )

    cost = duration * 5
    token = str(uuid.uuid4())

    confirmation = {
        "confirm_token": token,
        "job_id": job_id,
        "estimated_credits": cost
    }

    message = (
        "=== معاينة قبل التوليد ===\n"
        f"رقم المهمة: {job_id}\n"
        f"الوضع: {request.get('mode')}\n"
        f"المدة: {duration} ثوانٍ\n"
        f"التكلفة المتوقعة: {cost} Credits\n\n"
        "🔒 لم يتم إرسال الطلب بعد"
    )

    return (
        message,
        json.dumps(
            confirmation,
            ensure_ascii=False
        )
    )


def confirm_image_generation(confirmation_json):

    import importlib
    import time
    import requests
    from pathlib import Path

    # 4 outputs:
    # status, video, download, confirmation_data

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

    token = confirmation.get("confirm_token")
    job_id = confirmation.get("job_id")

    if not token or not job_id:
        return (
            "✗ بيانات التأكيد ناقصة",
            None,
            None,
            ""
        )

    if not _consume_image_confirmation(token):
        return (
            "🔒 تم منع الضغط المكرر",
            None,
            None,
            ""
        )

    request_path = Path(
        BASE
    ) / f"{job_id}_request.json"

    if not request_path.exists():
        return (
            "✗ ملف الطلب غير موجود",
            None,
            None,
            ""
        )

    request = json.loads(
        request_path.read_text(
            encoding="utf-8"
        )
    )

    request["type"] = "image_to_video"
    request["model"] = "gen4_turbo"

    request_path.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    jobs_file = Path(
        "/content/fadl_ai/video_engine/jobs.json"
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

    if not any(
        j.get("job_id") == job_id
        for j in jobs
    ):
        jobs.append({
            "job_id": job_id,
            "type": "image_to_video",
            "request_file": str(request_path),
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

    # =====================================================
    # إرسال المهمة
    # =====================================================

    from video_engine.providers import runway_provider

    runway_provider = importlib.reload(
        runway_provider
    )

    runway_provider.ALLOWED_PAID_JOB_ID = job_id
    runway_provider.PAID_ENGINE_ENABLED = True

    try:
        result = runway_provider.send_to_runway(
            job_id
        )

    finally:
        runway_provider.PAID_ENGINE_ENABLED = False
        runway_provider.ALLOWED_PAID_JOB_ID = None

    if not result.get("sent"):
        return (
            "✗ لم يتم قبول المهمة في Runway\n"
            + str(result.get("message", result)),
            None,
            None,
            ""
        )

    task_id = result.get("task_id")

    if not task_id:
        return (
            "✗ Runway قبل الطلب لكن لم يرجع Task ID",
            None,
            None,
            ""
        )

    # نستخدم نفس طريقة provider لجلب Secret
    api_key = runway_provider.get_runway_api_key()

    if not api_key:
        return (
            "✓ تم إرسال المهمة، لكن مفتاح المتابعة غير متاح\n"
            f"Task ID: {task_id}",
            None,
            None,
            ""
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": "2024-11-06"
    }

    task_url = (
        "https://api.dev.runwayml.com/v1/tasks/"
        + task_id
    )

    # =====================================================
    # انتظار نفس المهمة فقط
    # =====================================================

    for _ in range(120):

        r = requests.get(
            task_url,
            headers=headers,
            timeout=30
        )

        if r.status_code != 200:
            return (
                "✗ خطأ أثناء متابعة Runway: "
                f"{r.status_code}",
                None,
                None,
                ""
            )

        task = r.json()
        task_status = task.get("status")

        if task_status == "SUCCEEDED":

            outputs = task.get("output") or []

            if not outputs:
                return (
                    "✗ اكتمل التوليد لكن لم يظهر رابط الفيديو",
                    None,
                    None,
                    ""
                )

            video_url = outputs[0]

            output_dir = (
                Path(BASE)
                / "outputs"
            )

            output_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            output_path = (
                output_dir
                / f"{job_id}.mp4"
            )

            vr = requests.get(
                video_url,
                timeout=120
            )

            vr.raise_for_status()

            output_path.write_bytes(
                vr.content
            )

            # =============================================
            # FADL_OFFICIAL_WATERMARK_APPLIED
            # العلامة الرسمية بعد تنزيل الفيديو النهائي
            # =============================================
            from video_engine.watermark_engine import (
                add_fadl_watermark
            )

            watermarked_path = output_path.with_name(
                output_path.stem
                + "_fadl.mp4"
            )

            add_fadl_watermark(
                output_path,
                watermarked_path
            )

            return (
                "✅ تم توليد صورة → فيديو بنجاح\n"
                f"✅ job_id: {job_id}\n"
                f"✅ Task ID: {task_id}\n"
                f"✅ التكلفة المتوقعة: "
                f"{confirmation.get('estimated_credits')} Credits\n"
                "✅ تم تنزيل الفيديو النهائي\n"
                "🔒 تم إغلاق Runway بعد الإرسال",
                str(watermarked_path),
                str(watermarked_path),
                ""
            )

        if task_status == "FAILED":
            return (
                "✗ فشل التوليد\n"
                f"السبب: {task.get('failure')}",
                None,
                None,
                ""
            )

        if task_status in (
            "CANCELED",
            "CANCELLED"
        ):
            return (
                "✗ تم إلغاء المهمة في Runway",
                None,
                None,
                ""
            )

        time.sleep(5)

    return (
        "✗ انتهت مهلة انتظار الفيديو",
        None,
        None,
        ""
    )

