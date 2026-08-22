
import gradio as gr
import os
import json
import uuid
import sys


# =========================================================
# FADL AI — TEXT TO VIDEO MASTER RULES
# =========================================================

TEXT_TO_VIDEO_MASTER_GENERATION_INSTRUCTION = """
Create the scene exactly according to the user's description.

Preserve all explicitly requested details including:
people, number of people, age, appearance, skin tone,
clothing, clothing colors, location, objects, lighting,
weather, time of day, camera angle and requested actions.

Do not invent important actions, people, objects or
interactions that the user did not request.

When the user specifies a precise body movement,
direction, body part, side, endpoint, sequence or
repetition count, execute it exactly.

Maintain natural realistic human anatomy and movement.
Keep each character visually consistent throughout
the generated video.

When multiple people are present, keep them as distinct
individuals and do not merge, swap or transform them.

For structured religious actions such as prayer or wudu,
follow the explicitly provided movement description
precisely and do not approximate the requested action.

If speech is requested, preserve the requested spoken
content without inventing additional dialogue.
""".strip()



TEXT_TO_VIDEO_ISLAMIC_MODESTY_GUARD = """
ISLAMIC MODESTY GUARD:

Keep women and girls modestly dressed throughout the video.

Preserve any existing hijab, abaya, niqab or other modest
covering exactly as requested.

Never remove, reduce, shorten or make existing covering
more revealing during generation or movement.

Women's and girls' clothing must remain non-transparent,
non-revealing and appropriately loose.

Prevent accidental exposure and frame-to-frame modesty drift.

If the requested clothing is already modest, preserve it.

Do not automatically add niqab when it is not present
or explicitly requested.
""".strip()


TEXT_TO_VIDEO_ISLAMIC_MODESTY_NEGATIVE = """
MODESTY NEGATIVE:

No removal of hijab, abaya or niqab.
No transparent or revealing clothing.
No excessively tight clothing.
No accidental exposure during movement.
No clothing becoming less modest between frames.
No unwanted shortening or removal of existing garments.
""".strip()


TEXT_TO_VIDEO_MASTER_NEGATIVE_INSTRUCTION = """
DO NOT GENERATE:
extra people,
missing people,
identity swapping,
merged people,
unrequested clothing changes,
unrequested hairstyle changes,
unrequested objects,
missing requested objects,
random scene changes,
random camera movement,
unrequested actions,
unrequested touching,
unrequested hugging,
unrequested kissing,
romantic interaction unless explicitly requested,
extra arms,
extra hands,
extra legs,
extra fingers,
missing fingers,
deformed hands,
distorted limbs,
body intersection,
clothing penetration,
anatomy mutation,
unfinished precise actions,
wrong left or right side,
incorrect movement endpoint,
invented dialogue.
""".strip()


sys.path.insert(0, "/content/fadl_ai")
from video_engine.elevenlabs_tts import generate_speech

BASE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)
REQUESTS_DIR = f"{BASE}/requests"
OUTPUTS_DIR = f"{BASE}/outputs"
AUDIO_DIR = f"{BASE}/audio"

os.makedirs(REQUESTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)


def prepare_text_video(prompt, speech_text, duration, voice_type):

    prompt = (prompt or "").strip()
    speech_text = (speech_text or "").strip()

    if not prompt:
        return "✗ اكتبي وصف الفيديو أولًا"

    job_id = str(uuid.uuid4())[:8]

    request_data = {
        "job_id": job_id,
        "prompt": prompt,
        "speech_text": speech_text,
        "duration_seconds": int(duration),
        "voice_type": voice_type
    }

    request_path = os.path.join(
        REQUESTS_DIR,
        f"{job_id}.json"
    )

    with open(
        request_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            request_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    return (
        "✓ تم تجهيز طلب نص إلى فيديو\n"
        f"✓ رقم المهمة: {job_id}\n"
        f"✓ المدة المطلوبة: {int(duration)} ثوانٍ\n"
        "✓ وصف المشهد محفوظ\n"
        "⏳ التوليد النهائي ينتظر تشغيل GPU"
    )




def preview_speech(speech_text, voice_type):

    speech_text = (speech_text or "").strip()

    if not speech_text:
        return None

    # في نسخة الويب التجريبية:
    # لا نحاول تشغيل ElevenLabs حتى لا يظهر خطأ للمستخدم.
    try:
        from video_engine.providers import runway_provider

        if getattr(
            runway_provider,
            "FADL_WEB_TRIAL_MODE",
            False
        ):
            return None

    except Exception:
        pass

    audio_id = str(uuid.uuid4())[:8]

    output_path = os.path.join(
        AUDIO_DIR,
        f"{audio_id}.mp3"
    )

    try:
        return generate_speech(
            speech_text,
            voice_type,
            output_path
        )

    except Exception:
        return None


def get_latest_generated_video():

    videos = []

    for name in os.listdir(OUTPUTS_DIR):
        if name.lower().endswith(".mp4"):
            path = os.path.join(OUTPUTS_DIR, name)
            videos.append(path)

    if not videos:
        return None, None

    latest = max(
        videos,
        key=os.path.getmtime
    )

    return latest, latest


def add_text_to_video_ui():

    gr.Markdown("## نص إلى فيديو")

    gr.Markdown(
        """
        اكتب وصف المشهد الذي تريد إنشاءه،
        ثم اختر مدة الفيديو التقريبية.
        """
    )

    prompt_input = gr.Textbox(
        label="وصف الفيديو",
        placeholder=(
            "مثال: رجل يسير في مزرعة خضراء "
            "والجو ممطر بهدوء"
        ),
        lines=5
    )

    mode_input = gr.Radio(
        choices=[
            "يتكلم",
            "صامت"
        ],
        value="يتكلم",
        label="نوع الفيديو"
    )

    speech_input = gr.Textbox(
        label="الكلام الذي ستقوله الشخصية",
        placeholder="مثال: السلام عليكم، كيف حالكم؟",
        lines=3
    )

    motion_input = gr.Dropdown(
        choices=[
            "حسب الوصف",
            "حركة بسيطة وهادئة",
            "مشي طبيعي",
            "ثابت تقريبًا"
        ],
        value="حسب الوصف",
        label="نوع الحركة"
    )

    duration_input = gr.Slider(
        minimum=3,
        maximum=15,
        value=5,
        step=1,
        label="مدة الفيديو بالثواني"
    )

    voice_input = gr.Dropdown(
        choices=["رجل", "امرأة", "ولد", "بنت"],
        value="رجل",
        label="اختر الصوت"
    )

    voice_preview_button = gr.Button(
        "🔊 معاينة الصوت — غير متاحة في التجربة"
    )

    voice_preview = gr.Audio(
        label="معاينة صوت الشخصية",
        interactive=False
    )

    prepare_button = gr.Button(
        "معاينة التكلفة قبل التوليد"
    )

    cost_preview = gr.Textbox(
        label="معاينة التكلفة والحماية",
        interactive=False,
        lines=8
    )

    confirmation_data = gr.Textbox(
        visible=False
    )

    confirm_button = gr.Button(
        "✅ تأكيد التوليد"
    )

    preview_button = gr.Button(
        "عرض آخر فيديو مولد"
    )

    final_video = gr.Video(
        label="معاينة الفيديو النهائي",
        interactive=False
    )

    download_video = gr.File(
        label="تنزيل الفيديو النهائي",
        interactive=False
    )

    status = gr.Textbox(
        label="حالة الطلب",
        interactive=False,
        lines=6
    )

    voice_preview_button.click(
        fn=preview_speech,
        inputs=[
            speech_input,
            voice_input
        ],
        outputs=voice_preview
    )

    prepare_button.click(
        fn=prepare_paid_generation,
        inputs=[
            prompt_input,
            speech_input,
            duration_input,
            voice_input,
            mode_input,
            motion_input
        ],
        outputs=[
            cost_preview,
            confirmation_data
        ]
    )

    confirm_button.click(
        fn=confirm_and_generate_video,
        inputs=[
            confirmation_data
        ],
        outputs=[
            status,
            final_video,
            download_video,
            confirmation_data
        ]
    )

    preview_button.click(
        fn=get_latest_generated_video,
        inputs=[],
        outputs=[
            final_video,
            download_video
        ]
    )


# يتم ربط عناصر المعاينة داخل add_text_to_video_ui


# =========================================================
# Runway generation safety layer
# =========================================================

def calculate_runway_cost(duration):
    """
    حساب التكلفة المتوقعة فقط.
    لا يرسل أي طلب إلى Runway.
    """
    duration = int(duration)
    credits_per_second = 10
    return duration * credits_per_second


def _prepare_paid_generation_legacy_unused(
    prompt,
    speech_text,
    duration,
    voice_type,
    mode_choice,
    motion_choice
):
    """
    تجهيز الطلب وعرض التكلفة قبل أي إرسال مدفوع.
    """

    prompt = (prompt or "").strip()
    speech_text = (speech_text or "").strip()

    if not prompt:
        return (
            "✗ اكتبي وصف الفيديو أولًا",
            ""
        )

    mode_choice = (mode_choice or "يتكلم").strip()
    motion_choice = (motion_choice or "حسب الوصف").strip()

    if mode_choice == "صامت":
        mode = "silent"
        speech_text = ""
    else:
        mode = "talking"

        if not speech_text:
            return (
                "✗ اكتبي الكلام الذي ستقوله الشخصية",
                ""
            )

    cost = calculate_runway_cost(duration)

    message = (
        "=== معاينة قبل التوليد ===\n"
        f"المدة: {int(duration)} ثوانٍ\n"
        f"نوع الصوت: {voice_type}\n"
        f"وضع الفيديو: {mode}\n"
        f"الحركة: {motion_choice}\n"
        f"التكلفة المتوقعة: {cost} Credits\n\n"
        "🔒 لم يتم إرسال الطلب إلى Runway\n"
        "🔒 لم يتم استهلاك Credits\n"
        "اضغطي تأكيد التوليد فقط إذا أردتِ المتابعة."
    )

    confirmation_data = {
        "prompt": prompt,
        "speech_text": speech_text,
        "duration_seconds": int(duration),
        "voice_type": voice_type,
        "mode": mode,
        "motion_choice": motion_choice,
        "estimated_credits": cost,
        "master_generation_instruction":
            TEXT_TO_VIDEO_MASTER_GENERATION_INSTRUCTION,
        "master_negative_instruction":
            TEXT_TO_VIDEO_MASTER_NEGATIVE_INSTRUCTION
    }

    return message, json.dumps(
        confirmation_data,
        ensure_ascii=False
    )


# =========================================================
# SAFE REAL RUNWAY GENERATION
# =========================================================

CONFIRMATIONS_FILE = os.path.join(
    BASE,
    "used_confirmations.json"
)


def _load_used_confirmations():
    if not os.path.exists(CONFIRMATIONS_FILE):
        return []

    try:
        with open(CONFIRMATIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _consume_confirmation(token):
    used = _load_used_confirmations()

    if token in used:
        return False

    # نسجل التأكيد قبل الإرسال لمنع الضغط المكرر
    used.append(token)

    with open(CONFIRMATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            used,
            f,
            ensure_ascii=False,
            indent=2
        )

    return True


def prepare_paid_generation(
    prompt,
    speech_text,
    duration,
    voice_type,
    mode_choice,
    motion_choice
):

    prompt = (prompt or "").strip()
    speech_text = (speech_text or "").strip()

    if not prompt:
        return (
            "✗ اكتبي وصف الفيديو أولًا",
            ""
        )

    duration = int(duration)

    mode_choice = (
        mode_choice
        or "يتكلم"
    ).strip()

    motion_choice = (
        motion_choice
        or "حسب الوصف"
    ).strip()

    # =====================================================
    # نوع الفيديو
    # =====================================================

    if mode_choice == "صامت":
        mode = "silent"
        speech_text = ""

    else:
        mode = "talking"

        if not speech_text:
            return (
                "✗ اكتبي الكلام الذي ستقوله الشخصية",
                ""
            )

    # =====================================================
    # تعليمات الحركة
    # =====================================================

    motion_map = {
        "حسب الوصف": "",

        "حركة بسيطة وهادئة":
            " Natural calm subtle movement. "
            "No exaggerated or sudden motion.",

        "مشي طبيعي":
            " Natural relaxed walking pace. "
            "Natural arm movement and realistic body motion.",

        "ثابت تقريبًا":
            " Keep the person mostly still with only "
            "very subtle natural movement."
    }

    motion_instruction = motion_map.get(
        motion_choice,
        ""
    )

    effective_prompt = (
        prompt
        + motion_instruction
    ).strip()

    # =====================================================
    # التكلفة
    # =====================================================

    cost = calculate_runway_cost(
        duration
    )

    # رمز تأكيد لمرة واحدة
    confirm_token = str(
        uuid.uuid4()
    )

    confirmation_data = {
        "confirm_token": confirm_token,

        "prompt": effective_prompt,

        "original_prompt": prompt,

        "speech_text": speech_text,

        "duration_seconds": duration,

        "voice_type": voice_type,

        "mode": mode,

        "motion_choice": motion_choice,

        "model": "grok_imagine_1_5",

        "resolution": "480p",

        "ratio": "16:9",

        "estimated_credits": cost,

        "master_generation_instruction":
            TEXT_TO_VIDEO_MASTER_GENERATION_INSTRUCTION,

        "master_negative_instruction":
            TEXT_TO_VIDEO_MASTER_NEGATIVE_INSTRUCTION
    }

    message = (
        "=== معاينة قبل التوليد ===\n"
        f"المدة: {duration} ثوانٍ\n"
        f"نوع الصوت: {voice_type}\n"
        f"وضع الفيديو: {mode}\n"
        f"الحركة: {motion_choice}\n"
        f"التكلفة المتوقعة: {cost} Credits\n\n"
        "🔒 لم يتم إرسال أي طلب بعد\n"
        "🔒 لم يتم استهلاك Credits\n"
        "اضغطي «تأكيد التوليد» مرة واحدة فقط للمتابعة."
    )

    return (
        message,
        json.dumps(
            confirmation_data,
            ensure_ascii=False
        )
    )


def confirm_and_generate_video(confirmation_json):

    import time
    import requests
    import importlib
    from pathlib import Path

    if not confirmation_json:
        return (
            "✗ اعملي معاينة التكلفة أولًا",
            None,
            None,
            ""
        )

    try:
        data = json.loads(confirmation_json)
    except Exception:
        return (
            "✗ بيانات التأكيد غير صالحة",
            None,
            None,
            ""
        )

    token = data.get("confirm_token")

    if not token:
        return (
            "✗ رمز التأكيد غير موجود",
            None,
            None,
            ""
        )

    # أهم حماية: نفس التأكيد لا يعمل مرتين
    if not _consume_confirmation(token):
        return (
            "🔒 تم منع التوليد المكرر لهذا التأكيد",
            None,
            None,
            ""
        )

    job_id = str(uuid.uuid4())[:8]

    request_path = os.path.join(
        REQUESTS_DIR,
        f"{job_id}.json"
    )

    request_data = {
        "job_id": job_id,
        "type": "text_to_video",
        "prompt": data.get("prompt", ""),
        "speech_text": data.get("speech_text", ""),
        "duration_seconds": int(
            data.get("duration_seconds", 5)
        ),
        "voice_type": data.get("voice_type", "رجل"),
        "mode": data.get("mode", "silent"),

        "islamic_modesty_guard":
            TEXT_TO_VIDEO_ISLAMIC_MODESTY_GUARD,

        "islamic_modesty_negative_guard":
            TEXT_TO_VIDEO_ISLAMIC_MODESTY_NEGATIVE,

        "model": data.get(
            "model",
            "grok_imagine_1_5"
        ),
        "resolution": data.get(
            "resolution",
            "480p"
        ),
        "ratio": data.get(
            "ratio",
            "16:9"
        ),
        "estimated_credits": data.get(
            "estimated_credits"
        ),
        "confirmed_for_paid_generation": True,
        "master_generation_instruction": data.get(
            "master_generation_instruction",
            TEXT_TO_VIDEO_MASTER_GENERATION_INSTRUCTION
        ),
        "master_negative_instruction": data.get(
            "master_negative_instruction",
            TEXT_TO_VIDEO_MASTER_NEGATIVE_INSTRUCTION
        )
    }

    with open(
        request_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            request_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    # تسجيل المهمة في jobs.json
    jobs_file = Path(
        os.path.join(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    ".."
                )
            ),
            "video_engine",
            "jobs.json"
        )
    )

    try:
        jobs = json.loads(
            jobs_file.read_text(encoding="utf-8")
        )
        if not isinstance(jobs, list):
            jobs = []
    except Exception:
        jobs = []

    jobs.append({
        "job_id": job_id,
        "type": "text_to_video",
        "request_file": request_path,
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

    # تحميل Runway provider
    from video_engine.providers import runway_provider
    runway_provider = importlib.reload(runway_provider)

    # السماح لهذه المهمة فقط
    runway_provider.ALLOWED_PAID_JOB_ID = job_id
    runway_provider.PAID_ENGINE_ENABLED = True

    try:
        result = runway_provider.send_to_runway(job_id)

    finally:
        # إغلاق المحرك المدفوع فورًا
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

    api_key = os.environ.get(
        "RUNWAYML_API_SECRET"
    )

    if not api_key:
        return (
            "✓ تم إرسال المهمة، لكن مفتاح المتابعة غير موجود\n"
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

    # متابعة نفس المهمة فقط
    for _ in range(120):

        r = requests.get(
            task_url,
            headers=headers,
            timeout=30
        )

        if r.status_code != 200:
            return (
                f"✗ خطأ أثناء متابعة Runway: {r.status_code}",
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

            output_path = Path(
                OUTPUTS_DIR
            ) / f"{job_id}.mp4"

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
                "✅ تم توليد الفيديو بنجاح\n"
                f"✅ job_id: {job_id}\n"
                f"✅ Task ID: {task_id}\n"
                f"✅ التكلفة المتوقعة: "
                f"{data.get('estimated_credits')} Credits\n"
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

        if task_status == "CANCELED":
            return (
                "✗ تم إلغاء المهمة",
                None,
                None,
                ""
            )

        time.sleep(5)

    return (
        "⏳ المهمة ما زالت تعمل. لم يتم إرسال مهمة أخرى.",
        None,
        None,
        ""
    )

