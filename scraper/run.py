"""
Weekly job: fetch new items from all sources -> filter to problem-related
candidates -> classify with Claude Haiku -> merge into data/findings.json
-> copy to docs/findings.json for the GitHub Pages dashboard to fetch.

Run manually with:  python scraper/run.py
Run in CI with:      python scraper/run.py   (ANTHROPIC_API_KEY set as env var)
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.fetch import fetch_all
from scraper.extract import filter_candidates
from scraper.classify import classify_all

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_PATH = os.path.join(ROOT, "config", "sources.yaml")
DATA_PATH = os.path.join(ROOT, "data", "findings.json")
DOCS_DATA_PATH = os.path.join(ROOT, "docs", "findings.json")

# Safety cap: never classify more than this many candidates in one run,
# so a bug or a keyword-filter miss can't produce a surprise API bill.
MAX_CANDIDATES_PER_RUN = 150


def load_existing():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH) as f:
            return json.load(f)
    return {"last_updated": None, "findings": []}


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    with open(SOURCES_PATH) as f:
        cfg = yaml.safe_load(f)

    existing = load_existing()
    seen_hashes = {f["hash"] for f in existing["findings"]}

    print(f"Starting with {len(existing['findings'])} existing findings.")

    raw_items = fetch_all(cfg["sources"])
    print(f"Fetched {len(raw_items)} raw items across all sources.")

    candidates = filter_candidates(raw_items, cfg["problem_keywords"], seen_hashes)
    print(f"{len(candidates)} candidates matched problem keywords and are new.")

    if len(candidates) > MAX_CANDIDATES_PER_RUN:
        print(f"Capping at {MAX_CANDIDATES_PER_RUN} candidates for this run (cost safety).")
        candidates = candidates[:MAX_CANDIDATES_PER_RUN]

    new_findings = classify_all(candidates, api_key) if candidates else []
    print(f"{len(new_findings)} new findings after classification.")

    existing["findings"].extend(new_findings)
    existing["last_updated"] = datetime.now(timezone.utc).isoformat()

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(existing, f, indent=2)

    os.makedirs(os.path.dirname(DOCS_DATA_PATH), exist_ok=True)
    shutil.copyfile(DATA_PATH, DOCS_DATA_PATH)

    print(f"Done. Total findings now: {len(existing['findings'])}.")


if __name__ == "__main__":
    main()
