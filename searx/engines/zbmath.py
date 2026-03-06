# SPDX-License-Identifier: AGPL-3.0-or-later
"""zbMATH Open provides searchable mathematical publication metadata and
editorial reviews.

Configuration
=============

.. code:: yaml

   - name: zbmath
     engine: zbmath
     shortcut: zbm

Implementations
===============

"""

import typing as t

from datetime import datetime
from urllib.parse import urlencode

from searx.result_types import EngineResults

if t.TYPE_CHECKING:
    from searx.extended_types import SXNG_Response
    from searx.search.processors import OnlineParams

about = {
    "website": "https://zbmath.org/",
    "wikidata_id": "Q2510606",
    "official_api_documentation": "https://api.zbmath.org/v1/",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["math"]
paging = True
search_url = "https://api.zbmath.org/v1/document/_search"
results_per_page = 10


def request(query: str, params: "OnlineParams") -> None:
    args = {
        "search_string": query,
        "results_per_page": results_per_page,
        "page": params["pageno"] - 1,
    }
    params["url"] = f"{search_url}?{urlencode(args)}"


def response(resp: "SXNG_Response") -> EngineResults:
    res = EngineResults()
    json_data = resp.json()

    for doc in json_data.get("result", []):
        source = doc.get("source", {})
        series = _first(source.get("series", []))
        book = _first(source.get("book", []))
        doi, html_url, pdf_url = _extract_links(doc.get("links", []))
        source_text = source.get("source", "")
        review = _extract_review(doc.get("editorial_contributions", []))

        res.add(
            res.types.Paper(
                url=doc.get("zbmath_url") or html_url,
                title=_get_title(doc.get("title", {})),
                content=review or source_text,
                comments=source_text if review else "",
                authors=_extract_authors(doc.get("contributors", {})),
                journal=series.get("title", "") or source_text,
                publisher=series.get("publisher", "") or book.get("publisher", ""),
                volume=series.get("volume", ""),
                number=series.get("issue", ""),
                pages=source.get("pages", ""),
                doi=doi,
                html_url=html_url,
                pdf_url=pdf_url,
                tags=[
                    msc.get("code", "") for msc in doc.get("msc", []) if msc.get("code")
                ],
                type=doc.get("document_type", {}).get("description", ""),
                publishedDate=_parse_year(doc.get("year")),
            )
        )

    return res


def _extract_authors(contributors: dict[str, t.Any]) -> list[str]:
    authors = [
        author.get("name", "")
        for author in contributors.get("authors", [])
        if author.get("name")
    ]
    if len(authors) > 15:
        authors = authors[:15] + ["et al."]
    return authors


def _extract_links(links: list[dict[str, str]]) -> tuple[str, str, str]:
    doi = ""
    html_url = ""
    pdf_url = ""

    for link in links:
        url = link.get("url", "")
        if not url:
            continue
        if link.get("type") == "doi" and not doi:
            doi = link.get("identifier", "") or url.removeprefix("https://doi.org/")
            continue
        if not pdf_url and (url.endswith(".pdf") or "/pdf/" in url):
            pdf_url = url
            continue
        if not html_url:
            html_url = url

    return doi, html_url, pdf_url


def _extract_review(contributions: list[dict[str, t.Any]]) -> str:
    for contribution in contributions:
        text = (contribution.get("text") or "").strip()
        if text.startswith("Summary:"):
            text = text.removeprefix("Summary:").strip()
        elif text.startswith("Review:"):
            text = text.removeprefix("Review:").strip()
        if text:
            return text
    return ""


def _first(values: list[dict[str, t.Any]]) -> dict[str, t.Any]:
    return values[0] if values else {}


def _get_title(title_data: dict[str, str | None]) -> str:
    title = title_data.get("title") or ""
    subtitle = title_data.get("subtitle")
    if subtitle:
        return f"{title}: {subtitle}"
    return title


def _parse_year(year: str | None) -> datetime | None:
    if year and year.isdigit():
        return datetime(int(year), 1, 1)
    return None
