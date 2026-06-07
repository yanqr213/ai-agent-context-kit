"""Character and token budget helpers.

The token estimator intentionally uses a simple standard-library heuristic.
It is conservative enough for prompt sizing while staying provider-neutral.
"""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Estimate token count for mixed English/code/CJK text."""

    if not text:
        return 0
    ascii_chars = 0
    wide_chars = 0
    for char in text:
        if char.isspace():
            ascii_chars += 1
        elif ord(char) < 128:
            ascii_chars += 1
        else:
            wide_chars += 1
    return max(1, (ascii_chars + 3) // 4 + wide_chars)
