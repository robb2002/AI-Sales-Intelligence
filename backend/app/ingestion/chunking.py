"""Character chunking for Advisor indexing (AI_RAG_DESIGN.md §14).

Matches the approved sizes: ~1200 characters with ~150 overlap. A document shorter
than chunk_size is one chunk. Uses the same separator preference as LangChain's
RecursiveCharacterTextSplitter without requiring that package at runtime.
"""

from __future__ import annotations


def split_text(
    text: str,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    separators = ["\n\n", "\n", ". ", " ", ""]
    return _split_recursive(cleaned, separators, chunk_size, chunk_overlap)


def _split_recursive(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text else []

    separator = separators[0] if separators else ""
    next_seps = separators[1:] if len(separators) > 1 else [""]

    if separator == "":
        return _window_chunks(text, chunk_size, chunk_overlap)

    parts = text.split(separator)
    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = part if not current else current + separator + part
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.extend(_split_recursive(current, next_seps, chunk_size, chunk_overlap))
        if len(part) > chunk_size:
            chunks.extend(_split_recursive(part, next_seps, chunk_size, chunk_overlap))
            current = ""
        else:
            current = part
    if current:
        chunks.extend(_split_recursive(current, next_seps, chunk_size, chunk_overlap))
    return _merge_with_overlap(chunks, chunk_size, chunk_overlap)


def _window_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    step = max(1, chunk_size - chunk_overlap)
    out: list[str] = []
    start = 0
    while start < len(text):
        out.append(text[start : start + chunk_size])
        if start + chunk_size >= len(text):
            break
        start += step
    return out


def _merge_with_overlap(
    pieces: list[str], chunk_size: int, chunk_overlap: int
) -> list[str]:
    if not pieces:
        return []
    merged: list[str] = []
    buf = pieces[0]
    for piece in pieces[1:]:
        if len(buf) + 1 + len(piece) <= chunk_size:
            buf = f"{buf} {piece}".strip() if not buf.endswith(("\n", " ")) else buf + piece
        else:
            merged.append(buf)
            if chunk_overlap > 0 and len(buf) > chunk_overlap:
                overlap = buf[-chunk_overlap:]
                buf = f"{overlap}{piece}".strip()
                if len(buf) > chunk_size:
                    buf = piece
            else:
                buf = piece
    if buf:
        merged.append(buf)
    return merged
