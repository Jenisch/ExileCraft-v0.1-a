"""Data loading utilities for Path of Exile crafting information."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


ROOT = Path(__file__).parent
SAMPLE_DATA_PATH = ROOT / "data" / "affixes.json"
REPOE_DATA_DIR = ROOT / "data" / "repoe"

RELEVANT_CLASS_KEYWORDS = (
    "armour",
    "armor",
    "helmet",
    "helm",
    "glove",
    "boot",
    "shield",
    "buckler",
    "kite",
    "tower",
    "weapon",
    "axe",
    "bow",
    "claw",
    "dagger",
    "rapier",
    "sword",
    "sabre",
    "blade",
    "sceptre",
    "scepter",
    "mace",
    "hammer",
    "staff",
    "warstaff",
    "polearm",
    "spear",
    "wand",
    "jewellery",
    "jewelry",
    "amulet",
    "ring",
    "belt",
    "talisman",
    "quiver",
    "focus",
)

RELEVANT_TAGS = {
    "armour",
    "armor",
    "helmet",
    "helm",
    "gloves",
    "boots",
    "shield",
    "weapon",
    "two_hand_weapon",
    "one_hand_weapon",
    "bow",
    "claw",
    "dagger",
    "mace",
    "staff",
    "sword",
    "wand",
    "sceptre",
    "axe",
    "jewellery",
    "jewelry",
    "ring",
    "amulet",
    "belt",
    "talisman",
    "trinket",
    "quiver",
    "focus",
    "offhand",
    "off_hand",
}


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
    """Loads and provides lookup helpers for crafting data."""

    def __init__(
        self,
        source: str = "auto",
        *,
        repo_dir: Optional[Path] = None,
        sample_path: Optional[Path] = None,
    ) -> None:
        self.requested_source = source
        self.repo_dir = repo_dir or REPOE_DATA_DIR
        self.sample_path = sample_path or SAMPLE_DATA_PATH
        self._bases: List[BaseItem] = []
        self._affixes: List[Affix] = []
        self._source_used: str = "unknown"
        self._load()

    @property
    def source(self) -> str:
        """Return the data source that ended up being loaded."""

        return self._source_used

    def _load(self) -> None:
        loaders = {
            "repoe": self._load_repoe,
            "sample": self._load_sample,
        }
        if self.requested_source == "auto":
            try:
                self._load_repoe()
                self._source_used = "repoe"
                return
            except FileNotFoundError:
                pass
            self._load_sample()
            self._source_used = "sample"
            return

        loader = loaders.get(self.requested_source)
        if not loader:
            raise ValueError(
                "source must be one of {'auto', 'repoe', 'sample'} but "
                f"received '{self.requested_source}'"
            )
        loader()
        self._source_used = self.requested_source

    def _load_sample(self) -> None:
        if not self.sample_path.exists():
            raise FileNotFoundError(
                f"Crafting dataset missing at {self.sample_path}. Provide affixes.json to continue."
            )
        payload = json.loads(self.sample_path.read_text(encoding="utf8"))
        bases = [BaseItem.from_dict(entry) for entry in payload.get("bases", [])]
        affixes = [Affix.from_dict(entry) for entry in payload.get("affixes", [])]
        self._assign_filtered_payload(bases, affixes)

    def _load_repoe(self) -> None:
        base_items_file = self.repo_dir / "base_items.min.json"
        mods_file = self.repo_dir / "mods.min.json"
        if not base_items_file.exists() or not mods_file.exists():
            raise FileNotFoundError(
                "RePoE dataset not found. Run `python tools/import_repoe.py --download` or "
                "import your own RePoE data first."
            )

        base_payload: Dict[str, dict] = json.loads(base_items_file.read_text(encoding="utf8"))
        mod_payload: Dict[str, dict] = json.loads(mods_file.read_text(encoding="utf8"))

        bases, tag_lookup = self._convert_repoe_bases(base_payload)
        affixes = self._convert_repoe_affixes(mod_payload, tag_lookup)

        self._assign_filtered_payload(bases, affixes)

    def _convert_repoe_bases(
        self, payload: Dict[str, dict]
    ) -> Tuple[List[BaseItem], Dict[str, Tuple[str, Sequence[str]]]]:
        bases: List[BaseItem] = []
        tag_lookup: Dict[str, Tuple[str, Sequence[str]]] = {}
        for base_id, entry in payload.items():
            name = entry.get("name")
            item_class = entry.get("item_class", "Unknown")
            tags = list(entry.get("tags", []))
            if not name or item_class == "Hideout Doodads":
                continue

            influence = [
                self._format_influence(tag)
                for tag in tags
                if tag.endswith("_item") and tag not in {"default_item", "not_for_sale_item"}
            ]
            influence = [inf for inf in influence if inf]

            notes = entry.get("flavour_text", "") or ""
            craft_tips = self._derive_base_tips(tags)

            bases.append(
                BaseItem(
                    name=name,
                    item_class=item_class,
                    tags=tags,
                    influence=influence,
                    notes=notes,
                    craft_tips=craft_tips,
                )
            )
            tag_lookup[base_id] = (item_class, tags)

        bases.sort(key=lambda base: base.name)
        return bases, tag_lookup

    def _convert_repoe_affixes(
        self,
        payload: Dict[str, dict],
        base_lookup: Dict[str, Tuple[str, Sequence[str]]],
    ) -> List[Affix]:
        affixes: List[Affix] = []
        base_tags = list(base_lookup.values())
        for mod_id, entry in payload.items():
            generation_type = entry.get("generation_type")
            if generation_type not in (1, 2):
                continue
            name = entry.get("name") or entry.get("generation_weight_tag", "")
            if not name:
                # skip meta/internal mods without exposed names
                continue
            affix_type = "prefix" if generation_type == 1 else "suffix"
            required_level = int(entry.get("required_level", 1) or 1)

            spawn_tags = set(entry.get("spawn_tags", []))
            if not spawn_tags:
                spawn_tags = {
                    weight_entry["tag"]
                    for weight_entry in entry.get("spawn_weights", [])
                    if weight_entry.get("weight", 0) > 0 and weight_entry.get("tag") not in {"default"}
                }
            spawn_tags = {tag for tag in spawn_tags if not tag.startswith("no_")}

            allowed_classes = self._infer_allowed_item_classes(spawn_tags, base_tags)
            methods = self._heuristic_methods(entry, spawn_tags, affix_type)
            notes = self._derive_affix_notes(entry)

            affixes.append(
                Affix(
                    name=name,
                    type=affix_type,
                    item_classes=allowed_classes or ["Universal"],
                    required_tags=sorted(spawn_tags),
                    level=required_level,
                    methods=methods,
                    notes=notes,
                )
            )

        affixes.sort(key=lambda affix: (affix.type, affix.name))
        return affixes

    def _assign_filtered_payload(
        self, bases: Sequence[BaseItem], affixes: Sequence[Affix]
    ) -> None:
        filtered_bases = self._filter_relevant_bases(bases)
        allowed_classes = {base.item_class for base in filtered_bases}
        filtered_affixes = self._filter_relevant_affixes(affixes, allowed_classes)
        allowed_tags = {
            self._normalize_tag(tag) for base in filtered_bases for tag in base.tags
        }
        self._normalize_affix_tags(filtered_affixes, allowed_tags)
        self._bases = sorted(filtered_bases, key=lambda base: (base.item_class, base.name))
        self._affixes = sorted(filtered_affixes, key=lambda affix: (affix.type, affix.name))

    def _normalize_affix_tags(
        self, affixes: Sequence[Affix], allowed_tags: Set[str]
    ) -> None:
        """Trim affix tag requirements to those present on our filtered bases."""

        if not allowed_tags:
            return

        for affix in affixes:
            if not affix.required_tags:
                continue
            trimmed = {
                tag
                for tag in affix.required_tags
                if self._normalize_tag(tag) in allowed_tags
            }
            if trimmed:
                affix.required_tags = sorted(trimmed)
            else:
                affix.required_tags = []

    def _filter_relevant_bases(self, bases: Sequence[BaseItem]) -> List[BaseItem]:
        filtered: List[BaseItem] = []
        for base in bases:
            if self._is_relevant_base(base):
                filtered.append(base)
        return filtered

    def _filter_relevant_affixes(
        self, affixes: Sequence[Affix], allowed_classes: Iterable[str]
    ) -> List[Affix]:
        allowed = {self._normalize_class(name) for name in allowed_classes}
        base_tokens = {
            token for name in allowed_classes for token in self._tokenize(name)
        }
        filtered: List[Affix] = []
        for affix in affixes:
            if not affix.item_classes:
                filtered.append(affix)
                continue
            normalized = {self._normalize_class(name) for name in affix.item_classes}
            if not normalized:
                filtered.append(affix)
                continue
            if normalized & allowed:
                filtered.append(affix)
                continue
            # fall back to partial token overlap so similar class names are retained
            affix_tokens = {
                token for name in affix.item_classes for token in self._tokenize(name)
            }
            if affix_tokens & base_tokens:
                filtered.append(affix)
        return filtered

    def _is_relevant_base(self, base: BaseItem) -> bool:
        item_class = base.item_class.lower()
        if any(keyword in item_class for keyword in RELEVANT_CLASS_KEYWORDS):
            return True
        tags = {tag.lower() for tag in base.tags}
        if tags & RELEVANT_TAGS:
            return True
        return False

    def _infer_allowed_item_classes(
        self,
        spawn_tags: Sequence[str],
        base_tags: Sequence[Tuple[str, Sequence[str]]],
    ) -> List[str]:
        if not spawn_tags:
            return []
        allowed: List[str] = []
        required = set(spawn_tags)
        for item_class, tags in base_tags:
            if required.issubset(tags):
                allowed.append(item_class)
        seen = set()
        ordered: List[str] = []
        for item_class in allowed:
            if item_class not in seen:
                ordered.append(item_class)
                seen.add(item_class)
        return ordered

    def _heuristic_methods(
        self,
        mod_entry: Dict[str, object],
        spawn_tags: Sequence[str],
        affix_type: str,
    ) -> List[str]:
        methods: List[str] = []
        name = str(mod_entry.get("name", ""))
        mod_type = str(mod_entry.get("type", ""))

        if "Essence" in mod_type or "Essence" in name:
            methods.append("Apply the matching Essence on a clean item until it hits.")
        if "Delve" in mod_type or "delve" in mod_type.lower():
            methods.append("Target farm in Delve nodes or use Jagged/Corroded/Pristine fossils as appropriate.")
        if "Synthesis" in mod_type or "synthesised" in name.lower():
            methods.append("Combine Synthesised implicit bases or use Fractured bases to elevate odds.")

        if not methods:
            thematic = None
            for tag in ("attack", "caster", "minion", "speed", "defences", "ailment"):
                if tag in spawn_tags:
                    thematic = tag
                    break
            if thematic:
                methods.append(
                    f"Use Harvest Reforge {thematic} or Deafening Essences that roll {thematic} modifiers."
                )

        if not methods:
            methods.append(
                f"Spam alterations/regals on an ilvl {mod_entry.get('required_level', 1)}+ base and finish with metacrafts."
            )

        if affix_type == "prefix" and "influence" in spawn_tags:
            methods.append("Leverage Awakener's Orbs or Synthesised bases to guarantee influenced prefixes.")
        elif affix_type == "suffix" and "influence" in spawn_tags:
            methods.append("Use Maven orbs and Harvest reforge keep prefixes to secure influenced suffixes.")

        return methods

    def _derive_affix_notes(self, mod_entry: Dict[str, object]) -> str:
        if mod_entry.get("is_essence_only"):
            return "Only available from matching Essence tiers."
        if mod_entry.get("is_veiled"):
            return "Appears via Betrayal unveils."
        tags = mod_entry.get("tags", []) or []
        if "atlas_base_type" in tags:
            return "Only available on Atlas base types."
        return ""

    def _format_influence(self, tag: str) -> str:
        pretty = tag.replace("_item", "").replace("_", " ")
        pretty = pretty.title()
        if pretty == "Shaper":
            return "Shaper"
        if pretty == "Elder":
            return "Elder"
        if pretty.endswith(" Item"):
            return pretty[:-5]
        return pretty

    def _derive_base_tips(self, tags: Sequence[str]) -> List[str]:
        tips: List[str] = []
        tag_set = set(tags)
        if "two_hand_weapon" in tag_set or "staff" in tag_set:
            tips.append("Aim for 30% quality using Perfect Fossils before serious crafting.")
        if "caster" in tag_set:
            tips.append("Harvest Reforge Caster is a strong way to force caster prefixes.")
        if "attack" in tag_set:
            tips.append("Use Deafening Essences of Contempt/Zeal/Anger depending on desired attack affixes.")
        if {"armour", "evasion", "energy_shield"} & tag_set:
            tips.append("Balance suffixes with Eldritch Ichors/Embers for additional defences.")
        return tips

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

        item_class_norm = self._normalize_class(item_class or "")
        item_tokens = self._tokenize(item_class)
        tag_set = {self._normalize_tag(tag) for tag in (tags or []) if tag}
        results: List[Affix] = []
        for affix in self._affixes:
            if affix_type and affix.type.lower() != affix_type.lower():
                continue
            class_norms = [self._normalize_class(token) for token in affix.item_classes]
            matches_class = (
                not affix.item_classes
                or any(norm == "universal" for norm in class_norms)
                or item_class_norm and item_class_norm in class_norms
                or any(
                    item_class_norm and norm and (item_class_norm in norm or norm in item_class_norm)
                    for norm in class_norms
                )
            )
            if not matches_class and item_tokens:
                affix_token_sets = [self._tokenize(token) for token in affix.item_classes]
                matches_class = any(item_tokens & tokens for tokens in affix_token_sets if tokens)
            if matches_class:
                results.append(affix)
                continue
            required = {self._normalize_tag(tag) for tag in affix.required_tags if tag}
            if required and tag_set.issuperset(required):
                results.append(affix)
        return results

    @staticmethod
    def _normalize_aliases(value: str) -> str:
        if value is None:
            return ""
        value = str(value).lower().strip()
        if not value:
            return ""
        value = value.replace("armor", "armour")
        value = value.replace("jewelry", "jewellery")
        return value

    def _normalize_class(self, value: str) -> str:
        value = self._normalize_aliases(value)
        return re.sub(r"[^a-z0-9]", "", value)

    def _normalize_tag(self, value: str) -> str:
        value = self._normalize_aliases(value)
        return value.replace(" ", "_")

    def _tokenize(self, value: str) -> Set[str]:
        normalized = self._normalize_aliases(value)
        return {token for token in re.split(r"[^a-z0-9]+", normalized) if token}


__all__ = ["CraftingDataset", "BaseItem", "Affix"]
