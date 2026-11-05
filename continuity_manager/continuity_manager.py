
from copy import deepcopy
from pathlib import Path
import json

from film_memory.memory_engine import FilmMemory
from scene_planner.scene_planner import ScenePlanner
from character_library.character_library import (
    CharacterLibrary,
    CharacterProfile,
)
from location_library.location_library import (
    LocationLibrary,
    LocationProfile,
)


class ContinuityManager:
    """Coordinate film memory, character profiles, and location profiles."""

    def __init__(self, memory, character_library=None, location_library=None):
        if not isinstance(memory, FilmMemory):
            raise TypeError("memory must be a FilmMemory instance")
        self.memory = memory
        self.characters = character_library or CharacterLibrary()
        self.locations = location_library or LocationLibrary()
        self.planner = ScenePlanner(memory)

    def add_character_profile(self, film_id, profile):
        self.characters.validate_profile(profile)
        data = profile.to_dict() if isinstance(profile, CharacterProfile) else deepcopy(profile)
        film = self.memory.load_film(film_id)
        source_id = data["character_id"]

        for item in film["characters"]:
            if item.get("source_profile_id") == source_id:
                return deepcopy(item)

        appearance = deepcopy(data["appearance"])
        appearance["personality"] = deepcopy(data["personality"])
        appearance["accessories"] = deepcopy(data["accessories"])
        appearance["reference_images_metadata"] = deepcopy(data["reference_images"])

        notes = {
            "source_profile_id": source_id,
            "continuity_rules": list(data["continuity_rules"]),
            "metadata": deepcopy(data["metadata"]),
            "schema_version": data["schema_version"],
        }

        item = self.memory.add_character(
            film_id=film_id,
            name=data["name"],
            description=data["description"],
            appearance=appearance,
            clothing=deepcopy(data["clothing"]),
            voice=deepcopy(data["voice"]),
            reference_notes=json.dumps(data["reference_images"], ensure_ascii=False),
            continuity_notes=json.dumps(notes, ensure_ascii=False),
        )

        # Store the source-library ID in film memory, not just in the return value.
        film = self.memory.load_film(film_id)
        for saved in film["characters"]:
            if saved["character_id"] == item["character_id"]:
                saved["source_profile_id"] = source_id
                break
        self._save_metadata_edit(film_id, "characters", item["character_id"],
                                 "source_profile_id", source_id)
        return deepcopy(next(
            c for c in self.memory.load_film(film_id)["characters"]
            if c["character_id"] == item["character_id"]
        ))

    def add_location_profile(self, film_id, profile):
        self.locations.validate_location(profile)
        data = profile.to_dict() if isinstance(profile, LocationProfile) else deepcopy(profile)
        film = self.memory.load_film(film_id)
        source_id = data["location_id"]

        for item in film["locations"]:
            if item.get("source_profile_id") == source_id:
                return deepcopy(item)

        layout = {
            "layout": deepcopy(data["layout"]),
            "architecture": deepcopy(data["architecture"]),
            "furniture": deepcopy(data["furniture"]),
            "props": deepcopy(data["props"]),
            "color_palette": list(data["color_palette"]),
            "atmosphere": deepcopy(data["atmosphere"]),
            "character_positions": deepcopy(data["character_positions"]),
            "metadata": deepcopy(data["metadata"]),
            "schema_version": data["schema_version"],
        }

        notes = {
            "source_profile_id": source_id,
            "continuity_rules": list(data["continuity_rules"]),
        }

        item = self.memory.add_location(
            film_id=film_id,
            name=data["name"],
            description=data["description"],
            layout=layout,
            lighting=deepcopy(data["lighting"]),
            continuity_notes=json.dumps(notes, ensure_ascii=False),
        )

        self._save_metadata_edit(film_id, "locations", item["location_id"],
                                 "source_profile_id", source_id)
        return deepcopy(next(
            loc for loc in self.memory.load_film(film_id)["locations"]
            if loc["location_id"] == item["location_id"]
        ))

    def _save_metadata_edit(self, film_id, collection, item_id, key, value):
        # Use the memory engine's validated edit/write path.
        def operation(data):
            for item in data[collection]:
                id_key = "character_id" if collection == "characters" else "location_id"
                if item[id_key] == item_id:
                    item[key] = value
                    return
            raise ValueError("Cannot find item to update")
        self.memory._edit(film_id, operation)

    def plan_scene(self, film_id, title, actions, character_ids=None,
                   location_id=None, dialogue=None, camera=None,
                   continuity_notes=""):
        return self.planner.plan_and_save(
            film_id=film_id,
            title=title,
            actions=actions,
            character_ids=character_ids,
            location_id=location_id,
            dialogue=dialogue,
            camera=camera,
            continuity_notes=continuity_notes,
        )

    def record_story_event(self, film_id, event, scene_id=None):
        return self.memory.add_story_event(film_id, event, scene_id)

    def prepare_continue_context(self, film_id):
        context = self.memory.build_continuity_context(film_id)
        context["generation_enabled"] = False
        context["next_scene_number"] = len(context["prior_scenes"]) + 1
        context["continuity_summary"] = {
            "character_count": len(context["characters"]),
            "location_count": len(context["locations"]),
            "prior_scene_count": len(context["prior_scenes"]),
            "last_story_point": deepcopy(context["last_story_point"]),
            "visual_style": deepcopy(context["visual_style"]),
        }
        return context

    def prepare_before_scene(self, film_id, scene_number):
        if not isinstance(scene_number, int) or scene_number < 1:
            raise ValueError("scene_number must be a positive integer")
        context = self.memory.build_continuity_context(
            film_id, before_scene_number=scene_number
        )
        context["generation_enabled"] = False
        context["next_scene_number"] = scene_number
        return context

    def continue_film(self, film_id, title, actions, character_ids=None,
                      location_id=None, dialogue=None, camera=None,
                      continuity_notes=""):
        """Save the next scene using the film's latest continuity context.

        This method plans and saves a scene only. It does not generate media
        or call external providers.
        """
        from copy import deepcopy

        context = self.prepare_continue_context(film_id)
        prior_scenes = context.get("prior_scenes", [])
        characters = context.get("characters", [])
        locations = context.get("locations", [])

        # Reuse the latest scene's cast and location unless explicitly overridden.
        latest_scene = prior_scenes[-1] if prior_scenes else None

        if character_ids is None:
            if latest_scene is not None:
                character_ids = deepcopy(latest_scene.get("character_ids", []))
            else:
                character_ids = [
                    item["character_id"] for item in characters
                ]
        else:
            character_ids = list(character_ids)

        if location_id is None and latest_scene is not None:
            location_id = latest_scene.get("location_id")
        if location_id is None and locations:
            location_id = locations[0].get("location_id")

        # Inherit dialogue and camera unless the caller explicitly overrides them.
        if latest_scene is not None:
            if dialogue is None:
                dialogue = deepcopy(latest_scene.get("dialogue", []))
            if camera is None:
                camera = deepcopy(latest_scene.get("camera", {}))

        last_story_point = context.get("last_story_point")
        auto_context = ""
        if last_story_point not in (None, ""):
            story_text = (
                last_story_point
                if isinstance(last_story_point, str)
                else __import__("json").dumps(
                    last_story_point, ensure_ascii=False
                )
            )
            auto_context = "نقطة الاستئناف السابقة: " + story_text

        previous_notes = (
            latest_scene.get("continuity_notes", "")
            if latest_scene else ""
        )
        context_parts = [
            part for part in (auto_context, previous_notes, continuity_notes)
            if isinstance(part, str) and part.strip()
        ]
        combined_notes = " | ".join(context_parts)

        result = self.plan_scene(
            film_id=film_id,
            title=title,
            actions=actions,
            character_ids=character_ids,
            location_id=location_id,
            dialogue=dialogue,
            camera=camera,
            continuity_notes=combined_notes,
        )

        # Preserve the existing no-generation safety gate.
        result["generation_enabled"] = False
        result["continuity_context"] = context
        return result
