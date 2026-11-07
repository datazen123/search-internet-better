"""Lenses: user-owned rule files that steer sources, weights, diversity and width.

A lens is JSON (see lenses/*.json). Domain rules use a subset of Brave Goggles syntax
so existing goggle files can be pasted in. Our multiplier semantics are our own:
  boost=N    -> score x (1 + 0.25 * N)
  downrank=N -> score / (1 + 0.25 * N)
  discard    -> remove result
Precedence follows Goggles: discard > boost > downrank.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

LENS_DIR = Path(__file__).resolve().parent.parent / "lenses"


@dataclass
class Rule:
    pattern: str = ""          # substring/glob of URL path ('*' wildcard), may be empty
    site: str = ""             # domain suffix, e.g. "example.org"
    action: str = "boost"      # boost | downrank | discard
    strength: int = 1
    generic_discard: bool = False  # bare "$discard": drop everything not matched by another rule

    def matches(self, url: str, host: str) -> bool:
        if self.site and not (host == self.site or host.endswith("." + self.site)):
            return False
        if self.pattern:
            rx = re.escape(self.pattern).replace(r"\*", ".*").replace(r"\^", r"[/?&=]")
            if not re.search(rx, url):
                return False
        return True


def parse_goggle(text: str) -> list[Rule]:
    rules: list[Rule] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("!"):
            continue
        pattern, _, opts = line.partition("$")
        rule = Rule(pattern=pattern.strip())
        has_action = False
        for opt in filter(None, (o.strip() for o in opts.split(","))):
            key, _, val = opt.partition("=")
            key = key.strip().lower()
            if key in ("boost", "downrank"):
                rule.action = key
                rule.strength = max(1, min(10, int(val or 1)))
                has_action = True
            elif key == "discard":
                rule.action = "discard"
                has_action = True
            elif key == "site":
                rule.site = val.strip().lower().lstrip(".")
        if not has_action:
            continue
        if rule.action == "discard" and not rule.pattern and not rule.site:
            rule.generic_discard = True
        rules.append(rule)
    return rules


@dataclass
class Lens:
    name: str = "Default"
    purpose: str = ""
    engines: list[str] = field(default_factory=lambda: ["sample"])
    extra_queries: list[str] = field(default_factory=list)
    type_weights: dict[str, float] = field(default_factory=dict)
    goggle: str = ""
    language_target: dict[str, float] = field(default_factory=dict)
    max_per_domain: int = 3
    width: str = "tail"            # core | margin | tail
    slice_by: str = "source_type"  # source_type | language | engine
    quality_floor: str = "label"   # label | hide
    rotation_seed: str = ""        # optional: rotate tail items into view (exposure fairness)

    @property
    def rules(self) -> list[Rule]:
        return parse_goggle(self.goggle)

    @classmethod
    def from_dict(cls, d: dict) -> "Lens":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def load_lens(name: str) -> Lens:
    safe = re.sub(r"[^a-z0-9_-]", "", name.lower())
    path = LENS_DIR / f"{safe}.json"
    if not path.exists():
        path = LENS_DIR / "default.json"
    return Lens.from_dict(json.loads(path.read_text()))


def list_lenses() -> list[dict]:
    out = []
    for p in sorted(LENS_DIR.glob("*.json")):
        d = json.loads(p.read_text())
        out.append({"id": p.stem, "name": d.get("name", p.stem), "purpose": d.get("purpose", "")})
    return out
