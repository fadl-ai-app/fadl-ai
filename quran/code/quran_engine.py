from pathlib import Path

import os
import requests
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
from requests.auth import HTTPBasicAuth

BASE_URL = "https://apis-prelive.quran.foundation/content/api/v4"
AUTH_URL = "https://prelive-oauth2.quran.foundation/oauth2/token"

QF_CLIENT_ID = None
QF_CLIENT_SECRET = None
QF_ACCESS_TOKEN = None
quran_db = None


def configure(client_id, client_secret, database):
    global QF_CLIENT_ID, QF_CLIENT_SECRET, quran_db
    QF_CLIENT_ID = client_id
    QF_CLIENT_SECRET = client_secret
    quran_db = database


def refresh_qf_token():
    global QF_ACCESS_TOKEN

    # حماية عند فقدان مفاتيح Quran Foundation
    if not QF_CLIENT_ID or not QF_CLIENT_SECRET:
        print("✗ مفاتيح Quran Foundation غير مفعلة")
        print("✓ السور المحفوظة محليًا ما زالت متاحة")
        return False

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

    if not response.ok:
        print("✗ فشل تجديد Access Token")
        return False

    QF_ACCESS_TOKEN = response.json()["access_token"]
    print("✓ تم تجديد Access Token")
    return True


def get_surah_audio(surah_number, reciter_id=6, force_rebuild=False):
    global QF_ACCESS_TOKEN

    surah_number = int(surah_number)

    expected_count = int(
        quran_db[str(surah_number)]["ayah_count"]
    )

    expected_keys = [
        f"{surah_number}:{i}"
        for i in range(1, expected_count + 1)
    ]

    audio_dir = (
        str(Path(__file__).resolve().parents[1] / "audio") + "/"
        f"surah_{surah_number:03d}"
    )

    os.makedirs(audio_dir, exist_ok=True)

    complete_file = os.path.join(
        audio_dir,
        f"surah_{surah_number:03d}_complete.mp3"
    )

    if os.path.exists(complete_file) and not force_rebuild:
        print("✓ السورة موجودة مسبقًا")
        return complete_file

    if force_rebuild:
        for name in os.listdir(audio_dir):
            path = os.path.join(audio_dir, name)
            if os.path.isfile(path):
                os.remove(path)

    if not QF_ACCESS_TOKEN:
        if not refresh_qf_token():
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
        verse_key = str(item.get("verse_key", "")).strip()
        audio_url = item.get("url")

        if not verse_key or not audio_url:
            continue

        try:
            chapter, ayah = map(int, verse_key.split(":"))
        except Exception:
            continue

        if chapter == surah_number and 1 <= ayah <= expected_count:
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
        ayah_num = int(verse_key.split(":")[1])

        audio_url = item["url"]

        if audio_url.startswith("//"):
            audio_url = "https:" + audio_url
        elif not audio_url.startswith("http"):
            audio_url = (
                "https://audio.qurancdn.com/"
                + audio_url.lstrip("/")
            )

        output = os.path.join(
            audio_dir,
            f"{surah_number:03d}_{ayah_num:03d}.mp3"
        )

        response = requests.get(audio_url, timeout=90)
        response.raise_for_status()

        with open(output, "wb") as f:
            f.write(response.content)

        return verse_key, output

    downloaded = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
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

    if surah_number not in (1, 9):
        bismillah_file = (
            str(Path(__file__).resolve().parents[1] / "audio") + "/"
            "al_fatiha/001_001.mp3"
        )

        if os.path.exists(bismillah_file):
            combined = (
                AudioSegment.from_mp3(bismillah_file)
                + combined
            )

    combined.export(
        complete_file,
        format="mp3"
    )

    print("✓ تم إنشاء السورة كاملة")
    print("✓ عدد الآيات:", expected_count)

    return complete_file
