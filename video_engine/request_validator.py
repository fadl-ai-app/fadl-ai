
def validate_request(payload):

    mode = payload.get("mode", "")
    audio = payload.get("audio")
    prompt = str(
        payload.get("user_prompt", "")
    ).lower()

    talking_words = [
        "يتكلم",
        "يتحدث",
        "يقول",
        "يحكي",
        "تتكلم",
        "تحدث"
    ]

    has_talking_text = any(
        word in prompt
        for word in talking_words
    )

    has_audio = bool(audio)

    # حركة فقط
    if mode == "motion_only":

        if has_audio or has_talking_text:
            return {
                "valid": False,
                "reason":
                "الوضع حركة فقط لكن يوجد صوت أو طلب كلام"
            }


    # كلام بدون تحديد مناسب
    if (has_audio or has_talking_text):

        if mode not in [
            "talking",
            "motion_and_talking",
            "motion_and_talk",
            "talk_and_motion"
        ]:
            return {
                "valid": False,
                "reason":
                "يجب اختيار وضع الكلام عند وجود صوت"
            }


    return {
        "valid": True,
        "reason":
        "الطلب متوافق"
    }
