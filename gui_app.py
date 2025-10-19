"""Tkinter-powered desktop interface for the ExileCraft planner."""
from __future__ import annotations

import textwrap
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import font as tkfont
from typing import Dict, List, Optional

from crafting_engine import CraftingEngine
from poe_data import Affix, BaseItem, CraftingDataset


class CraftingApp(tk.Tk):
    """A lightweight desktop UI for browsing data and generating plans."""

    def __init__(self, *, source: str = "auto") -> None:
        super().__init__()
        self.title("ExileCraft Planner")
        self.geometry("1280x800")
        self.minsize(1000, 700)
        self.configure(bg="#0b0908")
        self.palette = self._configure_theme()

        try:
            self.dataset = CraftingDataset(source=source)
        except FileNotFoundError as exc:
            messagebox.showerror("Data not found", str(exc))
            self.destroy()
            raise SystemExit(1) from exc

        self.engine = CraftingEngine(self.dataset)

        self.filtered_bases: List[BaseItem] = list(self.dataset.bases)
        self.current_affixes: List[Affix] = list(self.dataset.affixes)
        self.affix_rows: Dict[str, Affix] = {}
        self.selected_base: Optional[BaseItem] = None
        self.selected_prefixes: List[Affix] = []
        self.selected_suffixes: List[Affix] = []

        self._build_layout()
        self._populate_bases(self.filtered_bases)
        self._refresh_affixes()

        if self.dataset.source == "sample":
            self.sample_hint.configure(
                text=(
                    "Sample dataset loaded – import RePoE for the complete game data. "
                    "Run `python tools/import_repoe.py --download` to fetch it automatically."
                )
            )

    # ------------------------------------------------------------------ layout
    def _configure_theme(self) -> Dict[str, str]:
        palette = {
            "base": "#090707",
            "surface": "#16100f",
            "panel": "#211917",
            "border": "#3a2c21",
            "accent": "#d3a95c",
            "accent_dark": "#a3742c",
            "focus": "#2d1f17",
            "text": "#f1e7d0",
            "muted": "#9f8c6c",
        }

        heading_font = tkfont.Font(family="Georgia", size=22, weight="bold")
        section_font = tkfont.Font(family="Georgia", size=11, weight="bold")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("PoE.TFrame", background=palette["surface"], borderwidth=0)
        style.configure(
            "PoE.TLabelframe",
            background=palette["surface"],
            bordercolor=palette["border"],
            borderwidth=1,
            relief="groove",
            foreground=palette["accent"],
        )
        style.configure(
            "PoE.TLabelframe.Label",
            background=palette["surface"],
            foreground=palette["accent"],
            font=section_font,
        )
        style.configure(
            "PoE.Heading.TLabel",
            background=palette["base"],
            foreground=palette["accent"],
            font=heading_font,
        )
        style.configure(
            "PoE.Section.TLabel",
            background=palette["surface"],
            foreground=palette["accent"],
            font=section_font,
        )
        style.configure(
            "PoE.Subtle.TLabel",
            background=palette["surface"],
            foreground=palette["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "PoE.TButton",
            background=palette["panel"],
            foreground=palette["text"],
            padding=6,
        )
        style.map(
            "PoE.TButton",
            background=[("active", palette["accent"]), ("pressed", palette["accent_dark"])],
            foreground=[("active", palette["base"]), ("pressed", palette["base"])],
        )
        style.configure(
            "PoE.Treeview",
            background=palette["panel"],
            fieldbackground=palette["panel"],
            foreground=palette["text"],
            rowheight=24,
            bordercolor=palette["border"],
            borderwidth=1,
        )
        style.map(
            "PoE.Treeview",
            background=[("selected", palette["accent"])],
            foreground=[("selected", palette["base"])],
        )
        style.configure(
            "PoE.Treeview.Heading",
            background=palette["border"],
            foreground=palette["accent"],
            relief="flat",
            font=section_font,
        )
        style.map(
            "PoE.Treeview.Heading",
            background=[("active", palette["accent_dark"])],
            foreground=[("active", palette["base"])],
        )
        style.configure(
            "PoE.TCheckbutton",
            background=palette["surface"],
            foreground=palette["text"],
        )
        style.map(
            "PoE.TCheckbutton",
            background=[("active", palette["panel"])],
            foreground=[("active", palette["accent"])],
        )
        style.configure(
            "PoE.TEntry",
            fieldbackground=palette["panel"],
            background=palette["panel"],
            foreground=palette["text"],
            bordercolor=palette["border"],
            borderwidth=1,
        )
        style.map(
            "PoE.TEntry",
            fieldbackground=[("focus", palette["focus"])],
            foreground=[("disabled", palette["muted"])],
        )
        style.configure(
            "PoE.Vertical.TScrollbar",
            background=palette["panel"],
            troughcolor=palette["surface"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
        )
        style.configure(
            "PoE.Horizontal.TScrollbar",
            background=palette["panel"],
            troughcolor=palette["surface"],
            bordercolor=palette["border"],
            lightcolor=palette["border"],
            darkcolor=palette["border"],
        )

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=10)
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(family="Segoe UI", size=10)
        self.heading_font = heading_font
        self.section_font = section_font

        self.option_add("*Listbox.background", palette["panel"])
        self.option_add("*Listbox.foreground", palette["text"])
        self.option_add("*Listbox.selectBackground", palette["accent"])
        self.option_add("*Listbox.selectForeground", palette["base"])
        self.option_add("*TCombobox*Listbox*Background", palette["panel"])
        self.option_add("*TCombobox*Listbox*Foreground", palette["text"])

        return palette
    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="PoE.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.columnconfigure(1, weight=1)

        title = ttk.Label(header, text="ExileCraft Planner", style="PoE.Heading.TLabel")
        title.grid(row=0, column=0, sticky="w")

        self.sample_hint = ttk.Label(header, style="PoE.Subtle.TLabel", wraplength=760)
        self.sample_hint.grid(row=1, column=0, columnspan=3, sticky="we", pady=(6, 0))

        content = ttk.Frame(self, style="PoE.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.columnconfigure(2, weight=2)
        content.rowconfigure(0, weight=3)
        content.rowconfigure(1, weight=2)

        self._build_base_panel(content)
        self._build_selection_panel(content)
        self._build_affix_panel(content)
        self._build_plan_panel(content)

    def _build_base_panel(self, parent: ttk.Frame) -> None:
        base_panel = ttk.Labelframe(parent, text="Item Bases", style="PoE.TLabelframe")
        base_panel.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=6)
        base_panel.columnconfigure(0, weight=1)
        base_panel.rowconfigure(1, weight=1)

        self.base_filter_var = tk.StringVar()
        self.base_filter_var.trace_add("write", lambda *_: self._apply_base_filter())
        search = ttk.Entry(base_panel, textvariable=self.base_filter_var, style="PoE.TEntry")
        search.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        search.insert(0, "Search name, class:Claw, tag:caster, influence:shaper…")
        search.bind("<FocusIn>", lambda event: self._clear_placeholder(event, self.base_filter_var))

        self.base_list = tk.Listbox(
            base_panel,
            exportselection=False,
            bg=self.palette["panel"],
            fg=self.palette["text"],
            selectbackground=self.palette["accent"],
            selectforeground=self.palette["base"],
            highlightbackground=self.palette["border"],
            highlightcolor=self.palette["accent"],
            relief="flat",
            activestyle="none",
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.base_list.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.base_list.bind("<<ListboxSelect>>", self._on_base_select)

        scrollbar = ttk.Scrollbar(
            base_panel,
            orient="vertical",
            command=self.base_list.yview,
            style="PoE.Vertical.TScrollbar",
        )
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 6))
        self.base_list.configure(yscrollcommand=scrollbar.set)

        self.base_count = ttk.Label(base_panel, text="0 bases", style="PoE.Subtle.TLabel")
        self.base_count.grid(row=2, column=0, sticky="w", padx=6, pady=(0, 6))

    def _build_selection_panel(self, parent: ttk.Frame) -> None:
        selection_panel = ttk.Labelframe(parent, text="Details & Picks", style="PoE.TLabelframe")
        selection_panel.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        selection_panel.columnconfigure(0, weight=1)
        selection_panel.rowconfigure(0, weight=2)
        selection_panel.rowconfigure(1, weight=1)
        selection_panel.rowconfigure(2, weight=1)

        self.base_details = tk.Text(
            selection_panel,
            height=12,
            wrap="word",
            state="disabled",
            bg=self.palette["panel"],
            fg=self.palette["text"],
            relief="flat",
            highlightbackground=self.palette["border"],
            highlightcolor=self.palette["accent"],
            insertbackground=self.palette["text"],
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.base_details.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        picks = ttk.Frame(selection_panel, style="PoE.TFrame")
        picks.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        picks.columnconfigure(0, weight=1)
        picks.columnconfigure(1, weight=1)
        picks.rowconfigure(1, weight=1)

        ttk.Label(picks, text="Chosen Prefixes", style="PoE.Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(picks, text="Chosen Suffixes", style="PoE.Section.TLabel").grid(
            row=0, column=1, sticky="w"
        )

        self.prefix_list = tk.Listbox(
            picks,
            exportselection=False,
            bg=self.palette["panel"],
            fg=self.palette["text"],
            selectbackground=self.palette["accent"],
            selectforeground=self.palette["base"],
            highlightbackground=self.palette["border"],
            highlightcolor=self.palette["accent"],
            relief="flat",
            activestyle="none",
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.prefix_list.grid(row=1, column=0, sticky="nsew", padx=(0, 3))
        self.suffix_list = tk.Listbox(
            picks,
            exportselection=False,
            bg=self.palette["panel"],
            fg=self.palette["text"],
            selectbackground=self.palette["accent"],
            selectforeground=self.palette["base"],
            highlightbackground=self.palette["border"],
            highlightcolor=self.palette["accent"],
            relief="flat",
            activestyle="none",
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.suffix_list.grid(row=1, column=1, sticky="nsew", padx=(3, 0))

        button_row = ttk.Frame(selection_panel, style="PoE.TFrame")
        button_row.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        ttk.Button(
            button_row, text="Remove Prefix", command=self._remove_prefix, style="PoE.TButton"
        ).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(
            button_row, text="Remove Suffix", command=self._remove_suffix, style="PoE.TButton"
        ).grid(
            row=0, column=1, sticky="ew", padx=3
        )
        ttk.Button(
            button_row, text="Clear All", command=self._clear_selection, style="PoE.TButton"
        ).grid(
            row=0, column=2, sticky="ew", padx=(3, 0)
        )

    def _build_affix_panel(self, parent: ttk.Frame) -> None:
        affix_panel = ttk.Labelframe(parent, text="Affix Browser", style="PoE.TLabelframe")
        affix_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 12), pady=6)
        affix_panel.columnconfigure(0, weight=1)
        affix_panel.rowconfigure(2, weight=1)

        top_row = ttk.Frame(affix_panel, style="PoE.TFrame")
        top_row.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        top_row.columnconfigure(0, weight=1)

        self.affix_filter_var = tk.StringVar()
        self.affix_filter_var.trace_add("write", lambda *_: self._refresh_affixes())
        affix_search = ttk.Entry(top_row, textvariable=self.affix_filter_var, style="PoE.TEntry")
        affix_search.grid(row=0, column=0, sticky="ew")
        affix_search.insert(0, "Search affixes, add type:prefix or method:essence…")
        affix_search.bind("<FocusIn>", lambda event: self._clear_placeholder(event, self.affix_filter_var))

        self.compatible_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            top_row,
            text="Only show compatible",
            variable=self.compatible_only,
            command=self._refresh_affixes,
            style="PoE.TCheckbutton",
        ).grid(row=0, column=1, padx=(6, 0))

        columns = ("type", "level", "methods")
        self.affix_tree = ttk.Treeview(
            affix_panel,
            columns=columns,
            show="tree headings",
            selectmode="browse",
            style="PoE.Treeview",
        )
        self.affix_tree.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.affix_tree.heading("#0", text="Affix")
        self.affix_tree.heading("type", text="Type")
        self.affix_tree.heading("level", text="Level")
        self.affix_tree.heading("methods", text="Acquisition")
        self.affix_tree.column("#0", width=240)
        self.affix_tree.column("type", width=80, anchor="center")
        self.affix_tree.column("level", width=60, anchor="center")
        self.affix_tree.column("methods", width=320)
        self.affix_tree.bind("<<TreeviewSelect>>", self._show_affix_details)
        self.affix_tree.bind("<Double-1>", self._quick_add_affix)
        self.affix_tree.tag_configure("prefix", foreground=self.palette["accent"])
        self.affix_tree.tag_configure("suffix", foreground="#8fb8ff")

        affix_scroll = ttk.Scrollbar(
            affix_panel,
            orient="vertical",
            command=self.affix_tree.yview,
            style="PoE.Vertical.TScrollbar",
        )
        affix_scroll.grid(row=2, column=1, sticky="ns", pady=(0, 6))
        self.affix_tree.configure(yscrollcommand=affix_scroll.set)

        button_bar = ttk.Frame(affix_panel, style="PoE.TFrame")
        button_bar.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 6))
        button_bar.columnconfigure(0, weight=1)
        button_bar.columnconfigure(1, weight=1)

        ttk.Button(
            button_bar,
            text="Add as Prefix",
            command=lambda: self._add_affix("prefix"),
            style="PoE.TButton",
        ).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(
            button_bar,
            text="Add as Suffix",
            command=lambda: self._add_affix("suffix"),
            style="PoE.TButton",
        ).grid(
            row=0, column=1, sticky="ew", padx=(3, 0)
        )

        self.affix_details = tk.Text(
            affix_panel,
            height=6,
            wrap="word",
            state="disabled",
            bg=self.palette["panel"],
            fg=self.palette["text"],
            relief="flat",
            highlightbackground=self.palette["border"],
            highlightcolor=self.palette["accent"],
            insertbackground=self.palette["text"],
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.affix_details.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=6, pady=(0, 6))

    def _build_plan_panel(self, parent: ttk.Frame) -> None:
        plan_panel = ttk.Labelframe(parent, text="Crafting Plan", style="PoE.TLabelframe")
        plan_panel.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=12, pady=(0, 12))
        plan_panel.columnconfigure(0, weight=1)
        plan_panel.rowconfigure(0, weight=0)
        plan_panel.rowconfigure(1, weight=1)

        button = ttk.Button(
            plan_panel,
            text="Generate plan",
            command=self._generate_plan,
            style="PoE.TButton",
        )
        button.grid(row=0, column=0, sticky="ne", padx=6, pady=6)

        self.plan_output = tk.Text(
            plan_panel,
            wrap="word",
            state="disabled",
            bg=self.palette["panel"],
            fg=self.palette["text"],
            relief="flat",
            highlightbackground=self.palette["border"],
            highlightcolor=self.palette["accent"],
            insertbackground=self.palette["text"],
            font=("Segoe UI", 11),
            borderwidth=0,
        )
        self.plan_output.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

    # ------------------------------------------------------------------ helpers
    def _clear_placeholder(self, event, variable: tk.StringVar) -> None:
        if variable.get().startswith("Search"):
            event.widget.delete(0, tk.END)

    def _populate_bases(self, bases: List[BaseItem]) -> None:
        self.base_list.delete(0, tk.END)
        for base in bases:
            label = f"{base.name} ({base.item_class})"
            self.base_list.insert(tk.END, label)
        self.base_count.configure(text=f"{len(bases)} bases shown")

    def _apply_base_filter(self) -> None:
        query = self.base_filter_var.get().strip()
        if not query or query.lower().startswith("search"):
            results = list(self.dataset.bases)
        else:
            results = self._filter_bases(self.dataset.bases, query)
        self.filtered_bases = results
        self._populate_bases(results)

    @staticmethod
    def _filter_bases(bases: List[BaseItem], query: str) -> List[BaseItem]:
        q = query.lower()
        if q.startswith("class:"):
            token = q.split(":", 1)[1].strip()
            return [base for base in bases if token in base.item_class.lower()]
        if q.startswith("tag:"):
            token = q.split(":", 1)[1].strip()
            return [base for base in bases if any(token == tag.lower() for tag in base.tags)]
        if q.startswith("influence:"):
            token = q.split(":", 1)[1].strip()
            return [
                base
                for base in bases
                if any(token in influence.lower() for influence in base.influence)
            ]
        return [base for base in bases if q in base.name.lower() or q in base.item_class.lower()]

    def _on_base_select(self, event) -> None:
        selection = event.widget.curselection()
        if not selection:
            return
        base = self.filtered_bases[selection[0]]
        self.selected_base = base
        self._show_base_details(base)
        self._refresh_affixes()

    def _show_base_details(self, base: BaseItem) -> None:
        tips = base.craft_tips or ["Clean sockets and reach 20% quality before advanced steps."]
        lines = [
            f"Name: {base.name}",
            f"Class: {base.item_class}",
            f"Tags: {', '.join(base.tags) or 'None'}",
            f"Influence: {', '.join(base.influence) or 'None'}",
        ]
        if base.notes:
            wrapped = textwrap.fill(base.notes, width=70)
            lines.append("")
            lines.append("Lore:")
            lines.append(wrapped)
        lines.append("")
        lines.append("Tips:")
        for tip in tips:
            lines.append(f" • {tip}")
        self._set_text(self.base_details, "\n".join(lines))

    def _refresh_affixes(self) -> None:
        if self.compatible_only.get() and self.selected_base:
            affixes = self.dataset.compatible_affixes(
                self.selected_base.item_class, tags=self.selected_base.tags
            )
        else:
            affixes = list(self.dataset.affixes)

        query = self.affix_filter_var.get().strip().lower()
        if query and not query.startswith("search"):
            if query.startswith("type:"):
                token = query.split(":", 1)[1].strip()
                affixes = [affix for affix in affixes if token in affix.type.lower()]
            elif query.startswith("method:"):
                token = query.split(":", 1)[1].strip()
                affixes = [
                    affix
                    for affix in affixes
                    if any(token in method.lower() for method in affix.methods)
                ]
            else:
                affixes = [
                    affix
                    for affix in affixes
                    if query in affix.name.lower()
                    or query in " ".join(affix.methods).lower()
                    or query in affix.notes.lower()
                ]

        self.current_affixes = affixes
        self.affix_tree.delete(*self.affix_tree.get_children())
        self.affix_rows.clear()
        for affix in affixes:
            item_id = self.affix_tree.insert(
                "",
                "end",
                text=affix.name,
                values=(affix.type.title(), affix.level, ", ".join(affix.methods) or "Unknown"),
                tags=(affix.type.lower(),),
            )
            self.affix_rows[item_id] = affix

        self._set_text(self.affix_details, "Select an affix to see details.")

    def _show_affix_details(self, event) -> None:
        selection = event.widget.selection()
        if not selection:
            return
        affix = self.affix_rows.get(selection[0])
        if not affix:
            return
        lines = [
            f"Name: {affix.name}",
            f"Type: {affix.type.title()}",
            f"Required level: {affix.level}",
            f"Matches classes: {', '.join(affix.item_classes) or 'Any'}",
            f"Requires tags: {', '.join(affix.required_tags) or 'None'}",
            "",
            "Acquisition:",
        ]
        for method in affix.methods or ["Unknown"]:
            lines.append(f" • {method}")
        if affix.notes:
            lines.append("")
            lines.append("Notes:")
            lines.append(textwrap.fill(affix.notes, width=70))
        self._set_text(self.affix_details, "\n".join(lines))

    def _quick_add_affix(self, _event) -> None:
        selection = self.affix_tree.selection()
        if not selection:
            return
        affix = self.affix_rows.get(selection[0])
        if not affix:
            return
        target = "prefix" if affix.type.lower() == "prefix" else "suffix"
        self._add_affix(target)

    def _add_affix(self, slot: str) -> None:
        selection = self.affix_tree.selection()
        if not selection:
            messagebox.showinfo("Select affix", "Choose an affix from the list first.")
            return
        affix = self.affix_rows.get(selection[0])
        if not affix:
            return
        slot = slot.lower()
        if slot not in {"prefix", "suffix"}:
            return
        collection = self.selected_prefixes if slot == "prefix" else self.selected_suffixes
        listbox = self.prefix_list if slot == "prefix" else self.suffix_list
        if affix in collection:
            messagebox.showinfo("Already added", f"{affix.name} is already in your {slot} list.")
            return
        collection.append(affix)
        listbox.insert(tk.END, affix.name)

    def _remove_prefix(self) -> None:
        self._remove_selected(self.prefix_list, self.selected_prefixes)

    def _remove_suffix(self) -> None:
        self._remove_selected(self.suffix_list, self.selected_suffixes)

    def _remove_selected(self, widget: tk.Listbox, collection: List[Affix]) -> None:
        selection = list(widget.curselection())
        selection.reverse()
        for index in selection:
            widget.delete(index)
            del collection[index]

    def _clear_selection(self) -> None:
        self.selected_prefixes.clear()
        self.selected_suffixes.clear()
        self.prefix_list.delete(0, tk.END)
        self.suffix_list.delete(0, tk.END)

    def _generate_plan(self) -> None:
        if not self.selected_base:
            messagebox.showinfo("Select a base", "Pick a base item to craft before generating a plan.")
            return
        request = self.engine.build_request(
            self.selected_base.name,
            [affix.name for affix in self.selected_prefixes],
            [affix.name for affix in self.selected_suffixes],
        )
        plan = self.engine.generate_plan(request)

        lines = []
        for index, step in enumerate(plan, start=1):
            lines.append(f"Step {index}: {step.title}")
            lines.append(textwrap.fill(step.details, width=100))
            lines.append("")
        if not lines:
            lines.append("No plan generated. Try selecting additional modifiers.")

        self._set_text(self.plan_output, "\n".join(lines))

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.configure(state="disabled")


def run_app(*, source: str = "auto") -> None:
    app = CraftingApp(source=source)
    app.mainloop()


__all__ = ["run_app", "CraftingApp"]
