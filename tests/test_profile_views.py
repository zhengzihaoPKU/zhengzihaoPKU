"""Offline regression tests for preserving the profile-view badge on failure."""

from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
import xml.etree.ElementTree as ET
from email.message import Message
from pathlib import Path
from unittest.mock import call, patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "update_profile_views.py"
SPEC = importlib.util.spec_from_file_location("update_profile_views", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
counter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(counter)

# Independent upstream-shaped fixture, rather than output from render_badge().
GOOD_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" role="img"
    aria-label="PROFILE VIEWS: 1,234" width="179" height="28">
  <title>PROFILE VIEWS: 1,234</title>
  <g fill="#fff"><text x="55" y="17">PROFILE VIEWS</text>
    <text x="140" y="17">1,234</text></g>
</svg>'''
ERROR_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg"
    aria-label="PROFILE VIEWS: error">
  <title>PROFILE VIEWS: error</title><text>error</text>
</svg>'''


class Response(io.BytesIO):
    """Minimal context-manager HTTP response with real content-type parsing."""

    def __init__(self, body: bytes, content_type: str = "image/svg+xml") -> None:
        super().__init__(body)
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.status = 200


class ParseCountTests(unittest.TestCase):
    def test_accepts_formatted_and_unformatted_counts(self) -> None:
        self.assertEqual(counter.parse_count(GOOD_SVG), 1234)
        self.assertEqual(counter.parse_count(GOOD_SVG.replace(b"1,234", b"1234")), 1234)

    def test_accepts_zero(self) -> None:
        self.assertEqual(counter.parse_count(GOOD_SVG.replace(b"1,234", b"0")), 0)

    def test_rejects_error_html_and_inconsistent_svg(self) -> None:
        invalid_responses = {
            "upstream error badge": ERROR_SVG,
            "HTML error": b"<html><body>Service unavailable</body></html>",
            "truncated XML": GOOD_SVG[:-7],
            "missing SVG namespace": GOOD_SVG.replace(b' xmlns="http://www.w3.org/2000/svg"', b""),
            "mismatched title": GOOD_SVG.replace(b"<title>PROFILE VIEWS: 1,234</title>", b"<title>PROFILE VIEWS: 1,200</title>"),
            "mismatched visible value": GOOD_SVG.replace(b">1,234</text>", b">1,200</text>"),
            "missing title": GOOD_SVG.replace(b"<title>PROFILE VIEWS: 1,234</title>", b""),
            "abbreviated count": GOOD_SVG.replace(b"1,234", b"1.2k"),
            "malformed thousands separator": GOOD_SVG.replace(b"1,234", b"12,34"),
            "negative count": GOOD_SVG.replace(b"1,234", b"-1"),
            "excessive count": GOOD_SVG.replace(b"1,234", b"123456789012345678901"),
        }
        for reason, body in invalid_responses.items():
            with self.subTest(reason=reason):
                with self.assertRaises((ValueError, ET.ParseError)):
                    counter.parse_count(body)


class FetchCountTests(unittest.TestCase):
    def test_fetches_origin_without_incrementing_or_abbreviating(self) -> None:
        with patch.object(counter, "urlopen", return_value=Response(GOOD_SVG)) as request:
            self.assertEqual(counter.fetch_count("zhengzihaoPKU"), 1234)
        request.assert_called_once()
        args, kwargs = request.call_args
        sent_request = args[0]
        url = urlsplit(sent_request.full_url)
        self.assertEqual((url.scheme, url.netloc, url.path), ("https", "komarev.com", "/ghpvc/"))
        self.assertEqual(parse_qs(url.query), {
            "username": ["zhengzihaoPKU"],
            "label": ["PROFILE VIEWS"],
            "style": ["for-the-badge"],
        })
        user_agent = sent_request.get_header("User-agent")
        self.assertTrue(user_agent)
        self.assertNotIn("github-camo", user_agent.lower())
        self.assertEqual(sent_request.get_header("Accept"), "image/svg+xml")
        self.assertEqual(kwargs, {"timeout": 20})

    def test_retries_temporary_error_then_returns_success(self) -> None:
        with patch.object(counter, "urlopen", side_effect=[URLError("temporary outage"), Response(GOOD_SVG)]) as request:
            with patch.object(counter.time, "sleep") as sleep:
                self.assertEqual(counter.fetch_count("zhengzihaoPKU"), 1234)
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_stops_after_three_network_failures(self) -> None:
        with patch.object(counter, "urlopen", side_effect=URLError("offline")) as request:
            with patch.object(counter.time, "sleep") as sleep:
                with self.assertRaises(URLError):
                    counter.fetch_count("zhengzihaoPKU")
        self.assertEqual(request.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(2), call(4)])

    def test_rejects_wrong_mime_type_and_oversized_responses(self) -> None:
        for body, content_type in [
            (GOOD_SVG, "text/html"),
            (b" " * (counter.MAX_RESPONSE_BYTES + 1), "image/svg+xml"),
        ]:
            with self.subTest(content_type=content_type, size=len(body)):
                with patch.object(counter, "urlopen", side_effect=lambda *_args, **_kwargs: Response(body, content_type)):
                    with patch.object(counter.time, "sleep"):
                        with self.assertRaises(ValueError):
                            counter.fetch_count("zhengzihaoPKU")


class UpdateBadgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.path = Path(self.temporary_directory.name) / "profile" / "profile-views.svg"

    def write_existing_badge(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(GOOD_SVG)

    def test_success_refreshes_badge_with_formatted_count(self) -> None:
        self.write_existing_badge()
        with patch.object(counter, "fetch_count", return_value=12345):
            self.assertEqual(counter.update_badge(self.path, "zhengzihaoPKU"), 12345)
        root = ET.fromstring(self.path.read_bytes())
        self.assertEqual(root.get("aria-label"), "PROFILE VIEWS: 12,345")
        self.assertEqual(root.find(f"{counter.SVG_NS}title").text, "PROFILE VIEWS: 12,345")
        self.assertIn("12,345", [node.text for node in root.iter(f"{counter.SVG_NS}text")])
        self.assertFalse(self.path.with_suffix(".svg.tmp").exists())

    def test_network_failure_preserves_existing_bytes(self) -> None:
        self.write_existing_badge()
        with patch.object(counter, "urlopen", side_effect=URLError("offline")):
            with patch.object(counter.time, "sleep"):
                with self.assertRaises(URLError):
                    counter.update_badge(self.path, "zhengzihaoPKU")
        self.assertEqual(self.path.read_bytes(), GOOD_SVG)

    def test_http_200_error_svg_preserves_existing_bytes(self) -> None:
        self.write_existing_badge()
        with patch.object(counter, "urlopen", side_effect=lambda *_args, **_kwargs: Response(ERROR_SVG)):
            with patch.object(counter.time, "sleep"):
                with self.assertRaises(ValueError):
                    counter.update_badge(self.path, "zhengzihaoPKU")
        self.assertEqual(self.path.read_bytes(), GOOD_SVG)

    def test_decreased_or_reset_count_preserves_existing_bytes(self) -> None:
        self.write_existing_badge()
        for count in (1233, 0):
            with self.subTest(count=count):
                with patch.object(counter, "fetch_count", return_value=count):
                    with self.assertRaisesRegex(ValueError, "decreased"):
                        counter.update_badge(self.path, "zhengzihaoPKU")
                self.assertEqual(self.path.read_bytes(), GOOD_SVG)

    def test_first_failure_does_not_create_badge(self) -> None:
        with patch.object(counter, "fetch_count", side_effect=URLError("offline")):
            with self.assertRaises(URLError):
                counter.update_badge(self.path, "zhengzihaoPKU")
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.parent.exists())

    def test_first_success_can_record_zero(self) -> None:
        with patch.object(counter, "fetch_count", return_value=0):
            self.assertEqual(counter.update_badge(self.path, "zhengzihaoPKU"), 0)
        root = ET.fromstring(self.path.read_bytes())
        self.assertEqual(root.get("aria-label"), "PROFILE VIEWS: 0")

    def test_atomic_replace_failure_preserves_badge_and_removes_temporary_file(self) -> None:
        self.write_existing_badge()
        with patch.object(counter, "fetch_count", return_value=12345):
            with patch.object(Path, "replace", side_effect=OSError("replace failed")):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    counter.update_badge(self.path, "zhengzihaoPKU")
        self.assertEqual(self.path.read_bytes(), GOOD_SVG)
        self.assertFalse(self.path.with_suffix(".svg.tmp").exists())


if __name__ == "__main__":
    unittest.main()
