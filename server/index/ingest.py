"""Fill the own index from WET / WARC files, or stream a random sample of Common Crawl.

Common Crawl: WET = extracted plain text, WARC = raw HTTP responses
(https://commoncrawl.org/get-started). Files are served at https://data.commoncrawl.org/;
each crawl lists its WET files in crawl-data/<CRAWL-ID>/wet.paths.gz. Common Crawl's
own Terms of Use apply to the data; page content stays the site owners' copyright.
Common Crawl is itself a sample (it archives a random subset of each site), and it skews
towards English (about 42.6% of pages in a recent crawl, CLD2 detection, per
https://commoncrawl.github.io/cc-crawl-statistics/plots/languages), so --lang filters
and --max-per-domain budgets are offered as explicit, reported levers.
"""
from __future__ import annotations
import gzip
import random
import urllib.request
from collections import Counter
from typing import BinaryIO, Iterable
from ..urlnorm import registered_domain
from ..adapters.base import USER_AGENT
from .extract import extract_html
from .store import Doc, Index
from .warc import iter_records, open_maybe_gzip, split_http_response, charset_of

CC_BASE = "https://data.commoncrawl.org/"
CC_LICENCE = "Common Crawl Terms of Use; content (c) site owners"

# ISO 639-3 (as used in Common Crawl's WARC-Identified-Content-Language) -> ISO 639-1
ISO3_TO_1 = {"eng": "en", "deu": "de", "fra": "fr", "spa": "es", "ita": "it", "por": "pt", "nld": "nl",
             "rus": "ru", "pol": "pl", "ukr": "uk", "ces": "cs", "swe": "sv", "dan": "da", "nor": "no",
             "fin": "fi", "tur": "tr", "ara": "ar", "fas": "fa", "heb": "he", "hin": "hi", "ben": "bn",
             "jpn": "ja", "zho": "zh", "kor": "ko", "vie": "vi", "tha": "th", "ind": "id", "msa": "ms",
             "swa": "sw", "ell": "el", "hun": "hu", "ron": "ro", "bul": "bg", "cat": "ca", "hrv": "hr",
             "srp": "sr", "slk": "sk", "slv": "sl", "lit": "lt", "lav": "lv", "est": "et", "tam": "ta",
             "tel": "te", "urd": "ur", "mar": "mr", "guj": "gu", "kan": "kn", "mal": "ml", "pan": "pa",
             "amh": "am", "yor": "yo", "hau": "ha", "ibo": "ig", "zul": "zu", "afr": "af", "tgl": "tl"}


def cc_language(header: str) -> tuple[str, str]:
    first = header.split(",")[0].strip().lower() if header else ""
    if not first:
        return "", ""
    return ISO3_TO_1.get(first, first), "identified by Common Crawl (CLD2) in the WET/WARC metadata"


def html_language(lang_attr: str) -> tuple[str, str]:
    code = lang_attr.split("-")[0].strip().lower()
    return (code, "declared by the page (<html lang>)") if code else ("", "")


class Budget:
    """Per-registered-domain cap and optional language allow-list, applied at ingest."""

    def __init__(self, max_per_domain: int = 0, langs: Iterable[str] = ()):
        self.max = max_per_domain
        self.langs = {l.lower() for l in langs}
        self.per_domain: Counter = Counter()
        self.skipped: Counter = Counter()

    def admit(self, url: str, lang: str) -> bool:
        if self.langs and lang not in self.langs:
            self.skipped["language filter"] += 1
            return False
        reg = registered_domain(url)
        if self.max and self.per_domain[reg] >= self.max:
            self.skipped["domain budget"] += 1
            return False
        self.per_domain[reg] += 1
        return True


def docs_from_stream(stream: BinaryIO, origin: str, licence: str = CC_LICENCE) -> Iterable[Doc]:
    for rec in iter_records(stream):
        url = rec.target_uri
        if not url.startswith(("http://", "https://")):
            continue
        fetched = rec.headers.get("warc-date", "")
        cc_lang = rec.headers.get("warc-identified-content-language", "")
        if rec.type == "conversion":  # WET: plain text, first line is usually the title
            text = rec.body.decode("utf-8", errors="replace").strip()
            title = text.split("\n", 1)[0][:300]
            lang, reason = cc_language(cc_lang)
            yield Doc(url=url, title=title, body=text, lang=lang, lang_reason=reason, origin=origin,
                      licence=licence, fetched=fetched,
                      truncated=bool(rec.headers.get("warc-truncated")))
        elif rec.type == "response":  # WARC: raw HTTP response
            status, hdrs, payload = split_http_response(rec.body)
            ctype = hdrs.get("content-type", "")
            if status != 200 or "html" not in ctype.lower():
                continue
            if "noindex" in hdrs.get("x-robots-tag", "").lower():
                continue
            ex = extract_html(payload.decode(charset_of(ctype), errors="replace"), url)
            if ex.noindex:
                continue
            lang, reason = cc_language(cc_lang)
            if not lang:
                lang, reason = html_language(ex.lang)
            yield Doc(url=url, title=ex.title, body=ex.text, lang=lang, lang_reason=reason, origin=origin,
                      licence=licence, fetched=fetched, truncated=bool(rec.headers.get("warc-truncated")))


def ingest(index: Index, docs: Iterable[Doc], budget: Budget | None = None, limit: int = 0,
           progress=None) -> Counter:
    budget = budget or Budget()
    c: Counter = Counter()
    for d in docs:
        if limit and c["added"] + c["replaced"] >= limit:
            break
        if not budget.admit(d.url, d.lang):
            continue
        status, _ = index.add(d)
        c[status] += 1
        if progress and (c["added"] + c["replaced"]) % 1000 == 0:
            progress(c)
            index.commit()
    index.commit()
    return c


def _with_skips(c: Counter, budget: Budget) -> Counter:
    c.update({f"skipped ({k})": v for k, v in budget.skipped.items()})
    return c


def ingest_files(index: Index, paths: list[str], licence: str = CC_LICENCE, budget: Budget | None = None,
                 limit: int = 0, progress=None) -> Counter:
    total: Counter = Counter()
    budget = budget or Budget()
    for p in paths:
        with open_maybe_gzip(p) as f:
            docs = docs_from_stream(f, origin=f"file:{p.rsplit('/', 1)[-1]}", licence=licence)
            left = limit - total["added"] - total["replaced"] if limit else 0
            if limit and left <= 0:
                break
            total.update(ingest(index, docs, budget=budget, limit=left, progress=progress))
    return _with_skips(total, budget)


def _open_url(url: str, timeout: float = 60.0):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout)


def cc_wet_paths(crawl: str) -> list[str]:
    with _open_url(f"{CC_BASE}crawl-data/{crawl}/wet.paths.gz") as r:
        return gzip.decompress(r.read()).decode().split()


def ingest_common_crawl(index: Index, crawl: str, files: int = 1, seed: str = "", per_file: int = 0,
                        budget: Budget | None = None, progress=None) -> Counter:
    """Stream `files` randomly chosen WET files (seeded, so the sample is reproducible)."""
    paths = cc_wet_paths(crawl)
    chosen = random.Random(seed or crawl).sample(paths, min(files, len(paths)))
    total: Counter = Counter()
    budget = budget or Budget()
    for p in chosen:
        with _open_url(CC_BASE + p) as resp, gzip.GzipFile(fileobj=resp) as gz:
            total.update(ingest(index, docs_from_stream(gz, origin=f"commoncrawl:{crawl}"), budget=budget,
                                limit=per_file, progress=progress))
        total["wet files"] += 1
    return _with_skips(total, budget)
