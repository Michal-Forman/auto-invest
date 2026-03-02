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
    m = re.match(r"(?:from\s+([\w]+)|import\s+([\w]+))", line.strip())
    return (m.group(1) or m.group(2)) if m else None


def sort_and_comment(path):
    isort.file(path)

    with open(path) as f:
        lines = f.readlines()

    # Remove any existing section comments so re-runs are idempotent
    label_set = set(LABELS.values())
    lines = [l for l in lines if l.strip() not in label_set]

    config = Config()
    out = []
    in_import_block = False
    current_section = None

    for line in lines:
        mod = get_top_module(line)
        if mod:
            section = place.module(mod, config=config)
            if section != current_section:
                label = LABELS.get(section)
                if label:
                    out.append(label + "\n")
                current_section = section
            in_import_block = True
            out.append(line)
        elif not line.strip() and in_import_block:
            out.append(line)
        else:
            in_import_block = False
            current_section = None
            out.append(line)

    with open(path, "w") as f:
        f.writelines(out)


EXCLUDE_DIRS = {"__pycache__", ".venv", "venv", ".git", "supabase", "scripts"}


def find_py_files(root):
    from pathlib import Path
    return [
        p for p in Path(root).rglob("*.py")
        if not any(part in EXCLUDE_DIRS for part in p.parts)
    ]


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    paths = find_py_files(root)
    for path in paths:
        sort_and_comment(path)
        print(f"Sorted: {path}")
