"""Unit tests for bridge tool formatting logic (backends are not called)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import MAX_MARKDOWN_CHARS, format_scrape_response  # noqa: E402


def test_scrape_success_maps_fields():
    payload = {
        "success": True,
        "data": {
            "markdown": "# Example\n\nBody text.",
            "metadata": {
                "title": "Example Domain",
                "sourceURL": "https://example.com",
                "statusCode": 200,
            },
        },
    }
    out = format_scrape_response(payload, "https://example.com")
    assert out == {
        "url": "https://example.com",
        "title": "Example Domain",
        "status_code": 200,
        "markdown": "# Example\n\nBody text.",
        "truncated": False,
    }


def test_scrape_truncates_long_markdown():
    payload = {
        "success": True,
        "data": {"markdown": "x" * (MAX_MARKDOWN_CHARS + 100), "metadata": {}},
    }
    out = format_scrape_response(payload, "https://example.com")
    assert len(out["markdown"]) == MAX_MARKDOWN_CHARS
    assert out["truncated"] is True


def test_scrape_failure_returns_error():
    payload = {"success": False, "error": "DNS resolution failed"}
    out = format_scrape_response(payload, "https://nope.invalid")
    assert out == {"error": "DNS resolution failed", "url": "https://nope.invalid"}


def test_scrape_failure_without_message_gets_default():
    out = format_scrape_response({}, "https://nope.invalid")
    assert out["error"] == "scrape failed"
