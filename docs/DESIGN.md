# Design: a user-shaped, bias- and noise-aware search engine

Full design (with diagrams): https://claude.ai/artifact/Bk3m9WTLdP6a1BDXCVk8cR
Background research report (interactive): https://claude.ai/artifact/YX5iHRtwaKtq746SynYnhG
Research notes with sources: `docs/research/`. As of 2026-11-08.

## Goal
No search engine can be neutral, because ordering is a choice. This one **shows its choices, lets you
change them, and shows what it leaves out**: a landscape (core, margins, long tail) instead of a top ten.
Grimmelmann (2011) argues "search neutrality" has no workable definition; we aim for chosen, visible,
user-adjustable bias instead.

| We can promise | We can't promise |
| --- | --- |
| Every ranking rule visible and adjustable | A ranking with no point of view |
| Several indexes; disagreement shown | Coverage of the whole web |
| Bias and noise measured per search | Zero bias in any single source |
| No click-popularity loop by default | That less popular means better |

## Principles
1. Show the shape, not just the top. 2. Every choice explainable. 3. Plural by design (several indexes/rankers).
4. Measure and report. 5. Provenance on every result. 6. No engagement loop by default.
7. Multilingual by default (translation labelled). 8. Private by default.

## Can we get all results? No.
Every API returns a ranked top slice (≤ ~200 per query): Brave ~200 (20×10 pages, $5/1k; no storage without
a storage-rights plan), Mojeek 10/40/100 by tier (£2–3/1k; entry tier 1-hour cache), Marginalia 100 (free
non-commercial; `dc` per-domain cap), Exa 100, Tavily 20, Kagi $12/1k. Google Programmable Search is closed to
new customers and sunsets 2027-01-01; Bing Search API retired 2025-08-11. Full corpora: Common Crawl (free),
EU Open Web Index (research licence). See `docs/research/experimental_search.md`.

What we do instead: merge engines → page deep → fan out reworded/translated queries → add an own long-tail
sample (Common Crawl) → re-rank the pool locally.

## Risks → mitigations
| Risk | Mitigation | Grounding |
| --- | --- | --- |
| Single-index monoculture | Merge independent indexes; show engine per result | Introna & Nissenbaum 2000 |
| Top-ten cut-off | Mountain view + deep paging | Marchionini 2006 |
| Popularity/engagement loops | No click feedback; fair-exposure re-rank; tail rotation | Singh & Joachims 2018; Biega et al. 2018 |
| Domain dominance | Per-domain cap; aspect diversification | Agrawal et al. 2009; xQuAD |
| English skew | Multilingual fan-out; language mix vs target | Steck 2018 (calibration) |
| Spam / MT filler in tail | Show labels, don't hide: duplicates, translation flags | Google spam-policy definitions |
| Hidden ranking choices | "Why it's here" | Introna & Nissenbaum |
| Order effects | Rank uncertainty; random order within band | Epstein & Robertson 2015 (contested generalisation) |
| Selective reading | Coverage nudges, not forced exposure | Robertson et al., Nature 2023 |

## Lenses
JSON files (see `lenses/`), stored in the user's browser unless exported. Controls: purpose, engines,
extra/reworded queries, source-type weights, Goggles-subset domain rules (boost/downrank/discard),
language target mix, max per domain, view width, slice mode, quality floor (label vs hide), rotation seed.
Precedents: Brave Goggles, Kagi Lenses/personalization, Kagi Small Web, Stract optics (archived), Marginalia.

## Architecture
Lens → query planner (rewordings, aspects, translations) → source adapters (Marginalia, Brave, Mojeek,
own Common Crawl slice) → merge & dedupe (normalised URL; engines found it) → signals & labels (fusion score,
agreement, source type, language, noise flags) → local re-rank (lens rules, domain cap, rotation) →
landscape (zone, radius, slice) + health panel.

## Health metrics
Top-3 domain share, domain Gini, domain diversity (normalised entropy), engine agreement, language mix vs
target, source-type mix, exposure Gini (position-weighted), noise share, rank uncertainty, coverage of what
the user opened.

## Legal / ToS
APIs only; no SERP scraping. Store only what each plan permits (default: request memory only). Per-vendor
adapters enforce terms and attribution. Own crawling follows RFC 9309. No query logs. Not legal advice.

## Prototype plan
1. Mountain view + local re-ranking on labelled sample ✅ (v0)
2. Merge engines (Marginalia + one paid) 3. Lens editor ✅ basic (save/export/import to finish)
4. Health panel ✅ (rank-uncertainty bar pending) 5. Multilingual fan-out 6. Common Crawl long-tail sample
7. Audit harness. See `BACKLOG.md`.

## Open decisions (owner)
- Which engines first (Marginalia free + Brave or Mojeek)?
- Personal tool or public product (storage rights, commercial keys)?
- Which languages first?
- Default view: classic list with optional mountain view (Hearst warns visualisations can hurt usability), or mountain first?
