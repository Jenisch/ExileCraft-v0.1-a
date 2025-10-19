"""Data loading utilities for the local Path of Exile crafting dataset."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import json


DATA_PATH = Path(__file__).parent / "data" / "affixes.json"


@dataclass
class BaseItem:
    """Represents an item base that can be crafted."""

    name: str
    item_class: str
    tags: List[str]
    influence: List[str]
    notes: str
    craft_tips: List[str]

    @classmethod
    def from_dict(cls, payload: dict) -> "BaseItem":
        return cls(
            name=payload["name"],
            item_class=payload["item_class"],
            tags=list(payload.get("tags", [])),
            influence=list(payload.get("influence", [])),
            notes=payload.get("notes", ""),
            craft_tips=list(payload.get("craft_tips", [])),
        )


@dataclass
class Affix:
    """Represents a target affix with metadata about how to acquire it."""

    name: str
    type: str
    item_classes: List[str]
    required_tags: List[str]
    level: int
    methods: List[str]
    notes: str

    @classmethod
    def from_dict(cls, payload: dict) -> "Affix":
        return cls(
            name=payload["name"],
            type=payload["type"],
            item_classes=list(payload.get("item_classes", [])),
            required_tags=list(payload.get("required_tags", [])),
            level=int(payload.get("level", 1)),
            methods=list(payload.get("methods", [])),
            notes=payload.get("notes", ""),
        )


class CraftingDataset:
    """Loads and provides lookup helpers for the local crafting data."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or DATA_PATH
        self._bases: List[BaseItem] = []
        self._affixes: List[Affix] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(
                f"Crafting dataset missing at {self.path}. Provide affixes.json to continue."
            )
        payload = json.loads(self.path.read_text(encoding="utf8"))
        self._bases = [BaseItem.from_dict(entry) for entry in payload.get("bases", [])]
        self._affixes = [Affix.from_dict(entry) for entry in payload.get("affixes", [])]

    @property
    def bases(self) -> List[BaseItem]:
        return list(self._bases)

    @property
    def affixes(self) -> List[Affix]:
        return list(self._affixes)

    def find_base(self, name: str) -> Optional[BaseItem]:
        name_lower = name.lower()
        for base in self._bases:
            if base.name.lower() == name_lower:
                return base
        return None

    def compatible_affixes(
        self,
        item_class: str,
        *,
        tags: Optional[Iterable[str]] = None,
        affix_type: Optional[str] = None,
    ) -> List[Affix]:
        """Return affixes compatible with an item class and optional tags."""

        tags = set(tags or [])
        results: List[Affix] = []
        for affix in self._affixes:
            if item_class not in affix.item_classes:
                continue
            if affix_type and affix.type != affix_type:
                continue
            if affix.required_tags and not tags.issuperset(affix.required_tags):
                continue
            results.append(affix)
        return results


__all__ = ["CraftingDataset", "BaseItem", "Affix"]
