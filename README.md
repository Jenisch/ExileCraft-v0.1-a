# ExileCraft v0.1-a

This prototype provides an offline, data-driven helper that assembles step-by-step Path of Exile crafting plans from a small curated dataset. It is intentionally lightweight so that you can extend the JSON data or heuristics without contacting external services.

## Features

* Interactive CLI that lets you pick a base item and desired prefixes/suffixes and outputs a human-readable crafting walkthrough.
* Simple heuristics that prioritise deterministic crafting techniques (Harvest augments, Essences, bench crafts) before probabilistic options.
* Extensible local dataset (`data/affixes.json`) containing example bases and mods with notes and acquisition tips.

## Usage

```bash
python main.py
```

Follow the prompts to pick a base, then "check" your desired affixes by entering the numbers shown in the menu. The tool prints the suggested crafting sequence.

### Extending the dataset

Add more item bases or affixes by editing `data/affixes.json`. Every entry can list:

* `item_classes` and `required_tags` to gate mods to the appropriate bases.
* `methods` with short descriptions of the strategies you want surfaced in the plan.
* `craft_tips` on bases to recommend preparatory work.

After updating the JSON, rerun the CLI to immediately use the new data.

## Limitations

This repository ships with a very small handcrafted dataset and does not scrape Grinding Gear Games' databases. For authoritative or league-specific information, export the official data and mirror its structure locally before running the planner.
