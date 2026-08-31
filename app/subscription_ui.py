import gradio as gr
import gem_manager


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
            ("💎 700 جوهرة", "70,000 جنيه سوداني"),
            ("💎 1,400 جوهرة", "140,000 جنيه سوداني"),
            ("💎 2,050 جوهرة", "170,000 جنيه سوداني"),
        ],
    },

    "🇪🇬 مصر": {
        "currency": "الجنيه المصري",
        "payment": "وسائل الدفع المتاحة + Visa / Mastercard",
        "plans": [
            ("💎 700 جوهرة", "510 جنيه مصري"),
            ("💎 1,400 جوهرة", "915 جنيه مصري"),
            ("💎 2,050 جوهرة", "1,270 جنيه مصري"),
        ],
    },

    "🇸🇦 السعودية": {
        "currency": "الريال السعودي",
        "payment": "وسائل الدفع المتاحة + Visa / Mastercard",
        "plans": [
            ("💎 700 جوهرة", "39 ريال سعودي"),
            ("💎 1,400 جوهرة", "69 ريال سعودي"),
            ("💎 2,050 جوهرة", "95 ريال سعودي"),
        ],
    },

    "🇦🇪 الإمارات": {
        "currency": "الدرهم الإماراتي",
        "payment": "وسائل الدفع المتاحة + Visa / Mastercard",
        "plans": [
            ("💎 700 جوهرة", "39 درهم إماراتي"),
            ("💎 1,400 جوهرة", "69 درهم إماراتي"),
            ("💎 2,050 جوهرة", "95 درهم إماراتي"),
        ],
    },

    "🌍 دولة أخرى": {
        "currency": "الدولار الأمريكي",
        "payment": "Visa / Mastercard",
        "plans": [
            ("💎 700 جوهرة", "$9.99"),
            ("💎 1,400 جوهرة", "$18"),
            ("💎 2,050 جوهرة", "$25"),
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



def get_payment_methods(country):
    """طرق الدفع للعرض فقط — لا دفع حقيقي."""

    methods = {
        "🇸🇩 السودان": [
            "بنكك — بنك الخرطوم",
            "Visa / Mastercard",
        ],

        "🇪🇬 مصر": [
            "Meeza",
            "Apple Pay",
            "Visa / Mastercard",
        ],

        "🇸🇦 السعودية": [
            "مدى",
            "STC Pay",
            "Apple Pay",
            "Visa / Mastercard",
        ],

        "🇦🇪 الإمارات": [
            "Apple Pay",
            "Samsung Pay",
            "Visa / Mastercard",
        ],

        "🌍 دولة أخرى": [
            "Visa / Mastercard",
        ],
    }

    return gr.update(
        choices=methods.get(country, []),
        value=None
    )

def get_plan_choices(country):
    """إظهار الباقات الخاصة بالدولة المختارة."""

    if not country or country not in SUBSCRIPTION_DATA:
        return gr.update(choices=[], value=None)

    plans = SUBSCRIPTION_DATA[country]["plans"]

    choices = [
        f"{gems} — {price}"
        for gems, price in plans
    ]

    return gr.update(
        choices=choices,
        value=None
    )


def _show_user_balance(request: gr.Request):
    username = request.username or "guest"
    balance = gem_manager.get_balance(username)
    return f"👤 المستخدم: **{username}**  |  💎 الرصيد: **{balance} جوهرة**"


def add_subscription_ui():

    balance_box = gr.Markdown("💎 جاري تحميل الرصيد...")

    gr.Markdown(
        """
        # 💎 الاشتراك في فضل AI

        ### 🎁 الخطة المجانية
        **فيديو واحد مجانًا للتجربة**
        
        📢 تتضمن إعلانات

        بعد استخدام الفيديو المجاني، يمكنك اختيار إحدى باقات الجواهر.

        ### 💎 الاشتراك المدفوع
        **بدون إعلانات**

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

    plan_choice = gr.Radio(
        choices=[],
        label="💎 اختر الباقة",
        value=None,
    )

    payment_choice = gr.Radio(
        choices=[],
        label="💳 اختر طريقة الدفع",
        value=None,
    )

    gr.Markdown(
        """
        🔒 **هذه معاينة فقط.**

        اختيار الباقة وطريقة الدفع لا ينفذ أي عملية مالية
        ولا يضيف جواهر حاليًا.
        """
    )

    country.change(
        fn=get_country_info,
        inputs=country,
        outputs=country_info,
    )

    country.change(
        fn=get_plan_choices,
        inputs=country,
        outputs=plan_choice,
    )

    country.change(
        fn=get_payment_methods,
        inputs=country,
        outputs=payment_choice,
    )

    return balance_box


if __name__ == "__main__":

    with gr.Blocks(
        title="فضل AI — الاشتراك"
    ) as demo:

        add_subscription_ui()

    demo.launch()
