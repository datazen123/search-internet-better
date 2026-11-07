# Crosscutting research: noise and bias in how search engines and AI companies crawl, index and serve the web

Date: 2026-11-08. Scope: Google, Microsoft Bing, xAI, DeepSeek, OpenAI, Anthropic.
Tags: [primary] = official/standards/regulator/court/peer-reviewed/vendor's own docs; [secondary] = law firm, press, vendor blog, or aggregator.
VERIFICATION NOTE: Items marked (not fetched) come from background knowledge or search snippets, not a page I read. Treat as leads. Several pages (Nature model collapse, PNAS SEME, EUR-Lex full text, Bing help) failed to load.

## 1. Taxonomy of noise and bias by pipeline stage

### 1.1 Discovery / crawl
- robots.txt is voluntary. RFC 9309 says the rules are not access authorization, and a file listing paths can reveal them. [primary] https://www.rfc-editor.org/rfc/rfc9309.html
- RFC 9309 failure semantics: a 4xx on robots.txt means the crawler may access everything; a 5xx or network failure means assume full disallow. Parsers must handle at least 500 KiB; cache should not exceed ~24h. [primary] same URL. Consequence: misconfigured sites silently get fully crawled or fully excluded.
- Crawler purpose splits are inconsistent across vendors. Cloudflare reports Meta, OpenAI and Anthropic run separate bots per purpose, while Google and Microsoft use unified crawlers. [primary for Cloudflare's own data] https://blog.cloudflare.com/crawlers-click-ai-bots-training/
- Training dominates AI crawling (~80% over 12 months; search ~18%; user actions ~2%) per Cloudflare. [primary, vendor data] same URL.
- Extraction without return traffic: Cloudflare's crawl-to-refer ratios (Jan to Jul 2025) were about 38,000:1 for Anthropic (down from ~287,000), ~1,100:1 for OpenAI, ~5:1 for Google. [primary, vendor data] same URL. Newer 2026 figures appear only in a secondary aggregator (not verified): https://ecorpit.com/ai-crawler-crawl-to-referral-ratio-2026-geo-decision/ [secondary]
- Spoofing/verification: Cloudflare says Anthropic's crawler was weaker on verification, so robots.txt compliance was hard to confirm in 2025, and Web Bot Auth (cryptographic bot signing) is not yet adopted industry-wide. [primary] same URL. Anthropic now publishes IP ranges (claude.com/crawling/bots.json). [primary] https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
- Compliance gaps observed: the Tow Center found some chatbots answered about content from publishers that block them (Perplexity free tier identified all ten paywalled National Geographic excerpts); it notes other access routes are possible. [secondary, journalism-school study] https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php
- Coverage bias: well-linked, fast, mostly-English sites are over-represented. Common Crawl's own stats show English at 42.56% of documents in CC-MAIN-2026-43 and rising (CLD2 primary-language detection, HTML only). [primary] https://commoncrawl.github.io/cc-crawl-statistics/plots/languages.html
- Crawl budget / JS rendering / login walls: general Google documentation exists but I did not fetch it. (not fetched)

### 1.2 Indexing
- Canonicalization, dedup and spam-classifier false positives: Google's spam policies define the targets (scaled content abuse, site reputation abuse, expired domain abuse, cloaking, hidden text, link spam) but do not publish false-positive rates. [primary] https://developers.google.com/search/docs/essentials/spam-policies
- Syndication confusion: Tow Center found tools cited syndicated copies (e.g., a Yahoo copy of a USA Today article even though USA Today blocks ChatGPT). [secondary] https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php
- Index pollution by machine-translated multi-way parallel content in low-resource languages (see section 5). [primary, arXiv preprint] https://arxiv.org/abs/2401.05749

### 1.3 Ranking
- Search Engine Manipulation Effect (Epstein and Robertson, PNAS 2015) is the standard citation for ranking order shifting voter preferences. (not fetched; page failed) https://www.pnas.org/doi/10.1073/pnas.1419828112 [primary, unverified by me]
- Data voids (Golebiewski and boyd, Data & Society): queries with little authoritative content can be filled by manipulators, especially during breaking news, new strategic terms, outdated terms, fragmented concepts and problematic queries. Freshness preference is exploited. [primary] https://datasociety.net/library/data-voids/
- Self-preferencing, commercial incentives, personalization and click-feedback loops: the DMA Art. 6(5) and the Commission's Google Shopping decision are the legal anchors. (not fetched) No peer-reviewed audit was fetched in this pass; recommend a follow-up.

### 1.4 Generative layer
- Citation accuracy: a human audit of four generative search engines (Bing Chat, NeevaAI, perplexity.ai, YouChat) found only ~51.5% of sentences fully supported by citations and ~74.5% of citations supporting their sentence. [primary, arXiv/ACL-line paper, 2023, old systems] https://arxiv.org/abs/2304.09848
- Attribution failures in 2025 tools: Tow Center reported >60% incorrect answers collectively on source-identification of news excerpts; Grok 3 94% incorrect; DeepSeek misattributed 115/200; Gemini and Grok 3 cited fabricated or broken URLs in over half of responses. Single run, one task type. [secondary] https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php
- Position effects in RAG: models use information at the start/end of long contexts better than the middle, so retrieval order biases answers. [primary, arXiv; published in TACL] https://arxiv.org/abs/2307.03172
- Prompt injection and LLM-SEO/GEO manipulation: Google's spam policy page says attempts to manipulate generative AI responses in Search can count as spam. [primary] https://developers.google.com/search/docs/essentials/spam-policies
- Model collapse (Shumailov et al., Nature 2024): fetch failed; claim not verified here. https://www.nature.com/articles/s41586-024-07566-y [primary, unverified by me]
- AI content prevalence: Graphite sampled 43k English Common Crawl articles with Surfer's detector and estimated AI-written articles passed human ones in Nov 2024, then flat. Page says a newer version supersedes it with a ~3.3 point lower share; author-acknowledged detector false positives of 4.2%, English-only, hybrid content unmeasured. Treat as vendor research, not peer-reviewed. [secondary] https://graphite.io/five-percent/more-articles-are-now-created-by-ai-than-humans

### 1.5 Governance
- Government-directed filtering: PNAS Nexus (Feb 2026) compared China-originating and other LLMs on 145 political questions; China-originating models refused more, answered shorter and less accurately; all models refused more in Chinese than English; observational, causation not established. [primary, peer-reviewed] https://fsi.stanford.edu/publication/political-censorship-large-language-models-originating-china
- Other DeepSeek audits found via search (arXiv, not read): "R1dacted" https://arxiv.org/abs/2505.12625 and https://arxiv.org/pdf/2506.12349 [primary preprints, unverified by me]
- Opaque provider chains: Tow Center notes Copilot was not blocked by any publisher likely because it uses BingBot. [secondary] https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php
- Researcher access: the DSA data-access delegated act (Art. 40) covers VLOPs and VLOSEs, with vetting by Digital Services Coordinators; Commission page published 2 Jul 2025 and expected first vetting Oct 2025. The page did not name Google/Bing; their VLOSE designation is background knowledge (not fetched here). [primary] https://digital-strategy.ec.europa.eu/en/news/commission-adopts-delegated-act-data-access-under-digital-services-act

## 2. Standards and opt-out mechanisms, and their limits

| Mechanism | Status (as read) | Limits | Source |
|---|---|---|---|
| robots.txt (RFC 9309) | IETF Proposed Standard | Voluntary; not auth; per-crawler tokens only; no purpose semantics | [primary] https://www.rfc-editor.org/rfc/rfc9309.html |
| Google-Extended | robots.txt token, no own user agent; controls Gemini training and grounding in Gemini Apps/Vertex; no effect on Search inclusion or ranking. Google says it plans AIPREF training-signal support (`__usage_ai-training`) in early 2027 | Does not stop Search-side AI features (AI Overviews) via Googlebot | [primary] https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers |
| OpenAI bots | GPTBot (training), OAI-SearchBot (search), ChatGPT-User (user-initiated; robots.txt may not apply) | Per-bot settings; user fetches bypass | [primary] https://developers.openai.com/api/docs/bots |
| Anthropic bots | ClaudeBot (training), Claude-User, Claude-SearchBot; says it honors robots.txt; will honor an IETF-draft "no AI training" signal from 30 Oct 2026 | Own claim only; blocking by IP discouraged | [primary] https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler |
| Bing / Microsoft, xAI, DeepSeek | Not verified (Bing help page needed JS; no xAI/DeepSeek crawler docs fetched) | Gap in this report | (not fetched) |
| TDMRep (W3C CG) | Final Community Group Report, 10 May 2024; not W3C Standard; `tdm-reservation` and `tdm-policy` via HTTP header (preferred), /.well-known/tdmrep.json, HTML meta, EPUB/PDF | Limited crawler adoption (not verified); ties to EU Art. 4 | [primary] https://w3c.github.io/cg-reports/tdmrep/CG-FINAL-tdmrep-20240510/ |
| IETF aipref WG | Active; vocabulary and attach drafts, charter milestones due 2026-08-31; enforcement, crawler auth and auditing out of scope | Page did not show current draft state; check datatracker | [primary] https://datatracker.ietf.org/wg/aipref/about/ |
| llms.txt | Community proposal (Jeremy Howard, Sept 2024), not a standards-body spec; it is an opt-in helper, not an opt-out | No enforcement or consent semantics | [primary, proponent's own site] https://llmstxt.org/ |
| ai.txt | Not verified | | (not fetched) |
| C2PA provenance | Not fetched. China's labeling rules mandate implicit metadata (see section 4). | | |

## 3. Legal landscape by jurisdiction (status as of 2026-11-08, from sources read)

| Jurisdiction | Instrument | Status | Source |
|---|---|---|---|
| EU | DSM Directive 2019/790 Arts. 3-4 (TDM exceptions; opt-out for commercial TDM by machine-readable means) | In force since 2019. Full article text not retrieved; relying on USCO's description and the courts. | [primary] https://eur-lex.europa.eu/eli/dir/2019/790/oj/eng (text not extracted) |
| EU | AI Act GPAI obligations; Code of Practice | GPAI obligations applied 2 Aug 2025; Commission enforcement powers (fines) from 2 Aug 2026; legacy models by 2 Aug 2027. CoP signatories listed: Google, Microsoft, OpenAI, Anthropic; xAI signed only the Safety and Security chapter | [primary] https://digital-strategy.ec.europa.eu/en/policies/guidelines-gpai-providers ; https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai |
| Germany | Kneschke v LAION, OLG Hamburg | Appeal dismissed; Sec. 44b TDM exception covers dataset creation and AI training; natural-language ToS reservation not machine-readable for 2021 download but could count in future; leave to appeal to BGH granted. Law-firm summary only. | [secondary] https://cm.twobirds.com/en/insights/2025/germany/higher-regional-court-hamburg-confirms-ai-training-was-permitted-(kneschke-v,-d-,-laion) |
| UK | Getty v Stability AI (High Court, 4 Nov 2025) | Secondary infringement claim failed (weights not an infringing copy); narrow trade mark findings; appeal status unknown from source. Bird & Bird acted for Stability. | [secondary] https://cm.twobirds.com/en/insights/2025/uk/stability-ai-defeats-getty-images-copyright-claims-in-first-of-its-kind-dispute-before-the-high-cour |
| UK | Government report under s.136 Data (Use and Access) Act 2025, 18 Mar 2026 | Opt-out TDM exception no longer the preferred option; no reform until evidence gathered; will explore transparency and AI-labelling best practice; 11,520 consultation responses | [primary] https://www.gov.uk/government/publications/report-and-impact-assessment-on-copyright-and-artificial-intelligence/report-on-copyright-and-artificial-intelligence |
| US | USCO Part 3 (pre-publication, 2025) | Advisory, not law. Fair use is a spectrum; factors 1 and 4 weigh heavily; unlicensed use is worse where licensing is feasible; pirated sources noted. Excerpt read only partly. | [primary] https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-3-Generative-AI-Training-Report-Pre-Publication-Version.pdf |
| Japan | Copyright Act Art. 30-4; ACA "General Concept on AI and Copyright" (Mar 2024) and checklist (31 Jul 2024) | Guidance exists; I did not extract its substance (index page only). USCO notes Japan's exception does not cover use where licenses are available. | [primary] https://www.bunka.go.jp/seisaku/chosakuken/aiandcopyright.html (Japanese) |
| China | Labeling Measures for AI-generated synthetic content (CAC, MIIT, MPS, NRTA) | Effective 1 Sep 2025 with mandatory national standard; explicit labels plus implicit metadata; bans removing/forging labels; app stores verify | [primary] https://www.cac.gov.cn/2025-03/14/c_1743654685896173.htm (Chinese) |
| South Korea | AI Basic Act | Effective 22 Jan 2026; generative output must be identified as AI-made (deepfakes clearly; others via watermark plus notice); fines up to 30M won; MSIT plans grace period of at least a year | [secondary] https://www.newsis.com/view/NISX20260121_0003484769 (Korean) |
| Brazil | PL 2338/2023 | Passed Senate; Chamber vote not held as of 24 Aug 2026, expected after October elections; copyright still under negotiation | [secondary] https://www.mobiletime.com.br/noticias/24/08/2026/marco-ia-voto-fim-do-ano/ (Portuguese) |
| India | DPIIT committee working paper on AI and copyright | Proposed hybrid/mandatory-licence model (search results only; not read; check current status) | [secondary] https://www.mondaq.com/india/copyright/1718746/exploring-the-dpiits-working-paper-on-generative-ai-and-copyright |

## 4. Practical detection heuristics for low-quality / SEO / AI-generated sources

From Google's spam policy page [primary] https://developers.google.com/search/docs/essentials/spam-policies:
1. Many pages produced mainly to rank, stitched or scraped from other pages (scaled content abuse); Google judges value and intent, not the tool used.
2. Third-party content hosted on a strong domain mostly to borrow its ranking (site reputation abuse), e.g., coupon/review sections unrelated to the host's main topic.
3. Repurposed expired domains (e.g., affiliate pages on a former agency domain); check domain history.
4. Cloaking (crawler sees different content) and hidden text/links.
5. Link-scheme signals: paid links without rel=nofollow/sponsored, excessive reciprocal links.

Evidence-based cautions:
- AI detectors have non-trivial error: Graphite's own validation estimated a 4.2% false-positive rate, so do not use a detector score alone. [secondary] https://graphite.io/five-percent/more-articles-are-now-created-by-ai-than-humans
- Check citation fidelity: roughly a quarter of generative-search citations did not support their sentence in the 2023 audit; open the source. [primary] https://arxiv.org/abs/2304.09848
- Prefer originals over syndicated copies, and check that cited URLs resolve (Tow Center fabricated-URL finding). [secondary] https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php
- Be most skeptical in data-void conditions (breaking news, new coined terms). [primary] https://datasociety.net/library/data-voids/
- For non-English queries, multi-way parallel translations of identical text across many languages are a red flag for machine-translated slop. [primary] https://arxiv.org/abs/2401.05749
- Provenance labels: in China and Korea, generated content must carry labels; absence is not proof of human origin, and metadata is strippable. [primary] https://www.cac.gov.cn/2025-03/14/c_1743654685896173.htm

## 5. Multilingual theme (language bias across the pipeline)

- Crawl corpus skew: Common Crawl CC-MAIN-2026-43 is 42.56% English; next are Russian 6.30%, German 5.77%, Japanese 4.89%, French 4.76%, Spanish 4.74%, Chinese 4.37%. English rose ~2 points across three recent crawls. Note CLD2 labels only primary language, HTML only. [primary] https://commoncrawl.github.io/cc-crawl-statistics/plots/languages.html
- Machine-translation pollution: a large share of web content in lower-resource languages is multi-way parallel, low-quality machine translation, skewed toward translated low-quality English; the abstract gives no single percentage. arXiv preprint (Thompson et al. line of work), abstract only. [primary-ish, preprint] https://arxiv.org/abs/2401.05749
- Cross-lingual RAG bias: with synthetic documents in en/de/zh/ar/hi, retrieval picked the query-language document 68% of the time; when none existed in the query language, models preferred English (49.3%) over German, Chinese, Hindi and Arabic. Preprint, five languages, one RAG design. [primary preprint] https://arxiv.org/html/2407.05502v3
- Language-dependent censorship: PNAS Nexus found all tested models refused more in Chinese prompts; model origin mattered more than language. [primary, peer-reviewed] https://fsi.stanford.edu/publication/political-censorship-large-language-models-originating-china
- Script/segmentation (CJK has no spaces, Arabic diacritics/shaping, Indic conjuncts and tokenizer inefficiency): not fetched this pass; no sourced claim made. Follow-up needed.
- Regulation in non-English jurisdictions: see section 3 rows for China (CAC, Chinese), Japan (ACA, Japanese), Korea (MSIT, Korean), Brazil (Portuguese), India. Korea and China sources were read in the original language; summaries are mine.
- Search-language note: searches were run in English, Korean, Chinese, Japanese and Portuguese; Japanese ACA and Korean primary legal text (law.go.kr) and India's DPIIT paper were not read in full.

## 6. Gaps and recommended follow-ups
1. Fetch EUR-Lex Arts. 3-4 and DSA Arts. 34-35, 40, DMA Art. 6(5) directly (CELEX pages returned only metadata).
2. Bing/Microsoft, xAI and DeepSeek crawler/opt-out documentation.
3. Peer-reviewed audits of web-search bias (e.g., ACM/Nature Human Behaviour) and Google AI Overviews accuracy.
4. Japan ACA March 2024 PDF; Korea statute text; India DPIIT paper; Common Crawl robots.txt/opt-out docs; C2PA spec; Cloudflare default-block and pay-per-crawl primary posts (search returned only secondary blogs).
5. Verify model collapse (Nature 2024) and SEME (PNAS 2015) pages that failed.
