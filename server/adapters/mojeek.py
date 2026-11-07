"""Mojeek Web Search API (own index).

Docs: https://www.mojeek.com/services/search/web-search-api/
Results per request by tier: 10 (Startup), 40 (Business), up to 100 (Enterprise).
Startup tier: 1-hour caching only, no storage. VERIFY parameter and field names
against the docs (MOJEEK_RESULTS_PER_REQUEST sets your tier's cap).
"""
import os
from .base import Adapter, RawResult


class MojeekAdapter(Adapter):
    name = "mojeek"
    env_key = "MOJEEK_API_KEY"

    @property
    def max_results(self):
        return int(os.environ.get("MOJEEK_RESULTS_PER_REQUEST", "10"))

    def search(self, query, depth):
        data = self._get_json("https://api.mojeek.com/search",
                              {"q": query, "api_key": os.environ[self.env_key], "fmt": "json",
                               "t": min(depth, self.max_results)})
        items = (data.get("response") or {}).get("results", [])
        return [RawResult(url=r.get("url", ""), title=r.get("title", ""), snippet=r.get("desc", ""),
                          engine=self.name, rank=i, query=query)
                for i, r in enumerate(items, start=1)]
