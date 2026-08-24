#!/usr/bin/env python3
"""Regenerate index.json from the tree: every top-level folder is a category, every .amazepkg in it a package. Run after adding, moving or removing packages, then commit both. Refuses an unreadable package or a manifest format newer than it knows."""

import hashlib
import json
import os
import sys
import zipfile

KNOWN_FORMAT = 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://raw.githubusercontent.com/Timour/AmazePackages/main/"
SKIP = {"tools", ".git", ".github"}


def package_row(folder: str, name: str) -> dict:
    path = os.path.join(ROOT, folder, name)
    with zipfile.ZipFile(path) as bundle:
        manifest = json.loads(bundle.read("package.json"))
    fmt = manifest.get("format")
    if not isinstance(fmt, int) or fmt > KNOWN_FORMAT:
        sys.exit("REFUSED %s/%s: package format %r is newer than %d"
                 % (folder, name, fmt, KNOWN_FORMAT))
    kinds = {}
    for entry in manifest.get("entries", ()):
        key = (entry.get("section") if entry.get("type") == "asset"
               else entry.get("kind", "file"))
        kinds[key] = kinds.get(key, 0) + 1
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return {
        "name": os.path.splitext(name)[0],
        "file": "%s/%s" % (folder, name),
        "bytes": os.path.getsize(path),
        "entries": len(manifest.get("entries", ())),
        "kinds": kinds,
        "package_format": fmt,
        "sha256": digest.hexdigest(),
    }


def main() -> int:
    categories = []
    for folder in sorted(os.listdir(ROOT)):
        if folder in SKIP or not os.path.isdir(os.path.join(ROOT, folder)):
            continue
        rows = [package_row(folder, name)
                for name in sorted(os.listdir(os.path.join(ROOT, folder)))
                if name.endswith(".amazepkg")]
        if rows:
            categories.append({"name": folder, "packages": rows})
    index = {"format": 1, "base": BASE, "categories": categories}
    out = os.path.join(ROOT, "index.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2)
        handle.write("\n")
    total = sum(len(c["packages"]) for c in categories)
    print("index.json: %d categories, %d packages"
          % (len(categories), total))
    return 0


sys.exit(main())
