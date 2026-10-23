"""Build static/js/collections-data.js and static/js/datasets-data.js from the paper database.

The database is data/papers.yaml in the GitHub list repo (https://github.com/hitcslj/3DGen4Robot),
which also generates that repo's README tables. By default it is read from a sibling checkout:

    python scripts/build_from_db.py [--db ../3DGen4Robot/data/papers.yaml]

Requires PyYAML (pip install pyyaml).
"""
import json
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.parent / "3DGen4Robot" / "data" / "papers.yaml"
COLLECTIONS_PATH = ROOT / "static" / "js" / "collections-data.js"
DATASETS_PATH = ROOT / "static" / "js" / "datasets-data.js"
DATASET_ATTRS = ("category", "type", "scale", "summary", "phys", "kin", "sim", "robot")


def db_path():
    if "--db" in sys.argv:
        return pathlib.Path(sys.argv[sys.argv.index("--db") + 1])
    return pathlib.Path(os.environ.get("PAPERS_DB", DEFAULT_DB))


def sort_key(e):
    # same order as the README tables: first release (arXiv v1) date
    if e.get("arxiv"):
        yymm, num = str(e["arxiv"]).split(".")
        return (f"20{yymm[:2]}-{yymm[2:]}", int(num))
    date = str(e.get("date", "0000"))
    return (date if len(date) > 4 else date + "-12", 0)


def paper_url(e):
    return f"https://arxiv.org/abs/{e['arxiv']}" if e.get("arxiv") else e.get("paper_url", "")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def write_js(path, var, payload):
    path.write_text(f"window.{var} = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def main():
    path = db_path()
    if not path.exists():
        sys.exit(f"Paper database not found at {path}. Clone the list repo next to this one or pass --db PATH.")
    db = yaml.safe_load(path.read_text(encoding="utf-8"))
    tax = {t["key"]: t for t in db["taxonomy"]}
    order = {t["key"]: i for i, t in enumerate(db["taxonomy"])}

    methods = sorted(db["methods"], key=lambda e: (order[e["section"]], sort_key(e)))
    collections = []
    for e in methods:
        t = tax[e["section"]]
        collections.append({
            "domain": t["group"],
            "category": t["homepage_category"],
            "citeKey": e.get("cite_key") or slug(e["name"]),
            "title": e["title"],
            "venue": e["venue"],
            "url": paper_url(e),
            "authors": e.get("authors", ""),
            "projectUrl": e.get("project", ""),
            "pdfUrl": paper_url(e),
            "codeUrl": e.get("code", ""),
        })
    write_js(COLLECTIONS_PATH, "COLLECTIONS_DATA", {"Count": len(collections), "value": collections})

    datasets = sorted(db["datasets"], key=lambda e: (order[e["section"]], sort_key(e)))
    items = []
    for e in datasets:
        home = e.get("homepage", {})
        item = {"group": tax[e["section"]]["homepage_category"], "category": home.get("category", ""),
                "name": e["name"], "venue": e["venue"]}
        item.update({k: home[k] for k in DATASET_ATTRS[1:] if home.get(k)})
        item["url"] = home.get("url") or e.get("website") or paper_url(e)
        items.append(item)
    write_js(DATASETS_PATH, "DATASETS_DATA", {"count": len(items), "items": items})
    print(f"Wrote {len(collections)} collection entries and {len(items)} dataset entries from {path}")


if __name__ == "__main__":
    main()
