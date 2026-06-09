"""Command-line interface for ai-agent-context-kit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

from . import __version__
from .core import DEFAULT_MAX_FILE_BYTES, DEFAULT_OUTPUT_DIR, DEFAULT_TOKEN_BUDGET, BuildOptions, build_context_bundle, normalize_ext


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    include_exts = {normalize_ext(value) for value in _split_csv(args.include_ext)}
    exclude_exts = {normalize_ext(value) for value in _split_csv(args.exclude_ext)}
    output_dir = Path(args.output_dir)
    root = Path(args.root)
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    options = BuildOptions(
        root=root,
        output_dir=output_dir,
        include_exts={ext for ext in include_exts if ext},
        exclude_exts={ext for ext in exclude_exts if ext},
        include_paths=args.include_path,
        exclude_paths=args.exclude_path,
        token_budget=args.token_budget,
        char_budget=args.char_budget,
        max_file_bytes=args.max_file_bytes,
        fail_on_secret=args.fail_on_secret,
        include_secret_files=args.include_secret_files,
        no_gitignore=args.no_gitignore,
        profile=args.profile,
        bundle_name=args.name,
        write_handoff=not args.no_handoff,
    )

    try:
        result = build_context_bundle(options)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Markdown bundle: {result.markdown_path}")
    print(f"JSON manifest: {result.manifest_path}")
    if result.handoff_path:
        print(f"Agent handoff: {result.handoff_path}")
    print(f"Included files: {result.included_count}")
    print(f"Excluded files: {result.excluded_count}")
    print(f"Estimated tokens: {result.estimated_tokens}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aictx",
        description="Build auditable prompt/context bundles for AI coding agents.",
    )
    parser.add_argument("root", nargs="?", default=".", help="Repository root to scan.")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for generated outputs.")
    parser.add_argument("--name", default="context-bundle", help="Output file basename without extension.")
    parser.add_argument(
        "--profile",
        choices=["generic", "codex", "claude", "claude-code"],
        default="generic",
        help="Agent-oriented instruction profile.",
    )
    parser.add_argument("--include-ext", action="append", default=[], help="Include only extensions, e.g. py,md,json. Repeatable or comma-separated.")
    parser.add_argument("--exclude-ext", action="append", default=[], help="Exclude extensions. Repeatable or comma-separated.")
    parser.add_argument("--include-path", action="append", default=[], help="Include only matching path glob. Repeatable.")
    parser.add_argument("--exclude-path", action="append", default=[], help="Extra ignore/path glob. Repeatable.")
    parser.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET, help="Approximate token budget.")
    parser.add_argument("--char-budget", type=int, default=None, help="Optional character budget.")
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES, help="Exclude files larger than this many bytes.")
    parser.add_argument("--no-gitignore", action="store_true", help="Ignore default .gitignore file.")
    parser.add_argument("--include-secret-files", action="store_true", help="Include files with potential secret findings, with warnings.")
    parser.add_argument("--fail-on-secret", action="store_true", help="Exit non-zero if potential secrets are detected.")
    parser.add_argument("--no-handoff", action="store_true", help="Do not write the agent handoff Markdown file.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _split_csv(values: Iterable[str]) -> List[str]:
    parts: List[str] = []
    for value in values:
        parts.extend(part.strip() for part in value.split(","))
    return [part for part in parts if part]


if __name__ == "__main__":
    raise SystemExit(main())
