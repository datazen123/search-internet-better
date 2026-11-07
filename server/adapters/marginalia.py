"""Marginalia Search API (independent/small-web index).

Docs: https://about.marginalia-search.com/article/api/  (count 1-100, dc = max results per domain)
Free non-commercial key by email; commercial use needs a metered key.
VERIFY the endpoint and response field names against the docs before relying on this
adapter; set MARGINALIA_API_URL if it differs. The old API is deprecated.
"""
import os
from .base import Adapter, RawResult


class MarginaliaAdapter(Adapter):
    name = "marginalia"
    env_key = "MARGINALIA_API_KEY"
    max_results = 100

    def search(self, query, depth):
        base = os.environ.get("MARGINALIA_API_URL", "https://api.marginalia.nu/{key}/search/{q}")
        key = os.environ[self.env_key]
        url = base.replace("{key}", key).replace("{q}", __import__("urllib.parse").parse.quote(query))
        data = self._get_json(url, {"count": min(depth, self.max_results), "dc": 3})
        out = []
        for i, r in enumerate(data.get("results", []), start=1):
            out.append(RawResult(url=r.get("url", ""), title=r.get("title", ""),
                                 snippet=r.get("description", ""), engine=self.name, rank=i, query=query))
        return out
