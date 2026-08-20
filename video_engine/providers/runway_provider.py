
import json
import base64
import mimetypes
import re
import requests
import sys
from google.colab import userdata
from pathlib import Path

VALIDATOR_DIR = "/content/fadl_ai/video_engine"

if VALIDATOR_DIR not in sys.path:
    sys.path.insert(0, VALIDATOR_DIR)

import request_validator

BASE = Path("/content/fadl_ai")
JOBS_FILE = BASE / "video_engine" / "jobs.json"

SENT_JOBS_FILE = BASE / "video_engine" / "runway_sent_jobs.json"

# =========================================================
# PUBLIC LAUNCH CREDIT SAFETY
# =========================================================

MAX_CREDITS_PER_JOB = 50
GLOBAL_DAILY_CREDIT_LIMIT = 500
RUNWAY_CREDITS_PER_SECOND = 10

DAILY_QUOTA_FILE = (
    BASE / "video_engine" / "runway_daily_quota.json"
)

DAILY_QUOTA_LOCK = (
    BASE / "video_engine" / "runway_daily_quota.lock"
)


def _quota_today():
    from datetime import datetime, timezone

    return datetime.now(
        timezone.utc
    ).date().isoformat()


def _estimate_request_credits(request_data):

    explicit = request_data.get(
        "estimated_credits"
    )

    try:
        if explicit is not None:
            credits = int(explicit)
            if credits > 0:
                return credits
    except Exception:
        pass

    duration = (
        request_data.get("duration_seconds")
        or request_data.get("duration")
        or 5
    )

    try:
        duration = int(duration)
    except Exception:
        duration = 5

    return duration * RUNWAY_CREDITS_PER_SECOND


def _read_quota_data():

    today = _quota_today()

    default = {
        "date": today,
        "spent_credits": 0,
        "reservations": {}
    }

    if not DAILY_QUOTA_FILE.exists():
        return default

    try:
        data = json.loads(
            DAILY_QUOTA_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return default

    if data.get("date") != today:
        return default

    if not isinstance(
        data.get("reservations"),
        dict
    ):
        data["reservations"] = {}

    try:
        data["spent_credits"] = int(
            data.get("spent_credits", 0)
        )
    except Exception:
        data["spent_credits"] = 0

    return data


def _write_quota_data(data):

    DAILY_QUOTA_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    DAILY_QUOTA_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def reserve_daily_credits(
    job_id,
    request_data
):

    import fcntl

    credits = _estimate_request_credits(
        request_data
    )

    # حد المهمة الواحدة
    if credits > MAX_CREDITS_PER_JOB:
        return {
            "allowed": False,
            "credits": credits,
            "reason":
                f"المهمة تحتاج {credits} Credits "
                f"والحد الأقصى للمهمة هو "
                f"{MAX_CREDITS_PER_JOB}."
        }

    DAILY_QUOTA_LOCK.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        DAILY_QUOTA_LOCK,
        "a+",
        encoding="utf-8"
    ) as lock_file:

        fcntl.flock(
            lock_file.fileno(),
            fcntl.LOCK_EX
        )

        try:
            data = _read_quota_data()

            reservations = data[
                "reservations"
            ]

            # إذا كانت نفس المهمة محجوزة
            if job_id in reservations:
                return {
                    "allowed": True,
                    "credits": int(
                        reservations[job_id]
                    ),
                    "already_reserved": True
                }

            reserved_total = sum(
                int(v)
                for v in reservations.values()
            )

            projected = (
                data["spent_credits"]
                + reserved_total
                + credits
            )

            if (
                projected
                > GLOBAL_DAILY_CREDIT_LIMIT
            ):
                return {
                    "allowed": False,
                    "credits": credits,
                    "spent":
                        data["spent_credits"],
                    "reserved":
                        reserved_total,
                    "daily_limit":
                        GLOBAL_DAILY_CREDIT_LIMIT,
                    "reason":
                        "تم الوصول إلى سقف "
                        "Runway اليومي لفضل AI."
                }

            reservations[job_id] = credits

            _write_quota_data(data)

            return {
                "allowed": True,
                "credits": credits,
                "spent":
                    data["spent_credits"],
                "daily_limit":
                    GLOBAL_DAILY_CREDIT_LIMIT
            }

        finally:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_UN
            )


def release_daily_credits(job_id):

    import fcntl

    DAILY_QUOTA_LOCK.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        DAILY_QUOTA_LOCK,
        "a+",
        encoding="utf-8"
    ) as lock_file:

        fcntl.flock(
            lock_file.fileno(),
            fcntl.LOCK_EX
        )

        try:
            data = _read_quota_data()

            data["reservations"].pop(
                job_id,
                None
            )

            _write_quota_data(data)

        finally:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_UN
            )


def commit_daily_credits(job_id):

    import fcntl

    DAILY_QUOTA_LOCK.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        DAILY_QUOTA_LOCK,
        "a+",
        encoding="utf-8"
    ) as lock_file:

        fcntl.flock(
            lock_file.fileno(),
            fcntl.LOCK_EX
        )

        try:
            data = _read_quota_data()

            credits = int(
                data["reservations"].pop(
                    job_id,
                    0
                )
            )

            data["spent_credits"] += credits

            _write_quota_data(data)

            return {
                "credits": credits,
                "spent_credits":
                    data["spent_credits"],
                "daily_limit":
                    GLOBAL_DAILY_CREDIT_LIMIT
            }

        finally:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_UN
            )


PROVIDER_NAME = "runway"

RUNWAY_SECRET_NAME = "RUNWAYML_API_SECRET"

def get_runway_api_key():
    import os

    # أولًا: المفتاح المفعّل في جلسة Colab الحالية
    env_key = os.environ.get(RUNWAY_SECRET_NAME)
    if env_key:
        return env_key

    # ثانيًا: Colab Secrets إذا كان موجودًا
    try:
        return userdata.get(RUNWAY_SECRET_NAME)
    except Exception:
        return None


# لا يوجد اتصال مدفوع حتى الآن
PAID_ENGINE_ENABLED = False
ALLOWED_PAID_JOB_ID = "ca956c3a"


def load_jobs():
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_job(job_id):
    for job in load_jobs():
        if job.get("job_id") == job_id:
            return job
    return None


def load_request(job):
    request_file = job.get("request_file")

    if not request_file:
        raise ValueError("ملف الطلب غير محدد")

    path = Path(request_file)

    if not path.exists():
        raise FileNotFoundError(
            f"ملف الطلب غير موجود: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_runway_payload(job_id):

    job = get_job(job_id)

    if not job:
        return {
            "ready": False,
            "message": "المهمة غير موجودة"
        }

    request = load_request(job)

    job_type = job.get("type")

    payload = {
        "provider": PROVIDER_NAME,
        "job_id": job_id,
        "job_type": job_type,
        "mode": request.get("mode", ""),

        # وصف المستخدم الأصلي
        "user_prompt": (
            request.get("motion_text")
            or request.get("prompt")
            or request.get("scene_description")
            or ""
        ),

        # قواعد فضل AI
        "master_instruction":
            request.get(
                "master_generation_instruction",
                ""
            ),

        "negative_instruction":
            request.get(
                "master_negative_instruction",
                ""
            ),

        "image":
            request.get("image"),

        "audio":
            request.get("audio"),

        "duration":
            (
                request.get("duration_seconds")
                or request.get("duration")
                or 5
            ),

        "paid_engine_enabled":
            PAID_ENGINE_ENABLED
    }

    return {
        "ready": True,
        "payload": payload,
        "message":
            "تم تجهيز المهمة فقط — لم يتم إرسالها أو خصم أي مبلغ"
    }



def load_sent_jobs():
    if not SENT_JOBS_FILE.exists():
        return []

    try:
        with open(SENT_JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def job_already_sent(job_id):
    return job_id in load_sent_jobs()


def mark_job_sent(job_id):
    sent = load_sent_jobs()

    if job_id not in sent:
        sent.append(job_id)

    with open(SENT_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(sent, f, ensure_ascii=False, indent=2)




def image_file_to_data_uri(image_path):
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"الصورة غير موجودة: {path}"
        )

    mime, _ = mimetypes.guess_type(str(path))

    if mime not in (
        "image/jpeg",
        "image/png",
        "image/webp"
    ):
        raise ValueError(
            f"نوع الصورة غير مدعوم: {mime}"
        )

    encoded = base64.b64encode(
        path.read_bytes()
    ).decode("ascii")

    return f"data:{mime};base64,{encoded}"




# ============================================================
# FADL AI — CONTENT SAFETY GUARD
# ============================================================

FADL_CONTENT_SAFETY_VERSION = "1.0"

# كلمات/عبارات شديدة الوضوح فقط.
# نتجنب الكلمات المحتملة في الكلام السوداني/المصري/السعودي العادي.
FADL_BLOCKED_CONTENT_PATTERNS = [

    # محتوى جنسي صريح
    r"\bporn\b",
    r"\bpornographic\b",
    r"\bexplicit sex\b",
    r"\bsexual intercourse\b",
    r"\bnude sex\b",

    # طلبات عري صريحة
    r"\bfully nude\b",
    r"\bcompletely naked\b",
    r"\bremove all (?:her|his|their) clothes\b",

    # عربي — عبارات صريحة عالية الثقة
    r"محتوي\s+اباحي",
    r"فيديو\s+اباحي",
    r"مشهد\s+جنسي\s+صريح",
    r"علاقه\s+جنسيه\s+صريحه",
    r"عاريه\s+تماما",
    r"بدون\s+ملابس\s+تماما",
]


def _fadl_normalize_safety_text(value):
    """
    Normalization بسيط للفحص فقط.
    لا يغيّر نص المستخدم الأصلي.
    """
    value = str(value or "").strip().lower()

    value = (
        value
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ة", "ه")
    )

    value = re.sub(r"\s+", " ", value)

    return value



# سباب/إهانات شديدة الوضوح فقط.
# القائمة متعمدة أن تكون صغيرة لتقليل False Positives
# في السوداني والمصري والسعودي.
FADL_SEVERE_PROFANITY_PATTERNS = [
    r"\bfuck\s+you\b",
    r"\bmotherfucker\b",
    r"\bfuck\s+off\b",

    # عربي بعد normalization
    r"يا\s+ابن\s+الكلب",
    r"يا\s+ابن\s+الكلبه",
    r"يلعن\s+ابوك",
    r"يلعن\s+امك",
]


def fadl_check_severe_profanity(value):
    normalized = _fadl_normalize_safety_text(
        value
    )

    if not normalized:
        return {
            "allowed": True,
            "matched": None,
        }

    for pattern in FADL_SEVERE_PROFANITY_PATTERNS:
        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        ):
            return {
                "allowed": False,
                "matched": pattern,
            }

    return {
        "allowed": True,
        "matched": None,
    }


def fadl_check_content_safety(request_data):
    """
    فحص محلي قبل Credits وقبل Runway.

    Returns:
        {
            "allowed": bool,
            "reason": str,
            "matched": str | None
        }
    """

    if not isinstance(request_data, dict):
        return {
            "allowed": False,
            "reason": "تعذر فحص محتوى الطلب.",
            "matched": None,
        }

    fields = [
        request_data.get("prompt"),
        request_data.get("motion_text"),
        request_data.get("scene_description"),
        request_data.get("speech_text"),
    ]

    combined = " ".join(
        str(v)
        for v in fields
        if v
    )

    normalized = _fadl_normalize_safety_text(
        combined
    )

    profanity = fadl_check_severe_profanity(
        combined
    )

    if not profanity.get("allowed"):
        return {
            "allowed": False,
            "reason": (
                "هذا الطلب غير متاح في فضل AI "
                "لأنه يتضمن ألفاظًا غير مناسبة."
            ),
            "matched": profanity.get("matched"),
        }

    # طلب فارغ ليس قضية Safety؛
    # Request Validator يتعامل معه.
    if not normalized:
        return {
            "allowed": True,
            "reason": "",
            "matched": None,
        }

    for pattern in FADL_BLOCKED_CONTENT_PATTERNS:

        if re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        ):
            return {
                "allowed": False,
                "reason": (
                    "هذا الطلب غير متاح في فضل AI "
                    "لأنه يتضمن محتوى غير مناسب."
                ),
                "matched": pattern,
            }

    return {
        "allowed": True,
        "reason": "",
        "matched": None,
    }





# =========================================================
# FADL WEB TRIAL GUARD
# =========================================================

# الوضع الافتراضي للويب التجريبي:
# يسمح بتصفح واستخدام الأقسام المحلية،
# لكنه يمنع أي توليد مدفوع حتى نفتحه نحن صراحة.

FADL_WEB_TRIAL_MODE = True
FADL_WEB_PAID_GENERATION_ENABLED = False


def fadl_web_trial_allows_paid_generation():
    """
    حماية إضافية خاصة بالويب التجريبي.
    False = لا يسمح بأي طلب مدفوع.
    """

    if FADL_WEB_TRIAL_MODE:
        return bool(
            FADL_WEB_PAID_GENERATION_ENABLED
        )

    return True


def send_to_runway(job_id):

    # FADL_WEB_TRIAL_BLOCK
    # هذه الحماية تعمل قبل أي Credits أو API.
    if not fadl_web_trial_allows_paid_generation():
        return {
            "sent": False,
            "charged": False,
            "message": (
                "التوليد المدفوع غير متاح حاليًا "
                "في النسخة التجريبية من فضل AI."
            ),
            "reason": "web_trial_paid_generation_locked"
        }


    if job_already_sent(job_id):
        return {
            "sent": False,
            "charged": False,
            "duplicate_blocked": True,
            "message": "تم منع إرسال المهمة لأنها أُرسلت سابقًا."
        }

    preview = prepare_runway_payload(job_id)

    if not preview.get("ready"):
        return {
            "sent": False,
            "charged": False,
            "message": preview.get(
                "message",
                "تعذر تجهيز المهمة"
            )
        }

    payload = preview["payload"]

    validation = request_validator.validate_request(
        payload
    )

    if not validation.get("valid"):
        return {
            "sent": False,
            "charged": False,
            "validation_failed": True,
            "message": validation.get(
                "reason",
                "الطلب غير صالح"
            )
        }

    # حماية مقصودة
    if job_id != ALLOWED_PAID_JOB_ID:
        return {
            "sent": False,
            "charged": False,
            "message": "هذه المهمة غير مصرح لها باستخدام Runway."
        }

    if not PAID_ENGINE_ENABLED:
        return {
            "sent": False,
            "charged": False,
            "message":
                "المحرك المدفوع مقفول. لم يتم إرسال المهمة ولم يتم الخصم."
        }

    # لا يتم الوصول إلى هنا إلا إذا تم فتح القفل يدويًا
    api_key = get_runway_api_key()

    if not api_key:
        return {
            "sent": False,
            "charged": False,
            "message": "مفتاح Runway غير متاح"
        }

    request_data = load_request(get_job(job_id))

    # =====================================================
    # بناء البرومبت الحقيقي الذي سيصل إلى Runway
    # =====================================================

    user_prompt = (
        request_data.get("motion_text")
        or request_data.get("prompt")
        or request_data.get("scene_description")
        or ""
    ).strip()

    master_instruction = (
        request_data.get("master_generation_instruction")
        or ""
    ).strip()

    negative_instruction = (
        request_data.get("master_negative_instruction")
        or ""
    ).strip()

    style_preservation_guard = (
        request_data.get("style_preservation_guard")
        or ""
    ).strip()

    style_negative_guard = (
        request_data.get("style_negative_guard")
        or ""
    ).strip()

    animal_preservation_guard = (
        request_data.get("animal_preservation_guard")
        or ""
    ).strip()

    animal_negative_guard = (
        request_data.get("animal_negative_guard")
        or ""
    ).strip()

    islamic_modesty_guard = (
        request_data.get("islamic_modesty_guard")
        or ""
    ).strip()

    islamic_modesty_negative_guard = (
        request_data.get("islamic_modesty_negative_guard")
        or ""
    ).strip()

    # =====================================================
    # Runway prompt budget
    # نحافظ على طلب المستخدم كاملًا قدر الإمكان
    # ونختصر قواعد فضل بدل قص الحركة المطلوبة
    # =====================================================

    RUNWAY_PROMPT_LIMIT = 950

    compact_rules = (
        "Keep exactly the same person, face, clothing, hairstyle, "
        "headwear, accessories, scene and camera. "
        "Add nothing new. "
        "Execute the requested action exactly with the correct side, "
        "direction, range and endpoint. "
        "Never reverse the motion. "
        "No extra movement. "
        "Keep hands, fingers and limbs anatomically correct."
    )

    compact_negative = (
        "No face drift, identity change, clothing or headwear change, "
        "extra limbs or fingers, wrong side, reversed motion, "
        "incomplete action or wrong endpoint."
    )

    # حماية أسلوب الصورة بدون استهلاك مساحة كبيرة من Prompt Budget
    if style_preservation_guard:
        compact_rules += (
            " Preserve the exact source visual style and character design. "
            "Anime/cartoon/illustration must remain in the same original style."
        )

    if style_negative_guard:
        compact_negative += (
            " No style conversion, style drift or character redesign."
        )

    if animal_preservation_guard:
        compact_rules += (
            " For animals, preserve exact species, anatomy, fur, markings "
            "and tail; never humanize or change species."
        )

    if animal_negative_guard:
        compact_negative += (
            " No animal-to-human change, species drift, missing tail "
            "or animal anatomy distortion."
        )

    if islamic_modesty_guard:
        compact_rules += (
            " Keep women and girls modestly dressed. Preserve existing hijab, "
            "abaya and niqab; keep clothing non-transparent, non-revealing "
            "and appropriately loose. Never reduce existing covering."
        )

    if islamic_modesty_negative_guard:
        compact_negative += (
            " No removal of hijab, abaya or niqab, no revealing or transparent "
            "clothing, no accidental exposure and no modesty drift."
        )

    prefix = "EXECUTE EXACTLY:\n"
    rules_block = (
        "\n\nFADL RULES:\n"
        + compact_rules
        + "\n\nAVOID:\n"
        + compact_negative
    )

    # الأولوية الكاملة لوصف المستخدم
    prompt = (
        prefix
        + user_prompt
        + rules_block
    ).strip()

    # لو بقي طويلًا جدًا، نقلل القواعد أولًا
    if len(prompt) > RUNWAY_PROMPT_LIMIT:

        compact_negative = (
            "No face drift, new clothing/headwear, extra limbs, "
            "wrong side, reversed motion or wrong endpoint."
        )

        rules_block = (
            "\n\nFADL RULES:\n"
            + compact_rules
            + "\n\nAVOID:\n"
            + compact_negative
        )

        prompt = (
            prefix
            + user_prompt
            + rules_block
        ).strip()

    # آخر حماية فقط إذا كان طلب المستخدم نفسه طويلًا جدًا
    if len(prompt) > RUNWAY_PROMPT_LIMIT:
        available = (
            RUNWAY_PROMPT_LIMIT
            - len(prefix)
            - len(rules_block)
        )

        trimmed = user_prompt[:available].rstrip()

        # لا ننهي في منتصف كلمة قدر الإمكان
        if len(trimmed) < len(user_prompt):
            last_space = trimmed.rfind(" ")
            if last_space > 100:
                trimmed = trimmed[:last_space].rstrip()

        prompt = (
            prefix
            + trimmed
            + rules_block
        ).strip()

    speech_text = (
        request_data.get("speech_text")
        or ""
    ).strip()

    # نضع الكلام داخل البرومبت نفسه ليحاول النموذج توليده طبيعيًا
    if speech_text:
        prompt = (
            prompt
            + "\nThe person clearly says in Arabic: "
            + speech_text
        )

    # قواعد جودة الحركة البشرية في فضل AI
    human_motion_quality = """
Natural relaxed human movement.
Natural realistic walking pace, not fast or rushed.
Smooth realistic body motion.
Natural arm swing while walking.
Anatomically correct hands and fingers.
Five natural fingers on each hand.
Hands remain stable and proportional.
No warped hands or deformed fingers.
No extra or missing fingers.
No distorted limbs.
No sudden or exaggerated body movement.
Consistent human anatomy throughout the video.
"""

    # لا نتجاوز حد Runway بعد إضافة جودة الحركة
    quality_block = "\n" + human_motion_quality.strip()

    if len(prompt) + len(quality_block) <= RUNWAY_PROMPT_LIMIT:
        prompt = prompt + quality_block

    # حماية نهائية قبل بناء runway_payload
    if len(prompt) > RUNWAY_PROMPT_LIMIT:
        prompt = prompt[:RUNWAY_PROMPT_LIMIT].rstrip()

        # تجنب القطع في منتصف الكلمة قدر الإمكان
        last_space = prompt.rfind(" ")
        if last_space > 800:
            prompt = prompt[:last_space].rstrip()

    job_type = (
        request_data.get("type")
        or request_data.get("_request_type")
        or get_job(job_id).get("type")
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06"
    }

    if job_type == "image_to_video":

        image_path = request_data.get("image")

        if not image_path:
            return {
                "sent": False,
                "charged": False,
                "message": "الصورة غير موجودة في الطلب"
            }

        image_data_uri = image_file_to_data_uri(
            image_path
        )

        # تحويل النسب البسيطة إلى القيم التي يقبلها Runway Image-to-Video
        ratio_map = {
            "16:9": "1280:720",
            "9:16": "720:1280",
            "4:3": "1104:832",
            "3:4": "832:1104",
            "1:1": "960:960",
            "21:9": "1584:672"
        }

        requested_ratio = request_data.get(
            "ratio",
            "16:9"
        )

        runway_ratio = ratio_map.get(
            requested_ratio,
            requested_ratio
        )

        allowed_ratios = {
            "1280:720",
            "720:1280",
            "1104:832",
            "832:1104",
            "960:960",
            "1584:672"
        }

        if runway_ratio not in allowed_ratios:
            runway_ratio = "1280:720"

        runway_payload = {
            "model": request_data.get(
                "model",
                "gen4_turbo"
            ),
            "promptImage": image_data_uri,
            "promptText": prompt,
            "ratio": runway_ratio,
            "duration": int(
                request_data.get(
                    "duration_seconds",
                    5
                )
            )
        }

        endpoint = (
            "https://api.dev.runwayml.com/v1/image_to_video"
        )

    else:

        runway_payload = {
            "model": request_data.get(
                "model",
                "grok_imagine_1_5"
            ),
            "promptText": prompt,
            "ratio": request_data.get(
                "ratio",
                "16:9"
            ),
            "resolution": request_data.get(
                "resolution",
                "480p"
            ),
            "duration": int(
                request_data.get(
                    "duration_seconds",
                    5
                )
            )
        }

        endpoint = (
            "https://api.dev.runwayml.com/v1/text_to_video"
        )

    # =====================================================
    # PUBLIC CREDIT QUOTA
    # =====================================================

    # =====================================================
    # FADL CONTENT SAFETY — BEFORE CREDITS / API
    # =====================================================

    safety = fadl_check_content_safety(
        request_data
    )

    if not safety.get("allowed"):
        return {
            "sent": False,
            "charged": False,
            "content_blocked": True,
            "message": safety.get(
                "reason",
                "هذا الطلب غير متاح في فضل AI."
            )
        }

    quota = reserve_daily_credits(
        job_id,
        request_data
    )

    if not quota.get("allowed"):
        return {
            "sent": False,
            "charged": False,
            "quota_blocked": True,
            "estimated_credits":
                quota.get("credits"),
            "daily_limit":
                GLOBAL_DAILY_CREDIT_LIMIT,
            "message":
                quota.get(
                    "reason",
                    "تم منع المهمة لحماية الرصيد."
                )
        }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=runway_payload,
            timeout=60
        )

    except Exception as e:

        # Runway لم يؤكد قبول المهمة
        release_daily_credits(job_id)

        return {
            "sent": False,
            "charged": False,
            "network_error": True,
            "message":
                f"تعذر الاتصال بـ Runway: {e}"
        }

    if response.status_code not in (200, 201):

        # لم يتم قبول المهمة، نرجع الحجز
        release_daily_credits(job_id)

        return {
            "sent": False,
            "charged": False,
            "http_status":
                response.status_code,
            "message":
                response.text
        }

    data = response.json()

    quota_result = commit_daily_credits(
        job_id
    )

    mark_job_sent(job_id)

    return {
        "sent": True,
        "charged": True,
        "task_id": data.get("id"),
        "response": data,
        "estimated_credits":
            quota_result.get("credits"),
        "daily_spent_credits":
            quota_result.get(
                "spent_credits"
            ),
        "daily_limit":
            GLOBAL_DAILY_CREDIT_LIMIT,
        "message":
            "تم إرسال المهمة إلى Runway مرة واحدة"
    }


print("Runway provider loaded safely")
