# SPDX-License-Identifier: AGPL-3.0-or-later
"""HAL (Hyper Articles en Ligne) is a French open-access repository for
scientific documents. The platform hosts over 1 million documents from
researchers worldwide, covering all scientific disciplines.

.. _HAL: https://hal.science/
.. _HAL API: https://api.archives-ouvertes.fr/docs/search

"""

import typing as t

from urllib.parse import urlencode
from datetime import datetime
from searx.result_types import EngineResults

if t.TYPE_CHECKING:
    from searx.extended_types import SXNG_Response
    from searx.search.processors import OnlineParams

about = {
    "website": "https://hal.science/",
    "wikidata_id": "Q314115",
    "official_api_documentation": "https://api.archives-ouvertes.fr/docs/search",
    "use_official_api": True,
    "require_api_key": False,
    "results": "JSON",
}

categories = ["science", "scientific publications"]
paging = True
search_url = "https://api.archives-ouvertes.fr/search/"
"""HAL Solr-based search endpoint. Returns JSON-formatted search results with
configurable field lists (`HAL API documentation`_).

.. _HAL API documentation: https://api.archives-ouvertes.fr/docs/search
"""


def request(query: str, params: "OnlineParams") -> None:
    # 20 results per page, standard for SearXNG
    rows = 20
    offset = rows * (params["pageno"] - 1)

    args = {
        "q": query,
        "wt": "json",
        "rows": rows,
        "start": offset,
        # Request only necessary fields to save bandwidth
        "fl": "title_s,authFullName_s,abstract_s,doiId_s,producedDateY_i,journalTitle_s,fileMain_s,halId_s",
    }
    params["url"] = f"{search_url}?{urlencode(args)}"


def response(resp: "SXNG_Response") -> EngineResults:
    res = EngineResults()
    json_data = resp.json()

    for item in json_data.get("response", {}).get("docs", []):
        # Safely extract list or string values (HAL returns lists for text fields)
        title_list = item.get("title_s", [])
        title = title_list[0] if title_list else ""
        if not title:
            continue

        abstract_list = item.get("abstract_s", [])
        content = abstract_list[0] if abstract_list else ""

        # Determine the canonical URL
        url = item.get("fileMain_s")
        if not url:
            hal_id = item.get("halId_s", "")
            url = f"https://hal.science/{hal_id}" if hal_id else ""

        paper = res.types.Paper(
            title=title,
            content=content,
            doi=item.get("doiId_s", ""),
            journal=item.get("journalTitle_s", ""),
            url=url,
        )

        # Format the year as a datetime object for SearXNG date filtering
        year = item.get("producedDateY_i")
        if year:
            paper.publishedDate = datetime(year, 1, 1)

        # Add author list
        paper.authors = item.get("authFullName_s", [])

        res.add(paper)

    return res
