"""Utilities for normalizing model message content into clean text."""

from __future__ import annotations

import re
from typing import Any


def normalize_content_to_text(content: Any) -> str:
    """Convert Anthropic/LangChain content blocks into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
                continue
            text = getattr(item, "text", None) or getattr(item, "content", None)
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        if isinstance(text, str):
            return text
    text = getattr(content, "text", None) or getattr(content, "content", None)
    if isinstance(text, str):
        return text
    return str(content)


def truncate_text(text: str, limit: int = 1400) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


# ---------------------------------------------------------------------------
# Canonical symbol extractor — single implementation used by all agents (G-4)
# ---------------------------------------------------------------------------

# Common English words and financial acronyms that look like tickers but aren't.
_SYMBOL_STOP_WORDS: frozenset[str] = frozenset({
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "WAS",
    "ONE", "OUR", "OUT", "HAS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD",
    "GET", "GOT", "SHOW", "NEWS", "WHAT", "FROM", "WITH", "THIS", "THAT",
    "WILL", "HAVE", "BEEN", "THEY", "WERE", "SAID", "EACH", "WHICH",
    # Financial acronyms that are NOT tickers
    "SEC", "EPS", "PE", "DCF", "RSI", "MACD", "ETF", "USD", "CEO", "CFO",
    "IPO", "GDP", "CPI", "FED", "API", "AI", "ML",
    # Agent / query words
    "REDDIT", "WSBT", "WSB",
})


def extract_symbols(text: str, max_symbols: int = 5) -> list[str]:
    """Extract stock ticker symbols from free text.

    Precedence:
    1. Explicit ``$TICKER`` notation (highest confidence)
    2. Bare ALL-CAPS words of 1-5 characters not in the stop-word list

    Returns a deduplicated list preserving order of first appearance.
    """
    if not text:
        return []

    # $TICKER patterns first (highest confidence)
    dollar_tickers = re.findall(r"\$([A-Z]{1,5})\b", text)

    # Bare uppercase words
    bare_words = re.findall(r"\b([A-Z]{1,5})\b", text)
    filtered_bare = [w for w in bare_words if w not in _SYMBOL_STOP_WORDS]

    # Merge, deduplicate, preserve order
    seen: set[str] = set()
    result: list[str] = []
    for sym in dollar_tickers + filtered_bare:
        if sym not in seen:
            seen.add(sym)
            result.append(sym)
        if len(result) >= max_symbols:
            break

    return result

