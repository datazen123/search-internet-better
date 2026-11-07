import unittest
from server.urlnorm import normalize, registered_domain
from server.lens import parse_goggle, Lens, load_lens
from server.metrics import gini, normalized_entropy
from server.pipeline import merge, add_signals, rerank, search
from server.adapters.base import RawResult


class UrlNorm(unittest.TestCase):
    def test_merges_common_variants(self):
        a = normalize("http://www.Example.org/a/?utm_source=x&b=2&a=1#frag")
        b = normalize("https://example.org/a?a=1&b=2")
        self.assertEqual(a, b)

    def test_registered_domain(self):
        self.assertEqual(registered_domain("https://news.bbc.co.uk/x"), "bbc.co.uk")
        self.assertEqual(registered_domain("https://a.b.example.org/x"), "example.org")


class Goggles(unittest.TestCase):
    def test_parse_rules(self):
        rules = parse_goggle("! comment\n$boost=3,site=a.org\n/best-$downrank=2\n$discard,site=spam.example\n")
        self.assertEqual([r.action for r in rules], ["boost", "downrank", "discard"])
        self.assertEqual(rules[0].strength, 3)
        self.assertTrue(rules[2].matches("https://x.spam.example/p", "x.spam.example"))
        self.assertFalse(rules[0].matches("https://b.org/", "b.org"))

    def test_generic_discard(self):
        rules = parse_goggle("$discard\n$boost=1,site=keep.org")
        self.assertTrue(rules[0].generic_discard)


class Metrics(unittest.TestCase):
    def test_gini_bounds(self):
        self.assertAlmostEqual(gini([1, 1, 1, 1]), 0.0)
        self.assertGreater(gini([0, 0, 0, 10]), 0.7)

    def test_entropy(self):
        self.assertAlmostEqual(normalized_entropy([5, 5]), 1.0)
        self.assertEqual(normalized_entropy([7]), 0.0)


def _raw(url, engine, rank, title="t", snippet="s"):
    return RawResult(url=url, title=title, snippet=snippet, engine=engine, rank=rank, query="q")


class Pipeline(unittest.TestCase):
    def test_merge_tracks_engines(self):
        items = merge([_raw("https://a.org/x", "e1", 1), _raw("http://www.a.org/x/", "e2", 4)])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["engines"], {"e1": 1, "e2": 4})

    def test_rules_change_order_and_discard(self):
        items = merge([_raw("https://a.org/1", "e1", 1, "alpha one"), _raw("https://b.org/1", "e1", 2, "beta two"),
                       _raw("https://spam.example/1", "e1", 3, "gamma three")])
        add_signals(items, ["e1"])
        lens = Lens(goggle="$boost=10,site=b.org\n$discard,site=spam.example")
        ranked = rerank(items, lens)
        self.assertEqual(ranked[0]["domain"], "b.org")
        self.assertNotIn("spam.example", [m["domain"] for m in ranked])

    def test_domain_cap_demotes_not_deletes(self):
        raws = [_raw(f"https://big.org/{i}", "e1", i + 1, f"title {i} unique{i}") for i in range(5)] + [_raw("https://small.org/1", "e1", 6, "other words here")]
        items = merge(raws)
        add_signals(items, ["e1"])
        ranked = rerank(items, Lens(max_per_domain=2))
        self.assertEqual(len(ranked), 6)
        self.assertLess(ranked.index(next(m for m in ranked if m["domain"] == "small.org")), 5)

    def test_end_to_end_sample(self):
        r = search("microplastics health effects", load_lens("default"))
        self.assertTrue(r["synthetic_sample"])
        self.assertEqual({m["zone"] for m in r["results"]}, {"core", "margin", "tail"})
        self.assertIn("domain_diversity", r["health"])
        self.assertTrue(all(m["why"] for m in r["results"]))
        self.assertTrue(any(m["noise_flags"] for m in r["results"]))


if __name__ == "__main__":
    unittest.main()
