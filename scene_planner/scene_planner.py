"""Offline cinematic scene planner for the isolated Film Studio."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScenePlan:
    title: str
    location_id: str | None = None
    character_ids: list[str] = field(default_factory=list)
    beats: list[dict[str, Any]] = field(default_factory=list)
    dialogue: list[dict[str, Any]] = field(default_factory=list)
    camera: dict[str, Any] = field(default_factory=dict)
    continuity_notes: str = ""

    def to_dict(self):
        return {
            "title": self.title,
            "location_id": self.location_id,
            "character_ids": list(self.character_ids),
            "beats": [dict(beat) for beat in self.beats],
            "dialogue": [dict(line) for line in self.dialogue],
            "camera": dict(self.camera),
            "continuity_notes": self.continuity_notes,
        }


class ScenePlanner:
    """Validates and stores ordered scene actions without generating media."""

    ALLOWED_ACTIONS = {
        "enter", "walk", "turn", "look", "stop", "gesture",
        "speak", "listen", "sit", "stand", "interact", "camera",
        "custom",
    }

    def __init__(self, memory):
        self.memory = memory

    def create_plan(
        self,
        film_id,
        title,
        actions,
        location_id=None,
        character_ids=None,
        dialogue=None,
        camera=None,
        continuity_notes="",
    ):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Scene title is required")
        if not isinstance(actions, list) or not actions:
            raise ValueError("Provide at least one ordered action")

        film = self.memory.load_film(film_id)
        known_characters = {
            item["character_id"] for item in film["characters"]
        }
        known_locations = {
            item["location_id"] for item in film["locations"]
        }

        character_ids = list(character_ids or [])
        if len(set(character_ids)) != len(character_ids):
            raise ValueError("Duplicate character ids are not allowed")
        if any(cid not in known_characters for cid in character_ids):
            raise ValueError("Plan references an unknown character")
        if location_id is not None and location_id not in known_locations:
            raise ValueError("Plan references an unknown location")

        normalized_actions = []
        for index, action in enumerate(actions, start=1):
            if not isinstance(action, dict):
                raise ValueError(f"Action {index} must be a dictionary")

            kind = action.get("action", "custom")
            if kind not in self.ALLOWED_ACTIONS:
                raise ValueError(
                    f"Unsupported action type at step {index}: {kind}"
                )

            description = action.get("description", "")
            if not isinstance(description, str) or not description.strip():
                raise ValueError(
                    f"Action {index} needs a description"
                )

            actor_id = action.get("character_id")
            if actor_id is not None and actor_id not in character_ids:
                raise ValueError(
                    f"Action {index} references a character "
                    "not included in this scene"
                )

            normalized_actions.append({
                "step": index,
                "action": kind,
                "character_id": actor_id,
                "description": description.strip(),
                "duration_seconds": action.get("duration_seconds"),
                "target": action.get("target"),
                "emotion": action.get("emotion"),
            })

        dialogue = list(dialogue or [])
        for index, line in enumerate(dialogue, start=1):
            if not isinstance(line, dict):
                raise ValueError(f"Dialogue line {index} must be a dictionary")
            speaker_id = line.get("character_id")
            if speaker_id is not None and speaker_id not in character_ids:
                raise ValueError(
                    f"Dialogue line {index} references a character "
                    "not included in this scene"
                )
            if not isinstance(line.get("text"), str):
                raise ValueError(
                    f"Dialogue line {index} needs text"
                )

        camera = dict(camera or {})
        plan = ScenePlan(
            title=title.strip(),
            location_id=location_id,
            character_ids=character_ids,
            beats=normalized_actions,
            dialogue=dialogue,
            camera=camera,
            continuity_notes=continuity_notes,
        )

        return plan

    def save_plan(self, film_id, plan):
        if not isinstance(plan, ScenePlan):
            raise TypeError("plan must be a ScenePlan")
        data = plan.to_dict()
        return self.memory.add_scene(
            film_id=film_id,
            title=data["title"],
            location_id=data["location_id"],
            character_ids=data["character_ids"],
            beats=data["beats"],
            dialogue=data["dialogue"],
            camera=data["camera"],
            continuity_notes=data["continuity_notes"],
        )

    def plan_and_save(self, film_id, **kwargs):
        plan = self.create_plan(film_id=film_id, **kwargs)
        saved_scene = self.save_plan(film_id, plan)
        return {
            "plan": plan.to_dict(),
            "saved_scene": saved_scene,
            "generation_enabled": False,
        }
