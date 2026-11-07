"""A small, polite, single-process crawler that feeds the own index.

Good-citizen rules (docs/research/build_crawler.md, sections 1.4, 1.5 and 4):
- Identifies itself: "<token>/<version> (+<info URL>)"; set CRAWLER_INFO_URL to a page that
  explains the bot and how to contact you. No cookies, no logins, no JavaScript.
- robots.txt per RFC 9309 (see robots.py): fetched before the first page of each host,
  cached for at most 24 hours, up to 5 redirects followed; 4xx -> allowed, 5xx or
  unreachable -> the host is not crawled. <meta name="robots"> and X-Robots-Tag
  noindex / nofollow are honoured; rel="nofollow" links are not followed.
- One request at a time per host, at least `min_delay` seconds apart (default 5 s).
  Crawl-delay is honoured up to `max_crawl_delay` (default 60 s; hosts asking for more
  are skipped rather than ignored). This Crawl-delay policy is ours, not the RFC's.
- 429 / 503: honour Retry-After (seconds or HTTP date), otherwise double the delay;
  3 consecutive failures stop the host for this run. At most 4 redirects per page.
- Bodies capped at 5 MiB (Common Crawl's current cap); truncation is recorded.
- Bias levers, reported in the run summary: per-registered-domain page budget, same-site
  restriction to the seeds' domains, and hosts are interleaved (the frontier is ordered by
  each host's next allowed time, so no single site monopolises the crawl).
"""
from __future__ import annotations
import gzip
import heapq
import os
import time
import urllib.error
import urllib.request
import zlib
from collections import Counter, deque
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit
from ..urlnorm import normalize, registered_domain
from .extract import extract_html
from .ingest import html_language
from .robots import Robots
from .store import Doc, Index
from .warc import charset_of

AGENT_TOKEN = "SearchInternetBetterBot"
VERSION = "0.1"
DEFAULT_INFO_URL = "https://github.com/datazen123/search-internet-better/blob/main/docs/CRAWLER.md"
MAX_BYTES = 5 * 1024 * 1024
ROBOTS_TTL = 24 * 3600
LICENCE = "crawled under robots.txt; content (c) site owners"


def user_agent() -> str:
    return f"{AGENT_TOKEN}/{VERSION} (+{os.environ.get('CRAWLER_INFO_URL', DEFAULT_INFO_URL)})"


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes
    url: str
    truncated: bool = False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None  # redirects are handled (and robots-checked) by the crawler


class HttpFetcher:
    def __init__(self, timeout: float = 15.0, max_bytes: int = MAX_BYTES):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.opener = urllib.request.build_opener(_NoRedirect())  # no cookie handler on purpose

    def __call__(self, url: str) -> Response:
        req = urllib.request.Request(url, headers={
            "User-Agent": user_agent(), "Accept": "text/html,application/xhtml+xml;q=0.9,text/plain;q=0.5",
            "Accept-Encoding": "gzip, deflate"})
        try:
            resp = self.opener.open(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            resp = e
        with resp:
            raw = resp.read(self.max_bytes + 1)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            status = resp.status if hasattr(resp, "status") and resp.status else resp.code
        truncated = len(raw) > self.max_bytes
        raw = raw[: self.max_bytes]
        enc = headers.get("content-encoding", "").lower()
        try:
            if enc == "gzip":
                raw = gzip.decompress(raw) if not truncated else zlib.decompressobj(31).decompress(raw)
            elif enc == "deflate":
                raw = zlib.decompress(raw)
        except (OSError, zlib.error):
            pass
        return Response(status, headers, raw[: self.max_bytes], url, truncated)


def retry_after_seconds(value: str, now: float | None = None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        dt = parsedate_to_datetime(value)
        return max(0.0, dt.timestamp() - (now if now is not None else time.time()))
    except (TypeError, ValueError):
        return None


@dataclass
class _Host:
    queue: deque = field(default_factory=deque)   # (url, redirect_hops, attempts)
    robots: Robots | None = None
    robots_at: float = 0.0
    delay: float = 0.0
    next_ok: float = 0.0      # earliest time the next request to this host may start
    scheduled: bool = False   # exactly one frontier entry per host
    failures: int = 0
    stopped: str = ""


class Crawler:
    def __init__(self, index: Index, fetch=None, min_delay: float = 5.0, max_crawl_delay: float = 60.0,
                 max_pages: int = 100, max_per_domain: int = 50, same_site: bool = True,
                 max_redirects: int = 4, clock=time.monotonic, sleep=time.sleep, log=None):
        self.index = index
        self.fetch = fetch or HttpFetcher()
        self.min_delay = min_delay
        self.max_crawl_delay = max_crawl_delay
        self.max_pages = max_pages
        self.max_per_domain = max_per_domain
        self.same_site = same_site
        self.max_redirects = max_redirects
        self.clock, self.sleep = clock, sleep
        self.log = log or (lambda msg: None)
        self.hosts: dict[str, _Host] = {}
        self.heap: list[tuple[float, str]] = []
        self.seen: set[str] = set()
        self.allowed_domains: set[str] = set()
        self.per_domain: Counter = Counter()
        self.stats: Counter = Counter()

    # frontier -------------------------------------------------------------------
    @staticmethod
    def _origin(url: str) -> str:
        p = urlsplit(url)
        return f"{p.scheme}://{p.netloc.lower()}"

    def add_seeds(self, urls) -> None:
        for u in urls:
            u = u.strip()
            if u and not u.startswith("#"):
                self.allowed_domains.add(registered_domain(u))
                self._enqueue(u)

    def _enqueue(self, url: str, hops: int = 0, front: bool = False, attempts: int = 0) -> None:
        if not url.startswith(("http://", "https://")):
            return
        key = normalize(url)
        if key in self.seen and not attempts:
            return
        if self.same_site and registered_domain(url) not in self.allowed_domains:
            self.stats["skipped (outside seed domains)"] += 1
            return
        self.seen.add(key)
        origin = self._origin(url)
        h = self.hosts.get(origin)
        if h is None:
            h = self.hosts[origin] = _Host(delay=self.min_delay)
        if h.stopped:
            return
        (h.queue.appendleft if front else h.queue.append)((url, hops, attempts))
        self._schedule(origin)

    def _schedule(self, origin: str) -> None:
        h = self.hosts[origin]
        if h.queue and not h.stopped and not h.scheduled:
            heapq.heappush(self.heap, (max(self.clock(), h.next_ok), origin))
            h.scheduled = True

    def _request(self, h: _Host, url: str) -> Response:
        """Every request to a host goes through here, so the per-host gap always holds."""
        wait = h.next_ok - self.clock()
        if wait > 0:
            self.sleep(wait)
        try:
            return self.fetch(url)
        finally:
            h.next_ok = self.clock() + h.delay

    # robots ---------------------------------------------------------------------
    def _robots(self, origin: str) -> tuple[Robots, bool]:
        """Return (robots, made_request)."""
        h = self.hosts[origin]
        if h.robots is not None and self.clock() - h.robots_at < ROBOTS_TTL:
            return h.robots, False
        url = origin + "/robots.txt"
        robots = None
        for _ in range(6):  # initial request + up to 5 redirects (RFC 9309 s2.3.1.2)
            try:
                r = self._request(h, url)
            except Exception:
                robots = Robots.disallow_all()  # unreachable: treat as complete disallow
                break
            if r.status in (301, 302, 303, 307, 308) and r.headers.get("location"):
                url = urljoin(url, r.headers["location"])
                continue
            robots = Robots.for_status(r.status, r.body)
            break
        h.robots = robots or Robots.allow_all()  # >5 redirects: robots.txt "unavailable"
        h.robots_at = self.clock()
        self.stats["robots.txt fetched"] += 1
        cd = h.robots.crawl_delay(AGENT_TOKEN)
        if cd is not None:
            if cd > self.max_crawl_delay:
                h.stopped = f"Crawl-delay {cd}s above our cap of {self.max_crawl_delay}s"
            else:
                h.delay = max(h.delay, cd)
                h.next_ok = max(h.next_ok, h.robots_at + h.delay)
        if h.robots.mode == "disallow_all":
            h.stopped = "robots.txt unreachable or server error (RFC 9309: assume disallow)"
        return h.robots, True

    # main loop ------------------------------------------------------------------
    def run(self) -> Counter:
        while self.heap and self.stats["pages indexed"] < self.max_pages:
            _, origin = heapq.heappop(self.heap)
            h = self.hosts[origin]
            h.scheduled = False
            if h.stopped or not h.queue:
                if h.stopped and h.queue:
                    self.stats[f"host stopped: {h.stopped}"] += 1
                    h.queue.clear()
                continue
            robots, requested = self._robots(origin)
            if h.stopped:
                self.stats[f"host stopped: {h.stopped}"] += 1
                h.queue.clear()
                continue
            if requested:
                self._schedule(origin)
                continue
            url, hops, attempts = h.queue.popleft()
            parts = urlsplit(url)
            path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
            if not robots.allowed(path, AGENT_TOKEN):
                self.stats["blocked by robots.txt"] += 1
                self._schedule(origin)
                continue
            if self.max_per_domain and self.per_domain[registered_domain(url)] >= self.max_per_domain:
                self.stats["skipped (domain budget)"] += 1
                self._schedule(origin)
                continue
            self._fetch_page(origin, h, url, hops, attempts)
        self.index.commit()
        self.stats["hosts seen"] = len(self.hosts)
        return self.stats

    def _fetch_page(self, origin: str, h: _Host, url: str, hops: int, attempts: int) -> None:
        self.stats["requests"] += 1
        try:
            r = self._request(h, url)
        except Exception as e:
            self._fail(origin, h, f"{type(e).__name__}")
            return
        if r.status in (301, 302, 303, 307, 308):
            loc = r.headers.get("location")
            if loc and hops < self.max_redirects:
                target = urljoin(url, loc)
                self.seen.discard(normalize(target))
                self._enqueue(target, hops + 1, front=True)
            else:
                self.stats["skipped (too many redirects)"] += 1
        elif r.status in (429, 503):
            ra = retry_after_seconds(r.headers.get("retry-after", ""))
            h.delay = min(3600.0, max(h.delay * 2, ra or 0.0))
            h.next_ok = self.clock() + h.delay
            h.failures += 1
            self.stats[f"HTTP {r.status} (backed off)"] += 1
            if h.failures >= 3:
                h.stopped = f"HTTP {r.status} three times"
            elif attempts < 2:
                self._enqueue(url, hops, front=True, attempts=attempts + 1)
        elif r.status >= 500:
            self._fail(origin, h, f"HTTP {r.status}")
            return
        elif r.status != 200:
            self.stats[f"HTTP {r.status}"] += 1
        else:
            h.failures = 0
            self._handle_ok(url, r)
        self._schedule(origin)

    def _fail(self, origin: str, h: _Host, why: str) -> None:
        h.failures += 1
        h.delay = min(3600.0, h.delay * 2)
        h.next_ok = self.clock() + h.delay
        self.stats[f"error: {why}"] += 1
        if h.failures >= 3:
            h.stopped = f"{why} three times"
        self._schedule(origin)

    def _handle_ok(self, url: str, r: Response) -> None:
        ctype = r.headers.get("content-type", "").lower()
        if "html" not in ctype:
            self.stats["skipped (not HTML)"] += 1
            return
        ex = extract_html(r.body.decode(charset_of(ctype), errors="replace"), url, AGENT_TOKEN)
        xrt = r.headers.get("x-robots-tag", "").lower()
        noindex = ex.noindex or "noindex" in xrt or "none" in xrt
        nofollow = ex.nofollow or "nofollow" in xrt or "none" in xrt
        if noindex:
            self.stats["skipped (noindex)"] += 1
        else:
            lang, reason = html_language(ex.lang)
            status, _ = self.index.add(Doc(url=url, title=ex.title, body=ex.text, lang=lang, lang_reason=reason,
                                           origin="crawl", licence=LICENCE,
                                           fetched=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                           truncated=r.truncated))
            if status in ("added", "replaced"):
                self.stats["pages indexed"] += 1
                self.per_domain[registered_domain(url)] += 1
                self.log(f"indexed {url}")
        if not nofollow:
            for link in ex.links:
                self._enqueue(link)
