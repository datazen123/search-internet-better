"""Health-panel metrics computed for every search (see docs/DESIGN.md, 'Measuring bias and noise')."""
from __future__ import annotations
import math
from collections import Counter


def gini(values: list[float]) -> float:
    xs = sorted(v for v in values if v >= 0)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * sum(xs)) - (n + 1) / n


def normalized_entropy(counts: list[int]) -> float:
    total = sum(counts)
    k = len([c for c in counts if c > 0])
    if total == 0 or k <= 1:
        return 0.0
    h = -sum((c / total) * math.log(c / total) for c in counts if c > 0)
    return h / math.log(k)


def health(results: list[dict], lens_target: dict[str, float], engines_queried: list[str]) -> dict:
    shown = [r for r in results if not r.get("hidden")]
    n = len(shown) or 1
    dom = Counter(r["registered_domain"] for r in shown)
    top3 = sum(c for _, c in dom.most_common(3)) / n
    lang = Counter(r["language"] for r in shown)
    types = Counter(r["source_type"] for r in shown)
    zones = Counter(r["zone"] for r in shown)
    noisy = sum(1 for r in shown if r["noise_flags"])
    agreement = Counter(len(r["engines"]) for r in shown)
    # position-weighted exposure (log discount, as in DCG) per domain
    exposure = Counter()
    for pos, r in enumerate(sorted(shown, key=lambda r: -r["score"]), start=1):
        exposure[r["registered_domain"]] += 1 / math.log2(pos + 1)
    lang_share = {k: v / n for k, v in lang.items()}
    target_gap = {k: round(lang_share.get(k, 0) - t, 3) for k, t in lens_target.items()} if lens_target else {}
    return {
        "results_shown": len(shown),
        "distinct_domains": len(dom),
        "top3_domain_share": round(top3, 3),
        "domain_gini": round(gini(list(dom.values())), 3),
        "domain_diversity": round(normalized_entropy(list(dom.values())), 3),
        "engines_queried": engines_queried,
        "found_by_n_engines": dict(sorted(agreement.items())),
        "zone_counts": dict(zones),
        "language_mix": {k: round(v, 3) for k, v in sorted(lang_share.items(), key=lambda kv: -kv[1])},
        "language_target_gap": target_gap,
        "source_type_mix": {k: round(v / n, 3) for k, v in types.most_common()},
        "noise_share": round(noisy / n, 3),
        "exposure_gini": round(gini(list(exposure.values())), 3),
    }
