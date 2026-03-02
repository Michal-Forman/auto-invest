#!/usr/bin/env python3
"""Run isort then add section header comments to import blocks."""

import re
import sys

import isort
from isort import Config, place

LABELS = {
    "FUTURE": "# Future",
    "STDLIB": "# Standard library",
    "THIRDPARTY": "# Third-party",
    "FIRSTPARTY": "# Local",
    "LOCALFOLDER": "# Local",
}


def get_top_module(line):
    """Extract the top-level module name from an import line, ignoring indented imports."""
    m = re.match(r"(?:from\s+([\w]+)|import\s+([\w]+))", line)
    return (m.group(1) or m.group(2)) if m else None


def sort_and_comment(path):
    # Remove existing section comments before isort so it doesn't duplicate them
    label_set = set(LABELS.values())
    with open(path) as f:
        raw_lines = f.readlines()
    with open(path, "w") as f:
        f.writelines(l for l in raw_lines if l.strip() not in label_set)

    config = Config(
        profile="black",
        force_sort_within_sections=True,
        known_third_party=["supabase"],
    )
    isort.file(path, config=config)

    with open(path) as f:
        lines = f.readlines()
    out = []
    in_import_block = False
    current_section = None
    deferred_blanks = []

    in_multiline = False

    for line in lines:
        mod = get_top_module(line)
        if mod:
            label = LABELS.get(place.module(mod, config=config))
            if label != current_section:
                # New section — flush blanks (they separate sections) and add header
                out.extend(deferred_blanks)
                if label:
                    out.append(label + "\n")
                current_section = label
            # Same section — drop deferred blank lines (Black artifact)
            deferred_blanks = []
            in_import_block = True
            in_multiline = "(" in line and ")" not in line
            out.append(line)
        elif in_multiline:
            # Continuation of a multi-line import
            if ")" in line:
                in_multiline = False
            out.append(line)
        elif not line.strip() and in_import_block:
            deferred_blanks.append(line)
        else:
            out.extend(deferred_blanks)
            deferred_blanks = []
            in_import_block = False
            current_section = None
            out.append(line)

    with open(path, "w") as f:
        f.writelines(out)


EXCLUDE_DIRS = {"__pycache__", ".venv", "venv", ".git", "supabase", "scripts"}


def find_py_files(root):
    from pathlib import Path

    return [
        p
        for p in Path(root).rglob("*.py")
        if not any(part in EXCLUDE_DIRS for part in p.parts)
    ]


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    paths = find_py_files(root)
    for path in paths:
        sort_and_comment(path)
        print(f"Sorted: {path}")
