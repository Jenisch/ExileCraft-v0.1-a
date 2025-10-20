# ExileCraft v0.1-a

This prototype provides an offline, data-driven helper that assembles step-by-step Path of Exile crafting plans. It now supports importing the full [RePoE](https://github.com/brather1ng/RePoE) database so you can browse every base and affix, while still shipping with a lightweight sample dataset for quick experiments.

## Features

* Desktop interface built with Tkinter so you can browse bases, review affix requirements, and build a plan without memorising the entire database.
* Browser interface served by Flask that mirrors Craft of Exile's emulator layout with live search, compatible-mod toggles, spawn-weight odds, and instant plan generation.
* Affix browser that mirrors in-game availability by applying RePoE spawn weights, so the **Only show compatible** toggle now reflects the true mod pool for the selected base.
* Human-readable stat descriptions and alteration odds for every mod, translated from RePoE's stat data so you instantly understand what each affix does and how rare it is.
* A Path of Exile-inspired dark theme with gilded highlights to make the planner feel native to Wraeclast instead of a plain console utility.
* Rich-styled console interface (optional) that mimics the gilded Path of Exile aesthetic while guiding you through base and modifier selection.
* Interactive planner that now includes a progress tracker, currency recommendations, and real spawn-weight math instead of generic "spam Alterations" advice.
* Curated base list limited to armour, jewellery, and weapon/off-hand classes so you are not overwhelmed by quest items or crafting-irrelevant clutter.
* Optional integration with the full RePoE dataset for thousands of bases and mods.
* Extensible local JSON fallback (`data/affixes.json`) for custom notes or private league tweaks.

## Requirements

Install the Python dependencies once inside your environment:

```bash
# Windows (Command Prompt or PowerShell)
py -m pip install -r requirements.txt

# macOS / Linux
python3 -m pip install -r requirements.txt
```

If you see `'pip' is not recognized` on Windows, using `py -m pip ...` (or `python -m pip ...` if your Python executable is named `python`) ensures the installer bundled with Python is used even when its Scripts directory is not on `PATH`.

(If you're refreshing an existing checkout, rerun the command to ensure the themed interface dependencies are installed before launching the planner.)

(If you plan to download the RePoE archive through the helper script, ensure outbound HTTPS access is available.)

## Usage

1. **Get the files**
   * If you're comfortable with Git, clone the repository: `git clone https://github.com/<your-account>/ExileCraft-v0.1-a.git`.
   * Otherwise download the repository as a ZIP (on GitHub use **Code ▸ Download ZIP**) and extract it anywhere on your machine. This keeps the files together so you don't need to copy/paste each script.

2. **Populate crafting data**
   * For the complete game database, run:

     ```bash
     python tools/import_repoe.py --download
     ```

     The script downloads the latest RePoE snapshot and extracts the required JSON files (including stat translations for readable mod text) into `data/repoe/`.
   * Already have RePoE locally? Point the importer at the `data` folder:

     ```bash
     python tools/import_repoe.py --source /path/to/RePoE/data
     ```

     Add `--force` if you want to overwrite an existing import.
   * Skip this step to try the bundled sample data.

3. **Launch ExileCraft**
   * **Browser interface (emulator-style):**
     * Windows: double-click `run_web.bat` or run `py main.py --web`.
     * macOS/Linux: run `./run_web.sh` (make it executable once via `chmod +x run_web.sh`) or call `python3 main.py --web`.
     * Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. Use `--host`/`--port` if you need a different bind address.
   * **Graphical interface (Tkinter):**
     * Windows: double-click the packaged `dist/ExileCraft.exe` (see the next section to build it) or run `py main.py` from Command Prompt/PowerShell.
     * macOS/Linux: run `./run_app.sh` (add execute permission once with `chmod +x run_app.sh` if needed) or call `python3 main.py` directly.
   * **Console interface (optional):**
     * Windows: run `dist/ExileCraft.exe --cli` after building it, or `py main.py --cli`.
     * macOS/Linux: run `./run_cli.sh` or `python3 main.py --cli`.

4. **Build your item**
   * In the browser or desktop interface, pick a base from the left column to review its tags, influence, and crafting tips.
   * Browse compatible affixes (or toggle the checkbox to explore every mod). Each entry shows its stat text, spawn weighting snippet, and alteration odds, so you can compare options before committing. Click an affix to inspect it, then add it to your prefix/suffix wishlist and press **Generate plan**.
   * Generated plans now start with a checklist you can tick off in-game, followed by step-by-step instructions that call out deterministic crafting options, recommended currencies, and the actual 1-in-X odds for Alteration attempts.
   * Prefer the CLI? Follow the prompts to enter the numeric choices and receive the plan in stylised panels.

## Build a Windows executable

You can bundle the planner into a single-file `ExileCraft.exe` with PyInstaller:

```bash
# Install dependencies (once per clone)
py -m pip install -r requirements.txt

# From the repository root
py tools/build_exe.py --clean
```

The finished executable will land in `dist/ExileCraft.exe`. Double-click it to launch the Path of Exile styled interface without relying on `.bat` launchers. Re-run the command whenever you update the code or import fresh data.

### Extending the dataset

* When using RePoE data, edit `data/repoe/base_items.min.json` or `data/repoe/mods.min.json` after import to experiment with custom bases/mods.
* To ship personal adjustments, continue editing `data/affixes.json`; it remains the fallback when no RePoE data is present.

Every entry can list:

* `item_classes` and `required_tags` to gate mods to the appropriate bases.
* `methods` with short descriptions of the strategies you want surfaced in the plan.
* `craft_tips` on bases to recommend preparatory work.

After updating the JSON, rerun the CLI to immediately use the new data.

## Limitations

* The RePoE importer depends on the public GitHub mirror. If the structure changes or network access fails, point the script at a manually downloaded copy instead.
* The heuristic crafting engine remains intentionally simple; treat the plan as a starting point and adjust for league mechanics or niche interactions.
