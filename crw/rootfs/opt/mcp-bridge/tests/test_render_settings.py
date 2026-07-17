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
    # torch need Tor, startpage's parser is broken, qwant 429s instantly)
    assert out["use_default_settings"] == {
        "engines": {
            "remove": ["wikidata", "ahmia", "torch", "startpage", "qwant"]
        }
    }
    assert "outgoing" not in out
    # base dict must not be mutated
    assert BASE["server"]["secret_key"] == "@SECRET_KEY@"


def test_safe_search_from_options_with_validation():
    assert render(BASE, {"safe_search": 2}, "k")["search"]["safe_search"] == 2
    assert render(BASE, {"safe_search": 9}, "k")["search"]["safe_search"] == 1
    assert render(BASE, {"safe_search": "x"}, "k")["search"]["safe_search"] == 1


def test_engine_keep_only():
    out = render(BASE, {"search_engines": ["duckduckgo", "brave"]}, "k")
    assert out["use_default_settings"] == {
        "engines": {"keep_only": ["duckduckgo", "brave"]}
    }


def test_outgoing_proxy():
    out = render(BASE, {"outgoing_proxy": "socks5://10.0.0.2:1080"}, "k")
    assert out["outgoing"]["proxies"] == {"all://": ["socks5://10.0.0.2:1080"]}
    # empty/null stays absent
    assert "outgoing" not in render(BASE, {"outgoing_proxy": ""}, "k")
    assert "outgoing" not in render(BASE, {"outgoing_proxy": None}, "k")
