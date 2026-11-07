"""Minimal WARC / WET record reader (ISO 28500; Common Crawl WARC and WET files).

Reads plain or gzip files (Common Crawl uses one gzip member per record; gzip.open reads
multi-member files transparently). Yields WarcRecord(headers, body) streaming, so large
files are not loaded into memory.
"""
from __future__ import annotations
import gzip
import io
from dataclasses import dataclass
from typing import BinaryIO, Iterator


@dataclass
class WarcRecord:
    headers: dict[str, str]   # header names lower-cased
    body: bytes

    @property
    def type(self) -> str:
        return self.headers.get("warc-type", "")

    @property
    def target_uri(self) -> str:
        return self.headers.get("warc-target-uri", "").strip("<>")


def open_maybe_gzip(path: str) -> BinaryIO:
    f = open(path, "rb")
    magic = f.read(2)
    f.seek(0)
    return gzip.GzipFile(fileobj=f) if magic == b"\x1f\x8b" else f


def iter_records(stream: BinaryIO) -> Iterator[WarcRecord]:
    while True:
        line = stream.readline()
        if not line:
            return
        if not line.strip():
            continue  # blank lines between records
        if not line.startswith(b"WARC/"):
            raise ValueError(f"not a WARC record header: {line[:40]!r}")
        headers: dict[str, str] = {}
        while True:
            h = stream.readline()
            if not h or not h.strip():
                break
            k, _, v = h.decode("utf-8", errors="replace").partition(":")
            headers[k.strip().lower()] = v.strip()
        n = int(headers.get("content-length", "0"))
        body = stream.read(n)
        yield WarcRecord(headers, body)


def split_http_response(body: bytes) -> tuple[int, dict[str, str], bytes]:
    """Split a WARC 'response' record body into (status, headers, payload)."""
    head, _, payload = body.partition(b"\r\n\r\n")
    if not _:
        head, _, payload = body.partition(b"\n\n")
    lines = head.decode("iso-8859-1").splitlines()
    status = 0
    if lines and lines[0].startswith("HTTP/"):
        parts = lines[0].split()
        status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    hdrs = {}
    for ln in lines[1:]:
        k, _, v = ln.partition(":")
        hdrs[k.strip().lower()] = v.strip()
    return status, hdrs, payload


def charset_of(content_type: str, default: str = "utf-8") -> str:
    for part in content_type.split(";"):
        k, _, v = part.strip().partition("=")
        if k.lower() == "charset" and v:
            enc = v.strip("\"' ").lower()
            try:
                io.TextIOWrapper(io.BytesIO(b""), encoding=enc)
                return enc
            except LookupError:
                return default
    return default
