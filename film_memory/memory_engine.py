"""Offline, isolated memory store for AI Film Studio prototypes."""

import hashlib
import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _now():
    return datetime.now(timezone.utc).isoformat()


def _slug(text):
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip()).strip("-").lower()
    return value or "film"


class FilmMemory:
    """Stores each film in its own integrity-checked JSON file."""

    def __init__(self, storage_dir):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, film_id):
        safe_id = str(film_id)
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", safe_id):
            raise ValueError("Invalid film id")
        path = (self.storage_dir / (safe_id + ".json")).resolve()
        if path.parent != self.storage_dir.resolve():
            raise ValueError("Invalid film path")
        return path

    @staticmethod
    def _digest(data):
        payload = dict(data)
        payload.pop("integrity_sha256", None)
        raw = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _write(self, data):
        data["updated_at"] = _now()
        data["integrity_sha256"] = self._digest(data)
        target = self._path(data["film_id"])
        target.parent.mkdir(parents=True, exist_ok=True)

        # Keep the atomic replace, and clean up the temporary file if any
        # serialization, write, or replace operation fails.
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=target.parent,
                prefix=target.name + ".", suffix=".tmp", delete=False
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")

            temp_path.replace(target)
            temp_path = None
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    # Preserve the original write/replace exception.
                    pass

        return data

    def create_film(self, title, premise="", language="ar", dialect=""):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Film title is required")
        film_id = _slug(title) + "_" + uuid.uuid4().hex[:10]
        data = {
            "schema_version": 1,
            "film_id": film_id,
            "title": title.strip(),
            "premise": premise,
            "language": language,
            "dialect": dialect,
            "visual_style": {},
            "characters": [],
            "locations": [],
            "scenes": [],
            "story_events": [],
            "last_story_point": "",
            "created_at": _now(),
            "updated_at": _now(),
            "integrity_sha256": "",
            "generation_enabled": False,
        }
        return self._write(data)

    def load_film(self, film_id):
        path = self._path(film_id)
        if not path.is_file():
            raise FileNotFoundError(f"No film found: {film_id}")
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported film memory schema")
        if data.get("integrity_sha256") != self._digest(data):
            raise ValueError("Film memory integrity check failed")
        return data

    def list_films(self):
        films = []
        for path in sorted(self.storage_dir.glob("*.json")):
            try:
                data = self.load_film(path.stem)
                films.append({
                    "film_id": data["film_id"],
                    "title": data["title"],
                    "updated_at": data["updated_at"],
                    "scene_count": len(data["scenes"]),
                })
            except Exception as exc:
                # One invalid record must not prevent other films from listing.
                # Log only the filename and exception type, not film contents.
                print(
                    "[FADL FILM STUDIO] Skipping unreadable film file "
                    f"{path.name}: {type(exc).__name__}"
                )
                continue
        return films

    def _edit(self, film_id, operation):
        data = self.load_film(film_id)
        operation(data)
        return self._write(data)

    def add_character(
        self, film_id, name, description="", appearance=None,
        clothing=None, voice=None, reference_notes="", continuity_notes=""
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Character name is required")
        item = {
            "character_id": "char_" + uuid.uuid4().hex[:12],
            "name": name.strip(),
            "description": description,
            "appearance": appearance or {},
            "clothing": clothing or {},
            "voice": voice or {},
            "reference_notes": reference_notes,
            "continuity_notes": continuity_notes,
        }
        def op(data):
            data["characters"].append(item)
        self._edit(film_id, op)
        return item

    def add_location(
        self, film_id, name, description="", layout=None,
        lighting=None, continuity_notes=""
    ):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Location name is required")
        item = {
            "location_id": "loc_" + uuid.uuid4().hex[:12],
            "name": name.strip(),
            "description": description,
            "layout": layout or {},
            "lighting": lighting or {},
            "continuity_notes": continuity_notes,
        }
        def op(data):
            data["locations"].append(item)
        self._edit(film_id, op)
        return item

    def add_scene(
        self, film_id, title, location_id=None, character_ids=None,
        beats=None, dialogue=None, camera=None, continuity_notes=""
    ):
        character_ids = list(character_ids or [])
        beats = list(beats or [])
        dialogue = list(dialogue or [])
        camera = camera or {}
        result = {}
        def op(data):
            known_chars = {c["character_id"] for c in data["characters"]}
            known_locs = {loc["location_id"] for loc in data["locations"]}
            if any(cid not in known_chars for cid in character_ids):
                raise ValueError("Scene references an unknown character")
            if location_id is not None and location_id not in known_locs:
                raise ValueError("Scene references an unknown location")
            result.update({
                "scene_id": "scene_" + uuid.uuid4().hex[:12],
                "scene_number": len(data["scenes"]) + 1,
                "title": title,
                "location_id": location_id,
                "character_ids": character_ids,
                "beats": beats,
                "dialogue": dialogue,
                "camera": camera,
                "continuity_notes": continuity_notes,
                "status": "planned",
            })
            data["scenes"].append(result)
            data["last_story_point"] = (
                beats[-1] if beats else title
            )
        self._edit(film_id, op)
        return result

    def add_story_event(self, film_id, event, scene_id=None):
        item = {
            "event_id": "event_" + uuid.uuid4().hex[:12],
            "event": event,
            "scene_id": scene_id,
            "created_at": _now(),
        }
        def op(data):
            scene_ids = {s["scene_id"] for s in data["scenes"]}
            if scene_id is not None and scene_id not in scene_ids:
                raise ValueError("Event references an unknown scene")
            data["story_events"].append(item)
            data["last_story_point"] = event
        self._edit(film_id, op)
        return item

    def set_visual_style(self, film_id, style):
        if not isinstance(style, dict):
            raise ValueError("Visual style must be a dictionary")
        def op(data):
            data["visual_style"] = style
        return self._edit(film_id, op)

    def update_scene_status(self, film_id, scene_id, status):
        allowed = {"planned", "ready_for_review", "approved", "generated"}
        if status not in allowed:
            raise ValueError("Unsupported scene status")
        def op(data):
            for scene in data["scenes"]:
                if scene["scene_id"] == scene_id:
                    scene["status"] = status
                    return
            raise ValueError("Unknown scene id")
        return self._edit(film_id, op)

    def build_continuity_context(self, film_id, before_scene_number=None):
        data = self.load_film(film_id)
        all_scenes = data["scenes"]

        if before_scene_number is None:
            scenes = all_scenes
            story_events = data["story_events"]
            last_story_point = data["last_story_point"]
        else:
            scenes = [
                scene for scene in all_scenes
                if scene["scene_number"] < before_scene_number
            ]

            # Historical context may only include events tied to prior scenes.
            prior_scene_ids = {scene["scene_id"] for scene in scenes}
            story_events = [
                event for event in data["story_events"]
                if event.get("scene_id") in prior_scene_ids
            ]

            # Prefer the latest event belonging to the latest prior scene.
            # If no such event exists, fall back to that scene's final beat/title.
            last_story_point = None
            if scenes:
                latest_prior_scene = max(
                    scenes, key=lambda scene: scene["scene_number"]
                )
                latest_scene_events = [
                    event for event in story_events
                    if event.get("scene_id") == latest_prior_scene["scene_id"]
                ]
                if latest_scene_events:
                    last_story_point = latest_scene_events[-1].get("event")
                else:
                    beats = latest_prior_scene.get("beats") or []
                    last_story_point = (
                        beats[-1] if beats else latest_prior_scene.get("title")
                    )

        return {
            "film_id": data["film_id"],
            "title": data["title"],
            "premise": data["premise"],
            "language": data["language"],
            "dialect": data["dialect"],
            "visual_style": data["visual_style"],
            "characters": data["characters"],
            "locations": data["locations"],
            "prior_scenes": scenes,
            "story_events": story_events,
            "last_story_point": last_story_point,
            "generation_enabled": False,
        }
