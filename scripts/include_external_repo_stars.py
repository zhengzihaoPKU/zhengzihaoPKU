#!/usr/bin/env python3
"""Add an external repository's live stars to a generated GitHub stats card."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


VISIBLE_STARS_PATTERN = re.compile(
    r'(?P<open><text\b[^>]*data-testid=["\']stars["\'][^>]*>\s*)'
    r'(?P<count>[\d,]+)'
    r'(?P<close>\s*</text>)',
    re.DOTALL,
)
DESCRIPTION_STARS_PATTERN = re.compile(r"Total Stars Earned: (?P<count>[\d,]+)")


def marker_pattern(repo: str) -> re.Pattern[str]:
    escaped_repo = re.escape(html.escape(repo, quote=False))
    return re.compile(rf"<!-- external-stars: {escaped_repo}=(?P<count>\d+) -->")


def fetch_repo_stars(repo: str, token: str | None) -> int:
    """Fetch the current stargazer count for owner/repository from GitHub."""
    encoded_repo = quote(repo, safe="/")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "zhengzihaoPKU-profile-card-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"https://api.github.com/repos/{encoded_repo}", headers=headers)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    stars = payload.get("stargazers_count")
    if not isinstance(stars, int):
        raise ValueError(f"GitHub returned no numeric stargazer count for {repo}")
    return stars


def parse_count(value: str) -> int:
    return int(value.replace(",", ""))


def update_card(path: Path, repo: str, repo_stars: int) -> int:
    """Update visible and accessible totals, returning the new total."""
    source = path.read_text(encoding="utf-8")
    visible_match = VISIBLE_STARS_PATTERN.search(source)
    description_match = DESCRIPTION_STARS_PATTERN.search(source)
    if not visible_match or not description_match:
        raise ValueError(f"Could not find the Total Stars fields in {path}")

    visible_total = parse_count(visible_match.group("count"))
    description_total = parse_count(description_match.group("count"))
    if visible_total != description_total:
        raise ValueError(f"Visible and accessible star totals disagree in {path}")

    repo_marker_pattern = marker_pattern(repo)
    existing_marker = repo_marker_pattern.search(source)
    previously_added_stars = int(existing_marker.group("count")) if existing_marker else 0
    updated_total = visible_total - previously_added_stars + repo_stars
    if updated_total < 0:
        raise ValueError(f"Computed a negative Total Stars value for {path}")

    updated = VISIBLE_STARS_PATTERN.sub(
        lambda match: (
            f'{match.group("open")}{updated_total}{match.group("close")}'
        ),
        source,
        count=1,
    )
    updated = DESCRIPTION_STARS_PATTERN.sub(
        f"Total Stars Earned: {updated_total}", updated, count=1
    )

    marker = f"<!-- external-stars: {html.escape(repo, quote=False)}={repo_stars} -->"
    if existing_marker:
        updated = repo_marker_pattern.sub(marker, updated, count=1)
    else:
        description_end = updated.find("</desc>")
        if description_end == -1:
            raise ValueError(f"Could not find the SVG description in {path}")
        insertion_point = description_end + len("</desc>")
        updated = f"{updated[:insertion_point]}\n        {marker}{updated[insertion_point:]}"

    path.write_text(updated, encoding="utf-8")
    return updated_total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="external repository as owner/name")
    parser.add_argument(
        "--stars",
        type=int,
        help="use a supplied star count instead of querying GitHub (useful for tests)",
    )
    parser.add_argument("card", type=Path)
    args = parser.parse_args()
    if args.stars is not None and args.stars < 0:
        parser.error("--stars cannot be negative")
    return args


def main() -> None:
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    repo_stars = args.stars
    if repo_stars is None:
        repo_stars = fetch_repo_stars(args.repo, token)

    total = update_card(args.card, args.repo, repo_stars)
    print(f"Total Stars: {total} (including {args.repo}: {repo_stars})")


if __name__ == "__main__":
    main()
