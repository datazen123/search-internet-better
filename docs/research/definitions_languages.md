# Crawl-demand definitions and distribution of internet languages

Research date: 2026-11-07/08. Tags: [primary] = the publisher's own page or the original paper; [secondary] = reporting or aggregation of someone else's data. Quotes are kept under 15 words. Figures are paraphrased from fetched pages, and I did not re-verify them beyond that.

## Q1. "Crawl demand favours popular, fast, well-linked sites"

### 1.1 Google: crawl capacity limit vs crawl demand
- Google's current crawl-budget guide defines the **crawl capacity limit** as a cap on how much time a server spends holding connections open for Google. Its purpose is to avoid overloading the server. [primary] https://developers.google.com/crawling/docs/crawl-budget
- The same page says Google raises the limit when the site stays healthy and responds quickly, and lowers it when the site slows. 5xx errors and 429 rate-limit responses also lower it. [primary] same URL
- **Crawl demand** is "determined by factors unique to that crawler". For Googlebot the stated factors are site size, update frequency, page quality and relevance relative to other sites. [primary] same URL
- **"Popularity" per Google:** popular URLs tend to be crawled more often so they stay fresh in Google's systems. The guide gives no formula or metric for popularity. [primary] same URL
- The 2017 blog post "What Crawl Budget Means for Googlebot" gives the older wording. [primary] https://developers.google.com/search/blog/2017/01/what-crawl-budget-means-for-googlebot
  - "Crawl rate limit" is the maximum parallel connections plus the wait between fetches.
  - Crawl demand has two named drivers, **popularity** (URLs popular on the Internet are crawled more often) and **staleness** (the system tries to keep URLs from going stale in the index). Site-wide events such as site moves can raise demand.
  - Crawl budget is crawl rate limit combined with crawl demand: "the number of URLs Googlebot can and wants to crawl".
  - Caveat: I read this post through a fetch tool's summary, not the raw text. The quoted definitions are consistent with the current guide.
- **Who needs to care (numbers).** The guide says it is for sites with 1M+ unique pages changing about weekly, or 10,000+ unique pages changing daily. It also covers sites with many URLs in "Discovered - currently not indexed". The page calls these figures rough estimates, not thresholds. Verified. [primary] https://developers.google.com/crawling/docs/crawl-budget
- **Server errors.** To slow Googlebot temporarily, Google says to serve 500, 503 or 429. The reduction applies to the whole hostname, and crawl rate recovers automatically once the errors stop. [primary] https://developers.google.com/crawling/docs/crawlers-fetchers/reduce-crawl-rate
  - Google advises against keeping this up for more than about 1-2 days. If a URL keeps returning these codes across days, it may be dropped from the index.
  - The Crawl Stats help page says not to return 503 or 429 for more than two or three days. [primary] https://support.google.com/webmasters/answer/9679690
- **Crawl Stats report metrics.** [primary] https://support.google.com/webmasters/answer/9679690
  - The metrics are total crawl requests, total download size and average response time.
  - Average response time is the mean across all resources fetched, with each linked resource counted separately.
  - Host status looks back 90 days and flags robots.txt, DNS and connectivity failures. Its example flags DNS failures above 5% on a day.
  - **There is no numeric "fast" threshold.** Google tells you to watch for sudden changes, not to hit a target such as a number of milliseconds.
- Gary Illyes / Search Off the Record: the 2022 episode "Should I worry about crawl budget?" (Illyes plus Martin Splitt and Lizzi Sassman) exists. I could only retrieve the landing page, not the transcript at goo.gle/sotr045-transcript, so I quote nothing from it. [primary, landing page only] https://dev.to/search-off-the-record/should-i-worry-about-crawl-budget Secondary coverage exists, for example https://www.seroundtable.com/googles-gary-illyes-crawl-budget-scheduling-host-load-22097.html [secondary, unread].

### 1.2 "Fast": response-time numbers
- **Google:** "fast" has no numeric threshold in the crawl-budget guide or the Crawl Stats report. The mechanism is qualitative: stable or better response times raise the capacity limit, slower ones lower it. [primary] (URLs above)
- **IR textbook (Manning, Raghavan, Schütze, ch. 20):** the politeness heuristic is to wait about 10x the time the last fetch from that host took before the next request. So slower hosts are inherently fetched less often. The same section says priority should combine change rate and page quality. [primary: the book's own site] https://nlp.stanford.edu/IR-book/html/htmledition/the-url-frontier-1.html
- **Mercator:** I did not retrieve the paper, so nothing is claimed about it.
- **Bing:** the Bing Webmaster blog says bingbot decides which sites to crawl, how often and how many pages per site. It says "billions of URLs" are crawled daily and names server load as a constraint. It gives no response-time thresholds. [primary] https://blogs.bing.com/webmaster/october-2018/bingbot-Series-Maximizing-Crawl-Efficiency
  - Its efficiency goal is to crawl a URL only when it is new or changed.
  - The article does not mention popularity or engagement, and I could not retrieve Bing's webmaster guidelines (a JS-only page), so "Bing lists engagement" is **unverified**.
- **Common Crawl:** I found no documented response-time threshold. Not verified either way.

### 1.3 "Well-linked": how link popularity is measured
- **Common Crawl host/domain web graph, May-July 2026** (crawls CC-MAIN-2026-21, -25, -30). [primary] https://commoncrawl.org/blog/host--and-domain-level-web-graphs-may-june-and-july-2026
  - The host graph has 240.4M nodes and 3.7B edges. 74.05% of nodes are dangling (no outlinks in the graph). The largest strongly connected component is 36.1M nodes (15.03%).
  - The domain graph has 118.0M nodes and 2.8B edges. 63.2% are dangling, and the largest SCC is 30.0M (25.39%).
  - Both graphs ship ranks files with **harmonic centrality** and **PageRank**.
  - The edge count averages only about 15 per host node (3.7B / 240.4M). That is a pure arithmetic observation of mine, not a claim from the page.
- **Does CCBot use these to prioritize?** Common Crawl's own blog says CCBot has used the metrics to guide crawl choices, and that harmonic centrality sets crawl priority, with higher-HC sites crawled more. [primary, but the post is aimed at SEOs and is thin on detail] https://commoncrawl.org/blog/how-seos-are-using-common-crawls-web-graph-data-for-ai-ranking-signals
  - An academic paper instead says common crawlers prioritize by PageRank-like connectivity, favoring high in-degree. [secondary: an arXiv paper citing Common Crawl, not the operator] https://arxiv.org/html/2502.13347v1
  - The two sources name different metrics (HC vs PageRank). Treat the exact mechanism as not fully documented.
- **In-degree distribution (Broder et al. 2000, "Graph structure in the Web").** [primary] https://www.cs.cornell.edu/courses/cs172/2002fa/handouts/broder+al2000.excerpt.html
  - The fraction of pages with i in-links is proportional to 1/i^2.1.
  - The May 1999 crawl had about 203M URLs and 1.47B links. Its strongly connected core was 56.5M pages, about 28% (my calculation from their table).
  - The out-degree exponent was not stated in the excerpt I read.
  - Meaning: a small number of pages hold a large share of inlinks. That is a heavy-tailed distribution, so link-prioritized crawling concentrates on a small head of the graph.
- **PageRank damping 0.85 (Brin & Page 1998):** I did not retrieve the paper in this session, so this is **unverified here**. Cite it from the paper directly before relying on it.

### 1.4 "Popular": link popularity vs traffic popularity
- Google's wording ("popular on the Internet", "popular URLs") does not say whether it means links, clicks or traffic. Neither the guide nor the 2017 post defines it. [primary] URLs above. Equating it with PageRank is an inference, not Google's statement.
- Common Crawl's popularity proxy is explicitly link-graph-based (harmonic centrality). It uses no traffic data in the sources I read. [primary]
- Bing: engagement as a crawl signal is not confirmed by anything I could retrieve (see 1.2).
- **Bottom line:** the claim is well supported for "fast" in the narrow sense that slow or erroring servers get a lower capacity limit. It is well supported for "popular" only as a stated qualitative driver. "Well-linked" is explicit for Common Crawl (harmonic centrality) but is an inference for Google.

## Q2. Distribution of languages on the internet

### 2.1 Lenses and numbers

**(a1) W3Techs, content language, as of 7 Nov 2026** [primary] https://w3techs.com/technologies/overview/content_language
- English 49.5%, Spanish 6.1%, German 5.9%, Japanese 4.9%, French 4.6%, Portuguese 4.1%, Russian 3.4%, Italian 2.8%, Dutch 2.1%, Polish 1.8%, Turkish 1.6%, Indonesian 1.2%, Chinese 1.2%, Persian 1.0%, Korean 0.9%, Arabic 0.6%, Bengali 0.1%. Hindi, Urdu, Tamil, Swahili and Hausa are each under 0.1%.
- The unit is the share of websites whose content language is known. English has stayed within 49.3-49.7% since Nov 2025. [primary] https://w3techs.com/technologies/history_overview/content_language
- **Methodology caveat:** the W3Techs pages I fetched do not state the sample or detection method. They defer to a general methodology page I did not read. A secondary summary says W3Techs reads language mainly from the homepage of the top-ranked sites. That inflates English relative to the whole web, and the same summary says the sample description is inconsistent. [secondary] https://en.wikipedia.org/wiki/Languages_used_on_the_Internet The "top 10M sites" framing in the task could not be confirmed from W3Techs itself.

**(a2) Common Crawl, crawl CC-MAIN-2026-43, share of HTML pages by primary language** [primary] https://commoncrawl.github.io/cc-crawl-statistics/plots/languages
- English 42.56%, Russian 6.30%, German 5.77%, Japanese 4.89%, French 4.76%, Spanish 4.74%, Chinese 4.37%, Italian 2.58%, Portuguese 2.47%, Polish 1.89%, Dutch 1.75%. Unknown is 3.06%.
- Method: CLD2 (about 160 languages), the first-detected language per document, HTML only.
- Rows for the low-web-share languages (Hindi etc.) come from the dataset CSV, via a fetch tool's summary. [primary] https://huggingface.co/datasets/commoncrawl/statistics
- Hindi in 2019-43 was 0.128%. In 2026-43 it is 0.211%, so the share is rising but is still tiny.
- Caveat: the crawl prioritizes by harmonic centrality (see 1.3), so it over-represents well-linked, mostly English sites. Common Crawl itself runs a project to add non-English seed URLs. [primary] https://blog.commoncrawl.org/blog/web-languages-needing-review-by-native-speakers

**(b) Internet users by language**
- ITU estimates 6 billion internet users in 2025, about three-quarters of the world, with 2.2 billion offline. ITU does **not** publish users by language. [primary] https://www.itu.int/en/mediacentre/Pages/PR-2025-11-17-Facts-and-Figures.aspx
- Internet World Stats (March 31, 2020): English 25.9%, Chinese 19.4%, Spanish 7.9%, Arabic 5.2%, Indonesian 4.3%, Portuguese 3.7%, French 3.3%, Japanese 2.6%, Russian 2.5%, German 2.0%, out of about 4.59B users. [secondary: via Wikipedia, because the IWS site blocked my fetch] https://en.wikipedia.org/wiki/Languages_used_on_the_Internet
  - **Quality flag:** the data is over six years old, it is a commercial site compiling estimates, and its method is not rigorous. Use it only as a rough order of magnitude.
  - I found no UNESCO current data by language.

**(c) Speakers worldwide, Ethnologue 2026 edition (millions, L1 / L2 / total)** [secondary: a Wikipedia table citing Ethnologue; the Ethnologue site would not load] https://en.wikipedia.org/wiki/List_of_languages_by_total_number_of_speakers
- English 450 / 1,090 / 1,530; Mandarin 988 / 194 / 1,183; Hindi 347 / 264 / 611; Spanish 487 / 75 / 561; Bengali 234 / 43 / 274; Urdu 78 / 168 / 246; Swahili 4 / 91 / 95; Hausa 58 / 36 / 94.
- Note that Hindi and Urdu are counted separately here, and Arabic is Modern Standard only (0 L1).

**(d) Wikipedia articles, top editions** [secondary: Wikipedia's list page, no explicit date on the article counts; edition count is "as of October 2026"] https://en.wikipedia.org/wiki/List_of_Wikipedias
- English 7.25M, Cebuano 6.12M, German 3.16M, French 2.78M, Swedish 2.63M, Dutch 2.23M, Spanish 2.14M, Russian 2.12M, Italian 1.99M, Egyptian Arabic 1.63M. There are 364 editions in total.
- Selected: Urdu 705k, Bengali 192k, Hindi 172k, Swahili 130k, Hausa 121k.
- Cebuano and Swedish rank high largely because of bot-generated articles, which is a known caveat (my knowledge, not from the fetched page). The meta.wikimedia.org page did not load.

**(e) Academic and observatory studies**
- UNESCO/Funredes (Pimienta, Prado, Blanco), "Twelve years of measuring linguistic diversity in the Internet" (2009). [primary] https://unesdoc.unesco.org/ark:/48223/pf0000187016
  - English fell from about 75% of pages in 1996 to about 45% by 2005. The authors think the true figure was below 40%.
  - They warn search-engine counts became unreliable after 2005, when indexes covered under 30% of the web.
  - They list divergent estimates by method: OCLC about 72% (1999, 2002), Inktomi 86.5% (2000), a Google-based estimate 50.8% (2008).
- Pimienta / OBDILCI blog (Nov 2024) puts English at about 20-25% of web pages, in a comparison of five measurement methods. I only saw the summary, not the study, so I have not verified the method. [primary: the author's own site, a blog post not peer-reviewed] https://www.obdilci.org/blog/methods/

### 2.2 Comparison table

Speaker shares are my calculation: Ethnologue totals divided by an assumed world population of about 8.2B. The population figure is not sourced. The "% internet users" column is IWS 2020 (stale, secondary). "n/a" means no figure found.

| Language | % web content, W3Techs (7 Nov 2026) | % Common Crawl (2026-43) | Speakers, millions (L1+L2) | % of world speakers (approx., 8.2B base) | % internet users (IWS, Mar 2020) |
|---|---|---|---|---|---|
| English | 49.5 | 42.56 | 1,530 | ~18.7 | 25.9 |
| Mandarin / Chinese | 1.2 | 4.37 | 1,183 | ~14.4 | 19.4 |
| Hindi | <0.1 | 0.21 | 611 | ~7.5 | n/a |
| Spanish | 6.1 | 4.74 | 561 | ~6.8 | 7.9 |
| Bengali | 0.1 | 0.11 | 274 | ~3.3 | n/a |
| Urdu | <0.1 | 0.03 | 246 | ~3.0 | n/a |
| Swahili | <0.1 | 0.01 | 95 | ~1.2 | n/a |
| Hausa | <0.1 | 0.004 | 94 | ~1.1 | n/a |
| Russian | 3.4 | 6.30 | 210 | ~2.6 | 2.5 |
| Japanese | 4.9 | 4.89 | 126 | ~1.5 | 2.6 |
| German | 5.9 | 5.77 | 133 | ~1.6 | 2.0 |

### 2.3 Why the lenses differ
1. **Unit of count.** W3Techs counts sites. Common Crawl counts crawled HTML pages. Ethnologue counts people. IWS counts online people grouped by language. None of these is speaker-weighted content.
2. **Sampling bias.** W3Techs reads mostly top-ranked homepages, which favours English and commercial sites. Common Crawl's link-centrality prioritization favours well-linked sites, which skew English and Western. Search-engine-count studies were biased by index coverage (UNESCO study).
3. **Detection method.** CLD2 covers about 160 languages and fails on some low-resource ones. A Common Crawl review notes 7 of 42 languages it checked cannot be detected at all. [primary] https://blog.commoncrawl.org/blog/web-languages-needing-review-by-native-speakers
4. **Walled content.** Social platforms, apps, video and logged-in content are not crawled. Chinese content behind the Great Firewall and in apps is under-represented in both W3Techs (1.2%) and Common Crawl (4.4%), despite about 1.2B Mandarin speakers. This is a plausible explanation, not something the sources prove.
5. **Definitions of "language".** Hindi vs Urdu, Arabic varieties and Chinese varieties are merged or split differently across datasets.
6. **Gaps for low-web-share languages.** Hindi is about 7.5% of speakers but about 0.2% of Common Crawl pages, roughly 35x under-represented. Bengali is about 3.3% of speakers against 0.11%, Urdu about 3.0% against 0.03%, Swahili about 1.2% against 0.01%, and Hausa about 1.1% against 0.004%. Wikipedia shows the same pattern: Urdu, Bengali, Hindi, Swahili and Hausa editions are each under 1M articles, while Cebuano has more than 6M.

### 2.4 Gaps and unverified items
- Not retrieved: the W3Techs methodology page, Ethnologue directly, Internet World Stats directly, the meta.wikimedia.org statistics, the Search Off the Record transcript, Bing's guidelines, the Brin & Page paper, Mercator, and any UNESCO/OIF figures after 2009 (the Funredes work stopped around then).
- Not found: any numeric "fast" threshold from Google, Bing or Common Crawl, and any official definition of "popularity" beyond the qualitative wording above.
