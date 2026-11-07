"""URL normalisation used to merge the same page returned by different engines."""
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref_src", "igshid")


def normalize(url: str) -> str:
    """Return a canonical-ish key for a URL.

    Lower-cases scheme and host, drops a leading "www.", default ports, fragments,
    tracking parameters and a trailing slash. Query parameter order is sorted.
    This is a merge key, not a claim about the site's real canonical URL.
    """
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    if scheme == "http":
        scheme = "https"  # treat http/https copies as the same page for merging
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parts.port
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith(TRACKING_PREFIXES)]
    query.sort()
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def registered_domain(url: str) -> str:
    """Approximate registered domain (last two labels; three for common 2nd-level ccTLDs).

    A real public-suffix list would be better; see BACKLOG.md.
    """
    host = domain(url)
    labels = host.split(".")
    second_level = {"co", "ac", "go", "or", "ne", "gov", "edu", "com", "org", "net"}
    if len(labels) >= 3 and labels[-2] in second_level and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])
