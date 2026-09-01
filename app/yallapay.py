import os
import hmac
import hashlib
import json
import time
import uuid
from typing import Optional

import requests


# ============================================================
# FADL AI — YallaPay TEST
# مستقل عن subscription_ui.py في المرحلة الأولى
# ============================================================

YALLAPAY_TEST_URL = (
    "https://gateway.yallapaysudan.com"
    "/api/v1/gateway/generatePaymentLink"
)


def _get_test_auth_token() -> str:
    value = os.environ.get("YALLAPAY_TEST_AUTH_TOKEN", "").strip()

    if not value:
        raise RuntimeError(
            "YALLAPAY_TEST_AUTH_TOKEN is not configured."
        )

    # نقبل القيمة سواء حُفظت مع Bearer أو بدونها.
    if value.lower().startswith("bearer "):
        return value[7:].strip()

    return value


def _get_webhook_secret() -> str:
    value = os.environ.get(
        "YALLAPAY_TEST_WEBHOOK_SECRET",
        ""
    ).strip()

    if not value:
        raise RuntimeError(
            "YALLAPAY_TEST_WEBHOOK_SECRET is not configured."
        )

    return value


def create_test_payment_link(
    amount: int,
    description: str,
    client_reference_id: Optional[str] = None,
    success_url: Optional[str] = None,
    failed_url: Optional[str] = None,
):
    """
    إنشاء رابط دفع YallaPay TEST فقط.

    لا تضيف جواهر.
    لا تعدل قاعدة البيانات.
    """

    amount = int(amount)

    if amount < 1000:
        raise ValueError(
            "YallaPay minimum payment amount is 1000 SDG."
        )

    if not client_reference_id:
        client_reference_id = str(uuid.uuid4())

    payload = {
        "amount": amount,
        "clientReferenceId": client_reference_id,
        "description": str(description),
        "commissionPaidByCustomer": False,
    }

    if success_url:
        payload["paymentSuccessfulRedirectUrl"] = success_url

    if failed_url:
        payload["paymentFailedRedirectUrl"] = failed_url

    token = _get_test_auth_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    response = requests.post(
        YALLAPAY_TEST_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "responseCode": str(response.status_code),
            "responseMessage": response.text,
        }

    if response.status_code >= 400:
        raise RuntimeError(
            f"YallaPay TEST HTTP {response.status_code}: {data}"
        )

    return data


def verify_test_webhook(
    raw_body: bytes,
    signature: str,
    timestamp: str,
    max_age_seconds: int = 300,
) -> bool:
    """
    التحقق من Webhook الخاص بـYallaPay TEST.

    مهم:
    التوقيع يحسب على raw JSON bytes قبل json.loads().
    """

    secret = _get_webhook_secret()

    if not signature or not timestamp:
        return False

    try:
        webhook_time = int(timestamp)
    except (TypeError, ValueError):
        return False

    # YallaPay يوثق timestamp بالـmilliseconds.
    now_ms = int(time.time() * 1000)

    if abs(now_ms - webhook_time) > max_age_seconds * 1000:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected,
        str(signature).strip(),
    )


def parse_test_webhook(raw_body: bytes):
    """
    تحليل جسم Webhook بعد نجاح التحقق منه.
    """

    data = json.loads(raw_body.decode("utf-8"))

    return {
        "clientReferenceId": data.get("clientReferenceId"),
        "paymentReferenceId": data.get("paymentReferenceId"),
        "status": data.get("status"),
        "timestamp": data.get("timestamp"),
    }
