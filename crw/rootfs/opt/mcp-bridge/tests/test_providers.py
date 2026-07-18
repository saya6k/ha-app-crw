"""Unit tests for provider brand -> SearXNG engine mapping."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from providers import PROVIDER_ENGINES, engines_for  # noqa: E402


def test_video_brand_maps_to_video_engine():
    assert engines_for("video", ["naver"]) == ["naver videos"]
    assert engines_for("video", ["youtube", "brave"]) == ["youtube", "brave.videos"]


def test_image_brand_maps_to_image_engine():
    assert engines_for("image", ["baidu", "duckduckgo"]) == [
        "baidu images",
        "duckduckgo images",
    ]


def test_wiki_brands_map_directly():
    assert engines_for("wiki", ["wikipedia", "wiktionary"]) == [
        "wikipedia",
        "wiktionary",
    ]


def test_unknown_brands_are_ignored():
    assert engines_for("video", ["nope", "youtube"]) == ["youtube"]
    assert engines_for("image", []) == []


def test_all_mapped_engines_exist_in_pinned_searxng():
    # engine-names extracted from searx/settings.yml @ the pinned commit
    known = set(
        Path(__file__).with_name("data-engine-names.txt").read_text().splitlines()
    )
    for tool_map in PROVIDER_ENGINES.values():
        for engine in tool_map.values():
            assert engine in known, engine


def test_news_brand_maps_to_news_engine():
    assert engines_for("news", ["naver", "reuters"]) == ["naver news", "reuters"]
