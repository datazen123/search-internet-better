"""HTML -> title, text, language attribute, links and robots directives (stdlib html.parser).

Deliberately simple and transparent: drops script/style/nav/footer/aside/form content,
keeps headings and paragraphs. Honours <meta name="robots"> (and the crawler's product
token) for noindex / nofollow, and rel="nofollow" on links.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag

SKIP = {"script", "style", "noscript", "template", "svg", "nav", "footer", "aside", "form", "iframe", "select"}
BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "blockquote", "pre"}
VOID = {"br", "img", "meta", "link", "input", "hr", "area", "base", "col", "embed", "source", "track", "wbr"}


@dataclass
class Extracted:
    title: str = ""
    text: str = ""
    description: str = ""
    lang: str = ""
    canonical: str = ""
    links: list[str] = field(default_factory=list)
    noindex: bool = False
    nofollow: bool = False


class _Parser(HTMLParser):
    def __init__(self, base_url: str, agent_token: str):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.agent = agent_token.lower()
        self.out = Extracted()
        self._skip = 0
        self._in_title = False
        self._title: list[str] = []
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "base" and a.get("href"):
            self.base = urljoin(self.base, a["href"])
        if tag == "html" and a.get("lang"):
            self.out.lang = a["lang"].strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = a.get("name", "").lower()
            if name == "description":
                self.out.description = a.get("content", "").strip()
            elif name in ("robots", self.agent):
                c = a.get("content", "").lower()
                self.out.noindex |= "noindex" in c or "none" in c
                self.out.nofollow |= "nofollow" in c or "none" in c
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split() and a.get("href"):
            self.out.canonical = urljoin(self.base, a["href"])
        elif tag == "a" and a.get("href") and "nofollow" not in a.get("rel", "").lower().split():
            href = urldefrag(urljoin(self.base, a["href"].strip()))[0]
            if href.startswith(("http://", "https://")):
                self.out.links.append(href)
        if tag in SKIP and tag not in VOID:
            self._skip += 1
        if tag in BLOCK:
            self._text.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in SKIP and self._skip:
            self._skip -= 1
        if tag in BLOCK:
            self._text.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self._title.append(data)
        elif not self._skip:
            self._text.append(data)

    def result(self) -> Extracted:
        self.out.title = re.sub(r"\s+", " ", "".join(self._title)).strip()
        lines = (re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in "".join(self._text).split("\n"))
        self.out.text = "\n".join(ln for ln in lines if ln)
        return self.out


def extract_html(html: str, base_url: str, agent_token: str = "") -> Extracted:
    p = _Parser(base_url, agent_token)
    try:
        p.feed(html)
        p.close()
    except Exception:  # malformed markup: keep whatever was parsed
        pass
    return p.result()
