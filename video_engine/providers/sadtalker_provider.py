
from pathlib import Path
import subprocess
import shutil

SADTALKER_DIR = Path("/content/SadTalker")


def run_lipsync(
    job_id,
    source_image,
    driven_audio,
    output_dir
):
    """
    تشغيل Lip-sync محلي باستخدام SadTalker.
    لا يستخدم Runway ولا Credits.
    """

    source_image = Path(source_image)
    driven_audio = Path(driven_audio)
    output_dir = Path(output_dir)

    if not SADTALKER_DIR.exists():
        return {
            "success": False,
            "message": "SadTalker غير موجود"
        }

    if not source_image.exists():
        return {
            "success": False,
            "message": f"الصورة غير موجودة: {source_image}"
        }

    if not driven_audio.exists():
        return {
            "success": False,
            "message": f"الصوت غير موجود: {driven_audio}"
        }

    result_dir = output_dir / "sadtalker_work"
    result_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "python",
        str(SADTALKER_DIR / "inference.py"),
        "--driven_audio", str(driven_audio),
        "--source_image", str(source_image),
        "--result_dir", str(result_dir),
        "--still",
        "--preprocess", "full",
        "--enhancer", "gfpgan"
    ]

    result = subprocess.run(
        cmd,
        cwd=str(SADTALKER_DIR),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "success": False,
            "return_code": result.returncode,
            "message": "SadTalker فشل",
            "stderr": result.stderr[-5000:]
        }

    videos = sorted(
        result_dir.rglob("*.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not videos:
        return {
            "success": False,
            "message": "SadTalker انتهى لكن لم نجد الفيديو"
        }

    final_video = output_dir / "final_lipsync.mp4"

    shutil.copy2(
        videos[0],
        final_video
    )

    return {
        "success": True,
        "job_id": job_id,
        "provider": "sadtalker",
        "video": str(final_video),
        "message": "تم إنشاء Lip-sync محلي بنجاح"
    }
