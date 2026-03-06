# SPDX-License-Identifier: AGPL-3.0-or-later
"""Math-Net site search powered by Google CSE.

Math-Net exposes its search UI through a Google Custom Search embed. To match
that behavior, this engine fetches the CSE bootstrap script to obtain the
transient request token and then queries the public CSE element endpoint.
"""

import json
import re
import typing as t

from urllib.parse import urlencode

from searx.enginelib import EngineCache
from searx.network import get as http_get
from searx.result_types import EngineResults

if t.TYPE_CHECKING:
    from searx.extended_types import SXNG_Response
    from searx.search.processors import OnlineParams

about: dict[str, t.Any] = {
    "website": "https://www.mathnet.ru/",
    "wikidata_id": None,
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["math"]
paging = True
max_page = 10

CSE_CX = "016263596811403645603:nkhdtbysq40"
CSE_JS_URL = f"https://cse.google.com/cse.js?cx={CSE_CX}"
CSE_SEARCH_URL = "https://cse.google.com/cse/element/v1"
CSE_CALLBACK = "google.search.cse.api1"
BOOTSTRAP_CACHE_TTL = 60 * 5

_CSE_TOKEN_RE = re.compile(r'"cse_token":\s*"([^"]+)"')
_CSE_LIB_VERSION_RE = re.compile(r'"cselibVersion":\s*"([^"]+)"')
_CSE_EXP_RE = re.compile(r'"exp":\s*\[(.*?)\]')
_CSE_FEXP_RE = re.compile(r'"fexp":\s*\[(.*?)\]')

CACHE: EngineCache


def setup(engine_settings: dict[str, t.Any]) -> bool:
    """Initialize the bootstrap cache."""

    global CACHE  # pylint: disable=global-statement

    CACHE = EngineCache(engine_settings["name"])
    return True


def _bootstrap_cache_key(option_lang: str) -> str:
    return f"bootstrap:{option_lang}"


def _get_option_lang(params: "OnlineParams") -> tuple[str, str]:
    locale = (params.get("searxng_locale") or "").lower()
    if locale.startswith("en"):
        return "eng", "en"
    return "rus", "ru"


def _get_bootstrap(search_page_url: str, option_lang: str) -> dict[str, str]:
    cache: EngineCache | None = globals().get("CACHE")
    cached = cache.get(_bootstrap_cache_key(option_lang)) if cache is not None else None
    if cached is not None:
        return cached

    resp = http_get(CSE_JS_URL, timeout=5, headers={"Referer": search_page_url})
    if not resp.ok:
        raise RuntimeError("Math-Net bootstrap request failed")

    token_match = _CSE_TOKEN_RE.search(resp.text)
    version_match = _CSE_LIB_VERSION_RE.search(resp.text)
    if token_match is None or version_match is None:
        raise RuntimeError("Math-Net bootstrap data missing from Google CSE script")

    exp_match = _CSE_EXP_RE.search(resp.text)
    fexp_match = _CSE_FEXP_RE.search(resp.text)

    bootstrap = {
        "cse_tok": token_match.group(1),
        "cselibv": version_match.group(1),
        "exp": exp_match.group(1).replace('"', '').split(",")[0].strip() if exp_match else "cc",
        "fexp": fexp_match.group(1).replace(" ", "") if fexp_match else "",
    }
    if cache is not None:
        cache.set(_bootstrap_cache_key(option_lang), bootstrap, expire=BOOTSTRAP_CACHE_TTL)
    return bootstrap


def request(query: str, params: "OnlineParams") -> None:
    """Query Math-Net's Google CSE endpoint with a fresh bootstrap token."""

    option_lang, ui_lang = _get_option_lang(params)
    search_page_url = "https://www.mathnet.ru/googlesitesearch.phtml?" + urlencode(
        {"option_lang": option_lang, "q": query}
    )
    bootstrap = _get_bootstrap(search_page_url, option_lang)

    query_args = {
        "rsz": "filtered_cse",
        "num": 10,
        "start": (params["pageno"] - 1) * 10,
        "hl": ui_lang,
        "source": "gcsc",
        "cselibv": bootstrap["cselibv"],
        "cx": CSE_CX,
        "q": query,
        "safe": "off",
        "cse_tok": bootstrap["cse_tok"],
        "exp": bootstrap["exp"],
        "callback": CSE_CALLBACK,
        "rurl": search_page_url,
    }
    if bootstrap["fexp"]:
        query_args["fexp"] = bootstrap["fexp"]

    params["headers"]["Referer"] = search_page_url
    params["url"] = CSE_SEARCH_URL + "?" + urlencode(query_args)


def response(resp: "SXNG_Response") -> "EngineResults":
    """Parse the JSONP payload returned by the Google CSE endpoint."""

    res = EngineResults()
    payload = resp.text.strip()
    if payload.startswith("/*O_o*/"):
        payload = payload[len("/*O_o*/") :].lstrip()

    json_start = payload.find("(")
    json_end = payload.rfind(");")
    if json_start == -1 or json_end == -1:
        raise ValueError("Math-Net response is not valid JSONP")

    data = json.loads(payload[json_start + 1 : json_end])
    if data.get("error"):
        raise ValueError(data["error"].get("message", "Math-Net search failed"))

    for item in data.get("results", []):
        url = item.get("unescapedUrl") or item.get("url")
        title = item.get("titleNoFormatting") or item.get("title")
        content = item.get("contentNoFormatting") or item.get("content")
        if not url or not title:
            continue
        res.add(res.types.MainResult(url=url, title=title, content=content or ""))

    return res
