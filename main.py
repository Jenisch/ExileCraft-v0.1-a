"""Command-line interface to generate Path of Exile crafting plans."""
from __future__ import annotations

from typing import List

from crafting_engine import CraftingEngine
from poe_data import CraftingDataset


def _safe_input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        print("\nInput stream closed. Exiting.")
        raise SystemExit(1)


def _prompt_selection(options: List[str], prompt: str) -> List[str]:
    while True:
        print(f"\n{prompt}")
        for index, option in enumerate(options, start=1):
            print(f"  [{index}] {option}")
        print("Enter numbers separated by commas (or leave blank to skip): ", end="")
        raw = _safe_input("").strip()
        if not raw:
            return []
        selections: List[str] = []
        try:
            for token in raw.split(","):
                token = token.strip()
                if not token:
                    continue
                idx = int(token)
                if idx < 1 or idx > len(options):
                    raise ValueError(
                        f"Choice {idx} out of range. Valid range is 1-{len(options)}."
                    )
                selections.append(options[idx - 1])
        except ValueError as exc:
            print(f"Error: {exc}")
            continue
        return selections


def main() -> None:
    dataset = CraftingDataset()
    engine = CraftingEngine(dataset)

    while True:
        print("Available bases:")
        for index, base in enumerate(dataset.bases, start=1):
            influence = f" (Influence: {', '.join(base.influence)})" if base.influence else ""
            print(f"  [{index}] {base.name}{influence}")

        choice = _safe_input("Select base number: ").strip()
        if not choice:
            print("Please enter the number corresponding to the base you want to craft.")
            continue
        try:
            base_index = int(choice)
        except ValueError:
            print("Base selection must be numeric. Please try again.")
            continue
        if base_index < 1 or base_index > len(dataset.bases):
            print(f"Base index {base_index} is out of range. Choose between 1 and {len(dataset.bases)}.")
            continue
        base = dataset.bases[base_index - 1]
        break

    possible_prefixes = [affix.name for affix in dataset.compatible_affixes(base.item_class, tags=base.tags, affix_type="prefix")]
    possible_suffixes = [affix.name for affix in dataset.compatible_affixes(base.item_class, tags=base.tags, affix_type="suffix")]

    chosen_prefixes = _prompt_selection(possible_prefixes, "Select desired prefixes")
    chosen_suffixes = _prompt_selection(possible_suffixes, "Select desired suffixes")

    request = engine.build_request(base.name, chosen_prefixes, chosen_suffixes)
    plan = engine.generate_plan(request)

    print("\nCrafting plan:")
    for step_number, step in enumerate(plan, start=1):
        print(f"\nStep {step_number}: {step.title}")
        print(step.details)


if __name__ == "__main__":
    main()
