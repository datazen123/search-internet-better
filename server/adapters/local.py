"""Own index adapter: BM25 over the project's own long-tail sample (server/index/).

Filled from Common Crawl WET/WARC files and/or the polite crawler. No vendor terms apply
to the ranking; the stored pages carry their own origin and licence label, which every
result reports as provenance. Available once the index holds at least one document.
"""
from __future__ import annotations
from .base import Adapter, RawResult


class LocalIndexAdapter(Adapter):
    name = "local"
    max_results = 200
    persistent_cache_allowed = True   # it is our own index; still, queries are never stored
    _index = None
    _index_path = None

    @classmethod
    def _open(cls):
        from ..index import index_path
        from ..index.store import Index
        p = index_path()
        if not p.exists():
            return None
        if cls._index is None or cls._index_path != p:
            if cls._index is not None:
                cls._index.close()
            cls._index, cls._index_path = Index(p), p
        return cls._index

    def available(self) -> bool:
        try:
            idx = self._open()
            return bool(idx and idx.count())
        except Exception:
            return False

    def search(self, query, depth):
        idx = self._open()
        out = []
        for i, h in enumerate(idx.search(query, min(depth, self.max_results)), start=1):
            extra = {"provenance": {"index": "own", "origin": h["origin"], "licence": h["licence"],
                                    "fetched": h["fetched"], "bm25": h["bm25"], "tokenizer": h["tokenizer"],
                                    "truncated": h["truncated"]}}
            if h["lang_reason"]:
                extra["language_reason"] = h["lang_reason"]
            if h["dup_of_url"]:
                extra["noise_hint"] = f"near-duplicate (SimHash) of {h['dup_of_url']} in own index"
            out.append(RawResult(url=h["url"], title=h["title"], snippet=h["snippet"], engine=self.name, rank=i,
                                 query=query, language=h["lang"], published=h["fetched"], extra=extra))
        return out
