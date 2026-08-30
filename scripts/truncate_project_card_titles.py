#!/usr/bin/env python3
"""Shorten generated project-card titles without changing repository names."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


HEADER_PATTERN = re.compile(
    r'(?P<open><text\b[^>]*data-testid=["\']header["\'][^>]*>\s*)'
    r'(?P<title>.*?)'
    r'(?P<close>\s*</text>)',
    re.DOTALL,
)
ELLIPSIS = "..."


def truncate_title(title: str, max_length: int) -> str:
    """Return a title no longer than max_length, including the ellipsis."""
    decoded_title = html.unescape(title.strip())
    if len(decoded_title) <= max_length:
        return decoded_title

    title_without_existing_ellipsis = decoded_title
    if title_without_existing_ellipsis.endswith(ELLIPSIS):
        title_without_existing_ellipsis = title_without_existing_ellipsis[: -len(ELLIPSIS)]

    prefix_length = max_length - len(ELLIPSIS)
    prefix = title_without_existing_ellipsis[:prefix_length].rstrip("-_. ")
    return f"{prefix}{ELLIPSIS}"


def update_card(path: Path, max_length: int) -> bool:
    """Apply the title rule to one generated SVG and report whether it changed."""
    source = path.read_text(encoding="utf-8")

    def replace_header(match: re.Match[str]) -> str:
        shortened_title = truncate_title(match.group("title"), max_length)
        escaped_title = html.escape(shortened_title, quote=False)
        return f'{match.group("open")}{escaped_title}{match.group("close")}'

    updated, replacements = HEADER_PATTERN.subn(replace_header, source, count=1)
    if replacements != 1:
        raise ValueError(f"Could not find exactly one project title in {path}")

    if updated == source:
        return False

    path.write_text(updated, encoding="utf-8")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-length",
        type=int,
        default=32,
        help="maximum title length, including the three-dot ellipsis",
    )
    parser.add_argument("cards", nargs="+", type=Path)
    args = parser.parse_args()
    if args.max_length <= len(ELLIPSIS):
        parser.error("--max-length must be greater than 3")
    return args


def main() -> None:
    args = parse_args()
    for card in args.cards:
        changed = update_card(card, args.max_length)
        status = "shortened" if changed else "unchanged"
        print(f"{card}: {status}")


if __name__ == "__main__":
    main()
