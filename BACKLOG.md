# Backlog

Ordered roughly by the prototype plan in docs/DESIGN.md. Check items off in PRs.

## Now (v0.x)
- [ ] Verify and enable the Marginalia adapter (free non-commercial key) against https://about.marginalia-search.com/article/api/
- [ ] Verify and enable one paid engine: Brave ($5/1k, ~200 results/query) or Mojeek (£2–3/1k)
- [ ] Language ID: replace script-only guess with fastText lid.176 (or CLD3) for Latin-script languages
- [ ] Near-duplicate detection: replace token Jaccard with SimHash (64-bit, Hamming ≤ 3)
- [ ] Public-suffix list for registered domains (replace the approximation in `server/urlnorm.py`)
- [ ] Rank-uncertainty bar per result in the UI (data already in `rank_spread`)
- [ ] "Random order within band" toggle (mitigates position effects)
- [ ] Export lens as file download (where the host allows) in addition to copy

## Next
- [ ] Multilingual fan-out: translated query variants per lens language target, translations labelled
- [ ] Query-aspect diversification (xQuAD-style) using reworded queries
- [ ] Topic clustering of the tail (Carrot2) as an extra slice mode
- [ ] Own long-tail sample: BM25 index over a Common Crawl slice (WET), labelled by licence
- [ ] Audit harness: fixed query set, monthly bias/noise report (Metaxa et al. audit method)
- [ ] Exposure rotation over time (Biega et al. amortised fairness) beyond the current seeded jitter

## Later / research
- [ ] Per-user bias awareness: on-device view of what your searches and reading leave out over time
- [ ] Per-user noise awareness: share of opened results later flagged as filler/duplicate
- [ ] Shared community lenses with provenance and review
- [ ] Open Web Index (EU) shards as an extra source (research licence)
- [ ] Evaluation set with per-language relevance judgments; diversity-aware nDCG
