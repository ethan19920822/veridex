from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..config import settings
from ..fetcher import Fetcher


@dataclass(slots=True)
class DiscoveredLink:
    url: str
    title: str


@dataclass(slots=True)
class SourceSpec:
    key: str
    name: str
    jurisdiction: str
    regulator: str
    index_url: str
    include_keywords: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = (
        "/about-us",
        "/contact",
        "/careers",
        "/privacy",
        "/accessibility",
        "/search",
        "/sitemap",
    )


class HtmlIndexAdapter:
    def __init__(self, spec: SourceSpec) -> None:
        self.spec = spec

    def _is_candidate(self, absolute_url: str, title: str) -> bool:
        if len(title.strip()) < 12:
            return False
        parsed_index = urlparse(self.spec.index_url)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != parsed_index.netloc:
            return False
        path = parsed.path.lower()
        if any(path.startswith(x.lower()) for x in self.spec.exclude_paths):
            return False
        if any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".zip", ".doc", ".docx", ".xlsx")):
            return False
        if self.spec.include_keywords:
            haystack = f"{path} {title}".lower()
            if not any(k.lower() in haystack for k in self.spec.include_keywords):
                return False
        return absolute_url.rstrip("/") != self.spec.index_url.rstrip("/")

    async def discover(self, fetcher: Fetcher) -> list[DiscoveredLink]:
        content, _, _ = await fetcher.get_bytes(self.spec.index_url)
        soup = BeautifulSoup(content, "html.parser")
        main = soup.find("main") or soup.body or soup
        found: list[DiscoveredLink] = []
        seen: set[str] = set()

        for anchor in main.select("a[href]"):
            title = " ".join(anchor.stripped_strings).strip()
            href = anchor.get("href", "").strip()
            if not href or href.startswith("#"):
                continue
            absolute = urljoin(self.spec.index_url, href).split("#")[0]
            if absolute in seen or not self._is_candidate(absolute, title):
                continue
            seen.add(absolute)
            found.append(DiscoveredLink(url=absolute, title=title[:500]))
            if len(found) >= settings.max_links_per_source:
                break
        return found
