"""Markdown chunking: split documents into semantically coherent pieces."""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 600
OVERLAP = 80
MIN_SPLIT_CHARS = 400
MAX_CHUNKS_PER_DOC = 30

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class Chunk:
    chunk_id: int
    heading_path: str
    text: str
    char_offset: int


def _split_sections(body: str) -> list[tuple[str, str]]:
    lines = body.splitlines()
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    current_path = ""

    def flush():
        text = "\n".join(buf).strip()
        if text:
            sections.append((current_path, text))

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            flush()
            buf.clear()
            level = len(m.group(1))
            heading = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
            current_path = " › ".join(h for _, h in stack)
        else:
            buf.append(line)
    flush()

    if not sections:
        body_clean = body.strip()
        return [("", body_clean)] if body_clean else []

    return sections


def _window_split(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    step = max_chars - overlap
    out = []
    i = 0
    while i < len(text):
        piece = text[i:i + max_chars]
        if not piece.strip():
            break
        out.append(piece)
        if i + max_chars >= len(text):
            break
        i += step
    return out


def split_markdown(
    body: str,
    max_chars: int = MAX_CHARS,
    overlap: int = OVERLAP,
    min_split_chars: int = MIN_SPLIT_CHARS,
) -> list[Chunk]:
    body = body.strip()
    if not body:
        return []

    if len(body) < min_split_chars:
        return [Chunk(chunk_id=0, heading_path="", text=body, char_offset=0)]

    sections = _split_sections(body)
    raw: list[tuple[str, str]] = []
    for heading_path, section_text in sections:
        for piece in _window_split(section_text, max_chars, overlap):
            raw.append((heading_path, piece))

    if not raw:
        return [Chunk(chunk_id=0, heading_path="", text=body, char_offset=0)]

    if len(raw) > MAX_CHUNKS_PER_DOC:
        step = len(raw) / MAX_CHUNKS_PER_DOC
        raw = [raw[int(i * step)] for i in range(MAX_CHUNKS_PER_DOC)]

    chunks: list[Chunk] = []
    cursor = 0
    for i, (hp, piece) in enumerate(raw):
        chunks.append(Chunk(chunk_id=i, heading_path=hp, text=piece, char_offset=cursor))
        cursor += len(piece)
    return chunks
