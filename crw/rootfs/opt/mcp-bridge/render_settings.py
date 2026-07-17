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

VALID_SAFE_SEARCH = (0, 1, 2)

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
    if engines:
        # keep_only must include every referenced `network:` parent or
        # SearXNG's network init crashes (KeyError) on the orphaned child.
        closure = list(engines)
        for engine in engines:
            parent = NETWORK_PARENTS.get(engine)
            if parent and parent not in closure:
                closure.append(parent)
        out["use_default_settings"] = {"engines": {"keep_only": closure}}
        # Force-enable what the user picked — several defaults ship
        # disabled. Auto-added parents keep their default state.
        out["engines"] = [{"name": e, "disabled": False} for e in engines]
    else:
        out["use_default_settings"] = {
            "engines": {"remove": list(DEFAULT_REMOVED_ENGINES)}
        }

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
