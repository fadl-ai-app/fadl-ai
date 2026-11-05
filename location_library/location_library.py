"""Structured cinematic location profiles for Film Studio."""

from copy import deepcopy
from dataclasses import dataclass, field
import uuid


def _require_text(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass
class LocationProfile:
    name: str
    description: str = ""
    layout: dict = field(default_factory=dict)
    architecture: dict = field(default_factory=dict)
    furniture: list = field(default_factory=list)
    props: list = field(default_factory=list)
    lighting: dict = field(default_factory=dict)
    color_palette: list = field(default_factory=list)
    atmosphere: dict = field(default_factory=dict)
    character_positions: dict = field(default_factory=dict)
    continuity_rules: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    location_id: str = field(
        default_factory=lambda: "loc_" + uuid.uuid4().hex[:12]
    )
    schema_version: int = 1

    def to_dict(self):
        return deepcopy({
            "schema_version": self.schema_version,
            "location_id": self.location_id,
            "name": self.name,
            "description": self.description,
            "layout": self.layout,
            "architecture": self.architecture,
            "furniture": self.furniture,
            "props": self.props,
            "lighting": self.lighting,
            "color_palette": self.color_palette,
            "atmosphere": self.atmosphere,
            "character_positions": self.character_positions,
            "continuity_rules": self.continuity_rules,
            "metadata": self.metadata,
        })


class LocationLibrary:
    """Validates and summarizes locations; never generates media."""

    def create_location(
        self,
        name,
        description="",
        layout=None,
        architecture=None,
        furniture=None,
        props=None,
        lighting=None,
        color_palette=None,
        atmosphere=None,
        character_positions=None,
        continuity_rules=None,
        metadata=None,
    ):
        name = _require_text(name, "name")

        for field_name, value in (
            ("layout", layout),
            ("architecture", architecture),
            ("lighting", lighting),
            ("atmosphere", atmosphere),
            ("character_positions", character_positions),
            ("metadata", metadata),
        ):
            if value is not None and not isinstance(value, dict):
                raise ValueError(f"{field_name} must be a dictionary")

        for field_name, value in (
            ("furniture", furniture),
            ("props", props),
            ("color_palette", color_palette),
            ("continuity_rules", continuity_rules),
        ):
            if value is not None and not isinstance(value, list):
                raise ValueError(f"{field_name} must be a list")

        if not isinstance(description, str):
            raise ValueError("description must be text")

        for field_name, items in (
            ("furniture", furniture or []),
            ("props", props or []),
        ):
            for index, item in enumerate(items, start=1):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"{field_name} item {index} must be a dictionary"
                    )
                _require_text(item.get("name"), f"{field_name}[{index}].name")

        colors = list(color_palette or [])
        if any(not isinstance(c, str) or not c.strip() for c in colors):
            raise ValueError("Each color must be non-empty text")

        rules = list(continuity_rules or [])
        if any(not isinstance(r, str) or not r.strip() for r in rules):
            raise ValueError("Each continuity rule must be non-empty text")

        positions = deepcopy(character_positions or {})
        for character_id, position in positions.items():
            _require_text(character_id, "character_id")
            if not isinstance(position, dict):
                raise ValueError("Each character position must be a dictionary")

        return LocationProfile(
            name=name,
            description=description.strip(),
            layout=deepcopy(layout or {}),
            architecture=deepcopy(architecture or {}),
            furniture=deepcopy(furniture or []),
            props=deepcopy(props or []),
            lighting=deepcopy(lighting or {}),
            color_palette=[c.strip() for c in colors],
            atmosphere=deepcopy(atmosphere or {}),
            character_positions=positions,
            continuity_rules=[r.strip() for r in rules],
            metadata=deepcopy(metadata or {}),
        )

    def validate_location(self, location):
        if isinstance(location, LocationProfile):
            data = location.to_dict()
        elif isinstance(location, dict):
            data = deepcopy(location)
        else:
            raise TypeError(
                "location must be LocationProfile or dictionary"
            )

        if data.get("schema_version") != 1:
            raise ValueError("Unsupported location schema")

        _require_text(data.get("location_id"), "location_id")
        _require_text(data.get("name"), "name")

        for field_name in (
            "layout", "architecture", "lighting", "atmosphere",
            "character_positions", "metadata",
        ):
            if not isinstance(data.get(field_name), dict):
                raise ValueError(f"{field_name} must be a dictionary")

        for field_name in (
            "furniture", "props", "color_palette", "continuity_rules"
        ):
            if not isinstance(data.get(field_name), list):
                raise ValueError(f"{field_name} must be a list")

        return {
            "valid": True,
            "location_id": data["location_id"],
            "name": data["name"],
            "furniture_count": len(data["furniture"]),
            "prop_count": len(data["props"]),
            "continuity_rule_count": len(data["continuity_rules"]),
        }

    def continuity_summary(self, location):
        """Return structured location details for future scene planning."""
        self.validate_location(location)
        data = (
            location.to_dict()
            if isinstance(location, LocationProfile)
            else deepcopy(location)
        )
        return {
            "location_id": data["location_id"],
            "name": data["name"],
            "layout": deepcopy(data["layout"]),
            "architecture": deepcopy(data["architecture"]),
            "furniture": deepcopy(data["furniture"]),
            "props": deepcopy(data["props"]),
            "lighting": deepcopy(data["lighting"]),
            "color_palette": list(data["color_palette"]),
            "atmosphere": deepcopy(data["atmosphere"]),
            "character_positions": deepcopy(data["character_positions"]),
            "continuity_rules": list(data["continuity_rules"]),
        }
