"""High-level heuristics for generating crafting plans."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from poe_data import Affix, BaseItem, CraftingDataset


@dataclass
class CraftingRequest:
    """User request describing a target item to craft."""

    base_name: str
    prefixes: Sequence[str]
    suffixes: Sequence[str]


@dataclass
class CraftingStep:
    """One actionable step in a crafting plan."""

    title: str
    details: str


class CraftingEngine:
    """Produces step-by-step crafting plans based on a limited heuristic."""

    def __init__(self, dataset: CraftingDataset) -> None:
        self.dataset = dataset

    def build_request(self, base_name: str, prefixes: Iterable[str], suffixes: Iterable[str]) -> CraftingRequest:
        return CraftingRequest(base_name=base_name, prefixes=list(prefixes), suffixes=list(suffixes))

    def generate_plan(self, request: CraftingRequest) -> List[CraftingStep]:
        base = self.dataset.find_base(request.base_name)
        if base is None:
            raise ValueError(f"Unknown base '{request.base_name}'. Update data/affixes.json with the base.")

        prefix_data = self._affix_lookup(request.prefixes)
        suffix_data = self._affix_lookup(request.suffixes)
        steps: List[CraftingStep] = []

        steps.append(
            CraftingStep(
                title="Acquire the correct base",
                details=self._format_base_acquisition(base),
            )
        )

        steps.extend(self._prepare_base_steps(base))

        if prefix_data:
            steps.extend(self._plan_for_affixes(prefix_data, "prefix"))
        if suffix_data:
            steps.extend(self._plan_for_affixes(suffix_data, "suffix"))

        steps.append(
            CraftingStep(
                title="Finish and protect the item",
                details=self._format_finishing_steps(base, prefix_data, suffix_data),
            )
        )
        return steps

    def _affix_lookup(self, names: Iterable[str]) -> Dict[str, Affix]:
        lookup = {}
        for name in names:
            match = next((affix for affix in self.dataset.affixes if affix.name.lower() == name.lower()), None)
            if not match:
                raise ValueError(
                    f"Affix '{name}' missing from dataset. Add it to data/affixes.json to continue."
                )
            lookup[match.name] = match
        return lookup

    def _prepare_base_steps(self, base: BaseItem) -> List[CraftingStep]:
        details: List[str] = []
        if base.influence:
            details.append(
                "Ensure the base drops or is chanced in the required influence: "
                + ", ".join(base.influence)
            )
        if "energy_shield" in base.tags:
            details.append(
                "Use Perfect Fossils (or Hillock rank 3 in Research) until the base reaches at least 28% quality."
            )
        details.extend(base.craft_tips)
        if not details:
            details.append("Clean all sockets and quality to 20% before starting advanced crafting.")
        return [CraftingStep(title="Prepare the base", details="\n".join(details))]

    def _plan_for_affixes(self, affixes: Dict[str, Affix], kind: str) -> List[CraftingStep]:
        steps: List[CraftingStep] = []
        remaining = list(affixes.values())

        deterministic = [affix for affix in remaining if self._has_deterministic_method(affix)]
        if deterministic:
            description = [
                self._best_method_description(affix) for affix in deterministic
            ]
            steps.append(
                CraftingStep(
                    title=f"Secure deterministic {kind} mods",
                    details="\n".join(description),
                )
            )
            remaining = [affix for affix in remaining if affix not in deterministic]

        if remaining:
            weighted_methods = [self._best_method_description(affix) for affix in remaining]
            steps.append(
                CraftingStep(
                    title=f"Hunt for remaining {kind} mods",
                    details="\n".join(weighted_methods),
                )
            )
        return steps

    def _has_deterministic_method(self, affix: Affix) -> bool:
        priority_keywords = ("Essence", "Harvest Augment", "Bench", "Influence-specific")
        return any(keyword in method for method in affix.methods for keyword in priority_keywords)

    def _best_method_description(self, affix: Affix) -> str:
        prioritised = self._prioritise_methods(affix.methods)
        primary = prioritised[0] if prioritised else "Use generic alteration/augmentation attempts."
        extra = f" (item level {affix.level}+ required)." if affix.level else ""
        return f"- {affix.name}: {primary}{extra}"

    def _prioritise_methods(self, methods: Sequence[str]) -> List[str]:
        priorities = [
            "Harvest Augment",
            "Essence",
            "Bench",
            "Influence-specific",
            "Fossil",
            "Harvest Reforge",
            "Alteration",
        ]
        def sort_key(method: str) -> int:
            for index, keyword in enumerate(priorities):
                if keyword in method:
                    return index
            return len(priorities)

        return sorted(methods, key=sort_key)

    def _format_base_acquisition(self, base: BaseItem) -> str:
        influence = f" with {', '.join(base.influence)} influence" if base.influence else ""
        return (
            f"Buy or farm a {base.name}{influence}. Item level should be at least "
            f"{max(80, max(affix.level for affix in self.dataset.compatible_affixes(base.item_class, tags=base.tags)))}"
            "."
        )

    def _format_finishing_steps(
        self, base: BaseItem, prefixes: Dict[str, Affix], suffixes: Dict[str, Affix]
    ) -> str:
        notes: List[str] = []
        if prefixes or suffixes:
            notes.append(
                "Lock prefixes or suffixes with crafting bench before using risky Harvest reforges or Aisling unveils."
            )
        if suffixes:
            notes.append("If resistances are lacking, bench craft a temporary resistance suffix until you upgrade.")
        if "energy_shield" in base.tags:
            notes.append("Finish with Eldritch Ichors/Embers to roll implicits without touching prefixes/suffixes.")
        notes.append("Use Divine Orbs only after all mandatory mods are secured.")
        return "\n".join(notes)


__all__ = [
    "CraftingEngine",
    "CraftingRequest",
    "CraftingStep",
]
