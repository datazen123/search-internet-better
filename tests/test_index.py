import gzip
import io
import os
import tempfile
import unittest
from server.index.robots import Robots
from server.index.simhash import simhash, hamming
from server.index.extract import extract_html
from server.index.store import Index, Doc
from server.index.warc import iter_records
from server.index.ingest import docs_from_stream, ingest, Budget
from server.index.crawler import Crawler, Response, retry_after_seconds, AGENT_TOKEN


class RobotsRFC9309(unittest.TestCase):
    TXT = """
User-Agent: *
Disallow: *.gif$
Disallow: /example/
Allow: /publications/

User-Agent: foobot
Disallow:/
Allow:/example/page.html
Allow:/example/allowed.gif

User-Agent: barbot
User-Agent: bazbot
Disallow: /example/page.html

User-Agent: quxbot
"""

    def setUp(self):
        self.r = Robots.parse(self.TXT)

    def test_rfc_example_groups(self):  # the worked example in RFC 9309 s5.1
        self.assertTrue(self.r.allowed("/example/page.html", "FooBot"))
        self.assertTrue(self.r.allowed("/example/allowed.gif", "foobot"))
        self.assertFalse(self.r.allowed("/other", "foobot"))
        self.assertFalse(self.r.allowed("/example/page.html", "bazbot"))
        self.assertTrue(self.r.allowed("/other", "barbot"))
        self.assertTrue(self.r.allowed("/anything", "quxbot"))  # empty group: allow
        self.assertFalse(self.r.allowed("/x/y.gif", "unknownbot"))
        self.assertTrue(self.r.allowed("/x/y.gif?z", "unknownbot"))  # $ anchors the end
        self.assertFalse(self.r.allowed("/example/a", "unknownbot"))

    def test_longest_match_and_tie(self):
        r = Robots.parse("User-agent: *\nDisallow: /a\nAllow: /a/b\nAllow: /c\nDisallow: /c\n")
        self.assertTrue(r.allowed("/a/b/c", "x"))
        self.assertFalse(r.allowed("/a/x", "x"))
        self.assertTrue(r.allowed("/c", "x"))  # tie -> allow

    def test_percent_encoding_and_robots_txt(self):
        r = Robots.parse("User-agent: *\nDisallow: /a%7Eb\nDisallow: /\n")
        self.assertFalse(r.allowed("/a~b", "x"))
        self.assertTrue(r.allowed("/robots.txt", "x"))

    def test_status_codes(self):
        self.assertTrue(Robots.for_status(404).allowed("/x", "x"))
        self.assertFalse(Robots.for_status(503).allowed("/x", "x"))

    def test_merged_groups_and_crawl_delay(self):
        r = Robots.parse("User-agent: a\nDisallow: /p\nCrawl-delay: 2\n\nUser-agent: a\nDisallow: /q\n")
        self.assertFalse(r.allowed("/p", "a"))
        self.assertFalse(r.allowed("/q", "a"))
        self.assertEqual(r.crawl_delay("A"), 2.0)


class SimHashTests(unittest.TestCase):
    def test_near_and_far(self):
        base = "the quick brown fox jumps over the lazy dog " * 20 + "while the cat sleeps in the warm sun all day"
        near = base.replace("warm sun", "hot sun")
        far = "completely unrelated text about rivers mountains and the economics of trade in the region " * 5
        self.assertLessEqual(hamming(simhash(base), simhash(near)), 3)
        self.assertGreater(hamming(simhash(base), simhash(far)), 10)


class Extraction(unittest.TestCase):
    def test_extracts_and_honours_directives(self):
        html = """<html lang="de-AT"><head><title> Hallo  Welt </title><meta name="robots" content="nofollow">
        <script>var x=1</script></head><body><nav>menu</nav><h1>Kopf</h1><p>Text &amp; mehr</p>
        <a href="/a#x">a</a><a rel="nofollow" href="/b">b</a><a href="mailto:x@y">m</a></body></html>"""
        ex = extract_html(html, "https://site.example/dir/")
        self.assertEqual(ex.title, "Hallo Welt")
        self.assertEqual(ex.lang, "de-AT")
        self.assertIn("Text & mehr", ex.text)
        self.assertNotIn("menu", ex.text)
        self.assertNotIn("var x", ex.text)
        self.assertEqual(ex.links, ["https://site.example/a"])
        self.assertTrue(ex.nofollow)
        self.assertFalse(ex.noindex)


def _wet(records):
    out = b"WARC/1.0\r\nWARC-Type: warcinfo\r\nContent-Length: 4\r\n\r\ninfo\r\n\r\n"
    for url, lang, text in records:
        body = text.encode()
        out += (f"WARC/1.0\r\nWARC-Type: conversion\r\nWARC-Target-URI: {url}\r\nWARC-Date: 2026-09-20T00:00:00Z\r\n"
                f"WARC-Identified-Content-Language: {lang}\r\nContent-Length: {len(body)}\r\n\r\n").encode() + body + b"\r\n\r\n"
    return gzip.compress(out)


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.idx = Index(":memory:")

    def tearDown(self):
        self.idx.close()

    def test_wet_ingest_search_dup_and_takedown(self):
        long = "Tide pools hold anemones, crabs and small fish. " * 15
        data = _wet([("https://shore.example/tidepools", "eng", "Tide pools guide\n" + long),
                     ("https://copy.example/tidepools", "eng", "Tide pools guide\n" + long + " extra"),
                     ("https://jp.example/umi", "jpn", "潮だまりの生き物\n潮だまりにはイソギンチャクやカニがいます。"),
                     ("https://other.example/x", "deu", "Gezeitentümpel und Krebse")])
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:
            c = ingest(self.idx, docs_from_stream(f, origin="commoncrawl:TEST"), Budget(langs=["en", "ja"]))
        self.assertEqual(c["added"], 3)
        hits = self.idx.search("tide pools crabs")
        self.assertEqual({h["url"] for h in hits}, {"https://shore.example/tidepools", "https://copy.example/tidepools"})
        dup = next(h for h in hits if h["url"].startswith("https://copy"))
        self.assertEqual(dup["dup_of_url"], "https://shore.example/tidepools")
        self.assertEqual(dup["lang"], "en")
        if self.idx.trigram:
            jp = self.idx.search("イソギンチャク")
            self.assertEqual(jp[0]["url"], "https://jp.example/umi")
            self.assertEqual(jp[0]["tokenizer"], "trigram")
        self.assertEqual(self.idx.remove(domain_suffix="shore.example"), 1)
        self.assertEqual(self.idx.search("tide pools")[0]["dup_of_url"], "")
        st = self.idx.stats()
        self.assertEqual(st["documents"], 2)
        self.assertEqual(st["origins"], {"commoncrawl:TEST": 2})

    def test_replace_same_url(self):
        self.idx.add(Doc(url="http://www.a.example/p/", title="old", body="alpha words"))
        status, _ = self.idx.add(Doc(url="https://a.example/p", title="new", body="beta words"))
        self.assertEqual(status, "replaced")
        self.assertEqual(self.idx.count(), 1)
        self.assertFalse(self.idx.search("alpha"))
        self.assertEqual(self.idx.search("beta")[0]["title"], "new")

    def test_domain_budget(self):
        docs = [Doc(url=f"https://big.example/{i}", title=f"page {i}", body=f"words number{i}") for i in range(5)]
        c = ingest(self.idx, docs, Budget(max_per_domain=2))
        self.assertEqual(c["added"], 2)


class FakeWeb:
    def __init__(self, pages):
        self.pages = pages
        self.log = []

    def __call__(self, url):
        self.log.append((self.now(), url))
        status, headers, body = self.pages.get(url, (404, {}, b""))
        return Response(status, {k.lower(): v for k, v in headers.items()}, body, url)


class CrawlerTests(unittest.TestCase):
    def _crawler(self, pages, **kw):
        t = [0.0]
        web = FakeWeb(pages)
        web.now = lambda: t[0]
        def sleep(s):
            t[0] += s
        idx = Index(":memory:")
        self.addCleanup(idx.close)
        return Crawler(idx, fetch=web, clock=lambda: t[0], sleep=sleep, **kw), web, idx

    def test_polite_crawl(self):
        H = {"Content-Type": "text/html; charset=utf-8"}
        pages = {
            "https://s.example/robots.txt": (200, {}, b"User-agent: *\nDisallow: /private\nCrawl-delay: 7\n"),
            "https://s.example/": (200, H, b'<html lang="en"><title>Home</title><p>welcome home page</p>'
                                         b'<a href="/a">a</a><a href="/private/x">p</a><a href="https://elsewhere.example/">e</a>'
                                         b'<a href="/old">o</a></html>'),
            "https://s.example/a": (200, H, b'<title>A</title><meta name="robots" content="noindex"><p>secret a</p><a href="/b">b</a>'),
            "https://s.example/b": (200, H, b"<title>B</title><p>bee page text</p>"),
            "https://s.example/old": (301, {"Location": "/b2"}, b""),
            "https://s.example/b2": (200, H, b"<title>B2</title><p>moved page text</p>"),
        }
        cr, web, idx = self._crawler(pages, min_delay=5)
        cr.add_seeds(["https://s.example/"])
        stats = cr.run()
        urls = [u for _, u in web.log]
        self.assertEqual(urls[0], "https://s.example/robots.txt")
        self.assertNotIn("https://s.example/private/x", urls)
        self.assertNotIn("https://elsewhere.example/", urls)
        times = [t for t, _ in web.log]
        self.assertTrue(all(b - a >= 7 for a, b in zip(times, times[1:])), times)  # crawl-delay honoured
        self.assertEqual({h["url"] for h in idx.search("page text home")},
                         {"https://s.example/", "https://s.example/b", "https://s.example/b2"})
        self.assertEqual(stats["skipped (noindex)"], 1)
        self.assertEqual(stats["blocked by robots.txt"], 1)

    def test_robots_5xx_stops_host(self):
        cr, web, _ = self._crawler({"https://down.example/robots.txt": (503, {}, b"")})
        cr.add_seeds(["https://down.example/"])
        cr.run()
        self.assertEqual([u for _, u in web.log], ["https://down.example/robots.txt"])

    def test_retry_after(self):
        self.assertEqual(retry_after_seconds("120"), 120.0)
        self.assertIsNone(retry_after_seconds("soon"))
        self.assertEqual(AGENT_TOKEN, "SearchInternetBetterBot")


class LocalAdapterEndToEnd(unittest.TestCase):
    def test_pipeline_uses_own_index(self):
        from server.pipeline import search
        from server.lens import Lens
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "i.sqlite")
            idx = Index(path)
            for i in range(6):
                idx.add(Doc(url=f"https://site{i}.example/tides", title=f"Tide tables {i}",
                            body=f"tide tables and coastal walks number {i}", lang="en",
                            lang_reason="declared by the page (<html lang>)", origin="crawl", licence="test"))
            idx.commit(); idx.close()
            old = os.environ.get("LOCAL_INDEX_PATH")
            os.environ["LOCAL_INDEX_PATH"] = path
            try:
                r = search("tide tables", Lens(engines=["local"]))
            finally:
                if old is None:
                    del os.environ["LOCAL_INDEX_PATH"]
                else:
                    os.environ["LOCAL_INDEX_PATH"] = old
        self.assertFalse(r["synthetic_sample"])
        self.assertEqual(r["engines"], ["local"])
        self.assertEqual(len(r["results"]), 6)
        self.assertEqual(r["health"]["own_index_share"], 1.0)
        top = r["results"][0]
        self.assertTrue(any(w.startswith("own index: BM25") for w in top["why"]))
        self.assertEqual(top["language_reason"], "declared by the page (<html lang>)")
        self.assertEqual(top["provenance"]["origin"], "crawl")


if __name__ == "__main__":
    unittest.main()
