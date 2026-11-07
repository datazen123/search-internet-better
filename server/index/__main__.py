"""Command line for the own index.

  python3 -m server.index stats
  python3 -m server.index add FILE.warc.gz|FILE.wet.gz ... [--limit N] [--lang en,de] [--max-per-domain N]
  python3 -m server.index commoncrawl --crawl CC-MAIN-2026-39 [--files 1] [--per-file 5000] [--seed S]
  python3 -m server.index crawl --seeds seeds.txt [--max-pages 100] [--delay 5] [--max-per-domain 50] [--any-site]
  python3 -m server.index search "query"
  python3 -m server.index remove --url URL | --domain example.org      (takedown)
  python3 -m server.index optimize
The index file is data/index/local.sqlite unless LOCAL_INDEX_PATH is set. It is git-ignored.
"""
from __future__ import annotations
import argparse
import json
import sys
from . import index_path
from .store import Index


def _load_env():
    from ..app import _load_env as load
    load()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m server.index", description="Own long-tail search index")
    ap.add_argument("--index", help="index file (default: LOCAL_INDEX_PATH or data/index/local.sqlite)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    sub.add_parser("optimize")
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--limit", type=int, default=10)
    for name in ("add", "commoncrawl"):
        p = sub.add_parser(name)
        p.add_argument("--lang", default="", help="comma-separated language codes to keep, e.g. en,de,ja")
        p.add_argument("--max-per-domain", type=int, default=0, help="page budget per registered domain")
        if name == "add":
            p.add_argument("files", nargs="+")
            p.add_argument("--limit", type=int, default=0)
            p.add_argument("--licence", default="Common Crawl Terms of Use; content (c) site owners")
        else:
            p.add_argument("--crawl", required=True, help="crawl id, e.g. CC-MAIN-2026-39 (see commoncrawl.org)")
            p.add_argument("--files", type=int, default=1, help="number of WET files to sample (about 150 MB each)")
            p.add_argument("--per-file", type=int, default=0, help="max documents per file")
            p.add_argument("--seed", default="", help="sampling seed (default: the crawl id)")
    c = sub.add_parser("crawl")
    c.add_argument("--seeds", required=True, help="file with one URL per line")
    c.add_argument("--max-pages", type=int, default=100)
    c.add_argument("--delay", type=float, default=5.0, help="minimum seconds between requests to one host")
    c.add_argument("--max-per-domain", type=int, default=50)
    c.add_argument("--any-site", action="store_true", help="follow links beyond the seeds' domains")
    r = sub.add_parser("remove")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--url"); g.add_argument("--domain")
    a = ap.parse_args(argv)

    _load_env()
    idx = Index(a.index or index_path())
    progress = lambda c: print(f"  ... {dict(c)}", file=sys.stderr)
    if a.cmd == "stats":
        print(json.dumps(idx.stats(), indent=2, ensure_ascii=False))
    elif a.cmd == "optimize":
        idx.optimize(); print("optimized")
    elif a.cmd == "search":
        for i, h in enumerate(idx.search(a.query, a.limit), 1):
            print(f"{i:>3}. {h['title'][:80]}\n     {h['url']}  [bm25 {h['bm25']}, {h['lang'] or '?'}, {h['origin']}]")
    elif a.cmd in ("add", "commoncrawl"):
        from .ingest import Budget, ingest_files, ingest_common_crawl
        budget = Budget(a.max_per_domain, [l for l in a.lang.split(",") if l])
        if a.cmd == "add":
            res = ingest_files(idx, a.files, licence=a.licence, budget=budget, limit=a.limit, progress=progress)
        else:
            res = ingest_common_crawl(idx, a.crawl, a.files, a.seed, a.per_file, budget, progress)
        print(json.dumps(dict(res), indent=2))
    elif a.cmd == "crawl":
        from .crawler import Crawler, user_agent
        print(f"crawling as: {user_agent()}", file=sys.stderr)
        cr = Crawler(idx, min_delay=a.delay, max_pages=a.max_pages, max_per_domain=a.max_per_domain,
                     same_site=not a.any_site, log=lambda m: print(m, file=sys.stderr))
        with open(a.seeds) as f:
            cr.add_seeds(f)
        print(json.dumps(dict(cr.run()), indent=2))
    elif a.cmd == "remove":
        print(f"removed {idx.remove(url=a.url or '', domain_suffix=a.domain or '')} document(s)")
    idx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
