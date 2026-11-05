"""Structured character profiles for the isolated Film Studio prototype."""

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
import re
import uuid


def _nonempty_text(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass
class CharacterProfile:
    name: str
    description: str = ""
    appearance: dict[str, Any] = field(default_factory=dict)
    clothing: dict[str, Any] = field(default_factory=dict)
    accessories: list[dict[str, Any]] = field(default_factory=list)
    voice: dict[str, Any] = field(default_factory=dict)
    reference_images: list[dict[str, Any]] = field(default_factory=list)
    personality: dict[str, Any] = field(default_factory=dict)
    continuity_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    character_id: str = field(
        default_factory=lambda: "char_" + uuid.uuid4().hex[:12]
    )
    schema_version: int = 1

    def to_dict(self):
        """Return a defensive copy so callers cannot mutate the profile."""
        return deepcopy({
            "schema_version": self.schema_version,
            "character_id": self.character_id,
            "name": self.name,
            "description": self.description,
            "appearance": self.appearance,
            "clothing": self.clothing,
            "accessories": self.accessories,
            "voice": self.voice,
            "reference_images": self.reference_images,
            "personality": self.personality,
            "continuity_rules": self.continuity_rules,
            "metadata": self.metadata,
        })


class CharacterLibrary:
    """Creates and validates profiles; does not generate or fetch media."""

    APPEARANCE_FIELDS = {
        "face", "skin_tone", "eyes", "eyebrows", "nose", "mouth",
        "hair", "facial_hair", "body_build", "height_description",
        "distinctive_features", "front_view", "left_view", "right_view",
        "back_view",
    }

    CLOTHING_FIELDS = {
        "outfit_name", "top", "bottom", "shoes", "colors",
        "fabric", "patterns", "season", "continuity_notes",
    }

    VOICE_FIELDS = {
        "language", "dialect", "pitch", "texture", "pace",
        "accent_notes", "voice_reference_notes",
    }

    def create_character(
        self,
        name,
        description="",
        appearance=None,
        clothing=None,
        accessories=None,
        voice=None,
        reference_images=None,
        personality=None,
        continuity_rules=None,
        metadata=None,
    ):
        name = _nonempty_text(name, "name")

        for field_name, value in (
            ("appearance", appearance),
            ("clothing", clothing),
            ("voice", voice),
            ("personality", personality),
            ("metadata", metadata),
        ):
            if value is not None and not isinstance(value, dict):
                raise ValueError(f"{field_name} must be a dictionary")

        for field_name, value in (
            ("accessories", accessories),
            ("reference_images", reference_images),
            ("continuity_rules", continuity_rules),
        ):
            if value is not None and not isinstance(value, list):
                raise ValueError(f"{field_name} must be a list")

        if not isinstance(description, str):
            raise ValueError("description must be text")

        refs = deepcopy(reference_images or [])
        for index, ref in enumerate(refs, start=1):
            if not isinstance(ref, dict):
                raise ValueError(
                    f"Reference image {index} must be a dictionary"
                )
            view = ref.get("view")
            if view is not None and view not in {
                "front", "left", "right", "back", "three_quarter", "other"
            }:
                raise ValueError(
                    f"Unsupported reference view at item {index}"
                )
            # References are descriptive metadata only.
            # No file, URL, or image is fetched or processed.

        rules = list(continuity_rules or [])
        if any(not isinstance(rule, str) or not rule.strip()
               for rule in rules):
            raise ValueError("Each continuity rule must be non-empty text")

        profile = CharacterProfile(
            name=name,
            description=description.strip(),
            appearance=deepcopy(appearance or {}),
            clothing=deepcopy(clothing or {}),
            accessories=deepcopy(accessories or []),
            voice=deepcopy(voice or {}),
            reference_images=refs,
            personality=deepcopy(personality or {}),
            continuity_rules=[rule.strip() for rule in rules],
            metadata=deepcopy(metadata or {}),
        )
        return profile

    def validate_profile(self, profile):
        if isinstance(profile, CharacterProfile):
            data = profile.to_dict()
        elif isinstance(profile, dict):
            data = deepcopy(profile)
        else:
            raise TypeError("profile must be CharacterProfile or dictionary")

        if data.get("schema_version") != 1:
            raise ValueError("Unsupported character profile schema")

        _nonempty_text(data.get("character_id"), "character_id")
        _nonempty_text(data.get("name"), "name")

        for field_name in (
            "appearance", "clothing", "voice", "personality", "metadata"
        ):
            if not isinstance(data.get(field_name), dict):
                raise ValueError(f"{field_name} must be a dictionary")

        for field_name in (
            "accessories", "reference_images", "continuity_rules"
        ):
            if not isinstance(data.get(field_name), list):
                raise ValueError(f"{field_name} must be a list")

        return {
            "valid": True,
            "character_id": data["character_id"],
            "name": data["name"],
            "reference_count": len(data["reference_images"]),
            "continuity_rule_count": len(data["continuity_rules"]),
        }

    def continuity_summary(self, profile):
        """Return a compact textual description for later scene planning."""
        report = self.validate_profile(profile)
        data = (
            profile.to_dict()
            if isinstance(profile, CharacterProfile)
            else deepcopy(profile)
        )

        return {
            "character_id": report["character_id"],
            "name": report["name"],
            "appearance": deepcopy(data["appearance"]),
            "clothing": deepcopy(data["clothing"]),
            "accessories": deepcopy(data["accessories"]),
            "voice": deepcopy(data["voice"]),
            "continuity_rules": list(data["continuity_rules"]),
            "reference_views": [
                ref.get("view", "unspecified")
                for ref in data["reference_images"]
            ],
        }
