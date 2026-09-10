# Migration & Integration Problem Tracker

A weekly-refreshed dashboard of documented problems enterprises face when
introducing new tech, migrating off legacy systems, or integrating the two —
focused on SAP and hyperscaler (AWS/Azure/GCP) environments.

**Live dashboard:** https://muneebchowdhury-del.github.io/tech-problem-tracker/

## How it works

1. A GitHub Action runs every Monday (`.github/workflows/weekly-scrape.yml`).
2. `scraper/run.py` fetches new items from the sources in `config/sources.yaml`
   (SAP/AWS/Azure/GCP blogs, tech press RSS, Hacker News, Reddit).
3. Items are filtered down to ones that actually mention a problem
   (`config/sources.yaml` → `problem_keywords`), to keep API costs low.
4. Each candidate is sent to Claude Haiku 4.5 (`scraper/classify.py`) to be
   categorized, tagged, and summarized in the model's own words — never
   copying the source text.
5. New findings are appended to `data/findings.json`, deduplicated by URL,
   and copied to `docs/findings.json`.
6. `docs/index.html` is a static dashboard that fetches `findings.json` and
   renders it with filters — this is what GitHub Pages serves.

## One-time setup

### 1. Create the repo
Create a new **public** repository on GitHub and push everything in this
folder to it:

```bash
cd tech-problem-tracker
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

(Public is recommended: GitHub Pages is free on public repos, and Actions
minutes are unlimited. If you need it private, Pages requires GitHub Pro.)

### 2. Add your Anthropic API key as a secret
The scraper needs an Anthropic API key to categorize findings.

1. Get a key from https://platform.claude.com (Console → API Keys).
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `ANTHROPIC_API_KEY`, value: your key.

Cost note: classifying ~50 new items/week with Haiku 4.5 costs roughly
$0.05–$0.20/week. There's a hard cap of 150 classifications per run
(`MAX_CANDIDATES_PER_RUN` in `scraper/run.py`) so a misconfigured source
can't run up a large bill unexpectedly.

### 3. Enable GitHub Pages
**Settings → Pages → Build and deployment → Source: "Deploy from a branch"
→ Branch: `main`, folder: `/docs`.** Save. GitHub will give you the live URL
within a minute or two.

### 4. Run it once manually
Don't wait for Monday — trigger the first run yourself:
**Actions tab → "Weekly scrape" → Run workflow.**

Check the Action's logs to confirm it fetched and classified successfully,
then visit your Pages URL to see the dashboard update.

## Local development

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python scraper/run.py
```

This updates `data/findings.json` and `docs/findings.json` locally — open
`docs/index.html` in a browser to preview.

## Extending it

- **Add a source:** add an entry to `config/sources.yaml`. RSS feeds need no
  code changes. New source *types* (e.g. a specific review site) need a new
  fetch function in `scraper/fetch.py`, registered in the `FETCHERS` dict.
- **Change the taxonomy:** edit `config/taxonomy.py`. The classifier prompt
  reads from it automatically. If you change categories, old findings in
  `data/findings.json` keep their existing category tags — you may want to
  manually re-tag or clear the file to start fresh.
- **Adjust cost/volume:** tune `problem_keywords` in `sources.yaml` (tighter
  keywords = fewer, cheaper classifications) or `MAX_CANDIDATES_PER_RUN` in
  `scraper/run.py`.
- **LinkedIn:** intentionally not scraped directly (against their ToS).
  Public LinkedIn posts that get indexed by search engines can still surface
  through the Hacker News/press sources organically, or you can manually
  add ones you find to `data/findings.json`.

## Project structure

```
tech-problem-tracker/
├── .github/workflows/weekly-scrape.yml   # the scheduled job
├── config/
│   ├── sources.yaml                      # source list + problem keywords
│   └── taxonomy.py                       # categories/severities/sizes/tech
├── scraper/
│   ├── fetch.py                          # RSS / HN / Reddit fetchers
│   ├── extract.py                        # keyword filter + dedup
│   ├── classify.py                       # Claude Haiku categorization
│   └── run.py                            # orchestrates the whole run
├── data/findings.json                    # source of truth, committed by CI
├── docs/
│   ├── index.html                        # the dashboard (GitHub Pages serves this)
│   └── findings.json                     # copy of data/findings.json for the dashboard to fetch
└── requirements.txt
```
