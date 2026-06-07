"""Safety checks for binary files, large files, and likely secrets."""

from __future__ import annotations

import math
import re
from typing import Iterable, List


SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|private[_-]?key)\b\s*[:=]\s*['\"]?[A-Za-z0-9_+/=-]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
]


def is_binary_bytes(data: bytes) -> bool:
    """Return True when bytes look binary rather than text."""

    if b"\x00" in data:
        return True
    if not data:
        return False
    sample = data[:4096]
    try:
        sample.decode("utf-8")
        return False
    except UnicodeDecodeError:
        pass
    text_bytes = bytearray({7, 8, 9, 10, 12, 13, 27})
    text_bytes.extend(range(32, 127))
    non_text = sum(1 for byte in sample if byte not in text_bytes)
    return non_text / len(sample) > 0.30


def shannon_entropy(value: str) -> float:
    """Compute Shannon entropy for a candidate secret-like value."""

    if not value:
        return 0.0
    frequencies = {char: value.count(char) for char in set(value)}
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in frequencies.values())


def detect_secret_findings(text: str) -> List[str]:
    """Find likely secrets without returning the secret values themselves."""

    findings: List[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append("matched secret-like pattern")
            break

    for match in re.finditer(r"(?i)\b[A-Z0-9_]*(?:TOKEN|SECRET|KEY|PASSWORD)[A-Z0-9_]*\b\s*[:=]\s*['\"]?([A-Za-z0-9_+/=-]{16,})", text):
        candidate = match.group(1)
        if shannon_entropy(candidate) >= 3.5:
            findings.append("high-entropy credential-like value")
            break
    return findings


def has_secret(text: str) -> bool:
    """Return True when text likely contains sensitive credentials."""

    return bool(detect_secret_findings(text))


def summarize_findings(findings: Iterable[str]) -> str:
    """Return a stable comma-separated finding summary."""

    unique = sorted(set(findings))
    return ", ".join(unique)
