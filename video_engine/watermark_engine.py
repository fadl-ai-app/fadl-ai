
from pathlib import Path
import subprocess
import shutil

FADL_WATERMARK_VERSION = "1.0"

BASE = Path(__file__).resolve().parents[1]
DEFAULT_ICON = (
    BASE / "app/assets/fadl_ai_icon.png"
)


def add_fadl_watermark(
    video_path,
    output_path=None,
    icon_path=None
):
    """
    إضافة علامة فضل AI:
    - 3% من عرض الفيديو
    - شفافية 60%
    - أسفل اليمين
    - يحافظ على الصوت
    - لا يستخدم Runway أو Credits
    """

    video_path = Path(video_path)

    if icon_path is None:
        icon_path = DEFAULT_ICON

    icon_path = Path(icon_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    if not icon_path.exists():
        raise FileNotFoundError(
            f"Watermark icon not found: {icon_path}"
        )

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg is not available"
        )

    if output_path is None:
        output_path = video_path.with_name(
            video_path.stem
            + "_fadl.mp4"
        )

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cmd = [
        "ffmpeg",
        "-y",

        "-i", str(video_path),
        "-i", str(icon_path),

        "-filter_complex",
        (
            "[1:v][0:v]"
            "scale2ref="
            "w=main_w*0.03:"
            "h=-1"
            "[wm][base];"

            "[wm]"
            "format=rgba,"
            "colorchannelmixer=aa=0.60"
            "[wm2];"

            "[base][wm2]"
            "overlay="
            "x=W-w-W*0.015:"
            "y=H-h-H*0.015"
            "[v]"
        ),

        "-map", "[v]",
        "-map", "0:a?",

        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "128k",

        "-movflags", "+faststart",

        str(output_path)
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Watermark failed:\n"
            + result.stderr[-3000:]
        )

    if not output_path.exists():
        raise RuntimeError(
            "Watermarked video was not created"
        )

    return str(output_path)
