"""Core scanning and bundle rendering logic."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

from .budget import estimate_tokens
from .ignore import build_matcher
from .models import BuildResult, ExcludedFile, FileRecord, Manifest, ScanResult
from .safety import detect_secret_findings, is_binary_bytes, summarize_findings


DEFAULT_MAX_FILE_BYTES = 512 * 1024
DEFAULT_TOKEN_BUDGET = 120_000
DEFAULT_OUTPUT_DIR = ".aictx"


@dataclass(frozen=True)
class BuildOptions:
    """Options controlling repository scan and output generation."""

    root: Path
    output_dir: Path
    include_exts: Set[str] = field(default_factory=set)
    exclude_exts: Set[str] = field(default_factory=set)
    include_paths: List[str] = field(default_factory=list)
    exclude_paths: List[str] = field(default_factory=list)
    token_budget: int = DEFAULT_TOKEN_BUDGET
    char_budget: Optional[int] = None
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    fail_on_secret: bool = False
    include_secret_files: bool = False
    no_gitignore: bool = False
    profile: str = "generic"
    bundle_name: str = "context-bundle"
    write_handoff: bool = True


def normalize_ext(ext: str) -> str:
    """Normalize a CLI extension value to lowercase dot form."""

    ext = ext.strip().lower()
    if not ext:
        return ext
    return ext if ext.startswith(".") else "." + ext


def build_context_bundle(options: BuildOptions) -> BuildResult:
    """Scan a repository and write Markdown and JSON context artifacts."""

    scan = scan_repository(options)
    options.output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = options.output_dir / f"{options.bundle_name}.md"
    manifest_path = options.output_dir / f"{options.bundle_name}.manifest.json"
    handoff_path = options.output_dir / f"{options.bundle_name}.handoff.md" if options.write_handoff else None

    markdown = render_markdown_bundle(scan, options, manifest_path.name)
    handoff = render_handoff(scan, options, markdown_path.name, manifest_path.name) if handoff_path else ""
    manifest = render_manifest(scan, options, markdown_path.name, handoff_path.name if handoff_path else None)

    markdown_path.write_text(markdown, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if handoff_path:
        handoff_path.write_text(handoff, encoding="utf-8")

    if options.fail_on_secret and any("secret" in warning.lower() or "credential" in warning.lower() for warning in scan.warnings):
        raise RuntimeError("Potential secrets were detected. Outputs were written with secret-like files excluded.")

    return BuildResult(
        markdown_path=markdown_path,
        manifest_path=manifest_path,
        handoff_path=handoff_path,
        included_count=len(scan.included),
        excluded_count=len(scan.excluded),
        estimated_tokens=scan.estimated_tokens,
        total_chars=scan.total_chars,
        warnings=scan.warnings,
    )


def scan_repository(options: BuildOptions) -> ScanResult:
    """Scan repository files according to options."""

    root = options.root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository root does not exist or is not a directory: {root}")

    matcher = _load_ignore_matcher(root, options)
    result = ScanResult(root=root)
    selected: List[FileRecord] = []
    budget_tokens = max(0, options.token_budget)
    budget_chars = options.char_budget
    current_tokens = 0
    current_chars = 0

    for path in _iter_files(root, matcher, options):
        rel = _relative_posix(root, path)
        size = path.stat().st_size
        extension = path.suffix.lower()

        exclusion = _extension_exclusion(rel, extension, options)
        if exclusion:
            result.excluded.append(ExcludedFile(rel, exclusion, size))
            continue
        if size > options.max_file_bytes:
            result.excluded.append(ExcludedFile(rel, f"larger than max file size ({options.max_file_bytes} bytes)", size))
            result.warnings.append(f"Excluded large file: {rel} ({size} bytes)")
            continue

        raw = path.read_bytes()
        if is_binary_bytes(raw):
            result.excluded.append(ExcludedFile(rel, "binary file", size))
            result.warnings.append(f"Excluded binary file: {rel}")
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                result.excluded.append(ExcludedFile(rel, "not valid UTF-8 text", size))
                result.warnings.append(f"Excluded non-UTF-8 file: {rel}")
                continue

        secret_findings = detect_secret_findings(text)
        if secret_findings and not options.include_secret_files:
            summary = summarize_findings(secret_findings)
            result.excluded.append(ExcludedFile(rel, f"potential secret ({summary})", size))
            result.warnings.append(f"Excluded potential secret file: {rel} ({summary})")
            continue
        if secret_findings:
            summary = summarize_findings(secret_findings)
            result.warnings.append(f"Included file with potential secret warning: {rel} ({summary})")

        chars = len(text)
        tokens = estimate_tokens(text)
        if budget_chars is not None and current_chars + chars > budget_chars:
            result.excluded.append(ExcludedFile(rel, f"char budget exceeded ({budget_chars})", size))
            result.truncated_by_budget = True
            continue
        if current_tokens + tokens > budget_tokens:
            result.excluded.append(ExcludedFile(rel, f"token budget exceeded ({budget_tokens})", size))
            result.truncated_by_budget = True
            continue

        current_chars += chars
        current_tokens += tokens
        selected.append(
            FileRecord(
                path=rel,
                absolute_path=path,
                size_bytes=size,
                extension=extension,
                sha256=hashlib.sha256(raw).hexdigest(),
                char_count=chars,
                estimated_tokens=tokens,
                text=text,
            )
        )

    result.included = selected
    result.total_chars = current_chars
    result.estimated_tokens = current_tokens
    if result.truncated_by_budget:
        result.warnings.append("One or more files were excluded because the context budget was reached.")
    return result


def render_markdown_bundle(scan: ScanResult, options: BuildOptions, manifest_name: str) -> str:
    """Render a Markdown context bundle."""

    created_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# AI Agent Context Bundle",
        "",
        f"- Repository: `{scan.root.name}`",
        f"- Root: `{scan.root}`",
        f"- Created at: `{created_at}`",
        f"- Profile: `{options.profile}`",
        f"- Manifest: `{manifest_name}`",
        f"- Included files: `{len(scan.included)}`",
        f"- Excluded files: `{len(scan.excluded)}`",
        f"- Estimated tokens: `{scan.estimated_tokens}`",
        f"- Total characters: `{scan.total_chars}`",
        "",
        "## Agent Instructions",
        "",
        _profile_instructions(options.profile),
        "",
        "## File Index",
        "",
    ]
    if scan.included:
        lines.extend(
            f"| `{file.path}` | {file.size_bytes} | {file.char_count} | {file.estimated_tokens} | `{file.sha256[:12]}` |"
            for file in scan.included
        )
        lines.insert(lines.index("## File Index") + 2, "| Path | Bytes | Chars | Est. tokens | SHA-256 |")
        lines.insert(lines.index("## File Index") + 3, "| --- | ---: | ---: | ---: | --- |")
    else:
        lines.append("_No files were included._")

    if scan.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in scan.warnings)

    lines.extend(["", "## Included Files", ""])
    for file in scan.included:
        language = _language_for_extension(file.extension)
        lines.extend(
            [
                f"### `{file.path}`",
                "",
                f"- Bytes: `{file.size_bytes}`",
                f"- SHA-256: `{file.sha256}`",
                f"- Estimated tokens: `{file.estimated_tokens}`",
                "",
                f"```{language}",
                file.text.rstrip("\n"),
                "```",
                "",
            ]
        )

    if scan.excluded:
        lines.extend(["## Excluded Files", ""])
        for excluded in scan.excluded:
            size = "" if excluded.size_bytes is None else f" ({excluded.size_bytes} bytes)"
            lines.append(f"- `{excluded.path}`: {excluded.reason}{size}")
        lines.append("")

    return "\n".join(lines)


def render_handoff(scan: ScanResult, options: BuildOptions, markdown_name: str, manifest_name: str) -> str:
    """Render a compact continuation prompt for an AI coding agent."""

    top_files = sorted(scan.included, key=lambda item: item.estimated_tokens, reverse=True)[:12]
    warnings = scan.warnings[:10]
    excluded = scan.excluded[:12]
    lines = [
        "# AI Agent Context Handoff",
        "",
        f"- Repository: `{scan.root.name}`",
        f"- Root: `{scan.root}`",
        f"- Profile: `{options.profile}`",
        f"- Markdown bundle: `{markdown_name}`",
        f"- JSON manifest: `{manifest_name}`",
        f"- Included files: `{len(scan.included)}`",
        f"- Excluded files: `{len(scan.excluded)}`",
        f"- Estimated tokens: `{scan.estimated_tokens}` / `{options.token_budget}`",
        f"- Total characters: `{scan.total_chars}`",
        f"- Budget truncated: `{str(scan.truncated_by_budget).lower()}`",
        "",
        "## Recommended Start",
        "",
        "1. Read the Markdown bundle file first.",
        "2. Use the JSON manifest to audit included and excluded files before assuming repository behavior.",
        "3. Treat warnings and budget truncation as uncertainty that must be resolved with repository inspection.",
        "4. Ask for missing files instead of guessing when an excluded file is relevant to the task.",
        "",
        "## Largest Included Files",
        "",
    ]
    if top_files:
        for file in top_files:
            lines.append(f"- `{file.path}`: {file.estimated_tokens} est. tokens, {file.char_count} chars, sha `{file.sha256[:12]}`")
    else:
        lines.append("- None.")

    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None.")

    lines.extend(["", "## Notable Exclusions", ""])
    if excluded:
        for item in excluded:
            size = "" if item.size_bytes is None else f", {item.size_bytes} bytes"
            lines.append(f"- `{item.path}`: {item.reason}{size}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Copyable Agent Prompt",
            "",
            "```text",
            f"You are working in repository `{scan.root.name}` with a prebuilt AI context bundle.",
            f"Read `{markdown_name}` for the bundled source context and `{manifest_name}` for the audit trail.",
            f"Profile: {options.profile}. Estimated context size: {scan.estimated_tokens} tokens out of budget {options.token_budget}.",
            "Before editing, review warnings, notable exclusions, and budget truncation.",
            "Do not assume behavior from excluded files. Ask for or inspect missing files when they affect the task.",
            "When you finish, report which bundled files were relevant, which excluded files you had to inspect, and which validation commands you ran.",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_manifest(scan: ScanResult, options: BuildOptions, markdown_name: str, handoff_name: Optional[str] = None) -> Manifest:
    """Render a JSON-serializable manifest."""

    outputs = {
        "markdown": markdown_name,
    }
    if handoff_name:
        outputs["handoff"] = handoff_name
    return {
        "schema_version": "1.0",
        "tool": "ai-agent-context-kit",
        "profile": options.profile,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "name": scan.root.name,
            "root": str(scan.root),
        },
        "outputs": outputs,
        "budgets": {
            "token_budget": options.token_budget,
            "char_budget": options.char_budget,
            "max_file_bytes": options.max_file_bytes,
            "estimated_tokens": scan.estimated_tokens,
            "total_chars": scan.total_chars,
            "truncated_by_budget": scan.truncated_by_budget,
        },
        "filters": {
            "include_exts": sorted(options.include_exts),
            "exclude_exts": sorted(options.exclude_exts),
            "include_paths": options.include_paths,
            "exclude_paths": options.exclude_paths,
            "gitignore_enabled": not options.no_gitignore,
        },
        "included_files": [
            {
                "path": file.path,
                "bytes": file.size_bytes,
                "extension": file.extension,
                "sha256": file.sha256,
                "chars": file.char_count,
                "estimated_tokens": file.estimated_tokens,
            }
            for file in scan.included
        ],
        "excluded_files": [
            {
                "path": file.path,
                "reason": file.reason,
                "bytes": file.size_bytes,
            }
            for file in scan.excluded
        ],
        "warnings": scan.warnings,
    }


def _load_ignore_matcher(root: Path, options: BuildOptions):
    gitignore_text = ""
    if not options.no_gitignore:
        gitignore = root / ".gitignore"
        if gitignore.exists():
            gitignore_text = gitignore.read_text(encoding="utf-8", errors="replace")
    return build_matcher(gitignore_text, options.exclude_paths)


def _iter_files(root: Path, matcher, options: BuildOptions) -> Iterable[Path]:
    output_dir = options.output_dir.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_dir = _relative_posix(root, current) if current != root else ""

        kept_dirs = []
        for dirname in sorted(dirnames):
            child = current / dirname
            rel = f"{rel_dir}/{dirname}".strip("/")
            if child.resolve() == output_dir or _is_within(child.resolve(), output_dir):
                continue
            if matcher.is_ignored(rel, is_dir=True):
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            path = current / filename
            rel = f"{rel_dir}/{filename}".strip("/")
            if _is_within(path.resolve(), output_dir):
                continue
            if matcher.is_ignored(rel, is_dir=False):
                continue
            if options.include_paths and not _matches_any_path(rel, options.include_paths):
                continue
            yield path


def _extension_exclusion(rel: str, extension: str, options: BuildOptions) -> Optional[str]:
    if options.include_exts and extension not in options.include_exts:
        return "extension not included"
    if options.exclude_exts and extension in options.exclude_exts:
        return "extension excluded"
    if _matches_any_path(rel, options.exclude_paths):
        return "path excluded"
    return None


def _matches_any_path(rel: str, patterns: Sequence[str]) -> bool:
    from fnmatch import fnmatchcase

    rel = rel.replace("\\", "/")
    return any(fnmatchcase(rel, pattern.replace("\\", "/").strip("/")) for pattern in patterns)


def _relative_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _profile_instructions(profile: str) -> str:
    if profile == "codex":
        return (
            "Use this bundle as repository context for Codex. Treat the manifest as the audit trail, "
            "respect excluded-file warnings, and ask before assuming behavior from omitted files."
        )
    if profile in {"claude", "claude-code"}:
        return (
            "Use this bundle as project context for Claude Code. Prefer the file index for navigation, "
            "then inspect included file blocks before proposing edits."
        )
    return (
        "Use this bundle as compact repository context for an AI coding assistant. The JSON manifest "
        "records inclusion, exclusion, budget, and safety decisions."
    )


def _language_for_extension(extension: str) -> str:
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".json": "json",
        ".md": "markdown",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
        ".sh": "bash",
        ".ps1": "powershell",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
    }.get(extension, "")
