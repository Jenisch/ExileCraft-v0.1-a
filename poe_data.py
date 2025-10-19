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

ALLOWED_AFFIX_DOMAINS = {
    "item",
    "crafted",
    "delve",
    "unveiled",
    "veiled",
    "abyss_jewel",
    "affliction_jewel",
}

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
    spawn_weights: List[Tuple[str, int]]
    stat_texts: List[str]
    stat_ranges: List[Tuple[int, int]]

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
            spawn_weights=[
                (str(entry[0]), int(entry[1]))
                for entry in payload.get("spawn_weights", [])
                if isinstance(entry, (list, tuple)) and len(entry) == 2
            ],
            stat_texts=list(payload.get("stat_texts", [])),
            stat_ranges=[
                (int(range_pair[0]), int(range_pair[1]))
                for range_pair in payload.get("stat_ranges", [])
                if isinstance(range_pair, (list, tuple)) and len(range_pair) == 2
            ],
        )


@dataclass
class AffixChance:
    """Represents the likelihood of rolling an affix within a mod pool."""

    weight: int
    total_weight: int

    @property
    def chance(self) -> float:
        if self.total_weight <= 0:
            return 0.0
        return self.weight / self.total_weight

    @property
    def expected_rolls(self) -> float:
        if self.weight <= 0:
            return float("inf")
        return self.total_weight / self.weight


class StatTranslator:
    """Translate RePoE stat blocks into human-readable text."""

    def __init__(self, entries: Sequence[dict]):
        self._by_length: Dict[int, List[dict]] = {}
        for entry in entries:
            ids = []
            for spec in entry.get("ids", []):
                if isinstance(spec, str):
                    ids.append(spec)
                else:
                    ids.append(spec.get("id", ""))
            if not ids:
                continue
            entry = dict(entry)
            entry["_ids"] = tuple(ids)
            self._by_length.setdefault(len(ids), []).append(entry)

    def translate(self, stats: Sequence[dict]) -> List[str]:
        if not stats:
            return []
        ids = tuple(stat.get("id", "") for stat in stats)
        candidates = self._by_length.get(len(ids), [])
        for entry in candidates:
            if entry.get("_ids") != ids:
                continue
            lines = []
            for variant in entry.get("English", []):
                if self._conditions_match(variant.get("condition", []), stats):
                    lines.append(self._format_variant(variant, stats))
            if lines:
                return lines
        # fall back to simple humanisation when translation is unavailable
        return [self._fallback(stat) for stat in stats]

    @staticmethod
    def _conditions_match(conditions: Sequence[dict], stats: Sequence[dict]) -> bool:
        if not conditions:
            return True
        padded = list(conditions) + [{}] * (len(stats) - len(conditions))
        for condition, stat in zip(padded, stats):
            if not condition:
                continue
            value = StatTranslator._stat_value(stat)
            if "min" in condition and value < condition["min"]:
                return False
            if "max" in condition and value > condition["max"]:
                return False
            if condition.get("negated") and value >= 0:
                return False
        return True

    @staticmethod
    def _format_variant(variant: dict, stats: Sequence[dict]) -> str:
        template = variant.get("string", "")
        formats = list(variant.get("format", []))
        formatted: List[str] = []
        for index, stat in enumerate(stats):
            fmt = formats[index] if index < len(formats) else "#"
            formatted.append(StatTranslator._format_value(stat, fmt))
        return template.format(*formatted)

    @staticmethod
    def _format_value(stat: dict, fmt: str) -> str:
        value_min = StatTranslator._coerce_number(stat.get("min", 0))
        value_max = StatTranslator._coerce_number(stat.get("max", value_min))
        if fmt == "ignore":
            return ""
        show_sign = fmt == "+#"
        if value_min == value_max:
            prefix = "+" if show_sign and value_max >= 0 else ""
            return f"{prefix}{value_max}"
        if show_sign:
            prefix = "+" if value_max >= 0 else ""
            return f"{prefix}{value_min}–{value_max}"
        return f"{value_min}–{value_max}"

    @staticmethod
    def _coerce_number(value: object) -> int:
        if isinstance(value, (int, float)):
            return int(round(value))
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _stat_value(stat: dict) -> int:
        value_min = StatTranslator._coerce_number(stat.get("min", 0))
        value_max = StatTranslator._coerce_number(stat.get("max", value_min))
        if value_min == value_max:
            return value_min
        if abs(value_max) >= abs(value_min):
            return value_max
        return value_min

    @staticmethod
    def _fallback(stat: dict) -> str:
        stat_id = str(stat.get("id", "unknown_stat")).replace("_", " ")
        value_min = StatTranslator._coerce_number(stat.get("min", 0))
        value_max = StatTranslator._coerce_number(stat.get("max", value_min))
        if value_min == value_max:
            return f"{value_min} {stat_id}".strip()
        return f"{value_min}–{value_max} {stat_id}".strip()


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
        self._stat_translator: Optional[StatTranslator] = None
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
        self._stat_translator = None
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

        translator: Optional[StatTranslator] = None
        translations_file = self.repo_dir / "stat_translations.min.json"
        if translations_file.exists():
            try:
                entries = json.loads(translations_file.read_text(encoding="utf8"))
                translator = StatTranslator(entries)
            except Exception:
                translator = None
        self._stat_translator = translator

        bases, tag_lookup = self._convert_repoe_bases(base_payload)
        affixes = self._convert_repoe_affixes(mod_payload, tag_lookup, translator)

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
        translator: Optional[StatTranslator],
    ) -> List[Affix]:
        affixes: List[Affix] = []
        base_tags = list(base_lookup.values())
        for mod_id, entry in payload.items():
            domain = str(entry.get("domain", "")).lower()
            if domain and domain not in ALLOWED_AFFIX_DOMAINS:
                continue

            generation_type = entry.get("generation_type")
            affix_type: Optional[str] = None
            if isinstance(generation_type, int):
                if generation_type == 1:
                    affix_type = "prefix"
                elif generation_type == 2:
                    affix_type = "suffix"
            else:
                kind = str(generation_type or "").lower()
                if "prefix" in kind:
                    affix_type = "prefix"
                elif "suffix" in kind:
                    affix_type = "suffix"
            if not affix_type:
                continue

            name = entry.get("name") or entry.get("generation_weight_tag", "")
            if not name:
                # skip meta/internal mods without exposed names
                continue
            required_level = int(entry.get("required_level", 1) or 1)

            spawn_tags = set(entry.get("spawn_tags", []))
            if not spawn_tags:
                spawn_tags = {
                    weight_entry["tag"]
                    for weight_entry in entry.get("spawn_weights", [])
                    if weight_entry.get("weight", 0) > 0 and weight_entry.get("tag") not in {"default"}
                }
            spawn_tags = {tag for tag in spawn_tags if not tag.startswith("no_")}
            if domain == "item" and not spawn_tags:
                # Skip legacy/internal mods that cannot naturally spawn on relevant items.
                continue

            allowed_classes = self._infer_allowed_item_classes(spawn_tags, base_tags)
            methods = self._heuristic_methods(entry, spawn_tags, affix_type)
            notes = self._derive_affix_notes(entry)

            stats = entry.get("stats", []) or []
            stat_texts, stat_ranges = self._translate_stats(stats, translator)

            spawn_weights = []
            for weight_entry in entry.get("spawn_weights", []) or []:
                tag = weight_entry.get("tag")
                weight = int(weight_entry.get("weight", 0) or 0)
                if not tag or weight <= 0:
                    continue
                spawn_weights.append((tag, weight))

            affixes.append(
                Affix(
                    name=name,
                    type=affix_type,
                    item_classes=allowed_classes or ["Universal"],
                    required_tags=sorted(spawn_tags),
                    level=required_level,
                    methods=methods,
                    notes=notes,
                    spawn_weights=spawn_weights,
                    stat_texts=stat_texts,
                    stat_ranges=stat_ranges,
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
        self._normalize_affix_tags(filtered_affixes)
        self._normalize_spawn_weights(filtered_affixes)
        self._bases = sorted(filtered_bases, key=lambda base: (base.item_class, base.name))
        self._affixes = sorted(filtered_affixes, key=lambda affix: (affix.type, affix.name))

    def _translate_stats(
        self, stats: Sequence[dict], translator: Optional[StatTranslator]
    ) -> Tuple[List[str], List[Tuple[int, int]]]:
        if not stats:
            return [], []
        stat_ranges: List[Tuple[int, int]] = []
        for entry in stats:
            minimum = StatTranslator._coerce_number(entry.get("min", 0))
            maximum = StatTranslator._coerce_number(entry.get("max", minimum))
            stat_ranges.append((minimum, maximum))
        if translator:
            stat_texts = translator.translate(stats)
        else:
            stat_texts = [StatTranslator._fallback(entry) for entry in stats]
        return stat_texts, stat_ranges

    def _normalize_affix_tags(self, affixes: Sequence[Affix]) -> None:
        """Normalize affix tag requirements without discarding gating rules."""

        for affix in affixes:
            if not affix.required_tags:
                continue
            normalised: List[str] = []
            for tag in affix.required_tags:
                normalised_tag = self._normalize_tag(tag)
                if not normalised_tag or normalised_tag in normalised:
                    continue
                normalised.append(normalised_tag)
            affix.required_tags = normalised

    def _normalize_spawn_weights(self, affixes: Sequence[Affix]) -> None:
        for affix in affixes:
            if not affix.spawn_weights:
                continue
            combined: Dict[str, int] = {}
            for tag, weight in affix.spawn_weights:
                normalised = self._normalize_tag(tag)
                if not normalised:
                    continue
                combined[normalised] = combined.get(normalised, 0) + int(weight)
            affix.spawn_weights = [(tag, weight) for tag, weight in combined.items() if weight > 0]

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
            if "universal" in normalized:
                filtered.append(affix)
                continue
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

        normalized_class, tag_set, base_tokens = self._build_base_context(item_class, tags)
        return list(
            self._iter_compatible_affixes(normalized_class, tag_set, base_tokens, affix_type)
        )

    def affix_roll_statistics(self, base: BaseItem, affix: Affix) -> Optional[AffixChance]:
        """Compute spawn weight share for a given affix on a base."""

        normalized_class, tag_set, base_tokens = self._build_base_context(
            base.item_class, base.tags
        )
        if not affix.spawn_weights:
            return None

        pool_weight = 0
        target_weight = 0
        for candidate in self._iter_compatible_affixes(
            normalized_class, tag_set, base_tokens, affix.type
        ):
            weight = self._effective_spawn_weight(candidate, tag_set, base_tokens)
            if weight <= 0:
                continue
            pool_weight += weight
            if candidate.name == affix.name:
                target_weight = weight

        if target_weight <= 0 or pool_weight <= 0:
            return None
        return AffixChance(weight=target_weight, total_weight=pool_weight)

    def _build_base_context(
        self, item_class: str, tags: Optional[Iterable[str]]
    ) -> Tuple[str, Set[str], Set[str]]:
        normalized_class = self._normalize_class(item_class or "")
        tag_set = {self._normalize_tag(tag) for tag in (tags or []) if tag}
        tag_set.discard("")
        tag_set.add("default")
        tag_set.add("default_item")
        if normalized_class:
            tag_set.add(normalized_class)

        base_tokens: Set[str] = set()
        for tag in tag_set:
            base_tokens.update(self._tokenize(tag))
        base_tokens.update(self._tokenize(item_class or ""))
        return normalized_class, tag_set, base_tokens

    def _iter_compatible_affixes(
        self,
        normalized_class: str,
        tag_set: Set[str],
        base_tokens: Set[str],
        affix_type: Optional[str],
    ) -> Iterable[Affix]:
        for affix in self._affixes:
            if affix_type and affix.type.lower() != affix_type.lower():
                continue
            if not self._matches_item_class(affix, normalized_class, base_tokens):
                continue
            if not self._matches_required_tags(affix, tag_set, base_tokens):
                continue
            if not self._matches_spawn_weights(affix, tag_set, base_tokens):
                continue
            yield affix

    def _matches_item_class(
        self, affix: Affix, normalized_class: str, base_tokens: Set[str]
    ) -> bool:
        if not affix.item_classes:
            return True
        class_norms = [self._normalize_class(token) for token in affix.item_classes]
        if any(norm == "universal" for norm in class_norms):
            return True
        if normalized_class and normalized_class in class_norms:
            return True
        if not base_tokens:
            return False
        affix_token_sets = [self._tokenize(token) for token in affix.item_classes]
        return any(tokens and tokens.issubset(base_tokens) for tokens in affix_token_sets)

    def _matches_required_tags(
        self, affix: Affix, tag_set: Set[str], base_tokens: Set[str]
    ) -> bool:
        if not affix.required_tags:
            return True
        for tag in affix.required_tags:
            if tag in tag_set:
                continue
            tokens = self._tokenize(tag)
            if not tokens or not tokens.issubset(base_tokens):
                return False
        return True

    def _matches_spawn_weights(
        self, affix: Affix, tag_set: Set[str], base_tokens: Set[str]
    ) -> bool:
        if not affix.spawn_weights:
            return True
        return self._effective_spawn_weight(affix, tag_set, base_tokens) > 0

    def _effective_spawn_weight(
        self, affix: Affix, tag_set: Set[str], base_tokens: Set[str]
    ) -> int:
        total_weight = 0
        for tag, weight in affix.spawn_weights:
            if weight <= 0:
                continue
            if tag in tag_set:
                total_weight += weight
                continue
            tokens = self._tokenize(tag)
            if tokens and tokens.issubset(base_tokens):
                total_weight += weight
        return total_weight

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
        normalized = re.sub(r"[^a-z0-9]", "", value)
        return self._singularize(normalized)

    def _normalize_tag(self, value: str) -> str:
        value = self._normalize_aliases(value)
        return value.replace(" ", "_")

    def _tokenize(self, value: str) -> Set[str]:
        normalized = self._normalize_aliases(value)
        tokens = {token for token in re.split(r"[^a-z0-9]+", normalized) if token}
        expanded: Set[str] = set(tokens)
        for token in tokens:
            singular = self._singularize(token)
            if singular:
                expanded.add(singular)
        return expanded

    def _singularize(self, token: str) -> str:
        """Best-effort singularization so class/tag comparisons survive plurals."""

        if not token:
            return ""
        if token.endswith("ies") and len(token) > 3:
            return token[:-3] + "y"
        if token.endswith("sses") or token.endswith("shes") or token.endswith("ches"):
            return token[:-2]
        if token.endswith("xes") or token.endswith("zes"):
            return token[:-2]
        if token.endswith("es") and len(token) > 2 and token[-3] not in "sxz":
            return token[:-2]
        if token.endswith("s") and not token.endswith("ss") and len(token) > 1:
            return token[:-1]
        return token


__all__ = ["CraftingDataset", "BaseItem", "Affix", "AffixChance"]
