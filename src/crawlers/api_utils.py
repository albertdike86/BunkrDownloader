"""Resolve current Bunkr media pages to signed download URLs."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

import requests

from src.config import BUNKR_API, DOWNLOAD_API, HEADERS

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


JS_VARIABLE = re.compile(r"var\s+(\w+)\s*=\s*(\".*?\"|'.*?'|[^;]+);", re.DOTALL)


def _extract_page_vars(soup: BeautifulSoup) -> dict[str, str]:
    """Extract CDN variables embedded in a media page."""
    for script in soup.find_all("script"):
        if script.string and "var jsCDN" in script.string:
            return {
                key: value.strip("'\"").replace(r"\/", "/")
                for key, value in JS_VARIABLE.findall(script.string)
            }
    return {}


def _extract_file_id(soup: BeautifulSoup) -> str | None:
    script = soup.find("script", attrs={"data-file-id": True})
    return script.get("data-file-id") if script else None


def get_api_response(item_url: str, soup: BeautifulSoup | None = None) -> str | None:
    """Resolve a media page and return its signed download URL."""
    if soup is None:
        return None

    page_vars = _extract_page_vars(soup)
    cdn_url = page_vars.get("jsCDN")

    try:
        with requests.Session() as session:
            session.headers.update(HEADERS)
            unsigned_url = None

            if not cdn_url:
                file_id = _extract_file_id(soup)
                if file_id:
                    response = session.post(
                        DOWNLOAD_API,
                        json={"id": file_id},
                        headers={"Accept-Encoding": "gzip, deflate"},
                        timeout=20,
                    )
                    response.raise_for_status()
                    data = response.json()
                    base_url, path = data.get("mediafiles"), data.get("path")
                    if base_url and path:
                        parsed = urlparse(base_url)
                        unsigned_url = urlunparse(parsed._replace(path=path))

            base_url = cdn_url or unsigned_url
            if not base_url:
                logging.warning("Could not resolve a media URL for %s", item_url)
                return None

            response = session.get(
                BUNKR_API,
                params={"path": urlparse(base_url).path},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

    except (requests.RequestException, ValueError) as req_err:
        logging.warning("Error resolving media URL for %s: %s", item_url, req_err)
        return None

    token, expires_at = data.get("token"), data.get("ex")
    if token and expires_at:
        return f"{base_url}?token={token}&ex={expires_at}"
    return base_url
