import concurrent.futures
import json
import pathlib
import re
from html import unescape
from urllib.parse import urljoin, urlparse

import bs4
import requests


ROOT = pathlib.Path(__file__).resolve().parents[1]
COLLECTIONS_PATH = ROOT / "static" / "js" / "collections-data.js"
BIB_PATH = pathlib.Path(r"D:\master\My-Paper\3D_Gen_for_Embodied_AI\survey\sample-base.bib")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
TIMEOUT = 20
MAX_WORKERS = 10

IGNORE_DOMAINS = {
    "arxiv.org",
    "doi.org",
    "dx.doi.org",
    "openaccess.thecvf.com",
    "proceedings.mlr.press",
    "openreview.net",
    "scholar.google.com",
    "semanticscholar.org",
    "api.semanticscholar.org",
    "ui.adsabs.harvard.edu",
    "reddit.com",
    "www.reddit.com",
    "x.com",
    "twitter.com",
    "www.twitter.com",
    "linkedin.com",
    "www.linkedin.com",
    "facebook.com",
    "www.facebook.com",
    "instagram.com",
    "www.instagram.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
     "tech.cornell.edu",
     "info.arxiv.org",
     "catalyzex.com",
     "www.catalyzex.com",
     "alphaxiv.org",
     "core.ac.uk",
     "txyz.ai",
     "www.cornell.edu",
     "www.bibsonomy.org",
     "www.connectedpapers.com",
     "www.litmaps.co",
     "www.scite.ai",
     "dagshub.com",
     "gotit.pub",
     "huggingface.co",
     "sciencecast.org",
     "replicate.com",
     "influencemap.cmlab.dev",
     "creativecommons.org",
     "www.creativecommons.org",
     "paperswithcode.com",
     "www.paperswithcode.com",
}

IGNORE_GITHUB_REPOS = {
    "Academic-project-page-template",
    "nerfies.github.io",
}


def load_collections():
    raw = COLLECTIONS_PATH.read_text(encoding="utf-8")
    raw = re.sub(r"^window\.COLLECTIONS_DATA\s*=\s*", "", raw)
    raw = re.sub(r";\s*$", "", raw)
    return json.loads(raw)


def save_collections(payload):
    text = "window.COLLECTIONS_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    COLLECTIONS_PATH.write_text(text, encoding="utf-8")


def parse_bib_entries(text):
    entries = {}
    for match in re.finditer(r"@(\w+)\{([^,]+),([\s\S]*?)\n\}", text):
        key = match.group(2).strip()
        body = match.group(3)
        fields = {}
        for field_match in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\".*?\"|[^,\n]+)", body, re.S):
            name = field_match.group(1).strip().lower()
            value = field_match.group(2).strip().rstrip(",")
            if value.startswith("{") and value.endswith("}"):
                value = value[1:-1]
            elif value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            fields[name] = value.strip()
        entries[key] = fields
    return entries


def clean_title(text):
    text = unescape(text or "")
    text = re.sub(r"[{}\\\\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_arxiv_url(fields):
    url = (fields.get("url") or "").strip()
    if "arxiv.org/" in url:
        return to_arxiv_abs(url)
    eprint = (fields.get("eprint") or "").strip()
    if eprint:
        return f"https://arxiv.org/abs/{eprint}"
    journal = (fields.get("journal") or "").strip()
    match = re.search(r"arXiv[:\s]+(\d{4}\.\d{4,5}(?:v\d+)?)", journal, re.I)
    if match:
        return f"https://arxiv.org/abs/{match.group(1)}"
    return ""


def to_arxiv_abs(url):
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", url, re.I)
    if not match:
        match = re.search(r"10\.48550/arXiv\.([^/?#]+)", url, re.I)
    if not match:
        return ""
    paper_id = match.group(1).replace(".pdf", "")
    return f"https://arxiv.org/abs/{paper_id}"


def normalize_url(url):
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url.lstrip("/")
        parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    normalized = parsed._replace(path=path, fragment="").geturl()
    return normalized


def is_github_repo(url):
    host = (urlparse(url).netloc or "").lower()
    if host != "github.com" and host != "www.github.com":
        return False
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 2:
        return False
    if parts[1] in IGNORE_GITHUB_REPOS:
        return False
    return True


def is_github_pages(url):
    host = (urlparse(url).netloc or "").lower()
    return host.endswith("github.io")


def is_arxiv(url):
    host = (urlparse(url).netloc or "").lower()
    return host == "arxiv.org" or host == "www.arxiv.org" or "doi.org" in host and "arxiv" in url.lower()


def classify_primary_url(url):
    url = normalize_url(url)
    if not url:
        return "", "", ""
    if is_github_repo(url):
        return "", "", url
    if is_arxiv(url):
        return "", to_arxiv_abs(url), ""
    return url, "", ""


def make_session():
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_html(session, url):
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    if "text/html" not in response.headers.get("content-type", ""):
        return ""
    return response.text


def link_text(a_tag):
    return " ".join(a_tag.get_text(" ", strip=True).split()).lower()


def is_noise(url):
    host = (urlparse(url).netloc or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in IGNORE_DOMAINS)


def extract_links_from_html(page_url, html):
    soup = bs4.BeautifulSoup(html, "html.parser")
    out = []
    for a_tag in soup.find_all("a", href=True):
        href = normalize_url(urljoin(page_url, a_tag["href"]))
        if not href.startswith("http"):
            continue
        out.append({"href": href, "text": link_text(a_tag)})
    return out


def choose_links(page_url, links):
    page_url = normalize_url(page_url)
    project_url = ""
    pdf_url = ""
    code_url = ""

    if page_url and not is_arxiv(page_url) and not is_github_repo(page_url):
        project_url = page_url
    if is_arxiv(page_url):
        pdf_url = to_arxiv_abs(page_url)
    if is_github_repo(page_url):
        code_url = page_url

    external_candidates = []
    for link in links:
        href = link["href"]
        text = link["text"]
        if href == page_url:
            continue
        if is_github_repo(href):
            code_url = code_url or href
            continue
        if is_arxiv(href):
            pdf_url = pdf_url or to_arxiv_abs(href)
            continue
        if is_noise(href):
            continue
        external_candidates.append({"href": href, "text": text})

    if not project_url:
        text_priority = [
            candidate["href"]
            for candidate in external_candidates
            if any(token in candidate["text"] for token in ("project", "homepage", "website", "page"))
        ]
        if text_priority:
            project_url = text_priority[0]
        elif len(external_candidates) == 1:
            project_url = external_candidates[0]["href"]
    return project_url, pdf_url, code_url


def enrich_entry(session, entry, bib_fields):
    current_url = normalize_url(entry.get("url", ""))
    project_url, pdf_url, code_url = classify_primary_url(current_url)

    bib_pdf = extract_arxiv_url(bib_fields)
    if bib_pdf:
        pdf_url = pdf_url or bib_pdf

    urls_to_probe = []
    if current_url:
        urls_to_probe.append(current_url)
    if pdf_url and pdf_url != current_url:
        urls_to_probe.append(pdf_url)

    seen = set()
    for probe_url in urls_to_probe:
        if probe_url in seen:
            continue
        seen.add(probe_url)
        try:
            html = fetch_html(session, probe_url)
        except Exception:
            continue
        links = extract_links_from_html(probe_url, html)
        cand_project, cand_pdf, cand_code = choose_links(probe_url, links)
        project_url = project_url or cand_project
        pdf_url = pdf_url or cand_pdf
        code_url = code_url or cand_code

    entry["projectUrl"] = normalize_url(project_url)
    entry["pdfUrl"] = normalize_url(pdf_url)
    entry["codeUrl"] = normalize_url(code_url)
    return entry


def main():
    payload = load_collections()
    entries = payload["value"]
    bib_entries = parse_bib_entries(BIB_PATH.read_text(encoding="utf-8"))

    session = make_session()

    def task(entry):
        bib_fields = bib_entries.get(entry["citeKey"], {})
        return enrich_entry(make_session(), dict(entry), bib_fields)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        enriched = list(executor.map(task, entries))

    payload["value"] = enriched
    save_collections(payload)

    stats = {
        "project": sum(1 for entry in enriched if entry.get("projectUrl")),
        "pdf": sum(1 for entry in enriched if entry.get("pdfUrl")),
        "code": sum(1 for entry in enriched if entry.get("codeUrl")),
    }
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
