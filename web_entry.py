import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import gradio as gr

ROOT = Path(__file__).resolve().parent

# ============================================================
# FADL AI — Render Web Entry
# ============================================================

os.chdir(ROOT)

# نضيف مجلدات المشروع للمسار
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

# ============================================================
# توافق المسارات القديمة التي يستخدمها main_app.py
# ============================================================

content_dir = Path("/content")
expected_path = content_dir / "fadl_ai"

try:
    content_dir.mkdir(parents=True, exist_ok=True)

    if not expected_path.exists():
        expected_path.symlink_to(ROOT, target_is_directory=True)

except Exception:
    pass

# ============================================================
# إنشاء واجهة Fadl AI
# ============================================================

from app.main_app import create_main_app

gradio_app = create_main_app()

# ============================================================
# FastAPI — Webhook Layer
# ============================================================

fastapi_app = FastAPI(
    title="Fadl AI",
)

# ============================================================
# تركيب Gradio داخل FastAPI
# ============================================================

app = gr.mount_gradio_app(
    fastapi_app,
    gradio_app,
    path="/",
    auth=[
        (
            os.environ["FADL_ADMIN_USER"],
            os.environ["FADL_ADMIN_PASS"],
        ),
        (
            os.environ["FADL_REVIEW_USER"],
            os.environ["FADL_REVIEW_PASS"],
        ),
    ],
)

# ============================================================
# تشغيل Render
# ============================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get("PORT", "10000")
    )

    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=port,
    )
