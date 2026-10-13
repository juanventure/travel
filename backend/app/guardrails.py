"""
Deterministic guardrails for host-agency compliance and commission protection.

Prompts alone can't be trusted to keep the chatbot from (a) sending guests to
third-party pages where they can book without us — which earns the advisor no
commission and breaks the "everything is tied to Fora's IATA#" condition — or
(b) sharing fares. These helpers enforce both IN CODE:

  * strip_links()   — removes any URL / bare domain not on the allowlist. Applied
                      to search snippets (so the model never sees booking links)
                      AND to every outbound chat message (so a link the model
                      produces from memory never reaches the guest).
  * scrub_prices()  — removes dollar amounts from third-party text before the
                      model sees it.

Own-site links stay allowed. When Partner Booking Links (Fora-IATA-attributed)
are added, put their host in OUTBOUND_LINK_ALLOWLIST.
"""
import os
import re
from urllib.parse import urlparse

# Hosts a guest may be sent to. Comma-separated; subdomains are allowed too.
ALLOWED_HOSTS = [
    h.strip().lower()
    for h in os.getenv("OUTBOUND_LINK_ALLOWLIST", "horizonvoyages.net,calendly.com").split(",")
    if h.strip()
]

# Full URLs (https://… or www.…), then bare domains like "royalcaribbean.com".
_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"')\]]+", re.IGNORECASE)
# The lookarounds keep email addresses intact (jane@gmail.com) and don't touch
# the inside of a URL that was already handled.
_BARE_RE = re.compile(
    r"(?<![@\w./-])(?:[a-z0-9-]+\.)+(?:com|net|org|co|io|travel|cruises?)\b(?![@\w-])",
    re.IGNORECASE,
)
_PRICE_RE = re.compile(
    r"(?:(?:US|USD)\s?)?\$\s?\d[\d,]*(?:\.\d{1,2})?(?:[kK]\b)?"
    r"(?:\s?(?:-|–|—|to)\s?\$?\d[\d,]*(?:\.\d{1,2})?)?"
    r"|\bUSD\s?\d[\d,]*(?:\.\d{1,2})?",
    re.IGNORECASE,
)


def _host_allowed(host: str) -> bool:
    host = (host or "").lower().removeprefix("www.")
    return any(host == a or host.endswith("." + a) for a in ALLOWED_HOSTS)


def _link_repl(match: re.Match) -> str:
    token = match.group(0)
    core = token.rstrip(".,;:!?")  # sentence punctuation isn't part of the link
    tail = token[len(core):]
    host = urlparse(core if "://" in core else "//" + core).hostname or ""
    return token if _host_allowed(host) else tail


def strip_links(text: str) -> str:
    """Remove every link/domain that isn't on the allowlist; tidy what's left."""
    if not text:
        return text
    lines = []
    for line in text.split("\n"):
        new = _BARE_RE.sub(_link_repl, _URL_RE.sub(_link_repl, line))
        if new != line:  # a link was removed — clean up dangling separators
            new = re.sub(r"[ \t]+([,.;:!?])", r"\1", new)
            new = re.sub(r"[ \t]{2,}", " ", new).rstrip(" \t-–—:|")
        lines.append(new)
    return "\n".join(lines)


def scrub_prices(text: str) -> str:
    """Replace dollar amounts with a neutral marker."""
    return _PRICE_RE.sub("(price omitted)", text) if text else text
