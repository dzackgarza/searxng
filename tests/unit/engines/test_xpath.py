# SPDX-License-Identifier: AGPL-3.0-or-later
# pylint: disable=missing-module-docstring,disable=missing-class-docstring,invalid-name

from collections import defaultdict
import mock

from searx.engines import xpath
from searx import logger

from tests import SearxTestCase

logger = logger.getChild('engines')


class TestXpathEngine(SearxTestCase):
    html = """
    <div>
        <div class="search_result">
            <a class="result" href="https://result1.com">Result 1</a>
            <p class="content">Content 1</p>
            <a class="cached" href="https://cachedresult1.com">Cache</a>
        </div>
        <div class="search_result">
            <a class="result" href="https://result2.com">Result 2</a>
            <p class="content">Content 2</p>
            <a class="cached" href="https://cachedresult2.com">Cache</a>
        </div>
    </div>
    """

    library_genesis_html = """
    <table id="tablelibgen">
        <tr>
            <th>Title</th>
            <th>Author(s)</th>
            <th>Publisher</th>
            <th>Year</th>
            <th>Language</th>
            <th>Pages</th>
            <th>Size</th>
            <th>Extension</th>
            <th>Mirrors</th>
        </tr>
        <tr>
            <td>
                <b>Algebra Thru Practice</b><br>
                <a href="edition.php?id=137871202">Algebra Through Practice: Volume 1, Sets, Relations and Mappings</a>
            </td>
            <td>T. S. Blyth, E. F. Robertson</td>
            <td>Cambridge University Press</td>
            <td><nobr>1984</nobr></td>
            <td>English</td>
            <td>109 / 108</td>
            <td><nobr><a href="/file.php?id=93103118">2 MB</a></nobr></td>
            <td>pdf</td>
            <td><nobr><a href="/ads.php?md5=90bace2a8c1a377e24145cc766df015a">1</a></nobr></td>
        </tr>
        <tr>
            <td>
                <b>Convexity and Discrete Geometry Including Graph Theory</b><br>
                <a href="edition.php?id=140140627">Convexity and Discrete Geometry Including Graph Theory</a>
            </td>
            <td>Jiri Matousek</td>
            <td>Springer</td>
            <td><nobr>2002</nobr></td>
            <td>English</td>
            <td>300</td>
            <td><nobr><a href="/file.php?id=93946418">3 MB</a></nobr></td>
            <td>pdf</td>
            <td><nobr><a href="/ads.php?md5=67d2c4d3c5f48db2ca0d59d74efa8432">1</a></nobr></td>
        </tr>
    </table>
    """

    def setUp(self):
        super().setUp()
        xpath.logger = logger.getChild('test_xpath')

    def test_request(self):
        xpath.search_url = 'https://url.com/{query}'
        xpath.categories = []
        xpath.paging = False
        query = 'test_query'
        dicto = defaultdict(dict)
        dicto['language'] = 'all'
        dicto['pageno'] = 1
        params = xpath.request(query, dicto)
        self.assertIn('url', params)
        self.assertEqual('https://url.com/test_query', params['url'])

        xpath.search_url = 'https://url.com/q={query}&p={pageno}'
        xpath.paging = True
        query = 'test_query'
        dicto = defaultdict(dict)
        dicto['language'] = 'all'
        dicto['pageno'] = 1
        params = xpath.request(query, dicto)
        self.assertIn('url', params)
        self.assertEqual('https://url.com/q=test_query&p=1', params['url'])

    def test_response(self):
        # without results_xpath
        xpath.url_xpath = '//div[@class="search_result"]//a[@class="result"]/@href'
        xpath.title_xpath = '//div[@class="search_result"]//a[@class="result"]'
        xpath.content_xpath = '//div[@class="search_result"]//p[@class="content"]'

        self.assertRaises(AttributeError, xpath.response, None)
        self.assertRaises(AttributeError, xpath.response, [])
        self.assertRaises(AttributeError, xpath.response, '')
        self.assertRaises(AttributeError, xpath.response, '[]')

        response = mock.Mock(text='<html></html>', status_code=200)
        self.assertEqual(xpath.response(response), [])

        response = mock.Mock(text=self.html, status_code=200)
        results = xpath.response(response)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'Result 1')
        self.assertEqual(results[0]['url'], 'https://result1.com/')
        self.assertEqual(results[0]['content'], 'Content 1')
        self.assertEqual(results[1]['title'], 'Result 2')
        self.assertEqual(results[1]['url'], 'https://result2.com/')
        self.assertEqual(results[1]['content'], 'Content 2')

        # with cached urls, without results_xpath
        xpath.cached_xpath = '//div[@class="search_result"]//a[@class="cached"]/@href'
        results = xpath.response(response)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['cached_url'], 'https://cachedresult1.com')
        self.assertEqual(results[1]['cached_url'], 'https://cachedresult2.com')
        self.assertFalse(results[0].get('is_onion', False))

        # results are onion urls (no results_xpath)
        xpath.categories = ['onions']
        results = xpath.response(response)
        self.assertTrue(results[0]['is_onion'])

    def test_response_results_xpath(self):
        # with results_xpath
        xpath.results_xpath = '//div[@class="search_result"]'
        xpath.url_xpath = './/a[@class="result"]/@href'
        xpath.title_xpath = './/a[@class="result"]'
        xpath.content_xpath = './/p[@class="content"]'
        xpath.cached_xpath = None
        xpath.categories = []

        self.assertRaises(AttributeError, xpath.response, None)
        self.assertRaises(AttributeError, xpath.response, [])
        self.assertRaises(AttributeError, xpath.response, '')
        self.assertRaises(AttributeError, xpath.response, '[]')

        response = mock.Mock(text='<html></html>', status_code=200)
        self.assertEqual(xpath.response(response), [])

        response = mock.Mock(text=self.html, status_code=200)
        results = xpath.response(response)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], 'Result 1')
        self.assertEqual(results[0]['url'], 'https://result1.com/')
        self.assertEqual(results[0]['content'], 'Content 1')
        self.assertEqual(results[1]['title'], 'Result 2')
        self.assertEqual(results[1]['url'], 'https://result2.com/')
        self.assertEqual(results[1]['content'], 'Content 2')

        # with cached urls, with results_xpath
        xpath.cached_xpath = './/a[@class="cached"]/@href'
        results = xpath.response(response)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['cached_url'], 'https://cachedresult1.com')
        self.assertEqual(results[1]['cached_url'], 'https://cachedresult2.com')
        self.assertFalse(results[0].get('is_onion', False))

        # results are onion urls (with results_xpath)
        xpath.categories = ['onions']
        results = xpath.response(response)
        self.assertTrue(results[0]['is_onion'])

    def test_response_library_genesis_selectors(self):
        xpath.search_url = 'https://libgen.li/index.php?req={query}'
        xpath.results_xpath = '//table[@id="tablelibgen"]//tr[position()>1]'
        xpath.url_xpath = './td[1]/a[normalize-space()][1]/@href'
        xpath.title_xpath = './td[1]/a[normalize-space()][1]'
        xpath.content_xpath = './td[position() >= 2 and position() <= 7]'
        xpath.cached_xpath = None
        xpath.categories = []

        response = mock.Mock(text=self.library_genesis_html, status_code=200)
        results = xpath.response(response)

        self.assertEqual(len(results), 2)
        self.assertEqual(
            results[0]['title'],
            'Algebra Through Practice: Volume 1, Sets, Relations and Mappings',
        )
        self.assertEqual(results[0]['url'], 'https://libgen.li/edition.php?id=137871202')
        self.assertIn('T. S. Blyth, E. F. Robertson', results[0]['content'])
        self.assertIn('Cambridge University Press', results[0]['content'])
        self.assertIn('1984', results[0]['content'])
        self.assertIn('2 MB', results[0]['content'])
        self.assertEqual(
            results[1]['title'],
            'Convexity and Discrete Geometry Including Graph Theory',
        )
        self.assertEqual(results[1]['url'], 'https://libgen.li/edition.php?id=140140627')
