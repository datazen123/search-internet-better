"""Search pipeline: plan -> fetch -> merge -> signals -> local re-rank -> landscape -> metrics.

Design rule: retrieve broadly, order carefully, show the shape (core / margin / tail),
and explain every placement ("why it's here").
"""
from __future__ import annotations
import hashlib
import math
import statistics
from concurrent.futures import ThreadPoolExecutor
from .adapters import get_adapters, RawResult
from .lens import Lens
from .metrics import health
from .signals import source_type, guess_language, tokens, jaccard, SOURCE_TYPES
from .urlnorm import normalize, domain, registered_domain

ZONES = ("core", "margin", "tail")
RRF_K = 60  # reciprocal-rank-fusion constant (Cormack et al. 2009 style)


def plan_queries(query: str, lens: Lens) -> list[str]:
    qs = [query] + [q.replace("{q}", query) for q in lens.extra_queries]
    seen, out = set(), []
    for q in qs:
        if q.strip() and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def fetch(queries: list[str], lens: Lens, depth: int) -> tuple[list[RawResult], list[str], list[dict]]:
    adapters = get_adapters(lens.engines) or get_adapters(["sample"])
    jobs = [(a, q) for a in adapters for q in queries]
    errors = []

    def run(job):
        a, q = job
        try:
            return a.search(q, min(depth, a.max_results))
        except Exception as e:  # surfaced to the user, never silently dropped
            errors.append({"engine": a.name, "query": q, "error": f"{type(e).__name__}: {e}"})
            return []

    with ThreadPoolExecutor(max_workers=8) as ex:
        raw = [r for batch in ex.map(run, jobs) for r in batch]
    return raw, [a.name for a in adapters], errors


def merge(raw: list[RawResult]) -> list[dict]:
    by_key: dict[str, dict] = {}
    for r in raw:
        if not r.url:
            continue
        key = normalize(r.url)
        m = by_key.get(key)
        if m is None:
            m = by_key[key] = {"key": key, "url": r.url, "title": r.title, "snippet": r.snippet,
                               "engines": {}, "queries": set(), "language_supplied": r.language,
                               "published": r.published, "extra": dict(r.extra)}
        best = m["engines"].get(r.engine)
        m["engines"][r.engine] = r.rank if best is None else min(best, r.rank)
        m["queries"].add(r.query)
        if len(r.snippet) > len(m["snippet"]):
            m["snippet"] = r.snippet
    out = list(by_key.values())
    for m in out:
        m["queries"] = sorted(m["queries"])
    return out


def add_signals(items: list[dict], engines_queried: list[str]) -> None:
    n_eng = max(1, len({e for m in items for e in m["engines"]}))
    for m in items:
        m["domain"] = domain(m["url"])
        m["registered_domain"] = registered_domain(m["url"])
        m["source_type"], m["source_type_reason"] = source_type(m["url"], m["extra"].get("source_type_hint", ""))
        m["language"], m["language_reason"] = guess_language(m["title"] + " " + m["snippet"], m["language_supplied"])
        ranks = list(m["engines"].values())
        m["fusion"] = sum(1 / (RRF_K + r) for r in ranks)
        m["agreement"] = len(ranks) / n_eng
        m["rank_spread"] = round(statistics.pstdev(ranks), 1) if len(ranks) > 1 else None
        m["tokens"] = tokens(m["title"] + " " + m["snippet"])
        m["noise_flags"] = []
    _flag_noise(items)


def _flag_noise(items: list[dict]) -> None:
    # near-duplicate clusters by title+snippet token overlap (cheap stand-in for SimHash)
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a["registered_domain"] != b["registered_domain"] and jaccard(a["tokens"], b["tokens"]) >= 0.8:
                for x, y in ((a, b), (b, a)):
                    flag = f"near-duplicate of {y['domain']}"
                    if flag not in x["noise_flags"]:
                        x["noise_flags"].append(flag)
    # one domain publishing the same item in many languages -> possible machine-translated filler
    langs_by_domain: dict[str, set] = {}
    for m in items:
        langs_by_domain.setdefault(m["registered_domain"], set()).add(m["language"])
    for m in items:
        if len(langs_by_domain[m["registered_domain"]]) >= 4:
            m["noise_flags"].append("same site in 4+ languages (possible machine-translated filler)")
    for m in items:
        if m["extra"].get("noise_hint"):
            m["noise_flags"].append(m["extra"]["noise_hint"])


def rerank(items: list[dict], lens: Lens) -> list[dict]:
    rules = lens.rules
    generic_discard = any(r.generic_discard for r in rules)
    max_fusion = max((m["fusion"] for m in items), default=1) or 1
    for m in items:
        why = []
        base = m["fusion"] / max_fusion
        why.append(f"found by {len(m['engines'])} engine(s); best rank {min(m['engines'].values())}")
        w = lens.type_weights.get(m["source_type"], 1.0)
        if w != 1.0:
            why.append(f"source type '{m['source_type']}' weighted x{w}")
        mult, discarded, matched = 1.0, False, False
        for r in rules:
            if r.generic_discard or not r.matches(m["url"], m["domain"]):
                continue
            matched = True
            if r.action == "discard":
                discarded = True
            elif r.action == "boost":
                mult *= 1 + 0.25 * r.strength
                why.append(f"lens rule boost={r.strength} ({r.site or r.pattern})")
            else:
                mult /= 1 + 0.25 * r.strength
                why.append(f"lens rule downrank={r.strength} ({r.site or r.pattern})")
        if generic_discard and not matched:
            discarded = True
        m["discarded"] = discarded
        if discarded:
            why.append("removed by a lens discard rule")
        m["score"] = base * w * mult
        m["why"] = why

    kept = sorted((m for m in items if not m["discarded"]), key=lambda m: -m["score"])
    # diversity: per-domain cap, extra items demoted (not deleted) so they stay visible in the tail
    per_dom: dict[str, int] = {}
    for m in kept:
        c = per_dom.get(m["registered_domain"], 0) + 1
        per_dom[m["registered_domain"]] = c
        if c > lens.max_per_domain:
            m["score"] *= 0.5 ** (c - lens.max_per_domain)
            m["why"].append(f"demoted: domain cap ({lens.max_per_domain} per domain)")
    # optional exposure rotation: deterministic jitter so different tail items surface on different days
    if lens.rotation_seed:
        for m in kept:
            h = int(hashlib.sha1((lens.rotation_seed + m["key"]).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
            m["score"] *= 0.9 + 0.2 * h
    for m in kept:
        if m["noise_flags"] and lens.quality_floor == "hide":
            m["hidden"] = True
            m["why"].append("hidden by lens quality floor (still counted in metrics)")
    return sorted(kept, key=lambda m: -m["score"])


def landscape(items: list[dict], lens: Lens, n_engines: int) -> None:
    """Assign zone, radius (0 = centre) and slice angle for the mountain-peak view."""
    if not items:
        return
    scores = [m["score"] for m in items]
    hi, lo = max(scores), min(scores)
    span = (hi - lo) or 1
    n = len(items)
    for i, m in enumerate(items):
        pct = i / max(1, n - 1)
        agree_all = len(m["engines"]) >= max(2, math.ceil(n_engines * 0.66))
        if pct <= 0.12 or (pct <= 0.25 and agree_all):
            zone = "core"
        elif pct <= 0.55:
            zone = "margin"
        else:
            zone = "tail"
        m["zone"] = zone
        m["radius"] = round(1 - (m["score"] - lo) / span, 3)
        m["slice"] = {"source_type": m["source_type"], "language": m["language"],
                      "engine": sorted(m["engines"])[0] if len(m["engines"]) == 1 else "several engines"}[lens.slice_by]
        m["why"].append(f"zone: {zone} (position {i + 1} of {n})")
    order = {"core": 0, "margin": 1, "tail": 2}
    allowed = order[lens.width]
    for m in items:
        m["in_window"] = order[m["zone"]] <= allowed


def search(query: str, lens: Lens, depth: int = 50) -> dict:
    queries = plan_queries(query, lens)
    raw, engines, errors = fetch(queries, lens, depth)
    items = merge(raw)
    add_signals(items, engines)
    ranked = rerank(items, lens)
    landscape(ranked, lens, len({e for m in ranked for e in m["engines"]}))
    for m in ranked:
        m.pop("tokens", None)
        m["synthetic"] = bool(m["extra"].get("synthetic"))
        m.pop("extra", None)
    synthetic = any(m["synthetic"] for m in ranked)
    return {
        "query": query,
        "queries_run": queries,
        "lens": lens.to_dict(),
        "engines": engines,
        "errors": errors,
        "synthetic_sample": synthetic,
        "discarded_count": sum(1 for m in items if m.get("discarded")),
        "results": ranked,
        "health": health(ranked, lens.language_target, engines) if ranked else {},
        "slices": SOURCE_TYPES if lens.slice_by == "source_type" else sorted({m["slice"] for m in ranked}),
    }
