"""Brave Search API (own index, supports Goggles).

Docs: https://api-dashboard.search.brave.com/app/documentation/web-search/query
count max 20 per page, offset max 9 (about 200 results per query). $5 per 1,000 requests.
Storage: no retention of results without a separate storage-rights plan, so this
adapter never writes results to disk.
"""
import os
from .base import Adapter, RawResult


class BraveAdapter(Adapter):
    name = "brave"
    env_key = "BRAVE_API_KEY"
    max_results = 200

    def search(self, query, depth):
        headers = {"X-Subscription-Token": os.environ[self.env_key]}
        url = "https://api.search.brave.com/res/v1/web/search"
        out, rank = [], 0
        pages = min(10, max(1, (min(depth, self.max_results) + 19) // 20))
        for offset in range(pages):
            data = self._get_json(url, {"q": query, "count": 20, "offset": offset}, headers=headers)
            items = (data.get("web") or {}).get("results", [])
            if not items:
                break
            for r in items:
                rank += 1
                out.append(RawResult(url=r.get("url", ""), title=r.get("title", ""),
                                     snippet=r.get("description", ""), engine=self.name, rank=rank,
                                     query=query, language=r.get("language", ""),
                                     published=r.get("page_age", "")))
        return out
