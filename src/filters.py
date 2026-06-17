"""
Lot filtering logic — keyword matching and spec parsing.
All functions are pure (no I/O) to make unit testing easy.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import ActorConfig


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html or "")
    return s.get_text()


def keyword_match(lot_naam: str, keywords: list[str]) -> bool:
    """True if any keyword appears in lot_naam (case-insensitive substring)."""
    name_lower = lot_naam.lower()
    return any(kw.lower() in name_lower for kw in keywords)


# RAM: context-aware — prefer values near RAM keywords; avoid storage values.
# "16GB DDR4", "geheugen: 16GB", "16 GB RAM"
_RAM_CONTEXT_RE = re.compile(
    r"(\d+)\s*(?:gb|mb)\s*(?:ram|ddr\d*|geheugen|werkgeheugen|dimm)"
    r"|(?:ram|ddr\d*|geheugen|werkgeheugen|dimm)\W{0,10}(\d+)\s*(?:gb|mb)",
    re.IGNORECASE,
)
# Storage context — GB values to exclude when no RAM context found
_STORAGE_CONTEXT_RE = re.compile(
    r"(\d+)\s*(?:gb|mb)\s*(?:ssd|hdd|nvme|m\.2|harddisk|opslag|schijf|flash|emmc)"
    r"|(?:ssd|hdd|nvme|m\.2|harddisk|opslag|schijf|flash|emmc)\W{0,10}(\d+)\s*(?:gb|mb)",
    re.IGNORECASE,
)
_ALL_GB_RE = re.compile(r"(\d+)\s*gb", re.IGNORECASE)
_ALL_MB_RE = re.compile(r"(\d+)\s*mb", re.IGNORECASE)

# SSD keywords
_SSD_POSITIVE = re.compile(r"\b(ssd|nvme|m\.2)\b", re.IGNORECASE)
_SSD_NEGATIVE = re.compile(r"\bhdd\b", re.IGNORECASE)

# Power adapter — Dutch words for "power adapter present"
_POWER_PRESENT = re.compile(
    r"\b(voeding|lader|adapter|oplader)\b"
    r".*?\b(erbij|aanwezig|inbegrepen|inclusief|meegeleverd|ja)\b"
    r"|\b(inclusief|inbegrepen|meegeleverd)\b"
    r".*?\b(voeding|lader|adapter|oplader)\b",
    re.IGNORECASE | re.DOTALL,
)


def _parse_ram_gb(text: str) -> int | None:
    """Return RAM in GB from plain text, preferring RAM-context values over storage values."""
    # 1. Try RAM-specific context matches first
    ram_hits: list[int] = []
    for m in _RAM_CONTEXT_RE.finditer(text):
        raw = m.group(1) or m.group(2)
        if raw:
            val = int(raw)
            # Determine unit from matched text
            matched = m.group(0).lower()
            if "mb" in matched:
                val = val // 1024
            ram_hits.append(val)
    if ram_hits:
        return max(ram_hits)

    # 2. Collect storage-context GB values to exclude
    storage_vals: set[int] = set()
    for m in _STORAGE_CONTEXT_RE.finditer(text):
        raw = m.group(1) or m.group(2)
        if raw:
            storage_vals.add(int(raw))

    # 3. Fall back: all GB values minus storage values
    all_gb = [int(v) for v in _ALL_GB_RE.findall(text) if int(v) not in storage_vals]
    if all_gb:
        return max(all_gb)

    all_mb = [int(v) for v in _ALL_MB_RE.findall(text)]
    if all_mb:
        return max(all_mb) // 1024

    return None


def spec_check(specs_html: str, config: "ActorConfig") -> dict:
    """
    Strip HTML, run all five spec filters against the plain text.

    Returns a dict with boolean values per filter:
        cpu, ram, ssd, power, bid_ok
    and extra info:
        ram_found_gb, bid_current
    """
    text = strip_html(specs_html)
    text_lower = text.lower()

    # CPU — any processor_keywords entry found
    cpu_ok = any(kw.lower() in text_lower for kw in config.processor_keywords)

    # RAM
    ram_gb = _parse_ram_gb(text)
    ram_ok = (ram_gb is not None) and (ram_gb >= config.ram_min_gb)

    # SSD
    has_ssd = bool(_SSD_POSITIVE.search(text))
    has_hdd = bool(_SSD_NEGATIVE.search(text))
    if has_ssd:
        ssd_ok = True
    elif has_hdd and not has_ssd:
        ssd_ok = False
    else:
        # Neither mentioned
        ssd_ok = not config.require_ssd

    # Power adapter
    has_power = bool(_POWER_PRESENT.search(text))
    if has_power:
        power_ok = True
    else:
        power_ok = not config.exclude_if_spec_unconfirmed

    return {
        "cpu": cpu_ok,
        "ram": ram_ok,
        "ram_found_gb": ram_gb,
        "ssd": ssd_ok,
        "power": power_ok,
    }


def all_specs_pass(spec_result: dict) -> bool:
    return all(spec_result[k] for k in ("cpu", "ram", "ssd", "power"))
