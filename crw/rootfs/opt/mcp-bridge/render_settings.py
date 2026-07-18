"""Render the runtime SearXNG settings from the base template + add-on options.

Invoked by the searxng s6 run script with the searxng venv's python
(PyYAML comes from SearXNG's own dependencies).
"""

import argparse
import copy
import json
import sys
from pathlib import Path

import yaml

from providers import engines_for

VALID_SAFE_SEARCH = (0, 1, 2)
PROVIDER_TOOLS = ("video", "image", "news", "wiki")

# Engines that fail or spam errors in a typical HA deployment:
# - wikidata: startup SPARQL query widely answered with 403
# - ahmia/torch: need a Tor proxy that isn't bundled
# - startpage: response parser broken against their current API (JSON error)
# - qwant*: rate-limits most self-hosted IPs from the first query (429).
#   The whole family must go together — qwant news/images/videos declare
#   `network: qwant`, and removing only the base engine breaks SearXNG's
#   network init with KeyError: 'qwant'.
DEFAULT_REMOVED_ENGINES = [
    "wikidata",
    "ahmia",
    "torch",
    "startpage",
    "qwant",
    "qwant news",
    "qwant images",
    "qwant videos",
]

# child engine -> engine whose `network:` it references, derived from the
# pinned SearXNG default settings (searx/settings.yml @ SEARXNG_COMMIT).
NETWORK_PARENTS = {
    "adobe stock video": "adobe stock",
    "adobe stock audio": "adobe stock",
    "brave.images": "brave",
    "brave.videos": "brave",
    "brave.news": "brave",
    "chinaso images": "chinaso news",
    "chinaso videos": "chinaso news",
    "lemmy users": "lemmy communities",
    "lemmy posts": "lemmy communities",
    "lemmy comments": "lemmy communities",
    "piped.music": "piped",
    "presearch images": "presearch",
    "presearch videos": "presearch",
    "presearch news": "presearch",
    "qwant news": "qwant",
    "qwant images": "qwant",
    "qwant videos": "qwant",
    "yacy images": "yacy",
    "yandex images": "yandex",
    "yandex music": "yandex",
}


def render(base: dict, options: dict, secret_key: str) -> dict:
    """Merge add-on options into the base settings template."""
    out = copy.deepcopy(base)
    out["server"]["secret_key"] = secret_key

    safe = options.get("safe_search")
    if safe in VALID_SAFE_SEARCH:
        out["search"]["safe_search"] = safe

    engines = [e for e in options.get("search_engines") or [] if e]

    # Engines backing the media/news/wiki tools must be loaded regardless of
    # the web engine selection, with their `network:` parents.
    provider_engines: list[str] = []
    for tool in PROVIDER_TOOLS:
        for e in engines_for(tool, options.get(f"{tool}_search_providers")):
            if e not in provider_engines:
                provider_engines.append(e)
    provider_closure = list(provider_engines)
    for e in provider_engines:
        parent = NETWORK_PARENTS.get(e)
        if parent and parent not in provider_closure:
            provider_closure.append(parent)

    if engines:
        # keep_only must include every referenced `network:` parent or
        # SearXNG's network init crashes (KeyError) on the orphaned child.
        closure = list(engines)
        for engine in engines:
            parent = NETWORK_PARENTS.get(engine)
            if parent and parent not in closure:
                closure.append(parent)
        for e in provider_closure:
            if e not in closure:
                closure.append(e)
        out["use_default_settings"] = {"engines": {"keep_only": closure}}
        enabled = engines + [e for e in provider_engines if e not in engines]
    else:
        removed = [
            e for e in DEFAULT_REMOVED_ENGINES if e not in provider_closure
        ]
        out["use_default_settings"] = {"engines": {"remove": removed}}
        enabled = provider_engines

    # Force-enable what the user picked — several defaults ship disabled.
    # Auto-added network parents keep their default state.
    engine_entries = [{"name": e, "disabled": False} for e in enabled]

    # provider_api_keys: "engine_name: key" entries activate key-gated
    # engines (e.g. youtube_api, flickr_api) that ship inactive upstream.
    for entry in options.get("provider_api_keys") or []:
        name, sep, key = str(entry).partition(":")
        if not sep or not name.strip() or not key.strip():
            continue
        engine_entries.append(
            {
                "name": name.strip(),
                "api_key": key.strip(),
                "inactive": False,
                "disabled": False,
            }
        )

    if engine_entries:
        out["engines"] = engine_entries

    proxy = options.get("outgoing_proxy")
    if proxy:
        out["outgoing"] = {"proxies": {"all://": [proxy]}}

    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--options", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    base = yaml.safe_load(Path(args.base).read_text())
    try:
        options = json.loads(Path(args.options).read_text())
    except (OSError, ValueError):
        options = {}

    Path(args.out).write_text(
        yaml.safe_dump(render(base, options, args.secret), sort_keys=False)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
