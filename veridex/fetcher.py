from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import settings
from .text import html_to_text, pdf_to_text


@dataclass(slots=True)
class FetchedDocument:
    url: str
    title: str
    text: str
    content_type: str


class Fetcher:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=settings.http_timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": settings.veridex_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def get_bytes(self, url: str) -> tuple[bytes, str, str]:
        response = await self.client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        return response.content, content_type, str(response.url)

    async def fetch_document(self, url: str, title: str = "") -> FetchedDocument:
        content, ctype, final_url = await self.get_bytes(url)
        is_pdf = "application/pdf" in ctype or final_url.lower().split("?")[0].endswith(".pdf")
        text = pdf_to_text(content) if is_pdf else html_to_text(content)
        return FetchedDocument(url=final_url, title=title or final_url, text=text, content_type=ctype)
