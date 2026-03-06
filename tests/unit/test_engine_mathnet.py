# SPDX-License-Identifier: AGPL-3.0-or-later
# pylint: disable=missing-module-docstring,disable=missing-class-docstring

import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock

import searx.engines
import searx.search
from tests import SearxTestCase


class MathNetTests(SearxTestCase):
    TEST_SETTINGS = "test_mathnet.yml"

    def setUp(self):
        super().setUp()
        self.mathnet = searx.engines.engines["mathnet"]

    def tearDown(self):
        searx.search.load_engines([])

    def test_default_categories_are_math(self):
        self.assertEqual(self.mathnet.categories, ["math", "other"])

    def test_request_uses_mathnet_cse_bootstrap(self):
        http_get = Mock(
            return_value=Mock(
                ok=True,
                text='google.search.cse.api.setAll({"cse_token":"token-123","cselibVersion":"lib-456","exp":["cc"],"fexp":[73152292,73152290]});',
            )
        )
        cache = Mock()
        cache.get.return_value = None

        params = {
            "pageno": 2,
            "searxng_locale": "en-US",
            "headers": {},
            "cookies": {},
        }

        self.setattr4test(self.mathnet, "http_get", http_get)
        self.setattr4test(self.mathnet, "CACHE", cache)

        self.assertIsNone(self.mathnet.request("vinberg", params))

        parsed_url = urlparse(params["url"])
        query = parse_qs(parsed_url.query)
        self.assertEqual(parsed_url.netloc, "cse.google.com")
        self.assertEqual(parsed_url.path, "/cse/element/v1")
        self.assertEqual(query["q"], ["vinberg"])
        self.assertEqual(query["cx"], [self.mathnet.CSE_CX])
        self.assertEqual(query["cse_tok"], ["token-123"])
        self.assertEqual(query["cselibv"], ["lib-456"])
        self.assertEqual(query["rurl"], ["https://www.mathnet.ru/googlesitesearch.phtml?option_lang=eng&q=vinberg"])
        self.assertEqual(query["start"], ["10"])
        self.assertEqual(params["headers"]["Referer"], query["rurl"][0])
        http_get.assert_called_once_with(
            self.mathnet.CSE_JS_URL,
            timeout=5,
            headers={"Referer": "https://www.mathnet.ru/googlesitesearch.phtml?option_lang=eng&q=vinberg"},
        )
        cache.set.assert_called_once()

    def test_response_parses_google_cse_payload(self):
        response = Mock(
            text="/*O_o*/\n"
            "google.search.cse.api1("
            + json.dumps(
                {
                    "results": [
                        {
                            "titleNoFormatting": "Persons: Vinberg, Ernest Borisovich - Mathnet.RU",
                            "unescapedUrl": "https://www.mathnet.ru/eng/person8541",
                            "contentNoFormatting": "È. B. Vinberg, “Some free algebras of automorphic forms on symmetric domains of type IV”.",
                        },
                        {
                            "titleNoFormatting": "È. B. Vinberg, “Hyperbolic reflection groups”",
                            "unescapedUrl": "https://www.mathnet.ru/eng/rm2140",
                            "contentNoFormatting": "Russian Math. Surveys, 40:1 (1985), 31–75.",
                        },
                    ]
                }
            )
            + "\n);"
        )

        results = self.mathnet.response(response)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Persons: Vinberg, Ernest Borisovich - Mathnet.RU")
        self.assertEqual(results[0]["url"], "https://www.mathnet.ru/eng/person8541")
        self.assertIn("automorphic forms", results[0]["content"])
        self.assertEqual(results[1]["url"], "https://www.mathnet.ru/eng/rm2140")
