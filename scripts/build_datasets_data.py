import json
import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = pathlib.Path(r"D:\master\My-Paper\3D_Gen_for_Embodied_AI\survey\sec\datasets.tex")
OUTPUT = ROOT / "static" / "js" / "datasets-data.js"


def clean_tex(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"~\\cite\{[^}]+\}", "", text)
    text = re.sub(r"\\href\{[^}]+\}\{[^}]+\}", "", text)
    text = text.replace(r"\&", "&")
    text = text.replace(r"\%", "%")
    text = text.replace(r"\_", "_")
    text = text.replace(r"\sim", "~")
    text = text.replace(r"\,", "")
    text = text.replace(r"\'{e}", "e")
    text = text.replace(r"\textit{", "")
    text = text.replace(r"\textbf{", "")
    text = text.replace("{", "")
    text = text.replace("}", "")
    text = re.sub(r"\$+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_table_block(text: str, label: str) -> str:
    match = re.search(rf"\\label\{{{re.escape(label)}\}}[\s\S]*?\\begin\{{tabular.*?\}}([\s\S]*?)\\bottomrule", text)
    if not match:
        raise ValueError(f"Could not find table for {label}")
    return match.group(1)


def extract_rows(block: str):
    return re.findall(r"^\s*\d+\s*&[\s\S]*?\\\\", block, flags=re.M)


def extract_url(field: str) -> str:
    match = re.search(r"\\href\{([^}]+)\}", field)
    return match.group(1).strip() if match else ""


def normalize_venue(text: str) -> str:
    text = clean_tex(text)
    text = text.replace(" '", "'")
    text = re.sub(r"([A-Za-z])'(\d{2})", r"\1 '\2", text)
    return text


def mark_value(text: str) -> str:
    text = text.strip()
    if r"\cmark" in text:
        return "Yes"
    if r"\pmark" in text:
        return "Partial"
    return "No"


def split_fields(row: str):
    compact = re.sub(r"\s+", " ", row.strip())
    parts = re.split(r"\s&\s", compact)
    if parts:
        parts[-1] = re.sub(r"\\\\\s*$", "", parts[-1]).strip()
    return parts


def build_object_entries(text: str):
    block = extract_table_block(text, "tab:datasets")
    entries = []
    for row in extract_rows(block):
        fields = split_fields(row)
        if len(fields) != 10:
            continue
        entries.append(
            {
                "group": "Object Assets",
                "category": clean_tex(fields[3]),
                "name": clean_tex(fields[1]),
                "venue": normalize_venue(fields[2]),
                "type": clean_tex(fields[3]),
                "scale": clean_tex(fields[4]),
                "summary": clean_tex(fields[5]),
                "phys": mark_value(fields[6]),
                "kin": mark_value(fields[7]),
                "sim": mark_value(fields[8]),
                "url": extract_url(fields[9]),
            }
        )
    return entries


def map_scene_category(text: str) -> str:
    if "182" in text:
        return "Source Scene"
    if "183" in text:
        return "Generated Scene"
    return "Domain-oriented Scene"


def build_scene_entries(text: str):
    block = extract_table_block(text, "tab:scene_datasets")
    entries = []
    for row in extract_rows(block):
        fields = split_fields(row)
        if len(fields) != 9:
            continue
        entries.append(
            {
                "group": "Scene Datasets",
                "category": map_scene_category(fields[7]),
                "name": clean_tex(fields[1]),
                "venue": normalize_venue(fields[2]),
                "type": clean_tex(fields[3]),
                "scale": clean_tex(fields[4]),
                "summary": clean_tex(fields[5]),
                "sim": mark_value(fields[6]),
                "url": extract_url(fields[8]),
            }
        )
    return entries


def map_demo_category(text: str) -> str:
    if "182" in text:
        return "Real-World Corpus"
    if "183" in text:
        return "Sim-Based Benchmark"
    return "Augmentation / Scaling System"


def build_demo_entries(text: str):
    block = extract_table_block(text, "tab:demo_datasets")
    entries = []
    for row in extract_rows(block):
        fields = split_fields(row)
        if len(fields) != 9:
            continue
        entries.append(
            {
                "group": "Robot Demonstrations",
                "category": map_demo_category(fields[7]),
                "name": clean_tex(fields[1]),
                "venue": normalize_venue(fields[2]),
                "type": clean_tex(fields[3]),
                "robot": clean_tex(fields[4]),
                "scale": clean_tex(fields[5]),
                "summary": clean_tex(fields[6]),
                "url": extract_url(fields[8]),
            }
        )
    return entries


def main():
    text = SOURCE.read_text(encoding="utf-8")
    items = build_object_entries(text) + build_scene_entries(text) + build_demo_entries(text)
    payload = {"count": len(items), "items": items}
    OUTPUT.write_text("window.DATASETS_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print(f"Wrote {len(items)} dataset entries to {OUTPUT}")


if __name__ == "__main__":
    main()
