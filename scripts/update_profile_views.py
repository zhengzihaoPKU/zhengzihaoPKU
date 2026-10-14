#!/usr/bin/env python3
"""Refresh the local profile-view badge, preserving it when upstream fails."""

from __future__ import annotations

import argparse
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SVG_NS = "{http://www.w3.org/2000/svg}"
USER_AGENT = "zhengzihaoPKU-profile-views-snapshot/1.0"
MAX_RESPONSE_BYTES = 64 * 1024
COUNT_PATTERN = re.compile(r"PROFILE VIEWS: ([0-9]+|[1-9][0-9]{0,2}(?:,[0-9]{3})+)")


def parse_count(source: bytes) -> int:
    """Reject error badges (including HTTP 200 errors) and incomplete responses."""
    root = ET.fromstring(source)
    if root.tag != f"{SVG_NS}svg":
        raise ValueError("The counter response is not an SVG badge")
    label = root.get("aria-label", "")
    match = COUNT_PATTERN.fullmatch(label)
    if not match:
        raise ValueError("The counter badge does not contain an exact numeric count")
    digits = match.group(1).replace(",", "")
    if len(digits) > 20:
        raise ValueError("The counter value is unexpectedly large")
    title = root.find(f"{SVG_NS}title")
    texts = ["".join(node.itertext()).strip() for node in root.iter(f"{SVG_NS}text")]
    if title is None or title.text != label or match.group(1) not in texts:
        raise ValueError("Visible and accessible counter values do not agree")
    return int(digits)


def fetch_count(username: str) -> int:
    # Only github-camo requests increment the counter in the upstream source:
    # https://github.com/antonkomarev/github-profile-views-counter/blob/master/public/index.php
    # Request the origin directly and never impersonate GitHub's image proxy.
    # Omit `abbreviated`: PHP interprets even the string "false" as true.
    query = urlencode({"username": username, "label": "PROFILE VIEWS", "style": "for-the-badge"})
    request = Request(
        f"https://komarev.com/ghpvc/?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "image/svg+xml"},
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                if response.headers.get_content_type() != "image/svg+xml":
                    raise ValueError("The counter returned a non-SVG response")
                source = response.read(MAX_RESPONSE_BYTES + 1)
            if len(source) > MAX_RESPONSE_BYTES:
                raise ValueError("The counter response is too large")
            return parse_count(source)
        except (OSError, ValueError, ET.ParseError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("Counter request did not complete")


def render_badge(count: int) -> str:
    """Render trusted local markup; never publish markup supplied by the service."""
    value = f"{count:,}"
    label_width = 113
    value_width = max(45, 20 + len(value) * 8)
    width = label_width + value_width
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" role="img" aria-label="PROFILE VIEWS: {value}">
  <title>PROFILE VIEWS: {value}</title>
  <desc>Latest successfully recorded profile views. Refreshed hourly; updates may be delayed.</desc>
  <g shape-rendering="crispEdges">
    <rect width="{label_width}" height="28" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="28" fill="#8C0000"/>
  </g>
  <g fill="#fff" text-anchor="middle" text-rendering="geometricPrecision" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="10" letter-spacing="1.1">
    <text x="57" y="17.5">PROFILE VIEWS</text>
    <text x="{label_width + value_width / 2:g}" y="17.5" font-weight="bold">{value}</text>
  </g>
</svg>
'''


def update_badge(path: Path, username: str) -> int:
    count = fetch_count(username)
    if path.exists() and count < parse_count(path.read_bytes()):
        raise ValueError("The count decreased; preserving the last good badge")
    source = render_badge(count)
    if path.exists() and path.read_text(encoding="utf-8") == source:
        return count
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".svg.tmp")
    try:
        temporary.write_text(source, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="zhengzihaoPKU")
    parser.add_argument("--output", type=Path, default=Path("profile/profile-views.svg"))
    args = parser.parse_args()
    try:
        count = update_badge(args.output, args.username)
    except (OSError, ValueError, ET.ParseError) as error:
        parser.exit(1, f"Profile views refresh failed; existing badge preserved: {error}\n")
    print(f"Profile views: {count:,} ({args.output})")


if __name__ == "__main__":
    main()
