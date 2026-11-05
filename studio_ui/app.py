from pathlib import Path
import json
import sys

import gradio as gr

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "studio_data" / "films"

# Import only local project modules. No provider or media-generation imports.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from film_memory.memory_engine import FilmMemory
from scene_planner.scene_planner import ScenePlanner
from continuity_manager.continuity_manager import ContinuityManager

memory = FilmMemory(DATA_DIR)
planner = ScenePlanner(memory)
continuity_manager = ContinuityManager(memory)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def film_choices():
    return [
        (f"{item['title']} — {item['film_id']}", item["film_id"])
        for item in memory.list_films()
    ]


def film_summary(film_id):
    if not film_id:
        return "اختاري فيلمًا أو أنشئي فيلمًا جديدًا."
    data = memory.load_film(film_id)
    return json_text({
        "العنوان": data["title"],
        "الفكرة": data["premise"],
        "اللغة": data["language"],
        "اللهجة": data["dialect"],
        "عدد الشخصيات": len(data["characters"]),
        "عدد المواقع": len(data["locations"]),
        "عدد المشاهد": len(data["scenes"]),
        "آخر نقطة قصصية": data["last_story_point"],
        "التوليد الخارجي": "معطّل",
    })


def refresh_films(selected=None):
    choices = film_choices()
    valid = [value for _, value in choices]
    current = selected if selected in valid else (valid[0] if valid else None)
    return gr.Dropdown(choices=choices, value=current), film_summary(current)


def create_film(title, premise, language, dialect):
    if not title or not title.strip():
        raise gr.Error("أدخلي عنوان الفيلم أولًا.")
    data = memory.create_film(
        title=title.strip(),
        premise=premise or "",
        language=language or "ar",
        dialect=dialect or "",
    )
    choices = film_choices()
    return (
        gr.Dropdown(choices=choices, value=data["film_id"]),
        film_summary(data["film_id"]),
        f"تم إنشاء الفيلم وحفظه محليًا: {data['title']}",
    )


def selected_film(film_id):
    return film_summary(film_id)


def add_character(film_id, name, description, appearance, clothing, voice, notes):
    if not film_id:
        raise gr.Error("اختاري فيلمًا أولًا.")
    item = memory.add_character(
        film_id=film_id,
        name=name,
        description=description or "",
        appearance={"description": appearance or ""},
        clothing={"description": clothing or ""},
        voice={"description": voice or ""},
        continuity_notes=notes or "",
    )
    return (
        f"تم حفظ الشخصية: {item['name']} — {item['character_id']}",
        film_summary(film_id),
    )


def add_location(film_id, name, description, layout, lighting, notes):
    if not film_id:
        raise gr.Error("اختاري فيلمًا أولًا.")
    item = memory.add_location(
        film_id=film_id,
        name=name,
        description=description or "",
        layout={"description": layout or ""},
        lighting={"description": lighting or ""},
        continuity_notes=notes or "",
    )
    return (
        f"تم حفظ الموقع: {item['name']} — {item['location_id']}",
        film_summary(film_id),
    )


def add_scene(
    film_id, title, character_ids_text, location_id,
    actions_text, dialogue_text, camera_text, notes
):
    if not film_id:
        raise gr.Error("اختاري فيلمًا أولًا.")

    try:
        character_ids = json.loads(character_ids_text or "[]")
        actions = json.loads(actions_text or "[]")
        dialogue = json.loads(dialogue_text or "[]")
        camera = json.loads(camera_text or "{}")
    except json.JSONDecodeError as exc:
        raise gr.Error(f"صيغة JSON غير صحيحة: {exc}")

    if not isinstance(character_ids, list):
        raise gr.Error("معرّفات الشخصيات يجب أن تكون قائمة JSON.")
    if not isinstance(actions, list) or not actions:
        raise gr.Error("أدخلي قائمة أفعال JSON تحتوي على فعل واحد على الأقل.")
    if not isinstance(dialogue, list) or not isinstance(camera, dict):
        raise gr.Error("الحوار يجب أن يكون قائمة، والكاميرا كائن JSON.")

    result = planner.plan_and_save(
        film_id=film_id,
        title=title,
        actions=actions,
        character_ids=character_ids,
        location_id=location_id or None,
        dialogue=dialogue,
        camera=camera,
        continuity_notes=notes or "",
    )

    return (
        "تم تخطيط المشهد وحفظه محليًا. التوليد الخارجي معطّل.\n\n"
        + json_text(result["saved_scene"]),
        film_summary(film_id),
    )


def continue_scene(
    film_id, title, character_ids_text, location_id,
    actions_text, dialogue_text, camera_text, notes
):
    if not film_id:
        raise gr.Error("اختاري فيلمًا أولًا.")
    if not title or not title.strip():
        raise gr.Error("أدخلي عنوان المشهد التالي.")

    try:
        actions = json.loads(actions_text or "[]")
        raw_character_ids = json.loads(character_ids_text or "[]")
        raw_dialogue = json.loads(dialogue_text or "[]")
        raw_camera = json.loads(camera_text or "{}")
    except json.JSONDecodeError as exc:
        raise gr.Error(f"صيغة JSON غير صحيحة: {exc}")

    if not isinstance(actions, list) or not actions:
        raise gr.Error("أدخلي قائمة أفعال JSON تحتوي على فعل واحد على الأقل.")
    if not isinstance(raw_character_ids, list):
        raise gr.Error("معرّفات الشخصيات يجب أن تكون قائمة JSON.")
    if not isinstance(raw_dialogue, list):
        raise gr.Error("الحوار يجب أن يكون قائمة JSON.")
    if not isinstance(raw_camera, dict):
        raise gr.Error("بيانات الكاميرا يجب أن تكون كائن JSON.")

    # Empty optional values mean: inherit from the latest saved scene.
    character_ids = raw_character_ids or None
    dialogue = raw_dialogue or None
    camera = raw_camera or None

    result = continuity_manager.continue_film(
        film_id=film_id,
        title=title.strip(),
        actions=actions,
        character_ids=character_ids,
        location_id=location_id.strip() or None if location_id else None,
        dialogue=dialogue,
        camera=camera,
        continuity_notes=notes or "",
    )

    # Explicitly preserve the safe, no-generation mode.
    result["generation_enabled"] = False
    saved_scene = result.get("saved_scene")
    if saved_scene is None:
        raise RuntimeError("Continuity manager returned no saved_scene.")

    context = result.get("continuity_context", {})
    context["generation_enabled"] = False

    status = (
        "تم حفظ المشهد التالي اعتمادًا على استمرارية الفيلم. "
        "التوليد الخارجي معطّل.\n\n"
        + json_text(saved_scene)
    )
    return status, film_summary(film_id), json_text(context)


def show_continuity(film_id):
    if not film_id:
        raise gr.Error("اختاري فيلمًا أولًا.")
    context = memory.build_continuity_context(film_id)
    context["generation_enabled"] = False
    return json_text(context)


# STEP15S_FRIENDLY_CALLBACK_ERRORS
# Convert unexpected callback failures into concise Arabic UI messages.
from functools import wraps as _step15s_wraps

def _step15s_friendly_errors(fn, action_label):
    @_step15s_wraps(fn)
    def _wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except gr.Error:
            raise
        except Exception as exc:
            print(
                "[FADL FILM STUDIO] UI action failed: "
                f"{action_label} ({type(exc).__name__})"
            )
            raise gr.Error(
                f"تعذّر {action_label}. راجعي المدخلات أو سلامة البيانات "
                "ثم حاولي مرة أخرى."
            ) from exc
    return _wrapped

create_film = _step15s_friendly_errors(create_film, "إنشاء الفيلم وحفظه")
add_character = _step15s_friendly_errors(add_character, "حفظ الشخصية")
add_location = _step15s_friendly_errors(add_location, "حفظ الموقع")
add_scene = _step15s_friendly_errors(add_scene, "تخطيط المشهد وحفظه")
continue_scene = _step15s_friendly_errors(
    continue_scene, "متابعة الفيلم وحفظ المشهد التالي"
)
show_continuity = _step15s_friendly_errors(
    show_continuity, "عرض سياق استمرارية القصة"
)

with gr.Blocks(title="FADL AI Film Studio") as demo:
    gr.Markdown(
        """
        # 🎬 FADL AI FILM STUDIO
        ### استديو إدارة الأفلام واستمرارية القصة
        **وضع آمن:** حفظ محلي فقط — لا توليد صور أو فيديو — لا خدمات خارجية.
        """
    )

    with gr.Tab("الأفلام"):
        with gr.Row():
            with gr.Column():
                film_title = gr.Textbox(label="عنوان الفيلم", placeholder="عنوان الفيلم")
                film_premise = gr.Textbox(label="فكرة الفيلم", lines=4)
                film_language = gr.Dropdown(
                    choices=[("العربية", "ar"), ("English", "en")],
                    value="ar",
                    label="لغة الفيلم",
                )
                film_dialect = gr.Textbox(label="اللهجة")
                create_button = gr.Button("إنشاء الفيلم وحفظه", variant="primary")
            with gr.Column():
                film_select = gr.Dropdown(
                    choices=film_choices(),
                    label="الفيلم الحالي",
                    value=None,
                )
                film_info = gr.Code(label="ملخص الفيلم", language="json")
                refresh_button = gr.Button("تحديث قائمة الأفلام")
                film_status = gr.Textbox(label="النتيجة", interactive=False)

        create_button.click(
            create_film,
            inputs=[film_title, film_premise, film_language, film_dialect],
            outputs=[film_select, film_info, film_status],
        )
        refresh_button.click(
            refresh_films,
            inputs=[film_select],
            outputs=[film_select, film_info],
        )
        film_select.change(
            selected_film,
            inputs=[film_select],
            outputs=[film_info],
        )

    with gr.Tab("الشخصيات"):
        gr.Markdown("تُحفظ بيانات الشخصية داخل ذاكرة الفيلم المحدد.")
        char_name = gr.Textbox(label="اسم الشخصية")
        char_description = gr.Textbox(label="الوصف")
        char_appearance = gr.Textbox(label="المظهر")
        char_clothing = gr.Textbox(label="الملابس")
        char_voice = gr.Textbox(label="الصوت واللهجة")
        char_notes = gr.Textbox(label="قواعد الاستمرارية")
        char_button = gr.Button("حفظ الشخصية")
        char_status = gr.Textbox(label="النتيجة", interactive=False)
        char_button.click(
            add_character,
            inputs=[
                film_select, char_name, char_description, char_appearance,
                char_clothing, char_voice, char_notes,
            ],
            outputs=[char_status, film_info],
        )

    with gr.Tab("المواقع"):
        gr.Markdown("تُحفظ بيانات الموقع داخل ذاكرة الفيلم المحدد.")
        loc_name = gr.Textbox(label="اسم الموقع")
        loc_description = gr.Textbox(label="الوصف")
        loc_layout = gr.Textbox(label="التخطيط المكاني")
        loc_lighting = gr.Textbox(label="الإضاءة")
        loc_notes = gr.Textbox(label="قواعد استمرارية الموقع")
        loc_button = gr.Button("حفظ الموقع")
        loc_status = gr.Textbox(label="النتيجة", interactive=False)
        loc_button.click(
            add_location,
            inputs=[
                film_select, loc_name, loc_description,
                loc_layout, loc_lighting, loc_notes,
            ],
            outputs=[loc_status, film_info],
        )

    with gr.Tab("تخطيط المشاهد"):
        gr.Markdown(
            """
            أدخلي بيانات المشهد بصيغة JSON.
            استخدمي معرّفات الشخصيات والمواقع المحفوظة في الفيلم الحالي.
            """
        )
        scene_title = gr.Textbox(label="عنوان المشهد")
        scene_character_ids = gr.Textbox(
            label="معرّفات الشخصيات — JSON list",
            value="[]",
        )
        scene_location_id = gr.Textbox(
            label="معرّف الموقع (اختياري)",
            value="",
        )
        scene_actions = gr.Code(
            label="الأفعال المرتبة — JSON list",
            language="json",
            value='[{"action":"custom","description":"تدخل الشخصية إلى المكان"}]',
        )
        scene_dialogue = gr.Code(
            label="الحوار — JSON list",
            language="json",
            value="[]",
        )
        scene_camera = gr.Code(
            label="ملاحظات الكاميرا — JSON object",
            language="json",
            value="{}",
        )
        scene_notes = gr.Textbox(label="ملاحظات الاستمرارية", lines=3)
        scene_button = gr.Button("تخطيط المشهد وحفظه", variant="primary")
        scene_status = gr.Textbox(label="المشهد المحفوظ", lines=10)
        scene_button.click(
            add_scene,
            inputs=[
                film_select, scene_title, scene_character_ids,
                scene_location_id, scene_actions, scene_dialogue,
                scene_camera, scene_notes,
            ],
            outputs=[scene_status, film_info],
        )

    with gr.Tab("استمرارية القصة"):
        gr.Markdown(
            "يمكنك عرض السياق المحفوظ أو حفظ المشهد التالي اعتمادًا "
            "على آخر مشهد. التوليد الخارجي معطّل."
        )

        gr.Markdown("### متابعة الفيلم من آخر مشهد")
        continuation_title = gr.Textbox(label="عنوان المشهد التالي")
        continuation_character_ids = gr.Textbox(
            label="معرّفات الشخصيات — اتركيها فارغة لوراثة آخر مشهد",
            value="",
        )
        continuation_location_id = gr.Textbox(
            label="معرّف الموقع — اتركيه فارغًا لوراثة آخر مشهد",
            value="",
        )
        continuation_actions = gr.Code(
            label="أفعال المشهد التالي — JSON list",
            language="json",
            value='[{"action":"custom","description":"تتابع الأحداث من المشهد السابق"}]',
        )
        continuation_dialogue = gr.Code(
            label="الحوار — اتركيه فارغًا لوراثة آخر مشهد",
            language="json",
            value="",
        )
        continuation_camera = gr.Code(
            label="الكاميرا — اتركيها فارغة لوراثة آخر مشهد",
            language="json",
            value="",
        )
        continuation_notes = gr.Textbox(
            label="ملاحظات استمرارية إضافية",
            lines=3,
        )
        continue_button = gr.Button(
            "متابعة الفيلم من آخر مشهد",
            variant="primary",
        )
        continuation_status = gr.Textbox(
            label="نتيجة المشهد التالي",
            lines=10,
            interactive=False,
        )

        continuation_context_output = gr.Code(
            label="سياق الاستمرارية بعد المتابعة",
            language="json",
        )
        continue_button.click(
            continue_scene,
            inputs=[
                film_select, continuation_title,
                continuation_character_ids, continuation_location_id,
                continuation_actions, continuation_dialogue,
                continuation_camera, continuation_notes,
            ],
            outputs=[
                continuation_status, film_info, continuation_context_output
            ],
        )

        continuity_button = gr.Button("عرض سياق الاستمرارية")
        continuity_output = gr.Code(label="سياق الفيلم", language="json")
        continuity_button.click(
            show_continuity,
            inputs=[film_select],
            outputs=[continuity_output],
        )

    gr.Markdown(
        """
        ---
        **حالة الأمان:** التوليد الخارجي غير مفعّل في هذه الواجهة.
        حفظ البيانات يحدث فقط عند الضغط على أزرار الحفظ.
        """
    )


if __name__ == "__main__":
    demo.launch()
