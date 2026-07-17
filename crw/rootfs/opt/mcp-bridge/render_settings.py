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

# Engines whose init fails or spams errors in a typical HA deployment:
# wikidata's startup SPARQL query is widely answered with 403, and the
# onion engines need a Tor proxy that isn't bundled.
DEFAULT_REMOVED_ENGINES = ["wikidata", "ahmia", "torch"]


def render(base: dict, options: dict, secret_key: str) -> dict:
    """Merge add-on options into the base settings template."""
    out = copy.deepcopy(base)
    out["server"]["secret_key"] = secret_key

    safe = options.get("safe_search")
    if safe in VALID_SAFE_SEARCH:
        out["search"]["safe_search"] = safe

    engines = [e for e in options.get("search_engines") or [] if e]
    if engines:
        out["use_default_settings"] = {"engines": {"keep_only": engines}}
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
