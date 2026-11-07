# CLAUDE.md — search-internet-better

Experimental, user-shaped, bias- and noise-aware web search. Instead of a cut-off top ten,
it shows the whole result landscape (core, margins, long tail), explains every placement,
and reports how biased or noisy each search is. Read `docs/DESIGN.md` before changing behaviour.

## Principles (do not erode without the owner's say-so)
1. **Show the shape, not just the top.** Core / margin / tail stay visible; nothing is silently cut.
2. **Every choice is explainable.** Each result carries `why[]`; any new signal must add a why line.
3. **Plural by design.** Merge several independent indexes; keep per-engine ranks on each result.
4. **Measure and report.** Health metrics per search (`server/metrics.py`); add a metric when you add a bias lever.
5. **Provenance on every result.** Engine(s), ranks, source type + reason, language + reason.
6. **No engagement loop by default.** Clicks never feed ranking unless a user explicitly opts in.
7. **Multilingual by default.** Machine translation is always labelled.
8. **Private by default.** No query logs, no persistent result cache; lenses live in the user's browser.
"Neutral" is not a claim we make: we make our biases visible and user-adjustable.

## Compliance rules (vendor terms + law)
- **APIs only.** Never scrape search engine result pages (Google/Bing ToS). Each vendor sits behind an adapter in `server/adapters/` that enforces its depth cap and storage terms.
- **No result storage** unless the plan allows it (Brave: separate storage-rights plan; Mojeek Startup: 1-hour cache only; Marginalia free key: non-commercial).
- Any own crawling follows RFC 9309 and the good-citizen checklist in `docs/research/build_crawler.md`.
- `.env` holds keys; never commit it.

## Layout
- `server/app.py` — stdlib HTTP server + JSON API (`/api/search`, `/api/lenses`, `/api/status`).
- `server/pipeline.py` — plan → fetch → merge → signals → re-rank → landscape → metrics.
- `server/lens.py` — lens schema + Brave-Goggles-subset parser (our own multiplier semantics, documented in the file).
- `server/signals.py` — source type, script-based language guess, noise flags (simple and transparent on purpose).
- `server/metrics.py` — health panel (top-3 share, Gini, entropy, exposure Gini, language/type mix, noise share).
- `server/adapters/` — `sample` (synthetic, offline), `marginalia`, `brave`, `mojeek`.
- `web/` — no-build front end: mountain-peak view (SVG), health panel, list, lens editor.
- `lenses/*.json` — built-in lenses. `data/sample_results.json` — SYNTHETIC sample, fictional `.example` domains.
- `docs/` — design + research notes (with sources) carried over from the research phase.

## Commands
- Run: `python3 -m server.app` → http://localhost:8000 (no dependencies; Python 3.10+).
- Test: `python3 -m unittest discover -s tests -t .`
- With live engines: copy `.env.example` to `.env` and add keys. With no keys, the sample adapter runs and the UI shows a synthetic-data banner.

## Working agreements
- Keep the server dependency-free until there is a clear reason; if adding deps, add `requirements.txt` and say why in the PR.
- Verify each vendor adapter against its current docs before enabling (endpoints/field names are marked VERIFY in the adapter files).
- The synthetic sample must always be labelled as such in the UI and API (`synthetic_sample: true`).
- Prefer primary, official sources when adding research claims to `docs/`; label secondary sources.
- Work on feature branches; small PRs; update `BACKLOG.md` and tests with each change.
