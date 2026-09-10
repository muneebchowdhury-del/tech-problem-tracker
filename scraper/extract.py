"""
Cheap pre-filtering before anything gets sent to the paid classifier:
  1. Keyword match — does this item even mention a problem/failure?
  2. Dedup — have we already seen this URL before?
"""

import hashlib


def matches_problem_keywords(item, keywords):
    haystack = f"{item.get('title', '')} {item.get('text', '')}".lower()
    return any(kw.lower() in haystack for kw in keywords)


def url_hash(url):
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def filter_candidates(raw_items, keywords, seen_hashes):
    """Returns items that (a) mention a problem and (b) haven't been seen before."""
    candidates = []
    for item in raw_items:
        if not item.get("url"):
            continue
        h = url_hash(item["url"])
        if h in seen_hashes:
            continue
        if not matches_problem_keywords(item, keywords):
            continue
        item["_hash"] = h
        candidates.append(item)
    return candidates
