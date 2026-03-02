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


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print("Usage: python sort_imports.py <file.py> [file.py ...]")
        sys.exit(1)
    for path in paths:
        sort_and_comment(path)
        print(f"Sorted: {path}")
