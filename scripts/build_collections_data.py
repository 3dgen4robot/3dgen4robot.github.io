import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SURVEY_DIR = pathlib.Path(r"D:\master\My-Paper\3D_Gen_for_Embodied_AI\survey")
BIB_PATH = SURVEY_DIR / "sample-base.bib"
COLLECTIONS_PATH = ROOT / "static" / "js" / "collections-data.js"

TEX_SOURCES = [
    {
        "path": SURVEY_DIR / "sec" / "data_generator.tex",
        "label": "tab:generative_objects",
        "domain": "Data Generator",
        "cat_map": {
            "182": "Articulated Objects",
            "183": "Physically-grounded Objects",
            "184": "Deformable Objects",
            "185": "End-to-End Pipelines",
        },
    },
    {
        "path": SURVEY_DIR / "sec" / "simulation_environments.tex",
        "label": "tab:embodied_scene_generation_summary",
        "domain": "Simulation Environments",
        "cat_map": {
            "182": "Structure-Driven",
            "183": "Controllable",
            "184": "Agentic",
        },
    },
    {
        "path": SURVEY_DIR / "sec" / "sim2real_bridge.tex",
        "label": "tab:sim2real_summary",
        "domain": "Sim2Real Bridge",
        "cat_map": {
            "182": "Digital Twin",
            "183": "Data Augmentation",
            "184": "Task & Demo Generation",
        },
    },
]


def load_existing_urls(path: pathlib.Path) -> dict:
    """Load existing projectUrl/pdfUrl/codeUrl keyed by citeKey."""
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"^window\.COLLECTIONS_DATA\s*=\s*", "", raw)
    raw = re.sub(r";\s*$", "", raw)
    data = json.loads(raw)
    return {
        entry["citeKey"]: {
            "projectUrl": entry.get("projectUrl", ""),
            "pdfUrl": entry.get("pdfUrl", ""),
            "codeUrl": entry.get("codeUrl", ""),
        }
        for entry in data.get("value", [])
    }


def parse_bib(path: pathlib.Path) -> dict:
    """Parse bib file → {citeKey: {title, authors}}."""
    text = path.read_text(encoding="utf-8")
    entries = {}
    for m in re.finditer(r"@\w+\{([^,]+),([\s\S]*?)\n\}", text):
        key = m.group(1).strip()
        body = m.group(2)
        fields = {}
        for fm in re.finditer(
            r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|[^,\n]+)", body, re.S
        ):
            name = fm.group(1).strip().lower()
            val = fm.group(2).strip().rstrip(",")
            if val.startswith("{") and val.endswith("}"):
                val = val[1:-1]
            elif val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            fields[name] = val.strip()
        entries[key] = fields
    return entries


def clean_bib_text(text: str) -> str:
    # Strip nested braces twice to handle {{...}}
    text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


_LOWERCASE_WORDS = {
    "a", "an", "the",
    "and", "but", "or", "nor", "for", "so", "yet",
    "at", "by", "in", "of", "on", "to", "up", "as", "via", "per",
    "from", "with", "into", "onto", "upon",
}

# Abbreviations / acronyms that should keep fixed casing
_FIXED_CASE = {
    "3d": "3D", "2d": "2D", "4d": "4D",
    "3dgs": "3DGS", "6-dof": "6-DoF", "6dof": "6DoF",
    "llm": "LLM", "vlm": "VLM", "llm/vlm": "LLM/VLM",
    "llms": "LLMs", "vlms": "VLMs", "lmms": "LMMs", "lmm": "LMM",
    "nerf": "NeRF",
    "urdf": "URDF", "urdf/mjcf": "URDF/MJCF", "mjcf": "MJCF",
    "rgb": "RGB", "rgb-d": "RGB-D", "rgbd": "RGB-D",
    "ai": "AI", "dof": "DoF",
    "mpm": "MPM", "fem": "FEM", "pbd": "PBD",
    "pbr": "PBR", "uv": "UV", "ar": "AR",
    "slam": "SLAM", "vae": "VAE", "gan": "GAN",
    "dit": "DiT", "sdf": "SDF", "pc": "PC",
    "real2sim": "Real2Sim", "sim2real": "Sim2Real",
    "real2render2real": "Real2Render2Real", "real2sim2real": "Real2Sim2Real",
}


def _apply_word(word: str, force_cap: bool) -> str:
    # Strip trailing punctuation for lookup, then restore
    suffix_match = re.search(r"[^\w\-/+]+$", word)
    suffix = suffix_match.group(0) if suffix_match else ""
    core = word[: len(word) - len(suffix)]
    lower = core.lower()
    if lower in _FIXED_CASE:
        return _FIXED_CASE[lower] + suffix
    if force_cap or lower not in _LOWERCASE_WORDS:
        return core.capitalize() + suffix
    return lower + suffix


def title_case(text: str) -> str:
    words = text.split()
    result = []
    force_next = False  # capitalize word after colon/dash punctuation
    for i, word in enumerate(words):
        is_first = i == 0
        is_last = i == len(words) - 1
        force_cap = is_first or is_last or force_next

        # Detect if this word ends with colon → force-cap next word
        force_next = word.rstrip().endswith(":")

        if "-" in word and word.lower() not in _FIXED_CASE:
            parts = word.split("-")
            capped = "-".join(_apply_word(p, True) if p else p for p in parts)
            result.append(capped)
        else:
            result.append(_apply_word(word, force_cap))
    return " ".join(result)


def clean_title(text: str) -> str:
    """Clean bib title and apply title case."""
    text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return title_case(text)


def extract_table_content(text: str, label: str) -> str:
    match = re.search(rf"\\label\{{{re.escape(label)}\}}", text)
    if not match:
        raise ValueError(f"Label not found: {label}")
    start = text.find(r"\midrule", match.end())
    if start == -1:
        raise ValueError(f"No midrule found for {label}")
    end = text.find(r"\bottomrule", start)
    if end == -1:
        raise ValueError(f"No bottomrule found for {label}")
    return text[start + len(r"\midrule") : end]


def strip_line_comments(text: str) -> str:
    """Remove lines that are purely comments (starting with %) and inline % comments."""
    result = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        # Remove inline % comment (not inside braces, a simplistic but sufficient approach)
        cleaned = re.sub(r"\s*%.*$", "", line)
        result.append(cleaned)
    return "\n".join(result)


def extract_rows(table_content: str) -> list:
    content = strip_line_comments(table_content)
    # Each data row starts with a number, &, and ends with \\
    pattern = re.compile(r"^\s*\d+\s*&[\s\S]*?\\\\", re.MULTILINE)
    return [m.group(0) for m in pattern.finditer(content)]


def split_fields(row: str) -> list:
    row = re.sub(r"\\\\\s*$", "", row, flags=re.S)
    return [f.strip() for f in row.split("&")]


def extract_cite_key(field: str) -> str:
    m = re.search(r"\\cite\{([^}]+)\}", field)
    return m.group(1).strip() if m else ""


def extract_url(field: str) -> str:
    m = re.search(r"\\href\{([^}]+)\}", field)
    return m.group(1).strip() if m else ""


def extract_category(field: str, cat_map: dict) -> str:
    m = re.search(r"\\ding\{(\d+)\}", field)
    return cat_map.get(m.group(1), "") if m else ""


def clean_venue(text: str) -> str:
    # Remove \textcolor{...}{...} wrappers
    text = re.sub(r"\\textcolor\{[^}]*\}\{[^}]*\}", "", text)
    # Remove \textbf{}, \textit{}, etc.
    text = re.sub(r"\\text\w+\{([^}]*)\}", r"\1", text)
    # Replace ~ with space
    text = text.replace("~", " ")
    # Remove remaining backslash commands
    text = re.sub(r"\\[a-zA-Z]+\s*", " ", text)
    # Remove braces
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_entries(source: dict, bib: dict, existing_urls: dict) -> list:
    text = source["path"].read_text(encoding="utf-8")
    domain = source["domain"]
    cat_map = source["cat_map"]

    table_content = extract_table_content(text, source["label"])
    rows = extract_rows(table_content)

    entries = []
    for row in rows:
        fields = split_fields(row)
        if len(fields) < 4:
            continue

        cite_key = extract_cite_key(fields[1])
        if not cite_key:
            continue

        venue = clean_venue(fields[2])
        category = extract_category(fields[-2], cat_map)
        url = extract_url(fields[-1])

        bib_entry = bib.get(cite_key, {})
        raw_title = bib_entry.get("title", "")
        title = clean_title(raw_title)

        raw_authors = bib_entry.get("author", "")
        authors = clean_bib_text(raw_authors)

        urls = existing_urls.get(cite_key, {"projectUrl": "", "pdfUrl": "", "codeUrl": ""})

        entries.append(
            {
                "domain": domain,
                "category": category,
                "citeKey": cite_key,
                "title": title,
                "venue": venue,
                "url": url,
                "authors": authors,
                "projectUrl": urls["projectUrl"],
                "pdfUrl": urls["pdfUrl"],
                "codeUrl": urls["codeUrl"],
            }
        )
    return entries


def main():
    existing_urls = load_existing_urls(COLLECTIONS_PATH)
    bib = parse_bib(BIB_PATH)

    all_entries = []
    for source in TEX_SOURCES:
        entries = build_entries(source, bib, existing_urls)
        print(f"  {source['domain']}: {len(entries)} entries")
        all_entries.extend(entries)

    payload = {"Count": len(all_entries), "value": all_entries}
    COLLECTIONS_PATH.write_text(
        "window.COLLECTIONS_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_entries)} entries to {COLLECTIONS_PATH}")


if __name__ == "__main__":
    main()
