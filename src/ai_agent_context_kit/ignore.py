"""Small .gitignore-style matcher implemented with the Python standard library."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable, List


@dataclass(frozen=True)
class IgnorePattern:
    pattern: str
    negated: bool = False
    directory_only: bool = False
    anchored: bool = False


DEFAULT_IGNORES = [
    ".git/",
    ".hg/",
    ".svn/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".tox/",
    ".venv/",
    "venv/",
    "env/",
    "node_modules/",
    "dist/",
    "build/",
    "*.egg-info",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.7z",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.pdf",
]


def parse_ignore_line(line: str) -> IgnorePattern | None:
    """Parse one .gitignore-style line."""

    stripped = line.rstrip("\n")
    if not stripped or stripped.lstrip().startswith("#"):
        return None
    negated = stripped.startswith("!")
    if negated:
        stripped = stripped[1:]
    directory_only = stripped.endswith("/")
    if directory_only:
        stripped = stripped.rstrip("/")
    anchored = stripped.startswith("/")
    stripped = stripped.lstrip("/")
    if not stripped:
        return None
    return IgnorePattern(stripped, negated=negated, directory_only=directory_only, anchored=anchored)


def parse_ignore_patterns(lines: Iterable[str]) -> List[IgnorePattern]:
    """Parse multiple .gitignore lines."""

    patterns = []
    for line in lines:
        pattern = parse_ignore_line(line)
        if pattern is not None:
            patterns.append(pattern)
    return patterns


class IgnoreMatcher:
    """Evaluate default and repository ignore patterns."""

    def __init__(self, patterns: Iterable[IgnorePattern]):
        self.patterns = list(patterns)

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> "IgnoreMatcher":
        return cls(parse_ignore_patterns(lines))

    def is_ignored(self, rel_path: str, is_dir: bool = False) -> bool:
        """Return whether a relative POSIX path is ignored."""

        rel_path = rel_path.replace("\\", "/").strip("/")
        ignored = False
        for pattern in self.patterns:
            if pattern.directory_only and not is_dir and not _path_under_directory(rel_path, pattern.pattern):
                continue
            if _matches(pattern, rel_path, is_dir):
                ignored = not pattern.negated
        return ignored


def build_matcher(gitignore_text: str = "", extra_patterns: Iterable[str] = ()) -> IgnoreMatcher:
    """Build a matcher from defaults, .gitignore text, and CLI ignore patterns."""

    lines = list(DEFAULT_IGNORES)
    if gitignore_text:
        lines.extend(gitignore_text.splitlines())
    lines.extend(extra_patterns)
    return IgnoreMatcher.from_lines(lines)


def _path_under_directory(rel_path: str, directory_pattern: str) -> bool:
    directory_pattern = directory_pattern.strip("/")
    parts = rel_path.split("/")
    return (
        rel_path == directory_pattern
        or rel_path.startswith(directory_pattern + "/")
        or any(fnmatch.fnmatchcase(part, directory_pattern) for part in parts)
    )


def _matches(pattern: IgnorePattern, rel_path: str, is_dir: bool) -> bool:
    raw = pattern.pattern
    path = PurePosixPath(rel_path)
    if pattern.directory_only:
        return _path_under_directory(rel_path, raw)
    if pattern.anchored:
        return fnmatch.fnmatchcase(rel_path, raw) or fnmatch.fnmatchcase(rel_path, raw + "/*")
    if "/" in raw:
        return fnmatch.fnmatchcase(rel_path, raw) or fnmatch.fnmatchcase(rel_path, raw + "/*")
    if fnmatch.fnmatchcase(path.name, raw):
        return True
    parts = rel_path.split("/")
    return any(fnmatch.fnmatchcase(part, raw) for part in parts)
