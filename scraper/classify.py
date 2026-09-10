"""
Sends each filtered candidate to Groq (fast open-model inference, e.g. Llama,
GPT-OSS, Qwen) for structured classification, via Groq's OpenAI-compatible
Chat Completions endpoint.

Note: Groq != Grok. Groq (groq.com, console.groq.com) hosts open-weight
models on their own inference hardware; Grok is xAI/Elon Musk's model.
This file targets Groq's API.

Free-tier rate limits (see https://console.groq.com/docs/rate-limits) are
generous enough for this workload (well under 1,000 requests/day and
200K tokens/day), but the 8,000 tokens/minute cap means we pace requests
rather than fire them all at once.

Any item that isn't actually about a real tech-transition problem (the
keyword filter is intentionally loose) gets tagged is_relevant=false by
the model and is dropped.
"""

import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.taxonomy import CATEGORIES, SEVERITIES, SIZES, TECHS

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"  # strong quality/cost balance on Groq's free tier as of writing
MODEL = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)

# Free tier: 8,000 tokens/minute. Each classification call runs ~500-700
# tokens combined, so ~5 seconds between calls keeps us comfortably under
# that even with some variance, without needing retry/backoff logic.
SECONDS_BETWEEN_CALLS = 5

SYSTEM_PROMPT = f"""You classify short articles/posts about enterprise technology \
transitions (system migrations, new-tech adoption, integration of new and \
existing systems) into a fixed taxonomy for a research dashboard.

Categories (pick 1-2 that best fit): {json.dumps(CATEGORIES)}
Severity (pick 1): {json.dumps(SEVERITIES)}
Organization size (pick 1, infer from context, default "Unspecified" if unclear): {json.dumps(SIZES)}
Technology (pick 1 that best fits, or use what's given if it's already accurate): {json.dumps(TECHS)}

Respond with ONLY a JSON object, no other text, matching this exact shape:
{{
  "is_relevant": true/false,
  "title": "short punchy restatement of the core problem, under 12 words, in your own words",
  "desc": "1-2 sentence plain-language summary of the problem, in your own words, never copying source text",
  "category": ["..."],
  "severity": "...",
  "size": "...",
  "tech": "...",
  "commonality": "one of: 'Widespread pattern', 'Common', 'Documented incident', 'Emerging pattern'",
  "fix": "1 sentence on what organizations did or could do to address this, in your own words"
}}

Set is_relevant=false if the item is not actually about a tech-transition \
problem (e.g. it's a product announcement, marketing post, or unrelated news). \
Never quote the source text directly — always paraphrase in your own words, \
this is a strict legal requirement."""


def classify_item(api_key, item):
    user_msg = f"""Title: {item['title']}
Source: {item['source']}
Suggested tech: {item['tech']}
Text: {item['text'][:2000]}"""

    payload = {
        "model": MODEL,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    }

    try:
        resp = requests.post(
            GROQ_BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("retry-after", 10))
            print(f"[warn] rate limited, sleeping {retry_after}s")
            time.sleep(retry_after)
            resp = requests.post(
                GROQ_BASE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Guard against accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result
    except Exception as e:
        print(f"[warn] classification failed for {item.get('url')}: {e}")
        return None


def classify_all(candidates, api_key):
    findings = []
    for i, item in enumerate(candidates):
        if i > 0:
            time.sleep(SECONDS_BETWEEN_CALLS)
        result = classify_item(api_key, item)
        if not result or not result.get("is_relevant"):
            continue
        findings.append({
            "title": result["title"],
            "desc": result["desc"],
            "category": result["category"][0] if result.get("category") else "Governance & Scope",
            "tech": result.get("tech", item["tech"]),
            "size": result.get("size", "Unspecified"),
            "severity": result.get("severity", "medium"),
            "commonality": result.get("commonality", "Documented incident"),
            "fix": result.get("fix", ""),
            "source": item["source"],
            "url": item["url"],
            "hash": item["_hash"],
        })
    return findings
