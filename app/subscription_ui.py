import gradio as gr
import gem_manager
from yallapay import create_test_payment_link


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
            "YallaPay TEST",
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



def create_yallapay_test_link(country, plan_choice, payment_choice, request: gr.Request):
    if country != "🇸🇩 السودان":
        return "⚠️ YallaPay TEST متاح حاليًا للسودان فقط."

    if not plan_choice:
        return "⚠️ اختاري الباقة أولًا."

    if payment_choice != "YallaPay TEST":
        return "⚠️ اختاري YallaPay TEST كطريقة دفع."

    import re

    match = re.search(
        r"💎\s*([\d,]+)\s*جوهرة\s*—\s*([\d,]+)",
        plan_choice
    )

    if not match:
        return "❌ تعذر قراءة الباقة المختارة."

    gems = int(match.group(1).replace(",", ""))
    amount = int(match.group(2).replace(",", ""))

    username = request.username or "guest"

    try:
        data = create_test_payment_link(
            amount=amount,
            description=f"Fadl AI — {gems} gems — {username}",
        )
    except Exception as e:
        return f"❌ فشل إنشاء رابط YallaPay TEST:\n\n`{e}`"

    payment_url = None

    if isinstance(data, dict):
        for key in ["paymentUrl", "paymentURL", "payment_url", "url"]:
            if data.get(key):
                payment_url = str(data[key])
                break

        nested = data.get("data")

        if isinstance(nested, dict) and not payment_url:
            for key in ["paymentUrl", "paymentURL", "payment_url", "url"]:
                if nested.get(key):
                    payment_url = str(nested[key])
                    break

    if payment_url:
        return (
            "### 💳 رابط دفع YallaPay TEST\n\n"
            f"**الباقة:** 💎 {gems:,} جوهرة  \n"
            f"**المبلغ:** {amount:,} جنيه سوداني  \n\n"
            f"[🔗 فتح صفحة الدفع TEST]({payment_url})\n\n"
            "⚠️ **TEST فقط — لم تتم إضافة أي جواهر.**"
        )

    return (
        "### ⚠️ استجابة YallaPay TEST\n\n"
        "لم يتم العثور على رابط الدفع في الاستجابة:\n\n"
        f"`{data}`\n\n"
        "**لم تتم إضافة أي جواهر.**"
    )



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
        🧪 **YallaPay TEST**

        تجربة إنشاء رابط الدفع فقط.
        لا تتم إضافة الجواهر من زر الدفع.
        """
    )

    payment_button = gr.Button(
        "💳 إنشاء رابط دفع YallaPay TEST",
        variant="primary",
    )

    payment_result = gr.Markdown(
        "اختاري السودان + الباقة + YallaPay TEST ثم اضغطي الزر."
    )

    country.change(
        fn=get_country_info,
        inputs=country,
        outputs=country_info,
    )

    payment_button.click(
        fn=create_yallapay_test_link,
        inputs=[country, plan_choice, payment_choice],
        outputs=payment_result,
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
