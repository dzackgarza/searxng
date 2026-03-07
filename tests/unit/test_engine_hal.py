# SPDX-License-Identifier: AGPL-3.0-or-later
# pylint: disable=missing-module-docstring,disable=missing-class-docstring

from datetime import datetime
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import searx.engines
import searx.search
from searx.result_types import EngineResults
from tests import SearxTestCase


class HALTests(SearxTestCase):
    TEST_SETTINGS = "test_hal.yml"

    def setUp(self):
        super().setUp()
        self.hal = searx.engines.engines["hal"]

    def tearDown(self):
        searx.search.load_engines([])

    def test_request_sets_search_url(self):
        params = {"pageno": 1}

        self.assertIsNone(self.hal.request("modular forms", params))

        parsed_url = urlparse(params["url"])
        query = parse_qs(parsed_url.query)
        self.assertEqual(parsed_url.netloc, "api.archives-ouvertes.fr")
        self.assertEqual(parsed_url.path, "/search/")
        self.assertEqual(query["q"], ["modular forms"])
        self.assertEqual(query["wt"], ["json"])
        self.assertEqual(query["rows"], ["20"])
        self.assertEqual(query["start"], ["0"])
        self.assertIn("title_s", query["fl"][0])
        self.assertIn("authFullName_s", query["fl"][0])
        self.assertIn("abstract_s", query["fl"][0])

    def test_request_handles_pagination(self):
        params = {"pageno": 3}

        self.assertIsNone(self.hal.request("algebraic geometry", params))

        parsed_url = urlparse(params["url"])
        query = parse_qs(parsed_url.query)
        self.assertEqual(query["start"], ["40"])
        self.assertEqual(query["rows"], ["20"])

    def test_response_maps_documents_to_papers(self):
        response = Mock()
        response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "title_s": ["Test Paper Title"],
                        "abstract_s": ["This is a test abstract"],
                        "authFullName_s": ["John Doe", "Jane Smith"],
                        "doiId_s": "10.1234/test",
                        "producedDateY_i": 2024,
                        "journalTitle_s": ["Test Journal"],
                        "fileMain_s": "https://hal.science/hal-00000001/document",
                        "halId_s": "hal-00000001",
                    }
                ]
            }
        }

        results = self.hal.response(response)

        self.assertIsInstance(results, EngineResults)
        self.assertEqual(len(results), 1)

        result = results[0]
        self.assertEqual(result.title, "Test Paper Title")
        self.assertEqual(result.content, "This is a test abstract")
        self.assertEqual(result.authors, ["John Doe", "Jane Smith"])
        self.assertEqual(result.doi, "10.1234/test")
        self.assertEqual(result.journal, "Test Journal")
        self.assertEqual(result.url, "https://hal.science/hal-00000001/document")
        self.assertEqual(result.publishedDate, datetime(2024, 1, 1))

    def test_response_falls_back_to_hal_url(self):
        response = Mock()
        response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "title_s": ["Paper Without PDF"],
                        "abstract_s": ["No PDF available"],
                        "authFullName_s": ["Bob Wilson"],
                        "halId_s": "hal-00000002",
                    }
                ]
            }
        }

        results = self.hal.response(response)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://hal.science/hal-00000002")

    def test_response_skips_empty_titles(self):
        response = Mock()
        response.json.return_value = {
            "response": {
                "docs": [
                    {"title_s": [], "abstract_s": ["No title"]},
                    {"title_s": ["Valid Title"], "abstract_s": ["Valid abstract"]},
                ]
            }
        }

        results = self.hal.response(response)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Valid Title")

    def test_response_handles_missing_optional_fields(self):
        response = Mock()
        response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "title_s": ["Minimal Paper"],
                        "halId_s": "hal-00000003",
                    }
                ]
            }
        }

        results = self.hal.response(response)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Minimal Paper")
        self.assertEqual(results[0].content, "")
        self.assertEqual(results[0].authors, [])
        self.assertEqual(results[0].doi, "")
        self.assertEqual(results[0].journal, "")
        self.assertIsNone(results[0].publishedDate)
