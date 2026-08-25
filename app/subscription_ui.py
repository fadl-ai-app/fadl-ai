import gradio as gr


# ==========================================
# FADL AI — Subscription UI
# مستقل تمامًا عن main_app.py
# الدفع الحقيقي غير مفعّل حاليًا
# ==========================================

SUBSCRIPTION_DATA = {
    "🇸🇩 السودان": {
        "currency": "الجنيه السوداني",
        "payment": "بنكك — بنك الخرطوم",
        "plans": [
            ("💎 350 جوهرة", "100 جنيه سوداني"),
            ("💎 700 جوهرة", "200 جنيه سوداني"),
            ("💎 1,500 جوهرة", "300 جنيه سوداني"),
        ],
    },

    "🇪🇬 مصر": {
        "currency": "الجنيه المصري",
        "payment": "وسائل الدفع المتاحة + Visa / Mastercard",
        "plans": [
            ("💎 350 جوهرة", "255 جنيه مصري"),
            ("💎 700 جوهرة", "510 جنيه مصري"),
            ("💎 1,500 جوهرة", "1,020 جنيه مصري"),
        ],
    },

    "🇸🇦 السعودية": {
        "currency": "الريال السعودي",
        "payment": "وسائل الدفع المتاحة + Visa / Mastercard",
        "plans": [
            ("💎 350 جوهرة", "19 ريال سعودي"),
            ("💎 700 جوهرة", "39 ريال سعودي"),
            ("💎 1,500 جوهرة", "75 ريال سعودي"),
        ],
    },

    "🇦🇪 الإمارات": {
        "currency": "الدرهم الإماراتي",
        "payment": "وسائل الدفع المتاحة + Visa / Mastercard",
        "plans": [
            ("💎 350 جوهرة", "19 درهم إماراتي"),
            ("💎 700 جوهرة", "39 درهم إماراتي"),
            ("💎 1,500 جوهرة", "75 درهم إماراتي"),
        ],
    },

    "🌍 دولة أخرى": {
        "currency": "الدولار الأمريكي",
        "payment": "Visa / Mastercard",
        "plans": [
            ("💎 350 جوهرة", "$5"),
            ("💎 700 جوهرة", "$10"),
            ("💎 1,500 جوهرة", "$20"),
        ],
    },
}


def get_country_info(country):
    if not country or country not in SUBSCRIPTION_DATA:
        return "اختر بلدك أولًا."

    data = SUBSCRIPTION_DATA[country]

    plans_html = ""

    for gems, price in data["plans"]:
        plans_html += f"""
        <div style="
            padding:14px;
            margin:10px 0;
            border:1px solid #ddd;
            border-radius:14px;
        ">
            <strong>{gems}</strong><br>
            {price}
        </div>
        """

    return f"""
    <div dir="rtl">

        <h3>💰 العملة</h3>
        <p>{data["currency"]}</p>

        <h3>💳 طريقة الدفع</h3>
        <p>{data["payment"]}</p>

        <h3>💎 الباقات</h3>

        {plans_html}

        <p>
        🔒 الدفع الحقيقي غير مفعّل حاليًا.
        </p>

    </div>
    """


def add_subscription_ui():

    gr.Markdown(
        """
        # 💎 الاشتراك في فضل AI

        اختر بلدك لعرض الأسعار وطرق الدفع المناسبة لك.
        """
    )

    country = gr.Dropdown(
        choices=list(SUBSCRIPTION_DATA.keys()),
        label="🌍 اختر بلدك",
        value=None,
    )

    country_info = gr.HTML(
        """
        <div dir="rtl">
            اختر بلدك أولًا.
        </div>
        """
    )

    country.change(
        fn=get_country_info,
        inputs=country,
        outputs=country_info,
    )


if __name__ == "__main__":

    with gr.Blocks(
        title="فضل AI — الاشتراك"
    ) as demo:

        add_subscription_ui()

    demo.launch()
