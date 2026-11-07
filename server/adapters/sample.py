"""Offline adapter over a SYNTHETIC, clearly labelled sample (data/sample_results.json).

It lets the whole pipeline and UI run with no API keys. Results are fictional
(.example domains) and must never be presented as real search results.
"""
import json
import re
from pathlib import Path
from .base import Adapter, RawResult

DATA = Path(__file__).resolve().parents[2] / "data" / "sample_results.json"


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"\w+", s.lower()) if len(t) > 2}


class SampleAdapter(Adapter):
    name = "sample"
    max_results = 200

    def search(self, query, depth):
        items = json.loads(DATA.read_text())["results"]
        q = _tokens(query)
        out = []
        for it in items:
            hay = _tokens(it["title"] + " " + it["snippet"] + " " + " ".join(it.get("topics", [])))
            if q and not (q & hay) and not it.get("always", False):
                continue
            for engine, rank in it["engines"].items():
                out.append(RawResult(url=it["url"], title=it["title"], snippet=it["snippet"],
                                     engine=f"sample-{engine}", rank=rank, query=query,
                                     language=it.get("lang", ""), published=it.get("date", ""),
                                     extra={"synthetic": True, "source_type_hint": it.get("type", "")}))
        return out[: depth * 3]
