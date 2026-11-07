# Research: an experimental, user-configurable, bias- and noise-aware search engine ("peripheral vision")
Compiled 2026-11-08. Tags: [primary] = vendor/official docs, the paper or publisher page itself; [secondary] = press, blogs, aggregators. Items marked (NOT VERIFIED) were not retrievable this session; treat as leads. Claims are paraphrased.

## 1. Can anyone get "all" results? Hard limits

| Source | Verified limit / status | URL | Tag |
|---|---|---|---|
| Google Programmable Search / Custom Search JSON API | `num` max 10; API caps total at 100 results (start+num > 100 errors). | https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list | [primary] |
| same | Closed to new customers; existing customers must migrate by 1 Jan 2027. 100 free queries/day, then $5 per 1,000 (up to 10k/day). Whole-web search not offered via this API; Vertex AI Search suggested for up to 50 domains. | https://developers.google.com/custom-search/v1/overview | [primary] |
| Google SERP depth | Google removed the 100-results-per-page option (`&num=100`) in mid-Sept 2025; ~10 per page now, so depth costs more requests. Google gave no detailed explanation; reasons in the article are the author's inference. | https://www.techwyse.com/blog/digital-marketing-101/google-drops-100-results-per-page | [secondary] |
| Bing Search APIs | Retired 11 Aug 2025; Microsoft points to Grounding with Bing Search inside Azure AI Agents. | https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement | [primary] |
| Grounding with Bing | Terms on raw-result access NOT VERIFIED this session (design assumption: LLM-grounding only, no raw SERP). Press coverage: https://www.theregister.com/2025/05/15/bing_search_apis_retired/ | [secondary] |
| Brave Search API | $5 per 1,000 requests, $5/month free credit, 50 req/s; Answers, Spellcheck, Autosuggest separate. | https://api-dashboard.search.brave.com/documentation/pricing | [primary] |
| Brave web search params | `count` max 20/page, `offset` max 9 (so roughly 200 results/query ceiling, my inference); Goggles supported (boost/demote domains, URL or inline, combinable). | https://api-dashboard.search.brave.com/app/documentation/web-search/query | [primary] |
| Brave storage | Search/AI plans permit no retention of any output; only a separate "storage rights" plan does. API grants no rights to third-party page content. | https://api-docs.search.brave.software/resources/help | [primary] |
| Brave index | Claims 40+ billion pages, no Google/Bing fallback (vendor claim). | https://brave.com/search/api/ | [primary, self-reported] |
| Mojeek API | Startup £2/1k (10 results/request, 5 q/s, 100k/day, 1-hour cache, no storage); Business £3/1k (40 results, storage rights); Enterprise up to 100 results. | https://www.mojeek.com/services/search/web-search-api/ | [primary] |
| Marginalia API | `count` 1-100, `dc` (max results per domain) 1-100, `page`, custom `filter`; free non-commercial key by email; commercial keys metered; old API deprecated. | https://about.marginalia-search.com/article/api/ | [primary] |
| Kagi Search API | Bearer-token API at kagi.com/api/v1/search; inherits account personalization (block/promote sites); $12 per 1,000 requests. | https://help.kagi.com/kagi/api/search.html ; https://kagi.com/api/pricing | [primary] |
| Exa | `numResults` 1-100 (higher by contacting support); search types auto/lite/deep; include/excludeDomains up to 1,200 entries. | https://exa.ai/docs/reference/search | [primary] |
| Tavily | `max_results` 0-20; include_domains up to 300 (with `prefer` mode that lets other domains in), exclude up to 150; date, language, country filters. | https://docs.tavily.com/documentation/api-reference/endpoint/search | [primary] |
| Common Crawl | Free full-corpus crawl data (WARC raw, WAT metadata, WET text) on S3 (us-east-1) and HTTPS; archives are hundreds of TB; CDXJ/URL index exists (details not on the page). It is an archive, not a ranked search service. | https://commoncrawl.org/get-started | [primary] |
| OpenWebSearch.eu / Open Web Index (OWI) | EU Horizon project ended 28 Feb 2026; OWI prototype live since May 2025; access = download index shards via openwebindex.eu dashboard under a research license (ethical self-assessment), Lexis platform, OWILIX CLI. As of 4 Apr 2026: public search API and frontend not launched; cannot yet match Google/Bing; commercial licensing unresolved; Open Search Foundation + Univ. Passau continuing. Later 2026 news items exist (Aug, Oct) but text not read. | https://openwebsearch.eu/title-42-months-in-the-making-openwebsearch-eu-project-end-results-look-promising/ ; https://openwebsearch.eu/2026/04/ | [primary] |
| YaCy | Free P2P/decentralized search software; each node can crawl and define its own index; no central request storage; index size not stated. | https://yacy.net/ | [primary] |
| SearXNG | Free metasearch aggregating up to ~261 services; no tracking; self-hostable. Upstream engines may CAPTCHA/block a bot-like instance; the built-in limiter exists for that reason. | https://docs.searxng.org/ ; https://docs.searxng.org/admin/searx.limiter.html | [primary] |

Why "all results" is infeasible (analysis, mine): every commercial API exposes a ranked top-k (10-200 results, per the limits above), not the matching set; indexes hold tens of billions of documents; and vendors cap depth (and since Sept 2025 raised its cost) deliberately. Truly full coverage only exists as raw corpora (Common Crawl, OWI shards) where you build your own retrieval. What IS possible: (a) union of many engines' top-k (metasearch), (b) deep paging up to each cap, (c) re-ranking those pools with your own rules, (d) own index over a slice (Common Crawl/OWI/YaCy) for a long-tail sample, (e) query reformulation fan-out (many differently worded queries reach different tails).

## 2. Precedents for user-defined ranking

- Brave Goggles: plain-text rule files; metadata lines start with `!`; actions `$boost=N`, `$downrank=N`, `$discard`; scope by `site=` or URL path; precedence discard > boost > downrank; generic `$discard` drops anything not matched by another rule; limits 2 MB, 100,000 instructions, 500 chars each, max 2 `*` and 2 `^` per rule; hosted on GitHub/GitLab/Gist and registered at search.brave.com/goggles/create. https://github.com/brave/goggles-quickstart/blob/main/getting-started.md [primary]. Request parameter name for the API not confirmed on the page I read (NOT VERIFIED).
- Stract optics: open-source (AGPL-3.0) engine with own crawler/index; optics are user-defined ranking/filter rules (restrict to blogs/indieweb/edu, tune signal mix); also demotes tracker-laden sites. Repo archived by owner 2 Apr 2026 (read-only), so use as reference design, not a dependency. https://github.com/StractOrg/stract [primary]. Optics syntax not verified.
- Kagi Lenses: restrict to up to 10 included/10 excluded sites, 5/5 keywords; also region, file type, date range; no image/video. https://help.kagi.com/kagi/features/lenses.html [primary]
- Kagi personalization: per-domain Block / Lower / Normal / Higher / Pin; domain-level only; toggle "Personalized" off per query. https://help.kagi.com/kagi/features/website-info-personalized-results.html [primary]
- Kagi Small Web: curated list of personal blogs/sites/YouTube channels (GitHub kagisearch/smallweb), recent content surfaced; separate evergreen index; flagged with a marker in the result info panel. https://help.kagi.com/kagi/search-details/small-web-in-search-results.html [primary]
- Marginalia: own index of the independent/small web; AGPL source; favors traditional IR over natural-language search and sees itself as complement to Google/Bing; API exposes per-domain cap `dc` (a ready-made diversity control). https://about.marginalia-search.com/ ; API page above [primary]. Its ranking algorithm description page was not retrievable (NOT VERIFIED).
- Mojeek: own index API with per-tier result counts and cache terms (above) [primary]. "No tracking" is the vendor's stance; not independently checked.
- Google Programmable Search custom engines: restrict to chosen sites; now closed to new customers (above) [primary].
- Wiby: GPLv2 engine over hand-picked "old-style" personal sites; JSON output at wiby.me/json; no documented user ranking controls. https://wiby.me/about/ [primary]
- Tavily `include_domains_mode=prefer` is an API-level "soft preference" analog of boost [primary, above].

## 3. Academic / expert literature

Diversification
- Agrawal, Gollapudi, Halverson, Ieong, WSDM 2009: taxonomy-based diversification for ambiguous queries; approximate objective, provably optimal in one special case; diversity-adapted NDCG/MRR/MAP beat commercial engines. https://www.microsoft.com/en-us/research/publication/diversifying-search-results/ [primary]
- Santos, Macdonald, Ounis (xQuAD), WWW 2010: probabilistic explicit-aspect diversification, aspects mined from query reformulations of three web engines; TREC 2009 Web track. https://eprints.gla.ac.uk/44363 [primary]
- Carbonell & Goldstein, MMR, SIGIR 1998: trades relevance against similarity to already-selected items. Page not retrievable this session (NOT VERIFIED); lead: https://dl.acm.org/doi/10.1145/290941.291025
Fairness / popularity
- Singh & Joachims, KDD 2018, fairness of exposure: exposure allocation as constraint, maximize user utility under it; expresses demographic parity, disparate treatment/impact. https://arxiv.org/abs/1802.07281 [primary]
- Biega, Gummadi, Weikum, SIGIR 2018, equity of attention: position bias means no single ranking is fair; amortize attention across a series of rankings to track relevance (ILP). https://arxiv.org/abs/1805.01788 [primary]
- Abdollahpouri et al. (arXiv 1907.13286): recommenders concentrate on popular items even for niche-taste users. https://arxiv.org/abs/1907.13286 [primary]
- Steck, RecSys 2018 calibrated recommendations: match list's category mix to user history using KL divergence; greedy submodular re-ranking with (1-1/e) guarantee. Described via survey: https://arxiv.org/html/2507.02643v1 [secondary]
Exploratory search / UI
- Marchionini, CACM 2006: lookup vs learn vs investigate; for the latter two recommends interactive control, overviews/previews, facets, clustering, favoring recall alongside precision, relevance feedback. https://ils.unc.edu/courses/2018_fall/inls509_001/Reading/Marchionini06.pdf [primary, course-hosted copy]
- Hearst, Search User Interfaces (CUP 2009), free online: ch. 5 results presentation, 6 reformulation, 8 navigation, 9 personalization, 10 visualization for search, 11 visualization for text analysis; chapter 10 notes visualization often falls short on usability. https://searchuserinterfaces.com/book/ [primary]
- Carrot2: BSD-licensed library that clusters search-result titles/snippets into labeled groups; REST service (DCS), Solr/Elasticsearch integrations. https://github.com/carrot2/carrot2 [primary]. FoamTree and Vivisimo/Clusty history not verified here. Live demo: https://search.carrot2.org/
- White & Roth exploratory search book: not retrieved (NOT VERIFIED).
Does search create bubbles / shape reality?
- Robertson et al., Nature 2023: across 2018 and 2020 US election waves, people engaged with more identity-congruent and unreliable news than Google showed them; authors attribute partisan/unreliable consumption mainly to user choice rather than algorithmic curation. https://www.networkscienceinstitute.org/publications/users-choose-to-engage-with-more-partisan-news-than-they-are-exposed-to-on-google-search [primary-ish, institute abstract page]. Design implication: showing wider results does not force people to read them; engagement design matters.
- Epstein & Robertson, PNAS 2015: five experiments in two countries; biased rankings shifted undecided voters' preferences by 20%+; effect can be masked from participants. https://ui.adsabs.harvard.edu/abs/2015PNAS..112E4512E [primary abstract]. (The lab-vs-field generalization is contested; see AlgorithmWatch critique https://algorithmwatch.org/en/watching-the-watchers-epstein-and-robertsons-search-engine-manipulation-effect/ [secondary, not read].)
- Metaxa et al., Foundations & Trends in HCI 2021: algorithm audits repeatedly query a system and record output; best practices with search audits as case study. https://hci.stanford.edu/publications/paper.php?id=447 [primary]
- Noble, Algorithms of Oppression (NYU Press 2018): commercial interests and engine dominance embed racism/sexism in search. https://muse.jhu.edu/book/64995 [primary publisher page]
- Introna & Nissenbaum, The Information Society 2000: crawling, indexing, ranking systematically favor some sites and sideline others; recommend disclosure of rules and public efforts toward inclusive search and meta-search tools. https://nissenbaum.tech.cornell.edu/papers/ShapingTheWeb.pdf [primary]
- Grimmelmann, "Some Skepticism About Search Neutrality" (2011): argues neutrality has no workable definition (eight candidate meanings fail); stresses user choice; treat antitrust/copyright/stealth marketing under existing law. https://laboratorium.net/archive/2011/01/18/some_skepticism_about_search_neutrality [primary, author's site]. Implication: aim for user-chosen, transparent bias, not "neutral" ranking.

## 4. Mitigation ideas mapped to sources (design proposals are mine)

1. Metasearch union across independent indexes (Brave, Mojeek, Marginalia, Kagi, Exa/Tavily, SearXNG instances) + dedupe by canonical URL. Grounds: caps above; SearXNG. Index overlap is itself a measurable signal of "tail" membership.
2. Per-domain cap and diversity re-rank: Marginalia `dc` precedent; MMR/xQuAD/Agrawal for algorithmic base; Tavily "prefer" for soft preference.
3. Source-diversity metrics shown to the user: domain entropy, Gini over domains, share of results from top-N domains, per-engine contribution, language/region mix (my metrics; calibration idea from Steck: compare result mix to a user-declared target mix).
4. Exposure/attention fairness: rotate or amortize which tail items get top slots across sessions (Biega), or allocate exposure to long-tail by constraint (Singh & Joachims).
5. User-tunable weights and rule files: Goggles/optics/Lenses as a portable rule format; implement own Goggles-compatible parser locally on the merged pool (re-ranking is local, so no vendor limits apply).
6. "Why this result" and rank uncertainty: show per-engine ranks, rank spread across engines, and which rule moved it (follows Introna & Nissenbaum's disclosure recommendation; implementation is mine).
7. Language/region toggles: Tavily/Brave/Kagi expose language/country/region filters; run the same query across several languages (translated reformulations) to expose non-English tails.
8. Long-tail sampling: deep-page to caps (Brave 200, Google CSE 100, Mojeek enterprise 100, Marginalia 100, Exa 100), plus reformulation fan-out (xQuAD-style aspects) and a Common Crawl/OWI shard sample for domains no engine returns.
9. Visualization: Carrot2 clustering and FoamTree-style treemaps; embedding-based topic maps built locally from snippets (embedding method is my suggestion; Hearst ch. 10 warns visualization often has usability problems, so keep a plain list as default and map as optional).
10. Measure with audit methodology (Metaxa et al.) over fixed query sets, logged over time.

## 5. Legal / ToS constraints (design must stay compliant)

- Google ToS: bars using automated means to access its services when this violates machine-readable instructions such as robots.txt. https://policies.google.com/terms [primary]. Practical reading (not legal advice): do not scrape google.com SERPs; use licensed APIs. Secondary overviews exist (https://dataforseo.com/?p=9578) but were not read.
- Google CSE API: closed to new customers; sunset 1 Jan 2027, so do not build on it [primary, above]. Its caching/display terms were not on the page (NOT VERIFIED).
- Brave: no retention without storage-rights plan; no rights to third-party page content [primary]. So any cache/index of results, analytics log, or training use requires that plan; ephemeral in-memory re-ranking is the safe default. Full ToS text not retrievable (NOT VERIFIED).
- Mojeek: Startup tier allows 1-hour caching only; storage rights only on Business/Enterprise [primary].
- Marginalia: non-commercial free key; commercial needs metered key [primary].
- Bing: raw API gone; do not scrape Bing either (same logic as Google; Bing ToS not read).
- SearXNG: self-hosted public-scraping instances can be blocked by upstreams; limiter is the project's mitigation [primary]. For a compliant design, prefer API-backed engines over scraper-backed ones.
- Common Crawl / OWI: free but OWI is research-license only; commercial use unresolved [primary]. Publisher copyright still applies to content derived from pages.
- Design rules: (1) API-only, per-vendor adapters; (2) store only what each plan permits (default: session memory, no persistent SERP cache); (3) show attribution/links back to origin; (4) make the tail-sampling index a separate Common Crawl/OWI derivative, labelled by license; (5) respect robots.txt for any own crawling.

## Gaps to follow up
Google/Bing ToS full text; Brave full ToS and `goggles` request parameter; Marginalia ranking article; Stract optics syntax; White & Roth book; xQuAD/MMR vs. later neural diversifiers; evidence on whether tail exposure changes user beliefs; OWI status after April 2026.
