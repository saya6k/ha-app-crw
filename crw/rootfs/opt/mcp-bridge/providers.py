"""Provider brand -> SearXNG engine mapping for the media/wiki search tools.

Brand names are what the add-on options expose; each tool maps a brand to
the engine of the matching category in the pinned SearXNG version (e.g.
picking "naver" for video_search queries the `naver videos` engine).
"""

PROVIDER_ENGINES: dict[str, dict[str, str]] = {
    "video": {
        "youtube": "youtube",
        "google": "google videos",
        "bing": "bing videos",
        "duckduckgo": "duckduckgo videos",
        "brave": "brave.videos",
        "naver": "naver videos",
        "qwant": "qwant videos",
        "sogou": "sogou videos",
        "360search": "360search videos",
        "presearch": "presearch videos",
        "dailymotion": "dailymotion",
        "vimeo": "vimeo",
        "peertube": "peertube",
        "sepiasearch": "sepiasearch",
        "rumble": "rumble",
        "odysee": "odysee",
        "bilibili": "bilibili",
        "niconico": "niconico",
        "pixabay": "pixabay videos",
    },
    "image": {
        "google": "google images",
        "bing": "bing images",
        "duckduckgo": "duckduckgo images",
        "brave": "brave.images",
        "naver": "naver images",
        "baidu": "baidu images",
        "qwant": "qwant images",
        "sogou": "sogou images",
        "presearch": "presearch images",
        "yandex": "yandex images",
        "mojeek": "mojeek images",
        "flickr": "flickr",
        "unsplash": "unsplash",
        "pexels": "pexels",
        "pixabay": "pixabay images",
        "wallhaven": "wallhaven",
        "deviantart": "deviantart",
        "imgur": "imgur",
        "openverse": "openverse",
    },
    "news": {
        "google": "google news",
        "bing": "bing news",
        "duckduckgo": "duckduckgo news",
        "brave": "brave.news",
        "naver": "naver news",
        "qwant": "qwant news",
        "presearch": "presearch news",
        "chinaso": "chinaso news",
        "yahoo": "yahoo news",
        "mojeek": "mojeek news",
        "karmasearch": "karmasearch news",
        "reuters": "reuters",
        "tagesschau": "tagesschau",
        "ansa": "ansa",
        "ilpost": "il post",
    },
    "wiki": {
        "wikipedia": "wikipedia",
        "wikidata": "wikidata",
        "wiktionary": "wiktionary",
        "wikiquote": "wikiquote",
        "wikisource": "wikisource",
        "wikibooks": "wikibooks",
        "wikivoyage": "wikivoyage",
        "wikinews": "wikinews",
        "wikispecies": "wikispecies",
        "encyclosearch": "encyclosearch",
    },
}


def engines_for(tool: str, brands: list[str] | None) -> list[str]:
    """Map selected brand names to engine names, ignoring unknown brands."""
    mapping = PROVIDER_ENGINES[tool]
    return [mapping[b] for b in brands or [] if b in mapping]


# Key-gated engines: activated only when their add-on option carries a key.
# option name -> engine name (all ship `inactive: true` upstream).
KEY_OPTION_ENGINES = {
    "youtube_api_key": "youtube_api",
    "flickr_api_key": "flickr_api",
    "brave_api_key": "braveapi",
}

# Which key-gated engine feeds which tool ("web" joins the general set).
KEY_ENGINE_TOOLS = {
    "video": [("youtube_api", "youtube_api_key")],
    "image": [("flickr_api", "flickr_api_key")],
}


def engines_for_tool(tool: str, options: dict) -> list[str]:
    """Engines for a tool: mapped brand providers plus key-gated engines."""
    engines = engines_for(tool, options.get(f"{tool}_search_providers"))
    for engine, key_option in KEY_ENGINE_TOOLS.get(tool, []):
        if options.get(key_option):
            engines.append(engine)
    return engines


def missing_key_hints(options: dict) -> list[str]:
    """Log lines for key-gated engines that stay off because no key is set."""
    return [
        f"{engine} stays disabled — set {key_option} to enable it"
        for key_option, engine in KEY_OPTION_ENGINES.items()
        if not options.get(key_option)
    ]
