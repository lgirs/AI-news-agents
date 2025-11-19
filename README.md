# AI News Agents

Automated three-agent workflow that curates, summarizes, and publishes daily AI business/economic/societal news.

## Project layout
```
agents/
  researcher.py      # weekly source curation
  reader.py          # Tue-Fri news digests
  publisher.py       # HTML publisher
  storage.py         # SQLite helpers
  models.py          # pydantic IO contracts
  theme_engine.py    # weather-aware theme selection

data/
  sources.db          # SQLite catalog (auto-created, ignored in git)
  source_catalog.json # canonical JSON snapshot of vetted sources
  feedback.json       # research feedback queue
  weather_stub.json   # fallback weather sample

digests/
  digest_YYYY-MM-DD.json

templates/
  daily_digest.html.j2

themes/
  palettes.json

dist/
  index.html

prefect_flows.py     # Prefect scheduler definitions
scheduler.md          # cron guidance
```

## Agent capabilities
- **Researcher** normalizes new sources weekly, persists them to SQLite, and maintains the `data/feedback.json` loop so editors can boost or retire feeds.
- **Reader** relies on `feedparser` for RSS feeds and uses the optional `newspaper3k` + `readability-lxml` summarization stack when available before assembling the JSON digest.
- **Publisher** applies the weather-aware theming engine to `templates/daily_digest.html.j2` and exports a static `dist/index.html` ready for GitHub Pages (our primary host) or any other static platform.

## Dependency installation matrix
Different environments can pick the install path that best matches their tooling:

| Scenario | Command |
| --- | --- |
| Poetry (baseline runtime) | `poetry install` |
| Poetry with HTML summarizers | `poetry install --with summarizers` |
| Pip/CI baseline | `pip install -r requirements/base.txt` |
| Pip/CI summarizers | `pip install -r requirements/summarizers.txt` |

The optional summarization stack (newspaper3k + readability-lxml) is now isolated as a Poetry extra so air-gapped or resource-constrained hosts can skip it without breaking the Reader agent. The Reader falls back to readability-only or raw headline summaries when those optional wheels are not installed (see `tests/test_reader.py`).

## Getting started
1. Install dependencies with Poetry (baseline) or pip:
   ```bash
   poetry install  # add --with summarizers for richer HTML summaries
   # or use the locked requirements files for CI/pip
   pip install -r requirements/base.txt
   pip install -r requirements/summarizers.txt  # optional
   ```
2. Run the agents manually:
   ```bash
   poetry run python -m agents.researcher --extra-feedback data/feedback_samples.json
   poetry run python -m agents.reader --date 2024-05-10
   poetry run python -m agents.publisher --date 2024-05-10
   ```
3. Generated files:
   - `data/source_catalog.json` (tracked) + `data/sources.db` (auto-created via `python -m agents.storage seed` or a Researcher run)
   - `digests/digest_YYYY-MM-DD.json`
   - `dist/index.html`

## Scheduling
We ship Prefect flows with timezone-aware cron schedules (`Europe/Helsinki`). Register deployments once Prefect is configured:
```bash
poetry run python prefect_flows.py
```
This builds deployments that can be served via Prefect Cloud/Server. Alternatively, see `scheduler.md` for crontab examples.

## Readiness + confirmations
- Track milestone status and any outstanding stakeholder questions in `docs/STATUS.md`. Update it whenever you finish a setup
  step or need an explicit confirmation (e.g., preferred hosting target, acceptable weather data source).
- Confirmed decisions so far:
  - Weather data can continue to use the free `wttr.in` endpoint; keep the offline stub for resilience.
  - The Researcher should maintain a global source mix unless future guidance says otherwise.
  - Publisher output will be deployed to GitHub Pages for the first release (see GitHub integration below).
- ⚠️ A release PR is still blocked until we harden dependency installation and expand the source catalog (see
  `docs/STATUS.md` for the gating checklist).

## Feedback loop
The Researcher agent writes `data/feedback.json` with weekly requests. Editors add suggestions (new sources, rating tweaks) to the `responses` array. The next Researcher run ingests those responses (plus any ad-hoc file passed via `--extra-feedback`), adjusts the catalog, and archives the note with a timestamp so it does not repeat. See inline docs within `agents/researcher.py` for accepted fields and heuristics.

## Expanding source coverage
1. Add candidate sources to `DEFAULT_SOURCES` in `agents/researcher.py`.
2. Provide metadata (ingestion type, cadence, base credibility).
3. Run the Researcher. It normalizes the entry, persists it to SQLite, and surfaces it to the News Reader.
4. Submit editorial feedback via `data/feedback.json` (or `data/feedback_samples.json` for demos) to retire, boost, or tag sources.
5. Optional: run `python -m agents.storage seed --catalog data/source_catalog.json` (or `python -m agents.researcher --extra-feedback data/feedback_samples.json`) to rebuild a multi-outlet `data/sources.db` locally. We ignore the SQLite file in git to avoid binary diffs, but the JSON catalog proves the expanded source list.

After seeding, inspect the catalog with `sqlite3 data/sources.db 'select source_id,name,ingestion_type from sources order by source_id;'` to confirm at least eight vetted sources are available to the Reader agent.

## Tests
Run the included tests before committing:
```bash
poetry run pytest
```

## GitHub integration
When wiring CI/CD:
1. Enable Poetry caching and run `poetry install` in workflows.
2. Execute `pytest` and optionally `prefect deployment inspect`.
3. Publish the contents of `dist/` via GitHub Pages (default target) or another static host if needed (see `publisher.py`).
4. Configure a cron workflow to invoke `prefect agent start` or directly run the CLI commands on schedule.
