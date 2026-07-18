"""Unit tests for the media/news/wiki search formatters."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import (  # noqa: E402
    format_image_response,
    format_news_response,
    format_video_response,
    format_wiki_response,
)

VIDEO_ROWS = [
    {
        "url": "https://www.youtube.com/watch?v=abc",
        "title": "HA 2026.7 review",
        "content": "Release walkthrough.",
        "thumbnail": "https://i.ytimg.com/vi/abc/hq.jpg",
        "author": "HomeTech",
        "length": "12:34",
        "publishedDate": "2026-07-01",
    },
    {"url": "https://vimeo.com/1", "title": "No extras"},
]


def test_video_scheme():
    out = format_video_response(VIDEO_ROWS, "ha review")
    assert out["source"] == "searxng"
    assert out["type"] == "videos"
    assert out["results"][0] == {
        "url": "https://www.youtube.com/watch?v=abc",
        "title": "HA 2026.7 review",
        "snippet": "Release walkthrough.",
        "site_name": "youtube.com",
        "thumbnail": "https://i.ytimg.com/vi/abc/hq.jpg",
        "channel": "HomeTech",
        "length": "12:34",
        "published": "2026-07-01",
    }
    assert out["results"][1]["thumbnail"] is None
    assert out["featured_image"] == "https://i.ytimg.com/vi/abc/hq.jpg"
    assert out["num_results"] == 2


def test_image_scheme():
    rows = [
        {
            "url": "https://page/1",
            "img_src": "https://cdn/full.jpg",
            "thumbnail_src": "https://cdn/thumb.jpg",
            "title": "Sunset",
        }
    ]
    out = format_image_response(rows, "sunset")
    assert out["type"] == "images"
    assert out["results"][0] == {
        "title": "Sunset",
        "image_url": "https://cdn/full.jpg",
        "thumbnail_url": "https://cdn/thumb.jpg",
        "source_url": "https://page/1",
        "site_name": "page",
    }
    assert out["featured_image"] == "https://cdn/full.jpg"


def test_news_scheme():
    rows = [
        {
            "url": "https://reuters.com/a",
            "title": "Headline",
            "content": "Body.",
            "publishedDate": "2026-07-17",
        }
    ]
    out = format_news_response(rows, "news q")
    assert out["type"] == "news"
    assert out["results"][0]["published"] == "2026-07-17"
    assert out["results"][0]["site_name"] == "reuters.com"


def test_wiki_scheme_and_empty_message():
    out = format_wiki_response([], "nothing")
    assert out["type"] == "wiki"
    assert out["results"] == []
    assert out["message"] == "No results found for this query."


def test_wiki_merges_infoboxes_first():
    # wikipedia answers via `infoboxes`, not `results`
    infoboxes = [
        {
            "infobox": "Home Assistant",
            "id": "https://en.wikipedia.org/wiki/Home_Assistant",
            "content": "Free and open-source home automation software.",
        }
    ]
    rows = [{"url": "https://en.wikipedia.org/wiki/Smart_home", "title": "Smart home", "content": "x"}]
    out = format_wiki_response(rows, "home assistant", infoboxes)
    assert out["results"][0] == {
        "url": "https://en.wikipedia.org/wiki/Home_Assistant",
        "title": "Home Assistant",
        "snippet": "Free and open-source home automation software.",
        "site_name": "en.wikipedia.org",
    }
    assert out["results"][1]["title"] == "Smart home"
    assert out["num_results"] == 2
