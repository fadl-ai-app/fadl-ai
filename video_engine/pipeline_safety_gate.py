
from pathlib import Path

import request_validator
import job_manager
import full_pipeline


def check_pipeline(job_id):

    # 1) تحميل الطلب
    try:
        request = full_pipeline.load_request(job_id)
    except Exception as e:
        return {
            "ok": False,
            "stage": "load_request",
            "reason": str(e)
        }

    # 2) فحص صحة الطلب
    try:
        validation = request_validator.validate_request(request)
    except Exception as e:
        return {
            "ok": False,
            "stage": "validation",
            "reason": str(e)
        }

    # يدعم أكثر من شكل لنتيجة الفاحص
    if isinstance(validation, tuple):
        valid = bool(validation[0])
        validation_reason = (
            validation[1]
            if len(validation) > 1
            else ""
        )
    elif isinstance(validation, dict):
        valid = bool(
            validation.get(
                "valid",
                validation.get("ok", False)
            )
        )
        validation_reason = validation.get(
            "reason",
            validation.get("message", "")
        )
    else:
        valid = bool(validation)
        validation_reason = ""

    if not valid:
        return {
            "ok": False,
            "stage": "validation",
            "reason":
                validation_reason
                or "الطلب لم يجتز الفحص"
        }

    # 3) تسجيل المهمة إن لم تكن مسجلة
    request_file = str(
        (
        Path(__file__).resolve().parents[1]
        / "image_to_video"
    )
        / f"{job_id}_request.json"
    )

    job_manager.ensure_job(
        job_id=job_id,
        job_type=request.get("mode", "video"),
        request_file=request_file
    )

    # 4) فحص حالة المهمة
    safety = job_manager.safety_status(job_id)

    if not safety["ok"]:
        return {
            "ok": False,
            "stage": "job_safety",
            "reason": safety["reason"],
            "checks": safety.get("checks", {})
        }

    # 5) تجهيز Pipeline فقط
    pipeline = full_pipeline.prepare_pipeline(
        job_id,
        dry_run=True
    )

    return {
        "ok": True,
        "stage": "ready",
        "reason": "كل بوابات الأمان اجتازت الفحص",
        "pipeline": pipeline,
        "job": job_manager.get_job(job_id)
    }
