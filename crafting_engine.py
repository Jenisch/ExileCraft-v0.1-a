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
            raise ValueError(
                f"Unknown base '{request.base_name}'. Update data/affixes.json with the base."
            )

        prefix_data = self._affix_lookup(request.prefixes)
        suffix_data = self._affix_lookup(request.suffixes)
        selected_affixes: List[Affix] = list(prefix_data.values()) + list(
            suffix_data.values()
        )
        prefix_categories = {self._method_category(affix) for affix in prefix_data.values()}
        suffix_categories = {self._method_category(affix) for affix in suffix_data.values()}
        all_categories = prefix_categories | suffix_categories

        steps: List[CraftingStep] = []

        steps.append(
            CraftingStep(
                title="Acquire the correct base",
                details=self._format_base_acquisition(base, selected_affixes),
            )
        )

        steps.extend(self._prepare_base_steps(base, all_categories))

        if prefix_data:
            steps.extend(self._detailed_steps_for_kind(prefix_data, "prefix"))
        if prefix_data and suffix_data:
            steps.append(self._stabilise_between_kinds())
        if suffix_data:
            steps.extend(self._detailed_steps_for_kind(suffix_data, "suffix"))

        steps.append(
            CraftingStep(
                title="Finish and protect the item",
                details=self._format_finishing_steps(
                    base,
                    prefix_data,
                    suffix_data,
                    prefix_categories,
                    suffix_categories,
                ),
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

    def _prepare_base_steps(
        self, base: BaseItem, categories: Iterable[str]
    ) -> List[CraftingStep]:
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
        category_set = set(categories)
        if "essence" in category_set:
            details.append(
                "Keep the base magic while spamming Essences so you can easily Regal once the target mod appears."
            )
        if "fossil" in category_set:
            details.append(
                "Prepare the correct resonator (3-4 socket for complex combos) and stock the required Fossils before you begin."
            )
        if {"harvest", "alt_regal", "influence"} & category_set:
            details.append(
                "Have bench crafts like 'Prefixes Cannot Be Changed' ready for locking progress before risky rerolls."
            )
        if not details:
            details.append("Clean all sockets and quality to 20% before starting advanced crafting.")
        return [CraftingStep(title="Prepare the base", details="\n".join(details))]

    def _detailed_steps_for_kind(
        self, affixes: Dict[str, Affix], kind: str
    ) -> List[CraftingStep]:
        ordered = sorted(
            affixes.values(),
            key=lambda affix: (
                self._method_rank(self._method_category(affix)),
                -affix.level,
                affix.name,
            ),
        )
        return [self._crafting_step_for_affix(affix, kind) for affix in ordered]

    def _stabilise_between_kinds(self) -> CraftingStep:
        opposite_instructions = [
            "After finishing your first set of mods, craft 'Cannot roll Prefixes/Suffixes' before reforging the other side.",
            "Be ready to use Harvest 'Reforge keep Prefixes/Suffixes' or beast Imprint crafts to recover if the reroll bricks the item.",
        ]
        return CraftingStep(
            title="Stabilise before working on the other mod type",
            details="\n".join(opposite_instructions),
        )

    def _crafting_step_for_affix(self, affix: Affix, kind: str) -> CraftingStep:
        category = self._method_category(affix)
        methods = self._prioritise_methods(affix.methods)
        primary = methods[0] if methods else "Spam alterations/regals until it appears."
        fallbacks = "; ".join(methods[1:3]) if len(methods) > 1 else ""
        details: List[str] = [
            f"Target: {affix.name} ({kind.title()}, item level {affix.level}+).",
            f"Primary approach: {primary}.",
        ]
        if fallbacks:
            details.append(f"Fallbacks: {fallbacks}.")
        details.extend(self._category_guidance(category, kind))
        if affix.notes:
            details.append(f"Notes: {affix.notes}.")
        return CraftingStep(
            title=f"Secure {kind} '{affix.name}'",
            details="\n".join(details),
        )

    def _category_guidance(self, category: str, kind: str) -> List[str]:
        opposite = "suffix" if kind == "prefix" else "prefix"
        opposite_plural = self._plural_kind(opposite)
        if category == "harvest":
            return [
                "Set up the opposite side with filler mods, then craft 'Cannot roll {opposite}' before using Harvest Augment or Reforge crafts.".format(
                    opposite=opposite_plural.title()
                ),
                "Harvest 'Reforge keep {opposite}' is your safety net once the target mod is locked in.".format(
                    opposite=opposite_plural
                ),
            ]
        if category == "essence":
            return [
                "Upgrade and spam the matching Essence on a clean base. Stop immediately once the target lands, then bench-lock the {opposite} before rerolling.".format(
                    opposite=opposite_plural
                ),
            ]
        if category == "fossil":
            return [
                "Use the listed Fossil combination in a resonator. Apply before each slam and keep an imprint handy if the fossil set is expensive.",
            ]
        if category == "influence":
            return [
                "Acquire or roll the correct influenced base, then use Awakener's Orbs or Maven Orbs as needed to isolate the modifier.",
                "Always lock the {opposite} with the bench before Maven/Orb attempts to avoid bricking finished mods.".format(
                    opposite=opposite_plural
                ),
            ]
        if category == "alt_regal":
            return [
                "Keep the item magic while spamming Alterations until the mod appears, Regal for a second mod, then bench craft to block {opposite} before finishing.".format(
                    opposite=opposite_plural
                ),
            ]
        if category == "bench":
            return [
                "Unlock this affix via unveiling or bench craft it after the other mandatory mods are secured.",
            ]
        return [
            "Use high-tier currency (Chaos/Essence/Harvest reforges) while locking the {opposite} whenever possible to control the mod pool.".format(
                opposite=opposite_plural
            ),
        ]

    @staticmethod
    def _plural_kind(kind: str) -> str:
        return "prefixes" if kind.lower() == "prefix" else "suffixes"

    def _method_category(self, affix: Affix) -> str:
        blob = " ".join(affix.methods).lower()
        if "harvest augment" in blob or "harvest reforge" in blob:
            return "harvest"
        if "essence" in blob:
            return "essence"
        if "fossil" in blob or "delve" in blob:
            return "fossil"
        if "awakener" in blob or "influence" in blob or "synthesised" in blob:
            return "influence"
        if "alteration" in blob or "regal" in blob:
            return "alt_regal"
        if "bench" in blob or "unveil" in blob:
            return "bench"
        return "generic"

    def _method_rank(self, category: str) -> int:
        order = ["harvest", "essence", "fossil", "influence", "bench", "alt_regal", "generic"]
        return order.index(category) if category in order else len(order)

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

    def _format_base_acquisition(self, base: BaseItem, affixes: Sequence[Affix]) -> str:
        influence = f" with {', '.join(base.influence)} influence" if base.influence else ""
        if affixes:
            required_ilvl = max(affix.level for affix in affixes)
        else:
            compatible = self.dataset.compatible_affixes(base.item_class, tags=base.tags)
            required_ilvl = max((affix.level for affix in compatible), default=75)
        recommended = max(required_ilvl, 82 if required_ilvl >= 82 else required_ilvl)
        return (
            f"Buy or farm a {base.name}{influence}. Item level must be {required_ilvl}+; aim for ilvl {recommended} "
            "to keep high-tier rolls available."
        )

    def _format_finishing_steps(
        self,
        base: BaseItem,
        prefixes: Dict[str, Affix],
        suffixes: Dict[str, Affix],
        prefix_categories: Iterable[str],
        suffix_categories: Iterable[str],
    ) -> str:
        notes: List[str] = []
        categories = set(prefix_categories) | set(suffix_categories)
        if prefixes or suffixes:
            notes.append(
                "Remove any meta-crafts, then bench 'Prefixes/Suffixes Cannot Be Changed' before Harvest, Essence, or Eldritch slams to secure progress."
            )
        if "harvest" in categories:
            notes.append(
                "Use Harvest 'Reforge keep Prefixes/Suffixes' to fix filler mods without endangering locked affixes."
            )
        if "essence" in categories:
            notes.append(
                "Upgrade your Essences with Remnants of Corruption so the final slam stays at the highest tier."
            )
        if "influence" in categories:
            notes.append(
                "Divine the item only after all influenced mods are secured; Awakener or Maven Orbs cannot be undone."
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
