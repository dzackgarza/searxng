# SPDX-License-Identifier: AGPL-3.0-or-later
# pylint: disable=missing-module-docstring,missing-class-docstring,invalid-name

from unittest import TestCase

from searx.engines import annas_archive


class TestAnnasArchive(TestCase):

    def test_default_categories_include_math(self):
        self.assertEqual(annas_archive.categories, ['files', 'books', 'math'])
