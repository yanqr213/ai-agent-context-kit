"""Data structures used by ai-agent-context-kit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class FileRecord:
    """A scanned file that is safe and selected for inclusion."""

    path: str
    absolute_path: Path
    size_bytes: int
    extension: str
    sha256: str
    char_count: int
    estimated_tokens: int
    text: str


@dataclass(frozen=True)
class ExcludedFile:
    """A file that was intentionally skipped."""

    path: str
    reason: str
    size_bytes: Optional[int] = None


@dataclass
class ScanResult:
    """Repository scan result before rendering output files."""

    root: Path
    included: List[FileRecord] = field(default_factory=list)
    excluded: List[ExcludedFile] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_chars: int = 0
    estimated_tokens: int = 0
    truncated_by_budget: bool = False


@dataclass(frozen=True)
class BuildResult:
    """Paths and summary produced by a build."""

    markdown_path: Path
    manifest_path: Path
    handoff_path: Optional[Path]
    included_count: int
    excluded_count: int
    estimated_tokens: int
    total_chars: int
    warnings: List[str]


Manifest = Dict[str, object]
