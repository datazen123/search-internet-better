"""64-bit SimHash for near-duplicate detection (Manku, Jain & Das Sarma, WWW 2007).

Near-duplicate when the Hamming distance is <= 3 (the paper's operating point for 64-bit
fingerprints). Features are overlapping 3-word shingles; hashing uses BLAKE2b (stdlib).
Banding: split the 64 bits into 4 bands of 16. If two fingerprints differ in at most 3 bits,
at least one band is identical (pigeonhole), so band equality finds every candidate.
"""
from __future__ import annotations
import hashlib
import re

BITS = 64
MAX_DISTANCE = 3
BANDS = 4
_MASK = (1 << BITS) - 1


def _features(text: str, k: int = 3) -> list[str]:
    words = re.findall(r"\w+", text.lower())
    if len(words) < k:
        return words
    return [" ".join(words[i:i + k]) for i in range(len(words) - k + 1)]


def simhash(text: str) -> int:
    v = [0] * BITS
    feats = _features(text)
    if not feats:
        return 0
    for f in feats:
        h = int.from_bytes(hashlib.blake2b(f.encode("utf-8"), digest_size=8).digest(), "big")
        for i in range(BITS):
            v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(BITS) if v[i] > 0)


def hamming(a: int, b: int) -> int:
    return bin((a ^ b) & _MASK).count("1")


def bands(h: int) -> list[int]:
    width = BITS // BANDS
    return [(h >> (i * width)) & ((1 << width) - 1) for i in range(BANDS)]


def to_signed(h: int) -> int:
    """SQLite integers are signed 64-bit."""
    return h - (1 << 64) if h >= 1 << 63 else h


def from_signed(h: int) -> int:
    return h + (1 << 64) if h < 0 else h
