# SPDX-License-Identifier: AGPL-3.0-or-later
# pylint: disable=missing-module-docstring,disable=missing-class-docstring

from datetime import datetime
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import httpx
import searx.engines
import searx.search
from searx.result_types import EngineResults
from tests import SearxTestCase


class ZbMathTests(SearxTestCase):
    TEST_SETTINGS = "test_zbmath.yml"

    def setUp(self):
        super().setUp()
        self.zbmath = searx.engines.engines["zbmath"]

    def tearDown(self):
        searx.search.load_engines([])

    def test_request_sets_search_url(self):
        params = {"pageno": 3}

        self.assertIsNone(self.zbmath.request("algebraic topology", params))

        parsed_url = urlparse(params["url"])
        query = parse_qs(parsed_url.query)
        self.assertEqual(parsed_url.netloc, "api.zbmath.org")
        self.assertEqual(parsed_url.path, "/v1/document/_search")
        self.assertEqual(query["search_string"], ["algebraic topology"])
        self.assertEqual(query["results_per_page"], ["10"])
        self.assertEqual(query["page"], ["2"])

    def test_response_maps_documents_to_papers(self):
        response = Mock()
        response.json.return_value = {
            "result": [
                {
                    "title": {"title": "Main Title", "subtitle": "A Subtitle"},
                    "contributors": {
                        "authors": [{"name": "Alice Example"}, {"name": "Bob Example"}]
                    },
                    "source": {
                        "source": "Journal of Algebra 292, No. 1, 65-99 (2005).",
                        "pages": "65-99",
                        "series": [
                            {
                                "title": "Journal of Algebra",
                                "publisher": "Elsevier",
                                "volume": "292",
                                "issue": "1",
                            }
                        ],
                        "book": [],
                    },
                    "links": [
                        {
                            "type": "doi",
                            "identifier": "10.1016/j.jalgebra.2004.12.023",
                            "url": "https://doi.org/10.1016/j.jalgebra.2004.12.023",
                        },
                        {"type": "arxiv", "url": "https://arxiv.org/abs/0809.0838"},
                    ],
                    "msc": [{"code": "17B05"}, {"code": "17B45"}],
                    "document_type": {"description": "journal article"},
                    "editorial_contributions": [{"text": "Review: From the text."}],
                    "year": "2005",
                    "zbmath_url": "https://zbmath.org/2240101",
                }
            ]
        }

        results = self.zbmath.response(response)

        self.assertIsInstance(results, EngineResults)
        self.assertEqual(len(results), 1)

        result = results[0]
        self.assertEqual(result.url, "https://zbmath.org/2240101")
        self.assertEqual(result.title, "Main Title: A Subtitle")
        self.assertEqual(result.content, "From the text.")
        self.assertEqual(result.comments, "Journal of Algebra 292, No. 1, 65-99 (2005).")
        self.assertEqual(result.authors, ["Alice Example", "Bob Example"])
        self.assertEqual(result.journal, "Journal of Algebra")
        self.assertEqual(result.publisher, "Elsevier")
        self.assertEqual(result.volume, "292")
        self.assertEqual(result.number, "1")
        self.assertEqual(result.pages, "65-99")
        self.assertEqual(result.doi, "10.1016/j.jalgebra.2004.12.023")
        self.assertEqual(result.html_url, "https://arxiv.org/abs/0809.0838")
        self.assertEqual(result.tags, ["17B05", "17B45"])
        self.assertEqual(result.type, "journal article")
        self.assertEqual(result.publishedDate, datetime(2005, 1, 1))

    def test_response_falls_back_to_source_without_review_text(self):
        response = Mock()
        response.json.return_value = {
            "result": [
                {
                    "title": {"title": "Only Source"},
                    "contributors": {"authors": [{"name": "Alice Example"}]},
                    "source": {
                        "source": "Proceedings volume 478, 39-60 (2009).",
                        "pages": "39-60",
                        "series": [],
                        "book": [{"publisher": "American Mathematical Society"}],
                    },
                    "links": [],
                    "msc": [],
                    "document_type": {"description": "serial article"},
                    "editorial_contributions": [{"text": "Summary:"}],
                    "year": "2009",
                    "zbmath_url": "https://zbmath.org/5526567",
                }
            ]
        }

        results = self.zbmath.response(response)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "Proceedings volume 478, 39-60 (2009).")
        self.assertEqual(results[0].comments, "")
        self.assertEqual(results[0].publisher, "American Mathematical Society")

    def test_response_ignores_null_review_text(self):
        response = httpx.Response(
            200,
            json={
                "result": [
                    {
                        "title": {"title": "The theory of convex homogeneous cones"},
                        "contributors": {
                            "authors": [{"name": "Vinberg, E. B."}],
                        },
                        "source": {
                            "source": (
                                "Trans. Mosc. Math. Soc. 12, 340-403 (1963); "
                                "translation from Tr. Mosk. Mat. O.-va 12, 303-358 (1963)."
                            ),
                            "pages": "340-403",
                            "series": [
                                {
                                    "title": "Transactions of the Moscow Mathematical Society",
                                    "publisher": "American Mathematical Society (AMS), Providence, RI",
                                    "volume": "12",
                                    "issue": None,
                                }
                            ],
                            "book": [],
                        },
                        "links": [],
                        "msc": [],
                        "document_type": {"description": "journal article"},
                        "editorial_contributions": [{"text": None}],
                        "year": "1963",
                        "zbmath_url": "https://zbmath.org/3225176",
                    }
                ],
                "status": "ok",
            },
        )

        results = self.zbmath.response(response)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, response.json()["result"][0]["source"]["source"])
        self.assertEqual(results[0].comments, "")
        self.assertEqual(results[0].url, "https://zbmath.org/3225176")
