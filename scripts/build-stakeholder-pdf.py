#!/usr/bin/env python3
"""Generate stakeholder-level executive PDF documentation from a JSON specification.

Features:
- Formalized `context_profile`:
  - `work`: Sopra Steria Group brand color palette (`#4B1E52` Deep Plum, `#CF022B` Crimson Red,
    `#EF7D00` Warm Coral, `#1E232A` Executive Slate, `#F5F5F7` Light Warm Grey) and corporate
    header/footer metadata (`Sopra Steria Group S.p.A.`, `client`, `audience`, `confidentiality`).
  - `personal`: Project-adaptive color palette (`ocean-slate`, `emerald-forest`, `indigo-modern`,
    `amber-editorial`, or `custom` hex colors) and personal/open-source metadata.
- Executive consulting typography: classic serif body text (`/Times-Roman` & `/Times-Bold`)
  paired with sans-serif headings, tables, and diagram labels (`/Helvetica` & `/Helvetica-Bold`)
  using Adobe AFM character width metrics.
- 100% native HD vector diagrams (Work Hierarchy tree and PERT/CPM Critical Path).
- Mandatory zero-ASE-footprint verification via `verify-external-clean.py` before saving.

Usage:
  python3 scripts/build-stakeholder-pdf.py --spec path/to/spec.json --output path/to/out.pdf
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

PAGE_W = 595.28  # A4 width in pt
PAGE_H = 841.89  # A4 height in pt
MARGIN_L = 36.0
MARGIN_R = 36.0
MARGIN_T = 40.0
MARGIN_B = 40.0
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

VALID_DOC_TYPES = {"project-plan", "as-is-report", "architecture-dossier", "release-report"}

PALETTES: dict[str, dict[str, str]] = {
    "sopra-steria": {
        "primary": "#4B1E52",       # Sopra Steria Deep Plum
        "accent": "#CF022B",        # Sopra Steria Crimson Red
        "secondary": "#EF7D00",     # Sopra Steria Warm Coral Orange
        "dark_neutral": "#1E232A",  # Executive Slate
        "light_surface": "#F5F5F7", # Warm Light Grey
    },
    "ocean-slate": {
        "primary": "#143366",
        "accent": "#D97706",
        "secondary": "#2563EB",
        "dark_neutral": "#1C2026",
        "light_surface": "#F3F6FA",
    },
    "emerald-forest": {
        "primary": "#064E3B",
        "accent": "#10B981",
        "secondary": "#0D9488",
        "dark_neutral": "#18221F",
        "light_surface": "#F2F9F6",
    },
    "indigo-modern": {
        "primary": "#1E1B4B",
        "accent": "#6366F1",
        "secondary": "#8B5CF6",
        "dark_neutral": "#181824",
        "light_surface": "#F5F5FA",
    },
    "amber-editorial": {
        "primary": "#27272A",
        "accent": "#D97706",
        "secondary": "#EA580C",
        "dark_neutral": "#18181B",
        "light_surface": "#FAF8F5",
    },
}

TIMES_ROMAN_W = {
    " ": 250, "!": 333, '"': 408, "#": 500, "$": 500, "%": 833, "&": 778, "'": 333,
    "(": 333, ")": 333, "*": 500, "+": 564, ",": 250, "-": 333, ".": 250, "/": 278,
    "0": 500, "1": 500, "2": 500, "3": 500, "4": 500, "5": 500, "6": 500, "7": 500,
    "8": 500, "9": 500, ":": 278, ";": 278, "<": 564, "=": 564, ">": 564, "?": 444,
    "@": 921, "A": 722, "B": 667, "C": 667, "D": 722, "E": 611, "F": 556, "G": 722,
    "H": 722, "I": 333, "J": 389, "K": 722, "L": 611, "M": 889, "N": 722, "O": 722,
    "P": 556, "Q": 722, "R": 667, "S": 556, "T": 611, "U": 722, "V": 722, "W": 944,
    "X": 722, "Y": 722, "Z": 611, "[": 333, "\\": 278, "]": 333, "^": 469, "_": 500,
    "`": 333, "a": 444, "b": 500, "c": 444, "d": 500, "e": 444, "f": 333, "g": 500,
    "h": 500, "i": 278, "j": 278, "k": 500, "l": 278, "m": 778, "n": 500, "o": 500,
    "p": 500, "q": 500, "r": 333, "s": 389, "t": 278, "u": 500, "v": 500, "w": 722,
    "x": 500, "y": 500, "z": 444, "{": 480, "|": 200, "}": 480, "~": 541,
}

TIMES_BOLD_W = {
    " ": 250, "!": 333, '"': 555, "#": 500, "$": 500, "%": 1000, "&": 833, "'": 333,
    "(": 333, ")": 333, "*": 500, "+": 570, ",": 250, "-": 333, ".": 250, "/": 278,
    "0": 500, "1": 500, "2": 500, "3": 500, "4": 500, "5": 500, "6": 500, "7": 500,
    "8": 500, "9": 500, ":": 333, ";": 333, "<": 570, "=": 570, ">": 570, "?": 500,
    "@": 930, "A": 722, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 778, "I": 389, "J": 500, "K": 778, "L": 667, "M": 944, "N": 722, "O": 778,
    "P": 611, "Q": 778, "R": 722, "S": 556, "T": 667, "U": 722, "V": 722, "W": 1000,
    "X": 722, "Y": 722, "Z": 667, "[": 333, "\\": 278, "]": 333, "^": 581, "_": 500,
    "`": 333, "a": 500, "b": 556, "c": 444, "d": 556, "e": 444, "f": 333, "g": 500,
    "h": 556, "i": 278, "j": 333, "k": 556, "l": 278, "m": 833, "n": 556, "o": 500,
    "p": 556, "q": 556, "r": 444, "s": 389, "t": 333, "u": 556, "v": 500, "w": 722,
    "x": 500, "y": 500, "z": 444, "{": 394, "|": 220, "}": 394, "~": 520,
}

HELV_REG_W = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 222,
    "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556, "7": 556,
    "8": 556, "9": 556, ":": 278, ";": 278, "<": 584, "=": 584, ">": 584, "?": 556,
    "@": 1015, "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778,
    "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556,
    "`": 222, "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556,
    "h": 556, "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556, "o": 556,
    "p": 556, "q": 556, "r": 333, "s": 500, "t": 278, "u": 556, "v": 500, "w": 722,
    "x": 500, "y": 500, "z": 500, "{": 334, "|": 260, "}": 334, "~": 584,
}

HELV_BOLD_W = {
    " ": 278, "!": 333, '"': 474, "#": 556, "$": 556, "%": 889, "&": 722, "'": 278,
    "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556, "7": 556,
    "8": 556, "9": 556, ":": 333, ";": 333, "<": 584, "=": 584, ">": 584, "?": 611,
    "@": 975, "A": 722, "B": 722, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 556, "K": 722, "L": 611, "M": 833, "N": 722, "O": 778,
    "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944,
    "X": 667, "Y": 667, "Z": 611, "[": 333, "\\": 278, "]": 333, "^": 584, "_": 556,
    "`": 278, "a": 556, "b": 611, "c": 556, "d": 611, "e": 556, "f": 333, "g": 611,
    "h": 611, "i": 278, "j": 278, "k": 556, "l": 278, "m": 889, "n": 611, "o": 611,
    "p": 611, "q": 611, "r": 389, "s": 556, "t": 333, "u": 611, "v": 556, "w": 778,
    "x": 556, "y": 556, "z": 500, "{": 389, "|": 280, "}": 389, "~": 584,
}


def hex_to_rgb_cmd(hex_str: str, stroke: bool = False) -> str:
    h = hex_str.strip().lstrip("#")
    if len(h) != 6:
        h = "1E232A"
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    op = "RG" if stroke else "rg"
    return f"{r:.3f} {g:.3f} {b:.3f} {op}"


def normalize_cp1252(text: str) -> str:
    replacements = {
        "\u2192": "->",
        "\u2194": "<->",
        "\u00a0": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def pdf_escape(text: str) -> str:
    norm = normalize_cp1252(text)
    return norm.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def measure_text_pt(text: str, font_size: float, bold: bool = False, sans: bool = False) -> float:
    table = (
        (HELV_BOLD_W if bold else HELV_REG_W)
        if sans
        else (TIMES_BOLD_W if bold else TIMES_ROMAN_W)
    )
    norm = normalize_cp1252(text)
    total = 0
    for ch in norm:
        if ch in table:
            total += table[ch]
        elif ch in ("\u2014", "\u2013"):
            total += 750 if ch == "\u2014" else 500
        else:
            total += 520
    return (total / 1000.0) * font_size


def wrap_text(text: str, max_width: float, font_size: float, bold: bool = False, sans: bool = False) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            if measure_text_pt(candidate, font_size, bold, sans) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def resolve_metadata_and_palette(meta: dict) -> tuple[dict, dict[str, str], list[str]]:
    errors: list[str] = []
    profile = meta.get("context_profile", "work")
    if profile not in ("work", "personal"):
        errors.append("metadata.context_profile must be 'work' or 'personal'")
        profile = "work"

    doc_type = meta.get("doc_type", "project-plan")
    if doc_type not in VALID_DOC_TYPES:
        errors.append(f"metadata.doc_type must be one of {sorted(VALID_DOC_TYPES)}")

    common_required = ("title", "subtitle", "project", "author", "version", "date")
    for field in common_required:
        if not isinstance(meta.get(field), str) or not meta[field].strip():
            errors.append(f"metadata.{field} is required")

    resolved = dict(meta)
    resolved["context_profile"] = profile
    resolved["doc_type"] = doc_type

    if profile == "work":
        # Work mode always uses Sopra Steria Group palette and corporate metadata defaults
        resolved.setdefault("organization", "Sopra Steria Group S.p.A.")
        resolved.setdefault("confidentiality", "Confidential — Client & Internal")
        for work_field in ("client", "audience"):
            if not isinstance(resolved.get(work_field), str) or not resolved[work_field].strip():
                errors.append(f"metadata.{work_field} is required when context_profile is 'work'")
        palette = dict(PALETTES["sopra-steria"])
        resolved["palette"] = "sopra-steria"
    else:
        resolved.setdefault("confidentiality", "Personal Project")
        palette_name = resolved.get("palette", "ocean-slate")
        if palette_name == "custom":
            custom = resolved.get("custom_colors", {})
            base = dict(PALETTES["ocean-slate"])
            for k in base:
                if isinstance(custom.get(k), str) and custom[k].strip():
                    base[k] = custom[k].strip()
            palette = base
        elif palette_name in PALETTES:
            palette = dict(PALETTES[palette_name])
        else:
            errors.append(f"metadata.palette '{palette_name}' is unknown")
            palette = dict(PALETTES["ocean-slate"])

    return resolved, palette, errors


class StakeholderPDFCanvas:
    def __init__(self, metadata: dict, palette: dict[str, str]) -> None:
        self.meta = metadata
        self.palette = palette
        self.pages: list[list[str]] = []
        self.y = PAGE_H - MARGIN_T
        self.new_page()

    def cmd(self, s: str) -> None:
        self.pages[-1].append(s)

    def new_page(self) -> None:
        if self.pages:
            self._draw_footer(len(self.pages))
        self.pages.append([])
        self.y = PAGE_H - MARGIN_T
        self._draw_header_strip()

    def _draw_header_strip(self) -> None:
        if len(self.pages) > 1:
            self.cmd(hex_to_rgb_cmd(self.palette["accent"]))
            self.cmd(f"{MARGIN_L:.1f} {PAGE_H - 29:.1f} {CONTENT_W:.1f} 0.9 re f")
            self.cmd("0.32 0.37 0.45 rg")
            if self.meta["context_profile"] == "work":
                hdr = (
                    f"{self.meta['client']} — {self.meta['project']} | "
                    f"{self.meta['title']} | Prepared for {self.meta['audience']}"
                )
            else:
                hdr = f"{self.meta['project']} — {self.meta['title']} | {self.meta['subtitle']} (v{self.meta['version']})"
            self.text(MARGIN_L, PAGE_H - 23, hdr, size=8.0, bold=False, sans=True)
            self.y = PAGE_H - MARGIN_T - 6

    def _draw_footer(self, page_num: int) -> None:
        self.cmd("0.84 0.87 0.92 rg")
        self.cmd(f"{MARGIN_L:.1f} {MARGIN_B - 10:.1f} {CONTENT_W:.1f} 0.6 re f")
        self.cmd("0.36 0.40 0.46 rg")
        if self.meta["context_profile"] == "work":
            left_txt = (
                f"{self.meta['organization']} — {self.meta['confidentiality']} ({self.meta['date']})"
            )
        else:
            repo_suffix = f" | {self.meta['repository_or_url']}" if self.meta.get("repository_or_url") else ""
            left_txt = (
                f"{self.meta['project']} — {self.meta['author']} "
                f"({self.meta['confidentiality']}, {self.meta['date']}){repo_suffix}"
            )
        self.text(MARGIN_L, MARGIN_B - 22, left_txt, size=8.0, sans=True)
        self.text(PAGE_W - MARGIN_R - 42, MARGIN_B - 22, f"Page {page_num}", size=8.0, bold=True, sans=True)

    def ensure_space(self, needed_h: float) -> None:
        if self.y - needed_h < MARGIN_B + 8:
            self.new_page()

    def text(self, x: float, y: float, txt: str, size: float = 10.0, bold: bool = False, sans: bool = False) -> None:
        font = ("/F4" if bold else "/F3") if sans else ("/F2" if bold else "/F1")
        self.cmd(f"BT {font} {size:.2f} Tf {x:.2f} {y:.2f} Td ({pdf_escape(txt)}) Tj ET")

    def text_centered(self, cx: float, y: float, txt: str, size: float = 8.0, bold: bool = False, sans: bool = True) -> None:
        w = measure_text_pt(txt, size, bold, sans)
        self.text(cx - w / 2.0, y, txt, size=size, bold=bold, sans=sans)

    def draw_banner(self) -> None:
        h = 70.0
        self.ensure_space(h + 12)
        top = self.y
        self.cmd(hex_to_rgb_cmd(self.palette["primary"]))
        self.cmd(f"{MARGIN_L:.1f} {top - h:.1f} {CONTENT_W:.1f} {h:.1f} re f")
        self.cmd(hex_to_rgb_cmd(self.palette["accent"]))
        self.cmd(f"{MARGIN_L:.1f} {top - h:.1f} 6.0 {h:.1f} re f")
        self.cmd("1 1 1 rg")
        self.text(MARGIN_L + 16, top - 23, self.meta["title"], size=13.5, bold=True, sans=True)
        self.cmd("0.92 0.94 0.98 rg")
        self.text(MARGIN_L + 16, top - 41, self.meta["subtitle"], size=9.8, bold=False, sans=True)
        if self.meta["context_profile"] == "work":
            meta_line = (
                f"Organization: {self.meta['organization']} | Client: {self.meta['client']} | "
                f"Prepared for: {self.meta['audience']} | v{self.meta['version']} ({self.meta['date']})"
            )
        else:
            meta_line = (
                f"Project: {self.meta['project']} | Author: {self.meta['author']} | "
                f"v{self.meta['version']} ({self.meta['date']})"
            )
        self.cmd("0.82 0.87 0.94 rg")
        self.text(MARGIN_L + 16, top - 57, meta_line, size=8.2, bold=False, sans=True)
        self.y = top - h - 14

    def section_heading(self, title: str) -> None:
        self.ensure_space(32)
        self.y -= 5
        self.cmd(hex_to_rgb_cmd(self.palette["primary"]))
        self.cmd(f"{MARGIN_L:.1f} {self.y - 19:.1f} {CONTENT_W:.1f} 21.0 re f")
        self.cmd(hex_to_rgb_cmd(self.palette["accent"]))
        self.cmd(f"{MARGIN_L:.1f} {self.y - 19:.1f} 4.0 21.0 re f")
        self.cmd("1 1 1 rg")
        self.text(MARGIN_L + 10, self.y - 13.5, title, size=10.5, bold=True, sans=True)
        self.y -= 26

    def paragraph(self, txt: str, size: float = 10.2, bold: bool = False, indent: float = 0.0) -> None:
        lines = wrap_text(txt, CONTENT_W - indent, size, bold, sans=False)
        line_h = size * 1.38
        self.ensure_space(len(lines) * line_h + 6)
        self.cmd("0.10 0.12 0.16 rg")
        for line in lines:
            self.text(MARGIN_L + indent, self.y - size, line, size=size, bold=bold, sans=False)
            self.y -= line_h
        self.y -= 4

    def bullets(self, items: list[str], size: float = 10.0) -> None:
        for item in items:
            lines = wrap_text(item, CONTENT_W - 18.0, size, bold=False, sans=False)
            line_h = size * 1.35
            self.ensure_space(len(lines) * line_h + 4)
            self.cmd(hex_to_rgb_cmd(self.palette["accent"]))
            self.text(MARGIN_L + 4, self.y - size, "-", size=size, bold=True, sans=True)
            self.cmd("0.10 0.12 0.16 rg")
            for idx, line in enumerate(lines):
                self.text(MARGIN_L + 16, self.y - size, line, size=size, bold=(idx == 0 and ":" in line[:18]), sans=False)
                self.y -= line_h
            self.y -= 2

    def draw_table(self, table_spec: dict) -> None:
        headers: list[str] = table_spec.get("headers", [])
        rows: list[list[str]] = table_spec.get("rows", [])
        if not headers:
            return
        n_cols = len(headers)
        raw_widths = table_spec.get("col_widths") or [1.0 / n_cols] * n_cols
        col_w = [w * CONTENT_W for w in raw_widths]
        hdr_h = 20.0
        self.ensure_space(hdr_h + 24)
        self.cmd(hex_to_rgb_cmd(self.palette["dark_neutral"]))
        self.cmd(f"{MARGIN_L:.1f} {self.y - hdr_h:.1f} {CONTENT_W:.1f} {hdr_h:.1f} re f")
        self.cmd("1 1 1 rg")
        cx = MARGIN_L
        for i, h_txt in enumerate(headers):
            self.text(cx + 5, self.y - 13.5, h_txt, size=8.5, bold=True, sans=True)
            cx += col_w[i]
        self.y -= hdr_h

        for r_idx, row in enumerate(rows):
            wrapped_cols = [
                wrap_text(str(row[c]) if c < len(row) else "", col_w[c] - 10, 8.8, sans=False)
                for c in range(n_cols)
            ]
            max_lines = max(len(wc) for wc in wrapped_cols) if wrapped_cols else 1
            row_h = max(18.0, max_lines * 11.5 + 6.0)
            self.ensure_space(row_h + 4)
            if r_idx % 2 == 1:
                self.cmd(hex_to_rgb_cmd(self.palette["light_surface"]))
                self.cmd(f"{MARGIN_L:.1f} {self.y - row_h:.1f} {CONTENT_W:.1f} {row_h:.1f} re f")
            self.cmd("0.82 0.85 0.90 RG 0.4 w")
            self.cmd(f"{MARGIN_L:.1f} {self.y - row_h:.1f} {CONTENT_W:.1f} {row_h:.1f} re S")
            self.cmd("0.12 0.14 0.18 rg")
            cx = MARGIN_L
            for c_idx, lines in enumerate(wrapped_cols):
                ly = self.y - 11.0
                for line in lines:
                    self.text(cx + 5, ly, line, size=8.8, bold=(c_idx == 0), sans=(c_idx == 0))
                    ly -= 11.2
                cx += col_w[c_idx]
            self.y -= row_h
        self.y -= 8

    def _draw_arrow_down(self, x: float, y_top: float, y_bot: float) -> None:
        self.cmd(f"{x:.2f} {y_top:.2f} m {x:.2f} {y_bot + 3.5:.2f} l S")
        self.cmd(
            f"{x:.2f} {y_bot:.2f} m {x - 2.8:.2f} {y_bot + 4.5:.2f} l "
            f"{x + 2.8:.2f} {y_bot + 4.5:.2f} l h f"
        )

    def _draw_arrow_right(self, x_left: float, x_right: float, y: float) -> None:
        self.cmd(f"{x_left:.2f} {y:.2f} m {x_right - 4.0:.2f} {y:.2f} l S")
        self.cmd(
            f"{x_right:.2f} {y:.2f} m {x_right - 4.8:.2f} {y + 2.8:.2f} l "
            f"{x_right - 4.8:.2f} {y - 2.8:.2f} l h f"
        )

    def draw_hierarchy_diagram(self, spec: dict) -> None:
        diag_h = 165.0
        self.ensure_space(diag_h + 26)
        caption = spec.get("caption", "Figure 1: Proposed Work Hierarchy")
        self.cmd(hex_to_rgb_cmd(self.palette["primary"]))
        self.text(MARGIN_L, self.y - 10, caption, size=9.5, bold=True, sans=True)
        self.y -= 16

        top = self.y
        bot = top - diag_h
        self.cmd(hex_to_rgb_cmd(self.palette["dark_neutral"]))
        self.cmd(f"{MARGIN_L:.2f} {bot:.2f} {CONTENT_W:.2f} {diag_h:.2f} re f")

        def draw_node(cx: float, cy: float, w: float, h: float, l1: str, l2: str, primary: bool = True) -> None:
            x0, y0 = cx - w / 2.0, cy - h / 2.0
            fill_hex = self.palette["primary"] if primary else "#282C34"
            stroke_hex = self.palette["accent"] if primary else self.palette["secondary"]
            self.cmd(hex_to_rgb_cmd(fill_hex))
            self.cmd(f"{hex_to_rgb_cmd(stroke_hex, stroke=True)} 1.0 w")
            self.cmd(f"{x0:.2f} {y0:.2f} {w:.2f} {h:.2f} re B")
            self.cmd("1 1 1 rg")
            self.text_centered(cx, cy + 3.5, l1, size=7.4, bold=True, sans=True)
            self.cmd("0.86 0.90 0.96 rg")
            self.text_centered(cx, cy - 8.0, l2, size=6.6, bold=False, sans=True)

        root = spec.get("root", {"title": "W-01: Foundation", "subtitle": "Baseline"})
        waves = spec.get("waves", [])[:2]
        features = spec.get("features", [])[:3]

        node_h = 30.0
        r1_y = top - 25.0
        root_cx = MARGIN_L + CONTENT_W / 2.0
        draw_node(root_cx, r1_y, 210.0, node_h, root.get("title", ""), root.get("subtitle", ""), primary=True)

        r2_y = top - 80.0
        if waves:
            xs = [MARGIN_L + CONTENT_W * 0.28, MARGIN_L + CONTENT_W * 0.72] if len(waves) > 1 else [root_cx]
            self.cmd("0.75 0.80 0.88 RG 0.75 0.80 0.88 rg 0.9 w")
            mid_y = (r1_y - node_h / 2.0 + r2_y + node_h / 2.0) / 2.0
            self.cmd(f"{root_cx:.2f} {r1_y - node_h / 2.0:.2f} m {root_cx:.2f} {mid_y:.2f} l S")
            if len(xs) > 1:
                self.cmd(f"{xs[0]:.2f} {mid_y:.2f} m {xs[-1]:.2f} {mid_y:.2f} l S")
            for idx, w_node in enumerate(waves):
                self._draw_arrow_down(xs[idx], mid_y, r2_y + node_h / 2.0)
                draw_node(xs[idx], r2_y, 195.0, node_h, w_node.get("title", ""), w_node.get("subtitle", ""), primary=True)

        r3_y = top - 135.0
        if features:
            n_f = len(features)
            step = CONTENT_W / (n_f + 1)
            for idx, f_node in enumerate(features):
                fx = MARGIN_L + step * (idx + 1)
                self.cmd("0.75 0.80 0.88 RG 0.75 0.80 0.88 rg 0.8 w")
                self._draw_arrow_down(fx, r2_y - node_h / 2.0, r3_y + node_h / 2.0)
                draw_node(fx, r3_y, 155.0, node_h, f_node.get("title", ""), f_node.get("subtitle", ""), primary=False)

        self.y = bot - 12.0

    def draw_critical_path_diagram(self, spec: dict) -> None:
        diag_h = 115.0
        self.ensure_space(diag_h + 26)
        caption = spec.get("caption", "Figure 2: Critical Path (PERT/CPM)")
        self.cmd(hex_to_rgb_cmd(self.palette["primary"]))
        self.text(MARGIN_L, self.y - 10, caption, size=9.5, bold=True, sans=True)
        self.y -= 16

        top = self.y
        bot = top - diag_h
        self.cmd(hex_to_rgb_cmd(self.palette["dark_neutral"]))
        self.cmd(f"{MARGIN_L:.2f} {bot:.2f} {CONTENT_W:.2f} {diag_h:.2f} re f")

        track = spec.get("primary_track", [])[:4]
        if track:
            box_w = 106.0
            box_h = 32.0
            gap = (CONTENT_W - 28.0 - len(track) * box_w) / max(1, len(track) - 1)
            cy = top - 34.0
            for i, node in enumerate(track):
                x0 = MARGIN_L + 14.0 + i * (box_w + gap)
                cx = x0 + box_w / 2.0
                self.cmd(hex_to_rgb_cmd(self.palette["primary"]))
                self.cmd(f"{hex_to_rgb_cmd(self.palette['accent'], stroke=True)} 1.1 w")
                self.cmd(f"{x0:.2f} {cy - box_h / 2.0:.2f} {box_w:.2f} {box_h:.2f} re B")
                self.cmd("1 1 1 rg")
                self.text_centered(cx, cy + 4.0, f"{node.get('code', '')}: {node.get('title', '')}", size=6.8, bold=True)
                self.cmd("0.92 0.85 0.88 rg")
                self.text_centered(cx, cy - 7.5, node.get("duration", ""), size=6.4, bold=False)
                if i < len(track) - 1:
                    self.cmd(f"{hex_to_rgb_cmd(self.palette['accent'], stroke=True)} {hex_to_rgb_cmd(self.palette['accent'])} 1.1 w")
                    self._draw_arrow_right(x0 + box_w, x0 + box_w + gap, cy)

        parallel = spec.get("parallel_track")
        if isinstance(parallel, dict):
            p_cy = top - 84.0
            pw = CONTENT_W - 140.0
            px0 = MARGIN_L + 70.0
            self.cmd("#282C34")
            self.cmd("0.18 0.20 0.25 rg")
            self.cmd(f"{hex_to_rgb_cmd(self.palette['secondary'], stroke=True)} 0.9 w")
            self.cmd(f"{px0:.2f} {p_cy - 13.0:.2f} {pw:.2f} 26.0 re B")
            self.cmd("0.95 0.96 0.98 rg")
            label = f"{parallel.get('code', '')}: {parallel.get('title', '')} — {parallel.get('duration', '')}"
            self.text_centered(px0 + pw / 2.0, p_cy - 3.0, label, size=7.0, bold=True)

        self.y = bot - 12.0

    def to_pdf_bytes(self) -> bytes:
        if self.pages:
            self._draw_footer(len(self.pages))

        objects: list[bytes] = []

        def add_obj(data: bytes) -> int:
            objects.append(data)
            return len(objects)

        font_f1 = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>")
        font_f2 = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>")
        font_f3 = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        font_f4 = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

        pages_id_placeholder = add_obj(b"")
        page_ids: list[int] = []

        for page_cmds in self.pages:
            stream_bytes = "\n".join(page_cmds).encode("cp1252", errors="replace")
            content_id = add_obj(
                f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
                + stream_bytes
                + b"\nendstream"
            )
            page_dict = (
                f"<< /Type /Page /Parent {pages_id_placeholder} 0 R "
                f"/MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
                f"/Resources << /Font << /F1 {font_f1} 0 R /F2 {font_f2} 0 R /F3 {font_f3} 0 R /F4 {font_f4} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
            page_ids.append(add_obj(page_dict))

        kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects[pages_id_placeholder - 1] = (
            f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>".encode("ascii")
        )

        info_dict = (
            f"<< /Title ({pdf_escape(self.meta['title'])}) "
            f"/Author ({pdf_escape(self.meta['author'])}) "
            f"/Subject ({pdf_escape(self.meta['subtitle'])}) "
            f"/Creator ({pdf_escape(self.meta.get('organization', self.meta['project']))}) >>"
        ).encode("cp1252", errors="replace")
        info_id = add_obj(info_dict)
        catalog_id = add_obj(f"<< /Type /Catalog /Pages {pages_id_placeholder} 0 R >>".encode("ascii"))

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: list[int] = [0]
        for idx, obj_bytes in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{idx} 0 obj\n".encode("ascii"))
            out.extend(obj_bytes)
            out.extend(b"\nendobj\n")

        xref_pos = len(out)
        out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        out.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        out.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
        )
        return bytes(out)


def load_cleaner():
    cleaner_path = Path(__file__).resolve().parent / "verify-external-clean.py"
    spec = importlib.util.spec_from_file_location("verify_external_clean", cleaner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {cleaner_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_pdf_from_spec(spec_data: dict, output_path: Path) -> tuple[bool, list[str]]:
    meta_raw = spec_data.get("metadata", {})
    meta, palette, errors = resolve_metadata_and_palette(meta_raw)
    if errors:
        return False, errors

    canvas = StakeholderPDFCanvas(meta, palette)
    canvas.draw_banner()

    for section in spec_data.get("sections", []):
        heading = section.get("heading")
        if heading:
            canvas.section_heading(heading)
        for p in section.get("paragraphs", []):
            canvas.paragraph(p)
        if section.get("bullets"):
            canvas.bullets(section["bullets"])
        if section.get("hierarchy_diagram"):
            canvas.draw_hierarchy_diagram(section["hierarchy_diagram"])
        if section.get("critical_path_diagram"):
            canvas.draw_critical_path_diagram(section["critical_path_diagram"])
        if section.get("table"):
            canvas.draw_table(section["table"])

    pdf_bytes = canvas.to_pdf_bytes()
    cleaner = load_cleaner()
    extracted = cleaner.extract_pdf_text_segments(pdf_bytes)
    findings = cleaner.scan_text("\n".join(extracted), str(output_path))
    if findings:
        return False, findings

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    return True, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", required=True, type=Path, help="Path to stakeholder PDF JSON specification")
    parser.add_argument("--output", required=True, type=Path, help="Output PDF file path")
    args = parser.parse_args(argv)

    if not args.spec.is_file():
        print(f"error: specification file not found: {args.spec}", file=sys.stderr)
        return 1

    try:
        spec_data = json.loads(args.spec.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.spec}: {exc}", file=sys.stderr)
        return 1

    ok, errors = build_pdf_from_spec(spec_data, args.output)
    if not ok:
        for err in errors:
            print(err, file=sys.stderr)
        print("FAIL: stakeholder PDF generation aborted due to validation or ASE footprint errors.", file=sys.stderr)
        return 1

    profile = spec_data.get("metadata", {}).get("context_profile", "work")
    palette = "sopra-steria" if profile == "work" else spec_data.get("metadata", {}).get("palette", "ocean-slate")
    print(f"PASS: generated stakeholder PDF '{args.output}' (profile={profile}, palette={palette}, zero ASE references).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
