from __future__ import annotations

import hashlib
import io
import re
from difflib import unified_diff

from bs4 import BeautifulSoup
from pypdf import PdfReader


_WHITESPACE = re.compile(r"[ \t]+")
_BLANKS = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = _WHITESPACE.sub(" ", raw).strip()
        if line:
            lines.append(line)
    return _BLANKS.sub("\n\n", "\n".join(lines)).strip()


def html_to_text(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    return normalize_text(main.get_text("\n", strip=True))


def pdf_to_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return normalize_text("\n".join(parts))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def line_diff(old: str, new: str, max_chars: int = 24000) -> str:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    diff = "\n".join(
        unified_diff(old_lines, new_lines, fromfile="previous", tofile="current", lineterm="", n=2)
    )
    if len(diff) > max_chars:
        diff = diff[:max_chars] + "\n... [diff truncated by Veridex Alpha]"
    return diff
