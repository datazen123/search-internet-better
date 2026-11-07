# Building your own web crawler and search indexer: developer-level research

Research date: 2026-11-08. Every factual claim carries a URL tagged [primary] or [secondary]. Items marked **(UNVERIFIED)** were not retrieved this session (fetch blocked or page empty); they come from background knowledge and need checking before you rely on them. All text is paraphrased.

Source gaps to know about: IRLbot paper (blocked by robots), Olston & Najork survey (fetch failed), EDPB Opinion 28/2024 PDF and Dutch AP page (fetch failed; secondary summaries used), Japan e-Gov Art. 30-4 text (fetch failed), EUR-Lex DSM Directive text (page returned only metadata), Korea TDM-exception status (not stated by retrieved sources), cloud pricing (no primary pricing retrieved).

---

## 1. Reference architecture

### 1.1 Pipeline overview
Fetch loop: frontier -> DNS -> robots check -> fetch -> parse/extract links -> URL filter + URL-seen test -> content-seen test -> store (WARC) -> index. This matches Mercator's design: worker threads pull a URL from the frontier, download it, run content-type-specific processing modules, and pass extracted links through a URL filter and duplicate-URL eliminator. [primary] https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf

### 1.2 URL frontier (Mercator front/back queues)
- Goals: one connection per host at a time, a gap of seconds between hits to the same host, high-priority pages first. [primary] https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html
- Front queues = priority (a prioritizer assigns an integer priority, e.g. from change history). Back queues = politeness, each holding URLs from a single host. A heap holds one entry per back queue with the earliest time that host may be contacted again. [primary] same URL
- Refill: when a back queue empties, pull from a front queue (biased to higher priority) until you find a URL whose host has no back queue; update the host-to-queue table. [primary] same URL
- Sizing rules of thumb: about 3 back queues per fetcher thread; wait about 10x the last fetch duration before re-contacting a host. [primary] https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html and https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf
- At web scale the frontier mostly lives on disk, with only queue heads in RAM. [primary] https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html
- Reusable implementation: the URL Frontier project defines a language-neutral gRPC API (get next URLs, update processed URLs, set per-host crawl rate, list hosts, stats), with a reference service and conformance test suite; Apache-2.0. [primary] https://github.com/crawler-commons/url-frontier

### 1.3 DNS
Mercator found the stock synchronized resolver allowed one outstanding lookup per process; a multi-threaded resolver talking to a local name server cut DNS from 70% to 14% of per-thread time. Lesson: run a local caching resolver and async lookups. [primary] https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf

### 1.4 Fetcher
- Async I/O, HTTP/1.1 plus HTTP/2, conditional GET, compression. CCBot, for example, supports HTTP/1.1 and HTTP/2 (TLS only), conditional GET, gzip/Brotli/Zstd, follows up to 4 redirects (5 for robots.txt), runs no JavaScript and keeps no cookies. [primary] https://commoncrawl.org/faq
- Google's crawlers use ETag/If-None-Match and Last-Modified/If-Modified-Since (ETag preferred when both exist) and default to HTTP/1.1 even though they support HTTP/2. [primary] https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers
- Size caps: Common Crawl raised its truncation limit from 1 MiB to 5 MiB from the March 2025 crawl. Pick a cap and record truncation in metadata. [primary] https://commoncrawl.org/blog/september-2026-crawl-archive-now-available
- Always set connect, read and total timeouts, and a max redirect count (see Section 9 for trap/robustness limits).

### 1.5 robots.txt per RFC 9309
- 2xx: parse and obey; unparseable lines are skipped. 3xx: follow at least 5 hops; beyond that may treat as unavailable. 4xx: treated as unavailable, so crawling is allowed. 5xx/unreachable: assume complete disallow; if undefined for a long time (30 days is the RFC's example) you may treat it as unavailable or keep using a cache. [primary] https://www.rfc-editor.org/rfc/rfc9309.html
- Cache: may cache; should not use a cached copy beyond 24 hours except when unreachable. Parse at least the first 500 KiB. [primary] https://www.rfc-editor.org/rfc/rfc9309.html
- Matching: case-sensitive paths; longest match wins; allow beats disallow on a tie; no match means allowed; `*` and `$` supported; product tokens case-insensitive; matching groups merge; fall back to the `*` group. [primary] https://www.rfc-editor.org/rfc/rfc9309.html
- Crawl-delay is not in the RFC (and Google ignores it; Google only supports user-agent, allow, disallow, sitemap), but CCBot honors it. Decide your own policy and document it. [primary] https://www.rfc-editor.org/rfc/rfc9309.html ; https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt ; https://commoncrawl.org/faq
- Google's concrete 5xx behavior: stop crawling for 12 hours, then use last good cache up to 30 days, then behave as if no robots.txt if the site is otherwise reachable. DNS, network and timeout failures count as 5xx. [primary] https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt
- Do not hand-write the parser: Google open-sourced its C++ parser/matcher (Apache-2.0, Bazel tests `robots_test`); it follows the REP spec for RFC 3986-conformant input but does not claim full RFC 9309 conformance. [primary] https://github.com/google/robotstxt

### 1.6 Sitemaps and push signals
- Sitemap limits: 50,000 URLs and 50 MB uncompressed per file; sitemap index up to 50,000 sitemaps; `lastmod` should reflect real page modification time; `Sitemap:` line in robots.txt; cross-host submission requires ownership proof via robots.txt. [primary] https://www.sitemaps.org/protocol.html
- IndexNow: site proves ownership with a key file (8-128 chars); batch POST up to 10,000 URLs; response codes 200/202/400/403/422/429. Consuming it as a search engine requires participation rules (market presence). [primary] https://www.indexnow.org/documentation

### 1.7 URL normalization and dedup
- URL-seen test: Mercator stored 8-byte Rabin fingerprints (1 billion = a little over 5 GB). A seek-per-lookup disk design capped throughput near 75 downloads/s; the better design batches new fingerprints in memory and merges sequentially into a sorted disk file. [primary] https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf
- Bloom filter option: trade a small false-positive rate (you never crawl a few new URLs) for RAM. (Technique is standard; no primary crawler source retrieved this session.) **(UNVERIFIED)**
- Near-duplicate content: shingle (k about 4 words), Jaccard threshold such as 0.9, min-hash sketches of about 200 permutations, super-shingles to avoid all-pairs comparison. [primary] https://nlp.stanford.edu/IR-book/html/htmledition/near-duplicates-and-shingling-1.html
- SimHash at web scale (Google, WWW 2007): 64-bit fingerprints, near-duplicate if Hamming distance at most 3 (precision and recall both about 0.75), multiple permuted sorted tables, 8 billion fingerprints is about 64 GB uncompressed. [primary] https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/33026.pdf

### 1.8 Parsing and extraction
- Boilerplate removal: trafilatura's own benchmark (990 docs, run 2026-10-02) puts trafilatura at about 0.92 F-score, jusText about 0.86, readability-lxml about 0.85. Caveat: author-run, test set skewed to German web pages, segments "not statistically representative". Treat as indicative. [secondary: vendor/author benchmark] https://trafilatura.readthedocs.io/en/latest/evaluation.html
- Tika is the parser behind StormCrawler's ParserBolt. [primary] https://stormcrawler.apache.org/
- Language ID: fastText lid.176 covers 176 languages; 126 MB full model, about 917 KB compressed model; CC BY-SA 3.0. [primary] https://fasttext.cc/docs/en/language-identification.html . Common Crawl's own language stats use CLD2. [primary] https://commoncrawl.github.io/cc-crawl-statistics/plots/languages (CLD3 not covered by fetched sources.)

### 1.9 JavaScript rendering tradeoffs
Common Crawl's crawler does not execute JavaScript. [primary] https://commoncrawl.org/faq . Crawlee offers one interface for plain HTTP and Playwright/Puppeteer, which makes a two-tier design natural: HTTP first, render only when extraction yields too little. [primary] https://github.com/apify/crawlee . Cost and sandboxing implications are in Sections 9 and 10.

### 1.10 Storage (WARC)
WARC (ISO 28500:2009) is a series of records with headers (date, type, length) and a content block; record types: warcinfo, response, resource, request, metadata, revisit, conversion, continuation; per-record gzip allows random access by offset; v1.1 dropped angle brackets around target URIs. [primary] https://www.loc.gov/preservation/digital/formats/fdd/fdd000236.shtml

### 1.11 Inverted index and compression
- Brin and Page's original layout: forward barrels sorted into inverted barrels, 2-byte hits, separate short index for title/anchor hits, repository compressed with zlib (about 3:1; bzip about 4:1). 24M pages fetched gave a 108.7 GB total with repository (55.2 GB excluding it); full inverted index was 37.2 GB. [primary] http://infolab.stanford.edu/~backrub/google.html
- Postings: store docID gaps, encode with variable-byte codes (7 payload bits/byte); bit-level gamma/delta codes compress more at CPU cost; VB cut Reuters RCV1 to 116 MB. [primary] https://nlp.stanford.edu/IR-book/html/htmledition/variable-byte-codes-1.html . Tantivy uses SIMD integer compression and mmap. [primary] https://github.com/quickwit-oss/tantivy

### 1.12 Ranking basics
- BM25 defaults in Elasticsearch: k1 = 1.2, b = 0.75. [primary] https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html
- PageRank: damping 0.85 in the original paper; computable for 26M pages in hours on one workstation (1998). [primary] http://infolab.stanford.edu/~backrub/google.html
- Freshness: Cho and Garcia-Molina's refresh-policy work (freshness and age metrics; counter-intuitively, a uniform policy beats proportional revisit). Fetch failed; the UW PDF was a login page. **(UNVERIFIED)** Candidate reading: https://courses.cs.washington.edu/courses/cse591d/00sp/cho.pdf (needs access).

### 1.13 Hybrid/vector option
Vespa combines free-text, structured and ANN vector conditions in one query with a query plan, and runs ranking expressions/ONNX models in stages. [primary] https://docs.vespa.ai/en/overview.html . Meilisearch offers hybrid search (semantic + full-text); its docs path suggests it is experimental. [primary] https://github.com/meilisearch/meilisearch

---

## 2. Open-source building blocks

| Component | Role | License | Language | Scale / maturity notes | Source |
|---|---|---|---|---|---|
| Apache Nutch | Crawler | Apache (project page does not state it; ASF project) | Java | Batch, Hadoop-based; plugin system; Solr/Elasticsearch indexing. CCBot is Nutch-based on Hadoop. | [primary] https://nutch.apache.org/ ; https://commoncrawl.org/faq |
| StormCrawler | Crawler SDK | Apache-2.0 | Java | Continuous, streaming on Apache Storm; OpenSearch/Solr/SQL modules; in production since 2014; no throughput numbers published on the page. | [primary] https://stormcrawler.apache.org/ |
| Heritrix 3 | Archival crawler | Apache-2.0 | Java | Internet Archive; robots/politeness built in; REST API; bean-based jobs; activity level unclear from page. | [primary] https://github.com/internetarchive/heritrix3 |
| Scrapy | Framework | BSD-3-Clause | Python | Very widely used (about 64k stars); extraction-oriented; broad-crawl needs your own frontier. | [primary] https://github.com/scrapy/scrapy |
| Crawlee | Framework | Apache-2.0 | JS/TS (Python port) | HTTP + headless browser, proxy rotation, persistent queue. | [primary] https://github.com/apify/crawlee |
| Colly | Framework | Apache-2.0 | Go | Per-domain delay/concurrency, robots; project claims over 1k req/s per core (self-reported). | [primary] https://github.com/gocolly/colly |
| Common Crawl data | Shortcut | Free access, Terms of Use apply | WARC/WAT/WET | See Section 3. | [primary] https://commoncrawl.org/get-started |
| Lucene / Solr | Index | Apache-2.0 (Apache projects) | Java | Analyzers incl. Kuromoji, Nori, SmartCN. | [primary] https://lucene.apache.org/core/10_0_0/analysis/nori/index.html |
| OpenSearch | Index server | Apache-2.0 fork (license not on fetched page) **(UNVERIFIED)** | Java | Docs: https://docs.opensearch.org/latest/ | [primary] |
| Elasticsearch | Index server | Elastic changed licenses in 2021 (to ELv2/SSPL); in Aug 2024 announced adding AGPL as an option | Java | Verify current terms before adoption. | [primary] https://www.elastic.co/blog/elasticsearch-is-open-source-again |
| Vespa | Index + serving + ML | License not stated on fetched page (believed Apache-2.0) **(UNVERIFIED)** | C++/Java | Content clusters replicate and auto-rebalance; scales by adding nodes. | [primary] https://docs.vespa.ai/en/overview.html |
| Tantivy | Index library | MIT | Rust | Lucene-like, BM25; CJK via third-party crates (jieba, lindera, Vaporetto); distributed search is Quickwit's job; speed claims self-reported. | [primary] https://github.com/quickwit-oss/tantivy |
| Meilisearch | Search server | MIT community edition; sharding etc. under Business Source License / commercial | Rust | Optimized for Chinese, Japanese, Hebrew, Latin-alphabet languages; Korean not mentioned. | [primary] https://github.com/meilisearch/meilisearch |
| Typesense | Search server | GPL-3 **(UNVERIFIED; docs page failed to load)** | C++ | In-memory design (unverified). | n/a |

---

## 3. Build versus bootstrap with Common Crawl

- Formats: WARC (raw HTTP responses/requests and crawl metadata), WAT (JSON metadata: headers, links), WET (extracted plain text). Hosted in `s3://commoncrawl/` (us-east-1), also HTTPS at data.commoncrawl.org; process in us-east-1 to avoid transfer fees. [primary] https://commoncrawl.org/get-started
- Scale of one recent crawl (CC-MAIN-2026-39): 2.17 billion pages, 361.4 TiB uncompressed, 587.2 million URLs new to the project, 40.4 million hosts / 33.2 million registered domains. [primary] https://commoncrawl.org/blog/september-2026-crawl-archive-now-available
- It is a sample: Common Crawl says it archives a randomly selected subset of a site, not whole sites. [primary] https://commoncrawl.org/faq
- Index and stats: per-crawl stats (pages, unique URLs, digests, hosts, TLD, MIME, language since 2018) are at https://commoncrawl.github.io/cc-crawl-statistics/ [primary] https://github.com/commoncrawl/cc-crawl-statistics . The fetched get-started page lists a CDXJ index and URL index but did not describe the columnar Parquet index; check https://commoncrawl.org/get-started and index.commoncrawl.org directly.
- When to bootstrap: prototype ranking, tokenization, language and quality filters with CC; use your own crawler only for freshness-critical or underrepresented sources. WARC byte-range reads by offset (from the index) let you pull individual pages without downloading whole files. [primary] https://www.loc.gov/preservation/digital/formats/fdd/fdd000236.shtml (per-record gzip)
- Cost numbers: no primary price table retrieved this session. Model the cost from: storage = TiB x provider rate; egress is avoided when computing in us-east-1 (per Common Crawl guidance above).

---

## 4. Being a good citizen

- Identification: stable UA with a product token, version and a URL describing the bot (CCBot/2.0 with a FAQ URL is the model). Heritrix docs tell operators to put contact info in the UA. [primary] https://commoncrawl.org/faq ; https://github.com/internetarchive/heritrix3
- Publish IP ranges as JSON and keep reverse DNS working so webmasters can verify via forward/reverse DNS (CCBot publishes /ccbot.json with dedicated IPv4 blocks). [primary] https://commoncrawl.org/faq
- robots.txt: follow Section 1.5 semantics exactly; re-fetch at least daily.
- Back-off: CCBot applies adaptive back-off on 429 and 5xx. [primary] https://commoncrawl.org/faq . Honor `Retry-After` on 429/503 (header semantics are in HTTP standards; not fetched) **(UNVERIFIED)**.
- Web Bot Auth: sign requests per RFC 9421. RFC defines Signature-Input/Signature, parameters created, expires, nonce, keyid, tag, alg, and supports Ed25519. [primary] https://www.rfc-editor.org/rfc/rfc9421.html . Cloudflare's recipe: Ed25519 key, JWK directory at `/.well-known/http-message-signatures-directory` (media type application/http-message-signatures-directory+json, self-signed with tag `http-message-signatures-directory`), requests carry `Signature-Input` (tag `web-bot-auth`, keyid = JWK thumbprint, created, short expires), `Signature`, and `Signature-Agent`; sign at least `@authority`; test at crawltest.com. [primary] https://developers.cloudflare.com/bots/concepts/bot/verified-bots/web-bot-auth/
- Cloudflare verified-bot criteria: deterministic identity (Web Bot Auth, or IP list + stable UA), reasonable request rates, obey robots and crawl-delay, declared purpose must match observed behavior. [primary] https://developers.cloudflare.com/bots/concepts/bot/verified-bots/policy/
- Note: the IETF Web Bot Auth drafts themselves were not fetched; verify draft status before depending on them.

---

## 5. Designing to reduce noise and bias

These are design proposals; the supporting evidence is cited per item.

1. Measure the skew first. In the latest Common Crawl crawl, English is about 42.6% of pages, then Russian 6.3%, German 5.8%, Japanese 4.9%, French 4.8%, Spanish 4.7%, Chinese 4.4%, Korean 0.9% (CLD2 detection). [primary] https://commoncrawl.github.io/cc-crawl-statistics/plots/languages
2. Seed diversity and quotas: seed per language/region from national registries, government and university listings, and sitemaps; set per-language and per-registered-domain budgets in the frontier priority function, so the front queues are not dominated by link-popular English hosts. (Design recommendation. Related evidence: IRLbot-style per-domain budgets curb spam and trap domains **(UNVERIFIED, paper not retrieved)**; China's standard GB/T 45652-2025 reportedly requires diverse data sources and caps illegal/undesirable content at 5% [secondary] https://hankunlaw.com/portal/article/index/cid/8/id/16431.html .)
3. Language ID at crawl time: run fastText lid (or CLD2) on extracted text; store language and confidence on every record; sample low-confidence docs for human review. [primary] https://fasttext.cc/docs/en/language-identification.html
4. Spam and machine-translated slop: use content-seen and near-duplicate suppression (SimHash k=3 or min-hash) to collapse template and spun content; add a quality classifier trained on labeled samples; down-weight domains with high duplicate ratios. [primary] https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/33026.pdf (dedup method). No primary source on MT-slop detection retrieved.
5. Popularity bias: PageRank-style ordering favors link-rich pages; mix it with per-host/per-language fairness quotas and random exploration slices (design recommendation).
6. Transparency: publish crawl stats the way Common Crawl does (pages, unique URLs, hosts, languages, MIME) per crawl. [primary] https://github.com/commoncrawl/cc-crawl-statistics

---

## 6. Multilingual specifics

- Chinese: Lucene SmartChineseAnalyzer (simplified Chinese; HMM package exists; limits not documented on the overview page). [primary] https://lucene.apache.org/core/10_0_0/analysis/smartcn/index.html . Rust options: tantivy-jieba, lindera, Vaporetto. [primary] https://github.com/quickwit-oss/tantivy
- Japanese: Kuromoji morphological analyzer with POS tagging, lemmatization, compound analysis. [primary] https://lucene.apache.org/core/10_0_0/analysis/kuromoji/index.html (tokenizer modes search/extended are not on that page **(UNVERIFIED)**).
- Korean: Nori morphological analyzer with POS filtering, decompounding and hanja-to-hangul conversion. [primary] https://lucene.apache.org/core/10_0_0/analysis/nori/index.html (decompound modes and mecab-ko-dic base: **UNVERIFIED** on that page).
- Meilisearch lists Chinese, Japanese, Hebrew as optimized; Korean not listed. [primary] https://github.com/meilisearch/meilisearch
- Not retrieved this session: ICU analysis chain, NFKC normalization, RTL (Arabic/Hebrew) and Indic specifics. Recommended starting points to fetch: Lucene analysis-icu docs and Unicode UAX #15 (normalization). **(UNVERIFIED)**
- Practical rule: tokenizer choice is per field and per language; keep the language code in the index, and do not share one analyzer across languages.

---

## 7. Legal and ethical checklist by jurisdiction

This is research, not legal advice. Dates are those stated in sources.

**United States**
- hiQ v. LinkedIn (9th Cir., on remand after Van Buren): the court found a serious question that the CFAA "without authorization" clause does not reach scraping of public pages, but it was a preliminary-injunction ruling and left open the final CFAA holding and LinkedIn's defenses. [primary] https://law.justia.com/cases/federal/appellate-courts/ca9/17-16783/17-16783-2022-04-18.html
- Meta v. Bright Data (N.D. Cal., Jan 23, 2024): Meta's terms could not be read to bar logged-off scraping of public data; limited to those terms; logged-in scraping not decided; other claims remained. [secondary: law-firm alert] https://www.quinnemanuel.com/the-firm/news-events/client-alert-what-does-the-meta-v-bright-data-summary-judgment-ruling-mean-for-web-scraping/
- Checklist: no logins, no circumvention of access controls, honor robots.txt and cease-and-desist letters, avoid creating ToS acceptance (accounts).

**European Union**
- GDPR: scraped personal data needs a lawful basis. EDPB Opinion 28/2024 sets a three-step legitimate-interest test (interest, necessity, balancing) with reasonable expectations and mitigating measures such as limits on collection and an opt-out. [secondary] https://thelens.slaughterandmay.com/post/102ju1c/ai-development-meets-gdpr-key-takeaways-from-the-edpbs-latest-opinion (primary PDF fetch failed; find it at edpb.europa.eu)
- Dutch AP: guidance (2024) says scraping is illegal under GDPR in most contexts; public availability does not equal consent. [secondary] https://iapp.org/news/a/netherlands-dpa-issues-guidance-against-web-scraping (primary AP page not retrieved; the IAPP page gave no date, other search results dated it around May 2024)
- Erasure (Art. 17): grounds include data no longer needed, objection under Art. 21, unlawful processing; controller must take reasonable steps to inform other controllers; exceptions include archiving/research where erasure would seriously impair the goal. [primary] https://gdpr-info.eu/art-17-gdpr/
- Database rights: CJEU Ryanair v PR Aviation (C-30/14): databases outside both copyright and sui generis protection are not covered by the Directive's mandatory user-rights provisions, so contract terms can restrict scraping. [secondary] https://legalblogs.wolterskluwer.com/copyright-blog/ryanair-ltd-v-pr-aviation-bv-contracts-rights-and-users-in-a-low-cost-database-law/
- DSM Directive 2019/790 (in force 6 June 2019) Arts. 3 and 4 TDM exceptions, including the Art. 4 rightsholder reservation by machine-readable means. [primary] https://eur-lex.europa.eu/eli/dir/2019/790/oj/eng (article text not retrieved: **UNVERIFIED** details; treat robots.txt and similar signals as the likely reservation channel, to be confirmed by counsel).

**United Kingdom**
- Existing TDM exception is s.29A CDPA. March 2026 government report under the Data (Use and Access) Act 2025 endorsed none of four options, left the law unchanged, and plans monitoring and evidence gathering; the earlier opt-out preference was dropped. [secondary] https://www.dlapiper.com/insights/publications/2026/03/tdm-and-training-ai-models-uk-government-publishes-report-and-impact-assessment (s.29A's non-commercial scope: UNVERIFIED in that page).

**Japan**
- Art. 30-4 Copyright Act (introduced by the 2018 amendment as a flexible rights limitation) targets uses such as AI/IoT/big data that do not significantly affect the market for the works. Agency for Cultural Affairs published "General Understanding on AI and Copyright" on 15 March 2024, plus a checklist and guidance on 31 July 2024. [primary] https://www.bunka.go.jp/seisaku/chosakuken/aiandcopyright.html (statute text and "enjoyment" / unreasonable-prejudice proviso detail not retrieved: **UNVERIFIED**).

**South Korea**
- Ministry of Culture, Sports and Tourism guide on fair use for generative AI training (Korean edition February 2026, English 18 May 2026) applies the four factors of Copyright Act Art. 35-5; commercial or web-crawling training is not automatically excluded; hypothetical cases are not authoritative interpretations. [primary] https://www.mcst.go.kr/english/policy/pressView.jsp?pSeq=635 ; [secondary] https://www.koreatimes.co.kr/amp/southkorea/20260518/korea-enters-global-ai-copyright-fray-with-english-guidebook
- Whether Korea has a dedicated TDM exception: not answered by retrieved sources; check statute and current bills with Korean counsel. Other regimes to check (Network Act, Unfair Competition Prevention Act, PIPA): not retrieved.

**China**
- Han Kun (April 2026): 2025 revision of the Anti-Unfair Competition Law added a provision (Art. 13) on improper data acquisition, e.g. circumventing technical measures; Interim Measures for Generative AI (2023) Art. 7 requires assessing legality of training data sources; Chinese courts have found unfair competition in substitutive scraping (Beijing IP Court Guiding Case 262; Shenzhen RMB 19.5M damages) while fair-use treatment of training is unsettled; national standards GB/T 45652-2025 and GB/T 45654-2025 call for authorization, respecting robots protocols and keeping collection records. [secondary: law firm commentary] https://hankunlaw.com/portal/article/index/cid/8/id/16431.html
- PIPL / Data Security Law / Cybersecurity Law specifics were not analyzed in that source; retrieve primary text before operating in China.

**Cross-jurisdiction operating rules (design recommendations)**: honor robots.txt and any machine-readable reservation; keep a documented takedown path; keep provenance per record (Section 11); do not collect from login-gated or paywalled areas; minimize personal data (drop it at extraction).

---

## 8. Phased build plan

| Phase | Scope | Components | Sizing evidence |
|---|---|---|---|
| 0. Bootstrap | Use a Common Crawl slice; build extraction, language ID, tokenization, BM25 | warcio-style WARC reader, trafilatura, fastText, Lucene/Tantivy | Brin & Page 1998 index was about 55 GB excluding repository for 24M pages (about 2.3 KB/page index; about 4.5 KB/page including repository) [primary] http://infolab.stanford.edu/~backrub/google.html |
| 1. MVP single machine | 1-10M pages, own politeness, robots, WARC output | Frontier with per-host queues and heap; sqlite/RocksDB URL-seen; async fetcher | Mercator on one 1999-era 4-server setup reached about 50M docs/day, network-limited, CPU under 50% [primary] https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf |
| 2. Scale-up single node | 100M-1B URLs | Disk-batched URL-seen (merge sorted fingerprint files); SimHash dedup | 1B 8-byte fingerprints about 5 GB; 8B SimHash about 64 GB [primary] Mercator PDF above; Manku et al. above |
| 3. Distributed | Partition frontier by host; Storm/Kafka-style streaming or Nutch/Hadoop batch; index shards | StormCrawler + OpenSearch or Nutch; or Vespa content cluster | See Section 9 |
| 4. Quality and fairness | Language quotas, spam classifier, evaluation harness, transparency stats | See Sections 5, 10 | CC monthly stats as the template |

IRLbot (single-server crawl of several billion pages; DRUM disk-based URL checking; budget-based spam control) is the key reference for phase 2; its figures could not be fetched here. **(UNVERIFIED)** Check https://research.cs.tamu.edu/irl/ via a mirror or the WWW 2008 proceedings.

---

## 9. Systems engineering: design and implementation considerations

### 9.1 Requirements and trade studies
- Functional: coverage (what fraction of target web/language set), freshness (age of copies), politeness (max load per host), content quality, index query features, provenance and takedown.
- Non-functional: throughput (pages/s), latency (fetch to searchable), availability, cost per million pages, operability.
- Main tensions: coverage vs freshness (a fixed fetch budget; Olston and Najork's survey frames crawling as optimizing coverage, freshness and politeness together; fetch failed, **UNVERIFIED**); politeness vs throughput (per-host delay bounds per-host rate, so throughput scales with number of distinct hosts, which is why back queues scale with threads [primary] https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html ); quality vs cost (rendering JS and running classifiers per page).
- Do the trade study with measurable targets, e.g. "95% of pages in news class refreshed within 6 h", "p99 per-host request interval at least X s".
- Cho and Garcia-Molina refresh results (uniform beats proportional) should drive recrawl design. **(UNVERIFIED, see 1.12)**

### 9.2 Capacity planning and sizing math (from primary data)
- Bytes/page: Common Crawl Sept 2026: 361.4 TiB / 2.17B pages is about 170 KiB uncompressed per page (computed from the figures in the blog). [primary] https://commoncrawl.org/blog/september-2026-crawl-archive-now-available
- Throughput: Brin and Page peaked above 100 pages/s with 4 crawlers (1998). Mercator averaged about 50M docs/day (about 580 docs/s) on a 160 Mbit/s link. [primary] http://infolab.stanford.edu/~backrub/google.html ; https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf
- Back-of-envelope: at 170 KiB/page, 1,000 pages/s is about 1.4 Gbit/s sustained inbound. Bandwidth is the first wall; in Mercator the crawl was network-limited, not CPU-limited. (Derived arithmetic.)
- Index-to-text ratios: 1998 index (without repository) was about 51% of the compressed repository (55.2 GB vs 53.5 GB repository; fetched HTML 147.8 GB). [primary] http://infolab.stanford.edu/~backrub/google.html . Modern ratios depend on analyzers and stored fields; measure on your own sample.
- Dedup memory: 8 B/URL fingerprint, 8 B/SimHash (plus table overhead). [primary] Mercator and Manku PDFs above.
- Frontier size: you need roughly 3 back queues per thread. [primary] https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html

### 9.3 Distributed design
- Partition the frontier by host (or registered domain) with consistent hashing so one worker owns all politeness state for a host; Mercator did host partitioning with a host splitter and about 80% of links staying local (relative links). [primary] https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf . Consistent hashing itself and work stealing are standard techniques; no primary crawler source retrieved. **(UNVERIFIED)**
- Frontier as a service: URL Frontier's gRPC API decouples crawler workers from the frontier store. [primary] https://github.com/crawler-commons/url-frontier
- Streaming vs batch: StormCrawler processes continuously on Storm with "guaranteed processing" (at-least-once; no silent loss), while Nutch runs batch jobs on Hadoop. [primary] https://stormcrawler.apache.org/ ; https://nutch.apache.org/ . Kafka as a queue between stages is a common pattern but was not on the fetched StormCrawler page. **(UNVERIFIED)**
- Delivery semantics: assume at-least-once, make fetch and index writes idempotent (key by URL fingerprint + fetch timestamp; dedup downstream). Checkpoint frontier state: Mercator checkpointed 1-4 times a day. [primary] https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf
- Back-pressure: bound queues between fetch, parse and index; when index lags, slow fetch rather than drop.
- Storage tiers: WARC on object storage as the system of record (immutable, content-addressed); derived indexes rebuildable from WARC. Common Crawl itself is WARC in S3. [primary] https://commoncrawl.org/get-started
- Index sharding/replication: Vespa content clusters replicate by configured count and rebalance automatically, queries fan out to relevant nodes [primary] https://docs.vespa.ai/en/overview.html ; Tantivy leaves distribution to Quickwit; Meilisearch sharding is an enterprise (BSL) feature [primary] https://github.com/quickwit-oss/tantivy ; https://github.com/meilisearch/meilisearch . OpenSearch shard-size guidance: page fetch did not cover it **(UNVERIFIED)**; measure.

### 9.4 Failure modes and robustness
- Spider traps, infinite calendars, session-ID URL explosions: cap URLs per host and per path pattern, cap depth, budget per domain; Mercator's paper does not discuss traps [primary] https://www.cs.cornell.edu/courses/cs685/2002fa/mercator.pdf , so use IRLbot-style budgets **(UNVERIFIED)** plus near-duplicate detection to notice repetitive content.
- Soft-404s: detect via near-duplicate fingerprints of error templates per host.
- Redirect loops: hard hop limit (CCBot 4 for pages, 5 for robots.txt; Google 5 for robots.txt). [primary] https://commoncrawl.org/faq ; https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt
- DNS failures: Google treats DNS/network/timeouts on robots.txt as server errors; mirror that. [primary] https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt
- Cloaking and adversarial content: compare responses fetched with different UAs on a sample; quarantine hosts that serve crawler-only content (design recommendation).

### 9.5 Security
- SSRF: your fetcher will be asked to fetch attacker-chosen URLs. Resolve DNS, validate the IP against blocked ranges (loopback, RFC1918, link-local incl. 169.254.169.254 cloud metadata, IPv6 ULA), connect to the validated IP while preserving Host/SNI, re-validate every redirect hop or disable automatic redirects. Prefer IMDSv2. [primary] https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- Decompression bombs and oversized bodies: enforce max decompressed size (note the Sitemap spec's own 50 MB cap applies after decompression) [primary] https://www.sitemaps.org/protocol.html ; cap robots.txt parse at 500 KiB or more [primary] https://www.rfc-editor.org/rfc/rfc9309.html
- Malicious files and parsers: run Tika/PDF/office parsers out-of-process in a sandbox with CPU/memory/time limits. (Standard practice; no primary source fetched.) **(UNVERIFIED)**
- Headless browsers: separate network namespace, no access to internal networks or credentials, ephemeral profiles, kill on timeout (same SSRF rules apply to subrequests). Crawlee documents the browser tier but not sandboxing. [primary] https://github.com/apify/crawlee
- Secrets and supply chain: no credentials on fetcher nodes; pin dependencies; the Web Bot Auth private key (the JWK `d` value) must never be published or sit on crawl nodes beyond the signer. [primary] https://developers.cloudflare.com/bots/concepts/bot/verified-bots/web-bot-auth/

### 9.6 Observability and operations
- Use Google SRE's four golden signals (latency, traffic, errors, saturation); page on symptoms, alert on causes only when definite and imminent; low-urgency items go to dashboards. [primary] https://sre.google/sre-book/monitoring-distributed-systems/
- Crawler-specific metrics: fetch rate per host and per registered domain, HTTP status class mix, DNS error rate, robots.txt status mix (watch 5xx robots which block hosts), frontier size by priority, back-queue idle ratio, URLs/s through URL-seen, bytes in/out, duplicate ratio, language mix vs quota, freshness lag per class, parse failure rate, index lag.
- Candidate SLOs: politeness violations = 0 (hard), robots staleness at most 24 h (matches RFC cache guidance [primary] https://www.rfc-editor.org/rfc/rfc9309.html ), freshness lag per class, index lag p95.

### 9.7 Testing and verification
- Robots conformance: run your parser against Google's open-source parser tests (`robots_test.cc`) as a differential oracle, and add RFC 9309 cases (5xx, 5-hop redirects, longest-match, `$`/`*`). [primary] https://github.com/google/robotstxt ; https://www.rfc-editor.org/rfc/rfc9309.html
- URL Frontier ships a conformance test suite for frontier implementations. [primary] https://github.com/crawler-commons/url-frontier
- Synthetic web: a local generator of hosts with configurable latency, error rates, infinite calendars, redirect loops, soft-404s and cloaking, to test politeness and trap handling under load (design recommendation).
- Index quality: build relevance judgments and compute nDCG / precision-recall on a test collection; the IR book chapter covers test collections, unranked and ranked measures, relevance assessment and refining a deployed system. [primary] https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-in-information-retrieval-1.html (TREC/pooling/nDCG pages are linked subsections, not read).
- Extraction quality: evaluate on your own multilingual sample; published extraction benchmarks are author-run and German-skewed. [secondary] https://trafilatura.readthedocs.io/en/latest/evaluation.html

### 9.8 Data governance
- Retention and erasure: build an erasure pipeline that can find a URL or person across WARC, derived text, index, and caches; GDPR Art. 17 requires erasure without undue delay when grounds apply and reasonable steps to tell other controllers. Archiving/research exceptions are narrow. [primary] https://gdpr-info.eu/art-17-gdpr/
- Provenance and audit logs: per record keep URL, fetch time, IP/UA used, robots decision and version, HTTP status, content digest, language, extraction version. WARC `warcinfo`/`metadata`/`revisit` record types fit this. [primary] https://www.loc.gov/preservation/digital/formats/fdd/fdd000236.shtml
- Transparency: public crawler page (UA, purpose, IP list JSON, opt-out instructions) and per-crawl statistics. [primary] https://commoncrawl.org/faq ; https://github.com/commoncrawl/cc-crawl-statistics
- Respect reservations: Chinese standards reportedly require robots-protocol respect and collection records [secondary] https://hankunlaw.com/portal/article/index/cid/8/id/16431.html ; EDPB lists opt-out and collection limits as mitigations [secondary] https://thelens.slaughterandmay.com/post/102ju1c/ai-development-meets-gdpr-key-takeaways-from-the-edpbs-latest-opinion

### 9.9 Team and expertise
| Role | Owns |
|---|---|
| Crawler / distributed-systems engineers | Frontier, fetcher, politeness, robots, scheduling, back-pressure, checkpointing |
| IR / ranking scientists | Tokenization choices, BM25 and learned ranking, dedup thresholds, evaluation sets and metrics |
| SRE | SLOs, capacity, on-call, incident response, cost control |
| Data engineers | WARC pipeline, object storage, index builds, dataset publication |
| NLP / linguists (per language) | Segmenters, language ID quality, normalization, translation-slop detection |
| Trust and safety / spam | Spam/quality classifiers, abuse reports, cloaking and trap hunting |
| Security engineer | SSRF controls, sandboxing, supply chain, key management |
| Legal / policy | Jurisdiction checklist (Section 7), takedowns, privacy impact, ToS review, transparency page |

### 9.10 Build versus buy and cost drivers
- Cost drivers in order of typical impact: bandwidth and fetch concurrency (network-limited in Mercator), storage (WARC at about 170 KiB/page uncompressed, before compression), compute for parsing/extraction/classifiers, headless rendering (CPU/RAM heavy; no primary figures retrieved), index storage and replication, people (Section 9.9).
- Buy/borrow: Common Crawl for historical breadth (Section 3); OpenSearch/Vespa managed or self-hosted for the index; Elasticsearch only after checking the current license. [primary] https://www.elastic.co/blog/elasticsearch-is-open-source-again
- Build: frontier policy, quality/bias controls and multilingual analysis, which are where differentiation lives.
- Pricing: no primary cloud price pages were retrieved; pull current S3, egress and compute prices from provider pages before budgeting.

---

## 10. Summary of residual gaps (for the coordinator)
1. Fetch EDPB Opinion 28/2024 and the Dutch AP guidance from primary hosts; fetch DSM Directive Arts. 2-4 text; fetch Japan Art. 30-4 text and the ACA guidance PDF.
2. Korea: confirm whether any TDM exception exists, plus PIPA and unfair-competition law. China: PIPL, DSL, Cybersecurity Law text.
3. IRLbot, Olston and Najork, and Cho and Garcia-Molina PDFs from alternate hosts.
4. IETF Web Bot Auth drafts; Retry-After semantics (RFC 9110); Unicode normalization and ICU docs; Common Crawl columnar index docs; OpenSearch shard sizing; cloud pricing.
5. Typesense license/architecture; Vespa and OpenSearch license pages.
