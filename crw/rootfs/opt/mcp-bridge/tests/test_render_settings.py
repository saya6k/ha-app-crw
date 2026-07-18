"""Unit tests for the SearXNG settings renderer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from render_settings import render  # noqa: E402

BASE = {
    "use_default_settings": True,
    "search": {"safe_search": 1, "formats": ["html", "json"]},
    "server": {"secret_key": "@SECRET_KEY@", "port": 8080},
}


def test_secret_and_defaults():
    out = render(BASE, {}, "s3cret")
    assert out["server"]["secret_key"] == "s3cret"
    assert out["search"]["safe_search"] == 1
    # noisy/broken engines are removed by default (wikidata 403s, ahmia/
    # torch need Tor, startpage's parser is broken, qwant 429s instantly).
    # The qwant family must be removed together: its siblings declare
    # `network: qwant` and orphaning them crashes network init.
    removed = out["use_default_settings"]["engines"]["remove"]
    assert removed == [
        "wikidata",
        "ahmia",
        "torch",
        "startpage",
        "qwant",
        "qwant news",
        "qwant images",
        "qwant videos",
    ]
    assert "outgoing" not in out
    # base dict must not be mutated
    assert BASE["server"]["secret_key"] == "@SECRET_KEY@"


def test_safe_search_from_options_with_validation():
    assert render(BASE, {"safe_search": 2}, "k")["search"]["safe_search"] == 2
    assert render(BASE, {"safe_search": 9}, "k")["search"]["safe_search"] == 1
    assert render(BASE, {"safe_search": "x"}, "k")["search"]["safe_search"] == 1


def test_web_engine_set_is_fixed_to_searxng_defaults():
    # No per-engine web selection: search_engines is not an option anymore,
    # the base stays SearXNG defaults minus the stability removals.
    out = render(BASE, {"search_engines": ["duckduckgo"]}, "k")
    assert "keep_only" not in out["use_default_settings"]["engines"]
    assert "remove" in out["use_default_settings"]["engines"]


def test_outgoing_proxy():
    out = render(BASE, {"outgoing_proxy": "socks5://10.0.0.2:1080"}, "k")
    assert out["outgoing"]["proxies"] == {"all://": ["socks5://10.0.0.2:1080"]}
    # empty/null stays absent
    assert "outgoing" not in render(BASE, {"outgoing_proxy": ""}, "k")
    assert "outgoing" not in render(BASE, {"outgoing_proxy": None}, "k")


# ---- media/wiki provider integration -------------------------------------


def test_providers_join_default_remove_mode():
    # default mode: providers must not stay in the removed list, and get
    # force-enabled; qwant videos also needs its network parent kept
    out = render(
        BASE,
        {"video_search_providers": ["qwant"], "image_search_providers": ["baidu"]},
        "k",
    )
    removed = out["use_default_settings"]["engines"]["remove"]
    assert "qwant videos" not in removed
    assert "qwant" not in removed  # network parent must stay loaded
    assert "wikidata" in removed  # unrelated removals intact
    enabled = [e["name"] for e in out["engines"]]
    assert enabled == ["qwant videos", "baidu images"]


def test_named_api_key_options_activate_engines():
    out = render(
        BASE,
        {
            "youtube_api_key": "AIza-test",
            "flickr_api_key": "flk",
            "brave_api_key": "",
        },
        "k",
    )
    entries = out["engines"]
    assert {
        "name": "youtube_api",
        "api_key": "AIza-test",
        "inactive": False,
        "disabled": False,
    } in entries
    assert {
        "name": "flickr_api",
        "api_key": "flk",
        "inactive": False,
        "disabled": False,
    } in entries
    # empty key -> engine stays untouched
    assert not any(e["name"] == "braveapi" for e in entries)
