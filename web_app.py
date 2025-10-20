"""Flask-powered web interface for the ExileCraft planner."""
from __future__ import annotations

import argparse
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template, request

from crafting_engine import CraftingEngine
from poe_data import Affix, AffixChance, BaseItem, CraftingDataset


def create_app(source: str = "auto") -> Flask:
    """Create and configure the Flask application."""

    dataset = CraftingDataset(source=source)
    engine = CraftingEngine(dataset)

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    base_lookup: Dict[str, BaseItem] = {
        str(index): base for index, base in enumerate(dataset.bases)
    }

    def _serialize_base(base_id: str, base: BaseItem) -> Dict[str, object]:
        return {
            "id": base_id,
            "name": base.name,
            "itemClass": base.item_class,
            "tags": base.tags,
            "influence": base.influence,
            "notes": base.notes,
            "craftTips": base.craft_tips,
        }

    def _serialize_affix(
        affix: Affix,
        *,
        base: Optional[BaseItem] = None,
    ) -> Dict[str, object]:
        chance: Optional[AffixChance] = None
        if base is not None:
            chance = dataset.affix_roll_statistics(base, affix)
        spawn_preview = [
            {"tag": tag, "weight": weight}
            for tag, weight in sorted(affix.spawn_weights, key=lambda item: item[0])[:8]
        ]
        return {
            "id": f"{affix.type}|{affix.name}",
            "name": affix.name,
            "type": affix.type,
            "level": affix.level,
            "itemClasses": affix.item_classes,
            "requiredTags": affix.required_tags,
            "methods": affix.methods,
            "notes": affix.notes,
            "statTexts": affix.stat_texts,
            "statRanges": affix.stat_ranges,
            "domain": affix.domain,
            "spawnWeights": spawn_preview,
            "chance": (
                {
                    "weight": chance.weight,
                    "totalWeight": chance.total_weight,
                    "chance": chance.chance,
                    "expectedRolls": chance.expected_rolls,
                }
                if chance
                else None
            ),
        }

    @app.get("/")
    def index() -> str:
        return render_template(
            "index.html",
            dataset_source=dataset.source,
        )

    @app.get("/api/meta")
    def meta() -> Dict[str, object]:
        return {
            "baseCount": len(dataset.bases),
            "affixCount": len(dataset.affixes),
            "source": dataset.source,
        }

    @app.get("/api/bases")
    def bases_endpoint():
        query = request.args.get("q", "").strip().lower()
        class_filter = request.args.get("class", "").strip().lower()
        results: List[Dict[str, object]] = []
        for base_id, base in base_lookup.items():
            name_lower = base.name.lower()
            class_lower = base.item_class.lower()
            if query and query not in name_lower and query not in class_lower:
                continue
            if class_filter and class_filter not in class_lower:
                continue
            results.append(_serialize_base(base_id, base))
        results.sort(key=lambda entry: (entry["itemClass"], entry["name"]))
        return jsonify(results)

    @app.get("/api/bases/<base_id>")
    def base_details(base_id: str):
        base = base_lookup.get(base_id)
        if base is None:
            return jsonify({"error": "Unknown base"}), 404
        return jsonify(_serialize_base(base_id, base))

    @app.get("/api/affixes")
    def affixes_endpoint():
        base_id = request.args.get("base_id")
        affix_type = request.args.get("type")
        search = request.args.get("search", "").strip()
        include_master = request.args.get("include_master", "0") == "1"
        compatible_only = request.args.get("compatible", "1" if base_id else "0") == "1"
        base = base_lookup.get(base_id) if base_id else None
        if base_id and base is None:
            return jsonify({"error": "Unknown base"}), 404

        if base is not None and compatible_only:
            affixes = dataset.compatible_affixes(
                base.item_class,
                tags=base.tags,
                affix_type=affix_type,
                include_master_crafts=include_master,
            )
        else:
            affixes = list(dataset.affixes)
            if affix_type:
                affixes = [
                    item
                    for item in affixes
                    if item.type.lower() == affix_type.lower()
                ]
            if not include_master:
                affixes = [item for item in affixes if item.domain != "crafted"]
        if search:
            query = search.lower()
            affixes = [
                item
                for item in affixes
                if query in item.name.lower()
                or any(query in text.lower() for text in item.stat_texts)
                or any(query in method.lower() for method in item.methods)
                or query in item.notes.lower()
            ]
        affixes.sort(key=lambda item: (item.type, item.level, item.name))
        return jsonify([
            _serialize_affix(item, base=base) for item in affixes
        ])

    @app.post("/api/plan")
    def plan_endpoint():
        payload = request.get_json(force=True, silent=True) or {}
        base_id = str(payload.get("base_id", ""))
        base = base_lookup.get(base_id)
        if base is None:
            return jsonify({"error": "Select a base before generating a plan."}), 400
        prefixes = payload.get("prefixes", []) or []
        suffixes = payload.get("suffixes", []) or []
        try:
            request_obj = engine.build_request(base.name, prefixes, suffixes)
            plan = engine.generate_plan(request_obj)
        except ValueError as exc:  # dataset missing entries
            return jsonify({"error": str(exc)}), 400
        return jsonify(
            {
                "base": base.name,
                "steps": [
                    {"title": step.title, "details": step.details} for step in plan
                ],
            }
        )

    return app


def _parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000).",
    )
    parser.add_argument(
        "--data-source",
        choices=["auto", "repoe", "sample"],
        default="auto",
        help="Data source to load (auto attempts RePoE then sample).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = _parse_args(argv)
    app = create_app(source=args.data_source)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
