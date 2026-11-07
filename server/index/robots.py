"""robots.txt parsing and matching per RFC 9309 (https://www.rfc-editor.org/rfc/rfc9309.html).

Why hand-written: the server is dependency-free and urllib.robotparser applies the first
matching rule, whereas RFC 9309 requires the most specific (longest) match. Implemented:
- groups start at user-agent lines; groups naming the same product token are merged;
- product token matched case-insensitively; fall back to the "*" group; no group -> allow;
- longest matching path wins; allow wins a tie; "*" wildcard and "$" end anchor;
- paths compared case-sensitively after percent-encoding normalisation;
- /robots.txt itself is always allowed; at most 500 KiB is parsed (RFC 9309 s2.5).
Crawl-delay is NOT part of RFC 9309; we read it and the crawler honours it (capped),
which is our documented policy (Common Crawl's CCBot honours it too).
Status handling (RFC 9309 s2.3.1) lives in for_status().
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from urllib.parse import quote, unquote

MAX_BYTES = 500 * 1024


def _norm(path: str) -> str:
    """Percent-encoding normalisation: decode, then re-encode everything outside the
    unreserved/reserved sets, so '/a%7eb' and '/a~b' compare equal. '*' and '$' kept."""
    return quote(unquote(path), safe="/?&=;:@+$,!*'()~-._%#[]")


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[tuple[bool, str]] = field(default_factory=list)  # (allow, pattern)
    crawl_delay: float | None = None


class Robots:
    def __init__(self, groups: list[_Group] | None = None, sitemaps: list[str] | None = None,
                 mode: str = "parsed"):
        self.groups = groups or []
        self.sitemaps = sitemaps or []
        self.mode = mode   # parsed | allow_all | disallow_all

    # construction -------------------------------------------------------------
    @classmethod
    def parse(cls, data: bytes | str) -> "Robots":
        if isinstance(data, bytes):
            data = data[:MAX_BYTES].decode("utf-8", errors="replace")
        else:
            data = data[:MAX_BYTES]
        groups: list[_Group] = []
        sitemaps: list[str] = []
        cur: _Group | None = None
        last_was_agent = False
        for raw in data.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, val = (s.strip() for s in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if cur is None or not last_was_agent:
                    cur = _Group()
                    groups.append(cur)
                cur.agents.append(val.lower())
                last_was_agent = True
                continue
            last_was_agent = False
            if key == "sitemap":
                sitemaps.append(val)
            elif cur is None:
                continue  # rules before any user-agent line are ignored
            elif key in ("allow", "disallow"):
                if val:  # an empty disallow matches nothing
                    cur.rules.append((key == "allow", _norm(val)))
            elif key == "crawl-delay":
                try:
                    cur.crawl_delay = float(val)
                except ValueError:
                    pass
        return cls(groups, sitemaps)

    @classmethod
    def allow_all(cls) -> "Robots":
        return cls(mode="allow_all")

    @classmethod
    def disallow_all(cls) -> "Robots":
        return cls(mode="disallow_all")

    @classmethod
    def for_status(cls, status: int, body: bytes = b"") -> "Robots":
        """RFC 9309 s2.3.1: 2xx parse; 4xx 'unavailable' -> allow; 5xx/unreachable -> disallow.
        Redirects are followed by the caller (up to 5 hops) before this is called."""
        if 200 <= status < 300:
            return cls.parse(body)
        if 400 <= status < 500:
            return cls.allow_all()
        return cls.disallow_all()

    # matching -----------------------------------------------------------------
    def _groups_for(self, agent: str) -> list[_Group]:
        token = agent.lower()
        mine = [g for g in self.groups if token in g.agents]
        return mine or [g for g in self.groups if "*" in g.agents]

    @staticmethod
    def _matches(pattern: str, path: str) -> bool:
        anchored = pattern.endswith("$")
        body = pattern[:-1] if anchored else pattern
        rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
        return re.match(rx + ("$" if anchored else ""), path) is not None

    def allowed(self, path: str, agent: str) -> bool:
        """path = URL path plus query, e.g. '/a/b?x=1'."""
        if self.mode != "parsed":
            return self.mode == "allow_all"
        path = _norm(path or "/")
        if path == "/robots.txt":
            return True
        best_len, best_allow = -1, True
        for g in self._groups_for(agent):
            for allow, pattern in g.rules:
                if self._matches(pattern, path):
                    n = len(pattern)
                    if n > best_len or (n == best_len and allow):
                        best_len, best_allow = n, allow
        return best_allow

    def crawl_delay(self, agent: str) -> float | None:
        delays = [g.crawl_delay for g in self._groups_for(agent) if g.crawl_delay is not None]
        return max(delays) if delays else None
