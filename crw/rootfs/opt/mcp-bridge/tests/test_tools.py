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


# ---- web_search ----------------------------------------------------------

from tools import effective_limit, format_search_response  # noqa: E402

SEARCH_PAYLOAD = {
    "success": True,
    "data": {
        "results": [
            {
                "url": "https://www.home-assistant.io/",
                "title": "Home Assistant",
                "description": "Open source home automation.",
                "snippet": "Open source home automation that puts local control first.",
                "thumbnailUrl": "https://brands.home-assistant.io/logo.png",
            },
            {
                "url": "https://github.com/home-assistant/core",
                "title": "home-assistant/core",
                "description": "GitHub repo.",
            },
        ]
    },
}


def test_search_success_maps_to_card_scheme():
    out = format_search_response(SEARCH_PAYLOAD, "home assistant")
    assert out["source"] == "searxng"
    assert out["query"] == "home assistant"
    assert out["num_results"] == 2
    assert out["results"][0] == {
        "url": "https://www.home-assistant.io/",
        "title": "Home Assistant",
        "snippet": "Open source home automation that puts local control first.",
        "site_name": "home-assistant.io",
    }
    # second result falls back to description for the snippet
    assert out["results"][1]["snippet"] == "GitHub repo."
    assert out["results"][1]["site_name"] == "github.com"
    assert out["featured_image"] == "https://brands.home-assistant.io/logo.png"
    assert "Summarize" in out["instruction"]


def test_search_empty_results():
    out = format_search_response({"success": True, "data": {"results": []}}, "q")
    assert out["num_results"] == 0
    assert out["results"] == []
    assert out["featured_image"] is None
    assert out["message"] == "No results found for this query."


def test_search_failure_returns_error():
    out = format_search_response({"success": False, "error": "backend down"}, "q")
    assert out == {"error": "backend down", "query": "q"}


def test_effective_limit_caps_to_configured_max(monkeypatch):
    monkeypatch.setenv("BRIDGE_MAX_RESULTS", "4")
    assert effective_limit(None) == 4
    assert effective_limit(2) == 2
    assert effective_limit(9) == 4


def test_effective_limit_bad_env_falls_back(monkeypatch):
    monkeypatch.setenv("BRIDGE_MAX_RESULTS", "banana")
    assert effective_limit(None) == 3
