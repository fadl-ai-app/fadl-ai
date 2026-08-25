
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# نخلي جذر المشروع هو مكان التشغيل
os.chdir(ROOT)

# نضيف مجلدات الواجهات للمسار بدون تعديل main_app.py
paths = [
    ROOT / "app",
    ROOT / "quran" / "code",
    ROOT / "prayer",
    ROOT / "wudu" / "code",
    ROOT / "image_to_video" / "code",
    ROOT / "text_to_video" / "code",
    ROOT / "video_engine",
]

for path in paths:
    path_str = str(path)

    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# خدعة آمنة:
# main_app.py يعتمد على مسارات /content/fadl_ai
# على Render نربط الاسم ده مؤقتًا بجذر المشروع بدون تعديل main_app.py
content_dir = Path("/content")
expected_path = content_dir / "fadl_ai"

try:
    content_dir.mkdir(parents=True, exist_ok=True)

    if not expected_path.exists():
        expected_path.symlink_to(ROOT, target_is_directory=True)
except Exception:
    # لو Render منع symlink، نستمر ونشوف الفحص قبل أي نشر
    pass

from app.main_app import create_main_app

app = create_main_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        auth=(
            os.environ["FADL_ADMIN_USER"],
            os.environ["FADL_ADMIN_PASS"]
        )
    )
