"""Recursive text chunker with overlap."""


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by character count.

    Uses paragraph → sentence → word boundaries for clean splits.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    if len(text) <= chunk_size:
        return [text]

    # Try splitting by paragraphs first
    separators = ["\n\n", "\n", ". ", " "]
    return _recursive_split(text, separators, chunk_size, overlap)


def _recursive_split(
    text: str, separators: list[str], chunk_size: int, overlap: int
) -> list[str]:
    """Recursively split text using progressively finer separators."""
    chunks = []
    current_sep = separators[0] if separators else ""

    if not current_sep or current_sep not in text:
        # Fall back to hard character split
        if not separators:
            return _hard_split(text, chunk_size, overlap)
        return _recursive_split(text, separators[1:], chunk_size, overlap)

    parts = text.split(current_sep)
    current_chunk = ""

    for part in parts:
        candidate = (current_chunk + current_sep + part).strip() if current_chunk else part.strip()

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If single part exceeds chunk_size, split it further
            if len(part.strip()) > chunk_size and len(separators) > 1:
                sub_chunks = _recursive_split(part.strip(), separators[1:], chunk_size, overlap)
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = part.strip()

    if current_chunk:
        chunks.append(current_chunk)

    # Add overlap between chunks
    if overlap > 0 and len(chunks) > 1:
        chunks = _add_overlap(chunks, overlap)

    return [c for c in chunks if c.strip()]


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Hard character split as last resort."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c.strip()]


def _add_overlap(chunks: list[str], overlap: int) -> list[str]:
    """Add overlap from previous chunk's tail to next chunk's head."""
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
        result.append(prev_tail + " " + chunks[i])
    return result
