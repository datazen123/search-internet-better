"""Own search index: SQLite FTS5 with BM25 ranking (stdlib sqlite3; no extra dependencies).

Ranking: FTS5's built-in bm25() (k1 = 1.2, b = 0.75, fixed by SQLite), with our own column
weights: title x5, body x1. These are choices, recorded in every result's provenance.
Scripts: the unicode61 tokenizer splits on non-alphanumerics, which leaves Chinese/Japanese
text as one long token, so documents are also indexed with the trigram tokenizer (SQLite
>= 3.34) and queries containing CJK characters use that table.
Duplicates: exact URL duplicates are merged on the normalised URL; near-duplicates
(SimHash Hamming <= 3) are kept and labelled, never silently dropped.
Takedown: remove(url=...) or remove(domain=...) deletes documents and their postings.
Privacy: the index stores pages, never queries.
"""
from __future__ import annotations
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from ..urlnorm import normalize, domain, registered_domain
from .simhash import simhash, hamming, bands, to_signed, from_signed

MAX_BODY_CHARS = 20_000
TITLE_WEIGHT, BODY_WEIGHT = 5.0, 1.0
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯豈-﫿]")

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  id INTEGER PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,          -- normalised URL (merge key)
  url TEXT NOT NULL,
  host TEXT NOT NULL,
  reg_domain TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  lang TEXT NOT NULL DEFAULT '',
  lang_reason TEXT NOT NULL DEFAULT '',
  origin TEXT NOT NULL DEFAULT '',   -- e.g. commoncrawl:CC-MAIN-2026-39, crawl, warc:file
  licence TEXT NOT NULL DEFAULT '',
  fetched TEXT NOT NULL DEFAULT '',
  indexed TEXT NOT NULL DEFAULT '',
  truncated INTEGER NOT NULL DEFAULT 0,
  simhash INTEGER NOT NULL DEFAULT 0,
  dup_of INTEGER                     -- id of an earlier near-duplicate, if any
);
CREATE INDEX IF NOT EXISTS docs_reg ON docs(reg_domain);
CREATE TABLE IF NOT EXISTS simbands (band INTEGER NOT NULL, value INTEGER NOT NULL, doc INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS simbands_bv ON simbands(band, value);
CREATE INDEX IF NOT EXISTS simbands_doc ON simbands(doc);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(title, body, content='docs', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2');
"""
TRIGRAM = """CREATE VIRTUAL TABLE IF NOT EXISTS fts_tri USING fts5(title, body, content='docs',
  content_rowid='id', tokenize='trigram')"""


@dataclass
class Doc:
    url: str
    title: str
    body: str
    lang: str = ""
    lang_reason: str = ""
    origin: str = ""
    licence: str = ""
    fetched: str = ""
    truncated: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Index:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.executescript(SCHEMA)
        try:
            self.db.execute(TRIGRAM)
            self.trigram = True
        except sqlite3.OperationalError:
            self.trigram = False
        self.db.commit()

    def close(self):
        self.db.close()

    # writing ------------------------------------------------------------------
    def _fts_tables(self):
        return ("fts", "fts_tri") if self.trigram else ("fts",)

    def _delete_ids(self, ids: list[int]) -> None:
        for i in ids:
            row = self.db.execute("SELECT title, body FROM docs WHERE id=?", (i,)).fetchone()
            if row is None:
                continue
            for t in self._fts_tables():
                self.db.execute(f"INSERT INTO {t}({t}, rowid, title, body) VALUES('delete', ?, ?, ?)", (i, *row))
            self.db.execute("DELETE FROM simbands WHERE doc=?", (i,))
            self.db.execute("UPDATE docs SET dup_of=NULL WHERE dup_of=?", (i,))
            self.db.execute("DELETE FROM docs WHERE id=?", (i,))

    def add(self, d: Doc) -> tuple[str, int | None]:
        """Insert or replace one document. Returns (status, id); status is added | replaced | empty."""
        body = (d.body or "").strip()
        if not body and not d.title:
            return "empty", None
        truncated = d.truncated or len(body) > MAX_BODY_CHARS
        body = body[:MAX_BODY_CHARS]
        key = normalize(d.url)
        h = simhash(d.title + " " + body)
        with self.lock:
            old = self.db.execute("SELECT id FROM docs WHERE key=?", (key,)).fetchone()
            if old:
                self._delete_ids([old[0]])
            dup = self._near_duplicate(h, registered_domain(d.url))
            cur = self.db.execute(
                "INSERT INTO docs(key,url,host,reg_domain,title,body,lang,lang_reason,origin,licence,fetched,"
                "indexed,truncated,simhash,dup_of) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (key, d.url, domain(d.url), registered_domain(d.url), d.title, body, d.lang, d.lang_reason,
                 d.origin, d.licence, d.fetched, _now(), int(truncated), to_signed(h), dup))
            i = cur.lastrowid
            for t in self._fts_tables():
                self.db.execute(f"INSERT INTO {t}(rowid, title, body) VALUES(?,?,?)", (i, d.title, body))
            if h:
                self.db.executemany("INSERT INTO simbands(band,value,doc) VALUES(?,?,?)",
                                    [(b, v, i) for b, v in enumerate(bands(h))])
            return ("replaced" if old else "added"), i

    def _near_duplicate(self, h: int, reg: str) -> int | None:
        """Earliest document on ANOTHER registered domain within Hamming distance 3."""
        if not h:
            return None
        cands = set()
        for b, v in enumerate(bands(h)):
            cands.update(r[0] for r in self.db.execute("SELECT doc FROM simbands WHERE band=? AND value=?", (b, v)))
        best = None
        for c in sorted(cands):
            row = self.db.execute("SELECT simhash, reg_domain FROM docs WHERE id=?", (c,)).fetchone()
            if row and row[1] != reg and hamming(from_signed(row[0]), h) <= 3:
                best = c
                break
        return best

    def commit(self):
        with self.lock:
            self.db.commit()

    def remove(self, url: str = "", domain_suffix: str = "") -> int:
        """Takedown path: delete one URL or every document on a domain (and its subdomains)."""
        with self.lock:
            if url:
                ids = [r[0] for r in self.db.execute("SELECT id FROM docs WHERE key=?", (normalize(url),))]
            else:
                d = domain_suffix.lower().lstrip(".")
                ids = [r[0] for r in self.db.execute("SELECT id FROM docs WHERE host=? OR host LIKE ?", (d, "%." + d))]
            self._delete_ids(ids)
            self.db.commit()
            return len(ids)

    def optimize(self):
        with self.lock:
            for t in self._fts_tables():
                self.db.execute(f"INSERT INTO {t}({t}) VALUES('optimize')")
            self.db.commit()

    # reading ------------------------------------------------------------------
    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM docs").fetchone()[0]

    @staticmethod
    def _match_expr(query: str, trigram: bool) -> str:
        if trigram:
            terms = [t for t in re.findall(r"\w+", query) if len(t) >= 3]
            if not terms:  # trigram needs >= 3 characters; split short CJK runs into nothing
                terms = [query.strip()] if len(query.strip()) >= 3 else []
        else:
            terms = re.findall(r"\w+", query.lower())
        return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms)

    def search(self, query: str, limit: int = 50) -> list[dict]:
        use_tri = self.trigram and bool(_CJK.search(query))
        table = "fts_tri" if use_tri else "fts"
        expr = self._match_expr(query, use_tri)
        if not expr:
            return []
        sql = (f"SELECT d.id, d.url, d.title, snippet({table}, 1, '', '', '…', 32), d.lang, d.lang_reason, "
               f"d.origin, d.licence, d.fetched, d.truncated, bm25({table}, ?, ?) AS s, d.dup_of, "
               f"(SELECT url FROM docs x WHERE x.id = d.dup_of) "
               f"FROM {table} JOIN docs d ON d.id = {table}.rowid WHERE {table} MATCH ? ORDER BY s LIMIT ?")
        with self.lock:
            rows = self.db.execute(sql, (TITLE_WEIGHT, BODY_WEIGHT, expr, limit)).fetchall()
        return [{"id": r[0], "url": r[1], "title": r[2], "snippet": r[3], "lang": r[4], "lang_reason": r[5],
                 "origin": r[6], "licence": r[7], "fetched": r[8], "truncated": bool(r[9]),
                 "bm25": float(f"{-r[10]:.4g}"), "dup_of_url": r[12] if r[11] else "",
                 "tokenizer": "trigram" if use_tri else "unicode61"} for r in rows]

    def stats(self) -> dict:
        """Transparency stats in the spirit of Common Crawl's per-crawl statistics."""
        q = lambda sql: self.db.execute(sql).fetchall()
        n = self.count()
        top = q("SELECT reg_domain, COUNT(*) c FROM docs GROUP BY reg_domain ORDER BY c DESC LIMIT 10")
        top3 = sum(c for _, c in top[:3])
        return {
            "documents": n,
            "hosts": q("SELECT COUNT(DISTINCT host) FROM docs")[0][0],
            "registered_domains": q("SELECT COUNT(DISTINCT reg_domain) FROM docs")[0][0],
            "languages": {k or "unknown": c for k, c in q("SELECT lang, COUNT(*) c FROM docs GROUP BY lang ORDER BY c DESC")},
            "origins": {k: c for k, c in q("SELECT origin, COUNT(*) c FROM docs GROUP BY origin ORDER BY c DESC")},
            "top_domains": dict(top),
            "top3_domain_share": round(top3 / n, 3) if n else 0.0,
            "near_duplicate_share": round(q("SELECT COUNT(*) FROM docs WHERE dup_of IS NOT NULL")[0][0] / n, 3) if n else 0.0,
            "truncated_share": round(q("SELECT COUNT(*) FROM docs WHERE truncated=1")[0][0] / n, 3) if n else 0.0,
            "trigram_tokenizer": self.trigram,
        }
