# search-internet-better

An experimental search engine that shows you the **whole landscape** of results for a question,
not just a top ten: the core everyone agrees on, the margins, and the long tail that popularity
ranking usually cuts off. You shape it with **lenses** (small rule files), and every search comes
with a **health panel** saying how concentrated, English-heavy or noisy the results are.

## Run it (no installs)
```
python3 -m server.app        # then open http://localhost:8000
```
With no API keys it runs on a clearly labelled **synthetic sample** (fictional `.example` sites).
To search the live web, copy `.env.example` to `.env` and add keys for Marginalia, Brave and/or Mojeek.

## The own index (no keys needed)
Besides the vendor APIs, the project has its own long-tail engine (`local`): a BM25 index you fill yourself.
```
python3 -m server.index commoncrawl --crawl CC-MAIN-2026-39 --files 1 --per-file 5000   # random Common Crawl sample
python3 -m server.index add some-file.warc.gz other.wet.gz                              # local WARC/WET files
python3 -m server.index crawl --seeds seeds.txt --max-pages 100                          # polite RFC 9309 crawler
python3 -m server.index stats                                                            # transparency stats (also GET /api/index)
python3 -m server.index remove --domain example.org                                      # takedown
```
Once the index holds documents, every lens queries it alongside the APIs. Results show their origin, licence and BM25 score.
Crawler policy and design: `docs/CRAWLER.md`.

## What you see
- **Mountain-peak view**: results as dots, centre = strongest combined relevance; slices by source type, language or engine; a width slider to include margins and tail.
- **Why it's here**: engines and ranks, rank spread, lens rules applied, source-type and language reasons, noise flags.
- **Health panel**: top-3 site share, source diversity, attention concentration, engine agreement, language and source-type mix, noise share.
- **Lens editor**: weights per source type, Brave-Goggles-style domain rules, language targets, per-domain cap, view width.

## Tests
```
python3 -m unittest discover -s tests -t .
```

Design: `docs/DESIGN.md`. Research notes with sources: `docs/research/`. Backlog: `BACKLOG.md`.
