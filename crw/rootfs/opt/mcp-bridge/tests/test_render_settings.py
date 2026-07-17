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


def test_engine_keep_only_enables_selection():
    out = render(BASE, {"search_engines": ["duckduckgo", "brave"]}, "k")
    assert out["use_default_settings"] == {
        "engines": {"keep_only": ["duckduckgo", "brave"]}
    }
    # selected engines are force-enabled (some defaults ship disabled)
    assert out["engines"] == [
        {"name": "duckduckgo", "disabled": False},
        {"name": "brave", "disabled": False},
    ]


def test_engine_selection_pulls_network_parents():
    # qwant news declares `network: qwant` — the parent must be kept (not
    # enabled) or SearXNG's network init dies with KeyError: 'qwant'
    out = render(BASE, {"search_engines": ["qwant news", "brave.images"]}, "k")
    keep = out["use_default_settings"]["engines"]["keep_only"]
    assert keep == ["qwant news", "brave.images", "qwant", "brave"]
    enabled = [e["name"] for e in out["engines"]]
    assert enabled == ["qwant news", "brave.images"]


def test_outgoing_proxy():
    out = render(BASE, {"outgoing_proxy": "socks5://10.0.0.2:1080"}, "k")
    assert out["outgoing"]["proxies"] == {"all://": ["socks5://10.0.0.2:1080"]}
    # empty/null stays absent
    assert "outgoing" not in render(BASE, {"outgoing_proxy": ""}, "k")
    assert "outgoing" not in render(BASE, {"outgoing_proxy": None}, "k")
