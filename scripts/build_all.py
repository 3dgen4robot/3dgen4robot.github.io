"""Run all build scripts and bump the JS cache-busting version in index.html."""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
# Both data files now come from the paper database (data/papers.yaml in the 3DGen4Robot list repo).
# build_collections_data.py / build_datasets_data.py, which parsed the survey's LaTeX tables,
# are kept for reference but no longer run.
SCRIPTS = [
    "build_from_db.py",
]


def run_scripts():
    for script in SCRIPTS:
        print(f"\n=== {script} ===")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / script), *sys.argv[1:]],
            check=True,
        )


def bump_version():
    version = datetime.now().strftime("%Y%m%d%H%M")
    html = INDEX.read_text(encoding="utf-8")
    html, n = re.subn(
        r'(static/js/(?:collections|datasets)-data\.js)\?v=[^"]+',
        rf"\1?v={version}",
        html,
    )
    INDEX.write_text(html, encoding="utf-8")
    print(f"\nBumped {n} version tag(s) to ?v={version}")


if __name__ == "__main__":
    run_scripts()
    bump_version()
