# SPDX-License-Identifier: AGPL-3.0-or-later
"""DuckDuckGo (browser-rendered via local stealth Playwright service).

DuckDuckGo serves a JS anti-bot challenge to non-browser search requests and
fingerprints plain headless browsers (redirect to ``static-pages/418.html``).
The stock ``duckduckgo`` engine therefore returns CAPTCHA/202 from this host.

This engine renders the main DuckDuckGo SERP through a local Playwright
service (Firecrawl ``playwright-service-ts`` patched with
``puppeteer-extra-plugin-stealth``) which executes the page JS and returns the
final HTML.  Results are parsed from DuckDuckGo's stable ``data-testid``
attributes (the CSS class names are obfuscated/rotated, the testids are not).

The render service must be running locally (see the systemd user unit
``searxng-scrape``); ``base_url`` points at it and ``enable_http`` is required
because it is plain-HTTP localhost.
"""

import json
from urllib.parse import urlencode

from lxml import html

from searx.utils import eval_xpath, eval_xpath_list, extract_text

about = {
    "website": "https://duckduckgo.com/",
    "wikidata_id": "Q12805",
    "use_official_api": False,
    "require_api_key": False,
    "results": "HTML",
}

categories = ["general", "web"]
paging = False

# Local stealth Playwright render service: POST /scrape -> {"content": <html>}.
base_url = "http://localhost:3003/scrape"
ddg_serp = "https://duckduckgo.com/"

results_xpath = '//*[@data-testid="result"]'
title_link_xpath = './/a[@data-testid="result-title-a"]'
snippet_xpath = './/*[@data-result="snippet"]'


def request(query, params):
    params["method"] = "POST"
    params["url"] = base_url
    params["json"] = {
        "url": ddg_serp + "?" + urlencode({"q": query}),
        "wait_after_load": 3500,
        "timeout": 30000,
    }
    params["headers"]["Content-Type"] = "application/json"
    return params


def response(resp):
    results = []

    content = json.loads(resp.text).get("content")
    if not content:
        return results

    dom = html.fromstring(content)
    for result in eval_xpath_list(dom, results_xpath):
        link = eval_xpath(result, title_link_xpath)
        if not link:
            continue
        url = link[0].get("href")
        title = extract_text(link[0])
        if not url or not title:
            continue
        results.append(
            {
                "url": url,
                "title": title,
                "content": extract_text(eval_xpath(result, snippet_xpath)) or "",
            }
        )

    return results
