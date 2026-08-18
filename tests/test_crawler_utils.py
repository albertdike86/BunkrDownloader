"""Tests for media-page filename extraction."""

import unittest

from bs4 import BeautifulSoup

from src.crawlers.crawler_utils import get_item_filename


class GetItemFilenameTests(unittest.TestCase):
    """Verify filenames survive the encodings returned by Bunkr pages."""

    @staticmethod
    def _soup(filename: str) -> BeautifulSoup:
        html = (
            '<h1 class="text-subs font-semibold text-base sm:text-lg truncate">'
            f"{filename}</h1>"
        )
        return BeautifulSoup(html, "html.parser")

    def test_repairs_utf8_text_misdecoded_as_latin1(self) -> None:
        self.assertEqual(get_item_filename(self._soup("cafÃ©.mp4")), "café.mp4")

    def test_normalizes_non_breaking_space(self) -> None:
        self.assertEqual(
            get_item_filename(self._soup("part\xa0three.mp4")),
            "part three.mp4",
        )

    def test_preserves_unicode_that_cannot_be_encoded_as_latin1(self) -> None:
        self.assertEqual(get_item_filename(self._soup("東京.mp4")), "東京.mp4")


if __name__ == "__main__":
    unittest.main()
