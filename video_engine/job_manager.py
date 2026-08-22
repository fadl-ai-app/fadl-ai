
import json
from pathlib import Path
from datetime import datetime

BASE = Path("/content/fadl_ai")
JOBS_FILE = BASE / "video_engine" / "jobs.json"


def load_jobs():
    if not JOBS_FILE.exists():
        return []

    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jobs(jobs):
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            jobs,
            f,
            ensure_ascii=False,
            indent=2
        )


def get_job(job_id):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:
            return job

    return None


def ensure_job(job_id, job_type, request_file):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:
            return job

    job = {
        "job_id": job_id,
        "type": job_type,
        "status": "ready",
        "request_file": request_file,
        "payment_confirmed": False,
        "created_at": datetime.now().isoformat()
    }

    jobs.append(job)
    save_jobs(jobs)

    return job


def can_start_job(job_id):
    job = get_job(job_id)

    if not job:
        return False, "المهمة غير موجودة"

    status = job.get("status", "ready")

    if status == "cancelled":
        return False, "المهمة ملغاة"

    if status == "processing":
        return False, "المهمة قيد التوليد بالفعل"

    if status == "completed":
        return False, "المهمة مكتملة بالفعل"

    if status in ["ready", "failed"]:
        return True, "المهمة قابلة للتشغيل"

    return False, f"حالة غير معروفة: {status}"


def mark_processing(job_id):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:

            allowed, message = can_start_job(job_id)

            if not allowed:
                return False, message

            job["status"] = "processing"
            job["started_at"] = datetime.now().isoformat()
            job["attempt_count"] = int(
                job.get("attempt_count", 0)
            ) + 1

            save_jobs(jobs)

            return True, "تم بدء المهمة"

    return False, "المهمة غير موجودة"


def mark_completed(job_id, output_file):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:

            job["status"] = "completed"
            job["output_file"] = str(output_file)
            job["completed_at"] = datetime.now().isoformat()

            save_jobs(jobs)

            return True

    return False


def mark_failed(job_id, error_message):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:

            job["status"] = "failed"
            job["error"] = str(error_message)
            job["failed_at"] = datetime.now().isoformat()

            save_jobs(jobs)

            return True

    return False


def cancel_job(job_id):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:

            if job.get("status") in [
                "processing",
                "completed"
            ]:
                return False, (
                    "لا يمكن إلغاء المهمة بعد بدء "
                    "التوليد أو اكتماله"
                )

            job["status"] = "cancelled"
            job["payment_confirmed"] = False
            job["cancelled_at"] = datetime.now().isoformat()

            save_jobs(jobs)

            return True, "تم إلغاء المهمة"

    return False, "المهمة غير موجودة"


def set_cost(job_id, amount, currency="USD"):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:

            job["estimated_cost"] = float(amount)
            job["currency"] = currency
            job["payment_confirmed"] = False
            job["cost_estimated_at"] = datetime.now().isoformat()

            save_jobs(jobs)

            return True

    return False


def confirm_payment(job_id):
    jobs = load_jobs()

    for job in jobs:
        if job.get("job_id") == job_id:

            if job.get("estimated_cost") is None:
                return False, "لا توجد تكلفة تقديرية"

            if job.get("status") == "cancelled":
                return False, "المهمة ملغاة"

            job["payment_confirmed"] = True
            job["payment_confirmed_at"] = datetime.now().isoformat()

            save_jobs(jobs)

            return True, "تم تأكيد الموافقة"

    return False, "المهمة غير موجودة"


def safety_status(job_id):
    job = get_job(job_id)

    if not job:
        return {
            "ok": False,
            "reason": "المهمة غير موجودة"
        }

    allowed, reason = can_start_job(job_id)

    checks = {
        "can_start": allowed,
        "not_cancelled":
            job.get("status") != "cancelled",
        "not_processing":
            job.get("status") != "processing",
        "not_completed":
            job.get("status") != "completed"
    }

    return {
        "ok": all(checks.values()),
        "reason": reason,
        "checks": checks,
        "job": job
    }
