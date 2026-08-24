from pathlib import Path
import os
import requests
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
from requests.auth import HTTPBasicAuth


QURAN_ROOT = Path(__file__).resolve().parents[1]

BASE_URL = "https://apis-prelive.quran.foundation/content/api/v4"
AUTH_URL = "https://prelive-oauth2.quran.foundation/oauth2/token"

HF_REPO_ID = "fadl-ai/fadl-ai-quran-audio"
HF_TOKEN_ENV = "HF_TOKEN"

QF_CLIENT_ID = None
QF_CLIENT_SECRET = None
QF_ACCESS_TOKEN = None
quran_db = None


def configure(client_id, client_secret, database):
    global QF_CLIENT_ID, QF_CLIENT_SECRET, quran_db
    QF_CLIENT_ID = client_id
    QF_CLIENT_SECRET = client_secret
    quran_db = database


def _surah_paths(surah_number):
    surah_number = int(surah_number)
    audio_dir = QURAN_ROOT / "audio" / f"surah_{surah_number:03d}"
    audio_dir.mkdir(parents=True, exist_ok=True)

    complete_file = (
        audio_dir / f"surah_{surah_number:03d}_complete.mp3"
    )

    return audio_dir, complete_file


def _download_from_huggingface(surah_number):
    """
    Download one complete surah MP3 from the private Hugging Face dataset.
    HF_TOKEN is read only from the Render environment.
    """
    surah_number = int(surah_number)
    _, complete_file = _surah_paths(surah_number)

    token = os.environ.get(HF_TOKEN_ENV)
    if not token:
        print("✗ HF_TOKEN غير موجود")
        return None

    filename = (
        f"audio/surah_{surah_number:03d}/"
        f"surah_{surah_number:03d}_complete.mp3"
    )

    url = (
        f"https://huggingface.co/datasets/{HF_REPO_ID}/"
        f"resolve/main/{filename}"
    )

    try:
        print(f"⬇️ تحميل سورة {surah_number} من Hugging Face")

        with requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=300,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()

            temp_file = complete_file.with_suffix(".mp3.part")

            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        f.write(chunk)

        if not temp_file.exists() or temp_file.stat().st_size == 0:
            try:
                temp_file.unlink()
            except Exception:
                pass
            print("✗ ملف Hugging Face فارغ")
            return None

        temp_file.replace(complete_file)

        print(
            "✓ تم تحميل السورة من Hugging Face:",
            complete_file.name,
        )
        return str(complete_file)

    except Exception as e:
        print(
            f"✗ تعذر تحميل سورة {surah_number} "
            f"من Hugging Face: {e}"
        )
        return None


def refresh_qf_token():
    global QF_ACCESS_TOKEN

    # Quran Foundation is only a fallback.
    if not QF_CLIENT_ID or not QF_CLIENT_SECRET:
        print("مفاتيح Quran Foundation غير مفعلة")
        return False

    try:
        response = requests.post(
            AUTH_URL,
            auth=HTTPBasicAuth(
                QF_CLIENT_ID.strip(),
                QF_CLIENT_SECRET.strip()
            ),
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "client_credentials",
                "scope": "content"
            },
            timeout=30
        )
    except Exception as e:
        print("✗ فشل الاتصال بـ Quran Foundation:", e)
        return False

    if not response.ok:
        print("✗ فشل تجديد Access Token")
        return False

    QF_ACCESS_TOKEN = response.json()["access_token"]
    print("✓ تم تجديد Access Token")
    return True


def get_surah_audio(
    surah_number,
    reciter_id=6,
    force_rebuild=False
):
    """
    Order:
    1) Use local complete MP3 if available.
    2) Download complete MP3 from private Hugging Face dataset.
    3) Fall back to the old Quran Foundation per-ayah builder if credentials exist.
    """
    global QF_ACCESS_TOKEN

    surah_number = int(surah_number)
    audio_dir, complete_file = _surah_paths(surah_number)

    # 1) Local file first.
    if (
        complete_file.exists()
        and complete_file.stat().st_size > 0
        and not force_rebuild
    ):
        print("✓ السورة موجودة محليًا")
        return str(complete_file)

    # Do not delete a known-good complete file merely because force_rebuild
    # was used; HF can replace it safely through a .part file.

    # 2) Hugging Face is the main source for missing surahs on Render.
    hf_file = _download_from_huggingface(surah_number)
    if hf_file:
        return hf_file

    # 3) Optional legacy fallback: Quran Foundation.
    if quran_db is None:
        print("✗ قاعدة القرآن غير مربوطة بالمحرك")
        return None

    expected_count = int(
        quran_db[str(surah_number)]["ayah_count"]
    )

    expected_keys = [
        f"{surah_number}:{i}"
        for i in range(1, expected_count + 1)
    ]

    if not QF_ACCESS_TOKEN:
        if not refresh_qf_token():
            print("✗ لا يوجد مصدر صوت متاح لهذه السورة")
            return None

    def fetch():
        return requests.get(
            f"{BASE_URL}/quran/recitations/{reciter_id}",
            headers={
                "x-auth-token": QF_ACCESS_TOKEN,
                "x-client-id": QF_CLIENT_ID
            },
            params={
                "chapter_number": surah_number,
                "fields": "verse_key,url"
            },
            timeout=30
        )

    try:
        r = fetch()

        if r.status_code in (401, 403):
            if refresh_qf_token():
                r = fetch()

        print("Status:", r.status_code)

        if not r.ok:
            print("✗ تعذر جلب التلاوة")
            print(r.text[:800])
            return None

        raw_files = r.json().get("audio_files", [])

        clean = {}

        for item in raw_files:
            verse_key = str(
                item.get("verse_key", "")
            ).strip()

            audio_url = item.get("url")

            if not verse_key or not audio_url:
                continue

            try:
                chapter, ayah = map(
                    int,
                    verse_key.split(":")
                )
            except Exception:
                continue

            if (
                chapter == surah_number
                and 1 <= ayah <= expected_count
            ):
                clean[verse_key] = item

        missing = [
            key for key in expected_keys
            if key not in clean
        ]

        if missing or len(clean) != expected_count:
            print("⛔ توقفنا لحماية ترتيب القرآن")
            print("الآيات الناقصة:", missing)
            return None

        print("✓ تم التحقق من ملفات السورة")

        def download_one(verse_key):
            item = clean[verse_key]
            ayah_num = int(
                verse_key.split(":")[1]
            )

            audio_url = item["url"]

            if audio_url.startswith("//"):
                audio_url = "https:" + audio_url
            elif not audio_url.startswith("http"):
                audio_url = (
                    "https://audio.qurancdn.com/"
                    + audio_url.lstrip("/")
                )

            output = audio_dir / (
                f"{surah_number:03d}_"
                f"{ayah_num:03d}.mp3"
            )

            response = requests.get(
                audio_url,
                timeout=90
            )
            response.raise_for_status()

            with open(output, "wb") as f:
                f.write(response.content)

            return verse_key, str(output)

        downloaded = {}

        with ThreadPoolExecutor(
            max_workers=6
        ) as executor:
            for verse_key, path in executor.map(
                download_one,
                expected_keys
            ):
                downloaded[verse_key] = path

        combined = AudioSegment.empty()

        for verse_key in expected_keys:
            combined += AudioSegment.from_mp3(
                downloaded[verse_key]
            )

        # Preserve the original basmala behavior if this file exists.
        if surah_number not in (1, 9):
            bismillah_file = (
                QURAN_ROOT
                / "audio"
                / "al_fatiha"
                / "001_001.mp3"
            )

            if bismillah_file.exists():
                combined = (
                    AudioSegment.from_mp3(
                        str(bismillah_file)
                    )
                    + combined
                )

        combined.export(
            str(complete_file),
            format="mp3"
        )

        print("✓ تم إنشاء السورة كاملة")
        print("✓ عدد الآيات:", expected_count)

        return str(complete_file)

    except Exception as e:
        print("✗ خطأ أثناء تجهيز التلاوة:", e)
        return None
