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
