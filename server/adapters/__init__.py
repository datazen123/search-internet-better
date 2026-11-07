"""Source adapters. Each adapter enforces its vendor's terms (depth, caching, attribution).

Default posture (see docs/DESIGN.md): licensed APIs only, results kept in memory for the
request, no persistent SERP cache, every result links back to its origin.
"""
from .base import Adapter, RawResult
from .sample import SampleAdapter
from .marginalia import MarginaliaAdapter
from .brave import BraveAdapter
from .mojeek import MojeekAdapter
from .local import LocalIndexAdapter

REGISTRY = {
    "sample": SampleAdapter,
    "marginalia": MarginaliaAdapter,
    "brave": BraveAdapter,
    "mojeek": MojeekAdapter,
    "local": LocalIndexAdapter,
}


def get_adapters(names):
    out = []
    for n in names:
        cls = REGISTRY.get(n)
        if cls is None:
            continue
        a = cls()
        if a.available():
            out.append(a)
    return out


def adapter_status():
    return {n: cls().available() for n, cls in REGISTRY.items()}
