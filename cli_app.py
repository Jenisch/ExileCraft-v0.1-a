"""Rich-styled console interface for the ExileCraft planner."""
from __future__ import annotations

import importlib.util
from typing import Iterable, List, Sequence

from crafting_engine import CraftingEngine
from poe_data import CraftingDataset, BaseItem


def _ensure_rich() -> None:
    if importlib.util.find_spec("rich") is None:
        raise RuntimeError(
            "The 'rich' package is required for the CLI. Install dependencies with "
            "`py -m pip install -r requirements.txt` on Windows or "
            "`python3 -m pip install -r requirements.txt` elsewhere."
        )


def _safe_input(console, prompt: str) -> str:
    try:
        return console.input(prompt)
    except EOFError:
        console.print("\n[bold red]Input stream closed. Exiting.")
        raise SystemExit(1)


def _render_banner(console) -> None:
    from rich.panel import Panel
    from rich.text import Text

    title = Text("ExileCraft Planner", style="bold gold1")
    subtitle = Text(
        "Design your dream item with guidance inspired by the Wraeclastian forge.",
        style="italic dark_orange",
    )
    banner = Panel.fit(
        Text.from_markup(
            "[bold #ffb347]\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\n"
            "   Path of Exile Crafting Atelier\n"
            "/////////////////////////////[/]"
        ),
        title="ExileCraft Planner",
        subtitle="Plan. Protect. Perfect.",
        border_style="gold1",
    )
    console.print(banner)
    console.print(title, justify="center")
    console.print(subtitle, justify="center")
    console.rule(style="dark_orange3")


def _choose_base(console, dataset: CraftingDataset) -> int:
    from rich.table import Table
    from rich.text import Text

    bases = dataset.bases
    while True:
        console.print(
            Text.from_markup("[bold gold1]Search bases[/] [dim](name, class:Claws, tag:caster, influence:shaper)[/]")
        )
        query = _safe_input(console, "[bold gold1]Search (Enter shows popular bases)[/]: ").strip()
        filtered = _filter_bases(bases, query) if query else bases
        if not filtered:
            console.print(f"[red]No bases matched '{query}'. Try another name or tag.")
            continue
        display = filtered[:25]
        table = Table(
            title="Select your base", title_style="bold gold1", header_style="bold orange1"
        )
        table.add_column("#", justify="right", style="bold gold3")
        table.add_column("Base", style="bold white")
        table.add_column("Class", style="light_goldenrod2")
        table.add_column("Influence", style="italic pale_turquoise1")
        for index, base in enumerate(display, start=1):
            influence = ", ".join(base.influence) if base.influence else "None"
            table.add_row(str(index), base.name, base.item_class, influence)
        console.print(table)
        if len(filtered) > len(display):
            console.print(
                f"[dim]{len(filtered) - len(display)} more results hidden. Refine your search or filter by tag/class."
            )
        raw = _safe_input(console, "[bold gold1]Enter base number (blank to search again)[/]: ").strip()
        if not raw:
            continue
        if not raw.isdigit():
            console.print("[red]Base selection must be numeric.")
            continue
        index = int(raw)
        if index < 1 or index > len(display):
            console.print(f"[red]Choice out of range. Select between 1 and {len(display)}.")
            continue
        chosen_base = display[index - 1]
        return bases.index(chosen_base)


def _filter_bases(bases: Sequence[BaseItem], query: str) -> List[BaseItem]:
    q = query.lower()
    if q.startswith("class:"):
        token = q.split(":", 1)[1].strip()
        return [base for base in bases if token in base.item_class.lower()]
    if q.startswith("tag:"):
        token = q.split(":", 1)[1].strip()
        return [base for base in bases if any(token == tag.lower() for tag in base.tags)]
    if q.startswith("influence:"):
        token = q.split(":", 1)[1].strip()
        return [base for base in bases if any(token in influence.lower() for influence in base.influence)]
    return [base for base in bases if q in base.name.lower()]


def _prompt_multi(console, options: Iterable[str], prompt: str) -> List[str]:
    from rich.table import Table

    options = list(options)
    if not options:
        return []
    table = Table(title=prompt, header_style="bold orange1")
    table.add_column("#", justify="right", style="bold gold3")
    table.add_column("Modifier", style="white")
    for idx, option in enumerate(options, start=1):
        table.add_row(str(idx), option)

    while True:
        console.print(table)
        console.print("[dim]Enter numbers separated by commas (leave blank to skip).[/]")
        raw = _safe_input(console, "[bold gold1]Your picks[/]: ").strip()
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
                    raise ValueError(f"Choice {idx} out of range. Valid range is 1-{len(options)}.")
                selections.append(options[idx - 1])
        except ValueError as exc:
            console.print(f"[red]{exc}")
            continue
        return selections


def _render_base_summary(console, base_index: int, dataset: CraftingDataset) -> None:
    from rich.panel import Panel
    from rich.text import Text

    base = dataset.bases[base_index]
    tips_text = (
        "\n".join(f"• {tip}" for tip in base.craft_tips)
        if base.craft_tips
        else "• Clean sockets and reach 20% quality before advanced steps."
    )
    notes = base.notes or ""
    body = Text()
    body.append(f"Class: {base.item_class}\n", style="light_goldenrod2")
    body.append(f"Tags: {', '.join(base.tags)}\n", style="grey70")
    if base.influence:
        body.append(f"Influence: {', '.join(base.influence)}\n", style="pale_turquoise1")
    if notes:
        body.append(f"Lore: {notes}\n", style="italic dark_orange")
    body.append("\nTips:\n", style="bold gold1")
    body.append(tips_text, style="white")
    console.print(Panel(body, title=f"{base.name}", border_style="gold3"))


def run_cli(*, source: str = "auto") -> None:
    _ensure_rich()

    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console()

    dataset = CraftingDataset(source=source)
    engine = CraftingEngine(dataset)

    _render_banner(console)
    if dataset.source == "sample":
        console.print(
            Panel(
                Text.from_markup(
                    "[bold red]Sample data loaded.[/] Run [italic]python tools/import_repoe.py --download[/] "
                    "or provide your own RePoE dump for the complete game database."
                ),
                border_style="red",
            )
        )

    base_index = _choose_base(console, dataset)
    _render_base_summary(console, base_index, dataset)
    base = dataset.bases[base_index]

    possible_prefixes = [
        affix.name for affix in dataset.compatible_affixes(base.item_class, tags=base.tags, affix_type="prefix")
    ]
    possible_suffixes = [
        affix.name for affix in dataset.compatible_affixes(base.item_class, tags=base.tags, affix_type="suffix")
    ]

    chosen_prefixes = _prompt_multi(console, possible_prefixes, "Desired Prefixes")
    chosen_suffixes = _prompt_multi(console, possible_suffixes, "Desired Suffixes")

    request = engine.build_request(base.name, chosen_prefixes, chosen_suffixes)
    plan = engine.generate_plan(request)

    console.rule("[bold gold1]Crafting Plan")
    for step_number, step in enumerate(plan, start=1):
        details = Text(step.details, style="white")
        panel = Panel(
            details,
            title=f"Step {step_number}: {step.title}",
            border_style="orange4",
        )
        console.print(panel)

    console.rule(style="dark_orange3")
    console.print(
        Text.from_markup(
            "[bold gold1]May your Exalted Orbs never brick![/] [italic dim]Press Enter to exit.[/]"
        )
    )
    _safe_input(console, "")


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    run_cli()
