from collections.abc import Sequence

from backend.services.pdf_processor import ExtractedPage


DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 150


def chunk_pages(
    pages: Sequence[ExtractedPage],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, int | str]]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than zero.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size.")

    chunks: list[dict[str, int | str]] = []
    seen_chunks_by_page: dict[int, set[str]] = {}
    step = chunk_size - chunk_overlap

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]
        if not isinstance(page_number, int) or not isinstance(text, str):
            raise ValueError("Each page must include an integer page_number and string text.")
        if not text.strip():
            continue

        seen_chunks = seen_chunks_by_page.setdefault(page_number, set())
        start = 0
        while start < len(text):
            chunk_text = text[start : start + chunk_size].strip()
            if chunk_text and chunk_text not in seen_chunks:
                chunks.append(
                    {
                        "chunk_index": len(chunks),
                        "page_number": page_number,
                        "text": chunk_text,
                    }
                )
                seen_chunks.add(chunk_text)

            if start + chunk_size >= len(text):
                break
            start += step

    return chunks
