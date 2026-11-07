from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = "experimental-search/0.1 (+https://github.com/; research prototype)"


@dataclass
class RawResult:
    url: str
    title: str
    snippet: str
    engine: str
    rank: int                     # 1-based rank within that engine's list for that query
    query: str = ""
    language: str = ""            # BCP-47 if the engine supplies it
    published: str = ""
    extra: dict = field(default_factory=dict)


class Adapter:
    name = "base"
    env_key = ""            # environment variable holding the API key ("" = no key needed)
    max_results = 10        # vendor's per-query depth cap
    persistent_cache_allowed = False

    def available(self) -> bool:
        return not self.env_key or bool(os.environ.get(self.env_key))

    def search(self, query: str, depth: int) -> list[RawResult]:
        raise NotImplementedError

    # helpers
    def _get_json(self, url: str, params: dict, headers: dict | None = None, timeout: float = 10.0):
        full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
