"""
Fetches raw candidate items (title, text, url, published date) from each
configured source. Each fetch_* function returns a list of dicts:
    {"title": str, "text": str, "url": str, "source": str, "tech": str}
"""

import time
import requests
import feedparser

USER_AGENT = "tech-problem-tracker/1.0 (+https://github.com/; research bot, respects robots.txt)"
TIMEOUT = 15


def fetch_rss(source_cfg):
    items = []
    try:
        feed = feedparser.parse(source_cfg["url"])
        for entry in feed.entries[:30]:
            text = entry.get("summary", "") or entry.get("description", "")
            items.append({
                "title": entry.get("title", ""),
                "text": strip_html(text),
                "url": entry.get("link", ""),
                "source": source_cfg["name"],
                "tech": source_cfg.get("tech", "General"),
            })
    except Exception as e:
        print(f"[warn] RSS fetch failed for {source_cfg['name']}: {e}")
    return items


def fetch_hn_algolia(source_cfg):
    """Hacker News Algolia search API — public, no auth, no scraping restrictions."""
    items = []
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": source_cfg["query"],
                "tags": "story",
                "numericFilters": f"created_at_i>{int(time.time()) - 7*24*3600}",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        for hit in resp.json().get("hits", [])[:30]:
            items.append({
                "title": hit.get("title") or "",
                "text": hit.get("story_text") or hit.get("title") or "",
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "source": "Hacker News",
                "tech": source_cfg.get("tech", "General"),
            })
    except Exception as e:
        print(f"[warn] HN fetch failed: {e}")
    return items


def fetch_reddit(source_cfg):
    """Reddit's public JSON endpoint for a subreddit's top posts this week.
    No auth required for read-only public listings, but Reddit rate-limits
    aggressively — keep request volume low and identify a real User-Agent."""
    items = []
    try:
        url = f"https://www.reddit.com/r/{source_cfg['subreddit']}/top.json"
        resp = requests.get(
            url,
            params={"t": "week", "limit": 25},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        for child in resp.json().get("data", {}).get("children", []):
            post = child.get("data", {})
            items.append({
                "title": post.get("title", ""),
                "text": post.get("selftext", "") or post.get("title", ""),
                "url": f"https://www.reddit.com{post.get('permalink', '')}",
                "source": f"Reddit r/{source_cfg['subreddit']}",
                "tech": source_cfg.get("tech", "General"),
            })
    except Exception as e:
        print(f"[warn] Reddit fetch failed for r/{source_cfg['subreddit']}: {e}")
    return items


def strip_html(text):
    import re
    return re.sub("<[^<]+?>", " ", text or "").strip()


FETCHERS = {
    "rss": fetch_rss,
    "hn_algolia": fetch_hn_algolia,
    "reddit": fetch_reddit,
}


def fetch_all(sources_cfg):
    all_items = []
    for source_cfg in sources_cfg:
        fetcher = FETCHERS.get(source_cfg["type"])
        if not fetcher:
            print(f"[warn] unknown source type: {source_cfg['type']}")
            continue
        print(f"Fetching: {source_cfg['name']}...")
        all_items.extend(fetcher(source_cfg))
        time.sleep(1)  # be polite between sources
    return all_items
