# SearchInternetBetterBot and the own index

The crawler's User-Agent links to this page:
`SearchInternetBetterBot/0.1 (+<CRAWLER_INFO_URL>)`. If you run the crawler yourself, set
`CRAWLER_INFO_URL` to a page **you** control that says who runs it and how to reach you.
Operators who don't own this repository should not point at this file.

## What it is
A small research crawler that fills the own long-tail index (`server/index/`). It runs only
when someone starts it by hand (`python3 -m server.index crawl`). It does not run continuously.

## What it does (and doesn't do)
| Rule | Behaviour | Grounding |
| --- | --- | --- |
| robots.txt | RFC 9309 matching: longest match wins, allow wins ties, `*` and `$`; groups merged; `*` fallback. Fetched before the first page of each host; cached ≤ 24 h; ≤ 5 redirects; first 500 KiB parsed | [primary] https://www.rfc-editor.org/rfc/rfc9309.html |
| robots.txt status | 4xx → allowed; 5xx, timeout or DNS failure → host not crawled | RFC 9309 §2.3.1 |
| Crawl-delay | Not in RFC 9309. **Our policy**: honoured up to 60 s; hosts asking for more are skipped | CCBot also honours it: [primary] https://commoncrawl.org/faq |
| Page directives | `<meta name="robots">`, `<meta name="SearchInternetBetterBot">` and `X-Robots-Tag`: noindex, nofollow, none; `rel="nofollow"` links are not followed | |
| Rate | One request at a time per host, ≥ 5 s apart (configurable upward with `--delay`) | Mercator-style per-host queues: [primary] https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html |
| Back-off | 429/503: honours `Retry-After`, otherwise doubles the delay; 3 failures stop the host | CCBot adaptive back-off: [primary] https://commoncrawl.org/faq |
| Redirects | ≤ 4 per page, and each redirect target is checked against robots.txt again | CCBot follows up to 4 |
| Size | Body capped at 5 MiB; truncation recorded on the document | Common Crawl's cap since March 2025 |
| Never | Logins, cookies, JavaScript, forms, paywalls, access-control circumvention | Legal checklist in `docs/research/build_crawler.md` §7 |

Not implemented yet: conditional GET / re-crawl scheduling, sitemaps, Web Bot Auth (RFC 9421) signing,
a published IP range. Until those exist, run it slowly and on a small seed list.

## Bias levers (reported in each run's summary)
- `--max-per-domain` page budget per registered domain (default 50).
- Same-site by default: only links within the seed list's registered domains are followed (`--any-site` lifts this).
- Hosts are interleaved: the frontier orders hosts by their next allowed request time, so one large site can't monopolise a run.
- Seed choice is the biggest lever. Seed per language and region (national registries, universities, government, community directories), not only from link-popular English hosts.

## Common Crawl instead of crawling
`python3 -m server.index commoncrawl --crawl CC-MAIN-YYYY-WW --files 1 --per-file 5000` streams a
seeded random sample of WET files from `https://data.commoncrawl.org/` (list:
`crawl-data/<crawl>/wet.paths.gz`, per [primary] https://commoncrawl.org/get-started). The Common Crawl
Terms of Use apply. Language codes come from Common Crawl's own identification (`WARC-Identified-Content-Language`,
ISO 639-3, mapped to 639-1). Filters: `--lang en,de,ja`, `--max-per-domain N`. Plan on English skew
(about 42.6% of pages, [primary] https://commoncrawl.github.io/cc-crawl-statistics/plots/languages).

## Index
SQLite FTS5 (stdlib), BM25 (SQLite's fixed k1 = 1.2, b = 0.75) with our column weights title ×5, body ×1.
A second trigram-tokenised table serves queries containing Chinese, Japanese or Korean characters, because
unicode61 does not segment those scripts. Morphological analysers (Kuromoji, Nori, smartcn) would do better.
Near-duplicates (64-bit SimHash, Hamming ≤ 3, [primary] Manku et al. 2007,
https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/33026.pdf) are labelled, not dropped.
Each document stores its origin, licence label, fetch date and language with its reason. Every result shows these.

## Takedown and privacy
`python3 -m server.index remove --url URL` or `--domain example.org` deletes documents immediately.
The index stores pages, never queries. Extracted text can contain personal data, so keep the index
private (it is git-ignored) unless you have a lawful basis to publish it (see build_crawler.md §7).
