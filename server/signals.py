"""Per-result signals and labels: source type, script/language guess, noise flags.

All heuristics here are deliberately simple and transparent; each label is shown to the
user with its reason. Replace with better classifiers over time (see BACKLOG.md).
"""
from __future__ import annotations
import re
from .urlnorm import domain

SOURCE_TYPES = ["research", "government", "news", "reference", "forum", "commercial", "personal", "other"]

_TYPE_PATTERNS = [
    ("government", re.compile(r"(\.gov(\.[a-z]{2})?$|\.go\.[a-z]{2}$|\.gouv\.|\.gob\.|\.int$|europa\.eu$|who\.int$|un\.org$)")),
    ("research", re.compile(r"(\.edu$|\.ac\.[a-z]{2}$|\.edu\.[a-z]{2}$|arxiv\.org$|doi\.org$|pubmed|ncbi\.nlm\.nih\.gov$|nature\.com$|sciencedirect\.com$|springer|wiley|plos\.org$|ssrn\.com$|researchgate|scholar)")),
    ("reference", re.compile(r"(wikipedia\.org$|wiktionary|britannica\.com$|wikidata)")),
    ("forum", re.compile(r"(reddit\.com$|stackexchange\.com$|stackoverflow\.com$|quora\.com$|forum|discourse|lemmy|news\.ycombinator\.com$)")),
    ("news", re.compile(r"(news|times|post|herald|guardian|reuters\.com$|apnews\.com$|bbc\.|cnn\.com$|nhk\.or\.jp$|yna\.co\.kr$)")),
    ("personal", re.compile(r"(blog|substack\.com$|medium\.com$|wordpress\.com$|github\.io$|neocities\.org$)")),
    ("commercial", re.compile(r"(shop|store|amazon\.|ebay\.|deals|coupon|best-?\w*-reviews)")),
]


def source_type(url: str, hint: str = "") -> tuple[str, str]:
    """Return (type, reason)."""
    if hint in SOURCE_TYPES:
        return hint, "label supplied by source data"
    host = domain(url)
    for t, rx in _TYPE_PATTERNS:
        if rx.search(host):
            return t, f"domain pattern matched ({host})"
    return "other", "no pattern matched"


_SCRIPTS = [
    ("ko", re.compile(r"[가-힯]")),
    ("ja", re.compile(r"[぀-ヿ]")),
    ("zh", re.compile(r"[一-鿿]")),
    ("ar", re.compile(r"[؀-ۿ]")),
    ("hi", re.compile(r"[ऀ-ॿ]")),
    ("bn", re.compile(r"[ঀ-৿]")),
    ("ru", re.compile(r"[Ѐ-ӿ]")),
    ("th", re.compile(r"[฀-๿]")),
    ("he", re.compile(r"[֐-׿]")),
]


def guess_language(text: str, supplied: str = "") -> tuple[str, str]:
    """Script-based guess. Latin-script text returns 'latin' (unknown language) unless supplied.

    Script detection cannot tell English from Spanish or Swahili; a proper language-ID model
    (e.g. fastText lid.176) is on the backlog.
    """
    if supplied:
        return supplied.split("-")[0].lower(), "language supplied by engine"
    for code, rx in _SCRIPTS:
        if len(rx.findall(text)) >= 2:
            return code, "script detected"
    return "latin", "Latin script; language not identified"


def tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"\w+", s.lower()) if len(t) > 2}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0
