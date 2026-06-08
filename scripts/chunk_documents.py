"""Load, clean, and chunk source documents for the unofficial guide.

The default chunk settings mirror planning.md:
- 200 words per chunk, roughly 150-250 tokens for this corpus.
- 35 words of overlap, roughly 30-50 tokens.

Output is JSON Lines so later embedding code can stream one chunk at a time.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_DOCUMENTS_DIR = Path("documents")
DEFAULT_RAW_OUTPUT_PATH = Path("data/raw_documents.jsonl")
DEFAULT_CLEAN_OUTPUT_PATH = Path("data/cleaned_documents.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/chunks.jsonl")
DEFAULT_CHUNK_WORDS = 200
DEFAULT_OVERLAP_WORDS = 35
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass(frozen=True)
class Document:
    source_name: str
    source_path: str
    raw_text: str
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_name: str
    source_path: str
    chunk_index: int
    word_count: int
    text: str


def load_pdf_text(path: Path) -> str:
    """Extract raw text from a PDF with page separators for source context."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "PDF support requires pdfplumber. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    page_texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            if text.strip():
                page_texts.append(f"[Page {page_number}]\n{text}")
    return "\n\n".join(page_texts)


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def clean_text(text: str) -> str:
    """Normalize common PDF/text extraction noise without erasing content."""
    text = html.unescape(text)
    text = text.replace("\x00", " ")
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", text)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = remove_reference_sections(text)
    text = remove_boilerplate_lines(text)
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(
        r"Downloaded from .+?(?=(\n|\[Page \d+\]|$))",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Frontiers in [A-Za-z ]+\s+\d+\s+frontiersin\.org\s+",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\[Page \d+\]\s+[A-Z][A-Za-z-]+(?: and [A-Z][A-Za-z-]+)?\s+"
        r"10\.\d{4,9}/[A-Za-z0-9./-]+\s*",
        lambda match: match.group(0).split("]")[0] + "] ",
        text,
    )
    text = re.sub(
        r"The authors have declared no conflicts of interest.+$",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def remove_reference_sections(text: str) -> str:
    """Remove bibliography sections, which are poor retrieval evidence."""
    headings = [
        r"\n\s*references\s*\n",
        r"\n\s*literature cited\s*\n",
        r"\n\s*bibliography\s*\n",
        r"\n\s*further reading\s*\n",
        r"\n\s*conflict of interest\s*\n",
        r"\n\s*related wires articles\s*\n",
    ]
    search_start = max(0, int(len(text) * 0.45))
    tail = text[search_start:]
    positions = [
        search_start + match.start()
        for heading in headings
        for match in re.finditer(heading, tail, flags=re.IGNORECASE)
    ]
    if not positions:
        return text
    return text[: min(positions)]


def remove_boilerplate_lines(text: str) -> str:
    """Drop repeated web/PDF boilerplate while keeping substantive article text."""
    boilerplate_patterns = [
        r"^\s*cookie(s)?\b",
        r"^\s*privacy policy\b",
        r"^\s*terms (of use|and conditions)\b",
        r"^\s*share (this|on)\b",
        r"^\s*read more\b",
        r"^\s*subscribe\b",
        r"^\s*advertisement\b",
        r"^\s*all rights reserved\b",
        r"^\s*copyright\b",
        r"^\s*downloaded from\b",
        r"^\s*how to cite this article\b",
        r"^\s*frontiers in\b.*\|\s*www\.frontiersin\.org\b",
        r"^\s*creative commons attribution license\b",
        r"^\s*conflict of interest\b",
        r"^\s*publisher.?s note\b",
    ]
    kept_lines: list[str] = []
    for line in text.splitlines():
        normalized = line.strip()
        if not normalized:
            kept_lines.append("")
            continue
        lowered = normalized.lower()
        if "terms and conditions" in lowered and "wiley online library" in lowered:
            continue
        if "downloaded from" in lowered and "online library" in lowered:
            continue
        if any(re.search(pattern, lowered) for pattern in boilerplate_patterns):
            continue
        kept_lines.append(normalized)
    return "\n".join(kept_lines)


def iter_document_paths(documents_dir: Path) -> Iterable[Path]:
    for path in sorted(documents_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def load_documents(documents_dir: Path) -> list[Document]:
    documents: list[Document] = []
    for path in iter_document_paths(documents_dir):
        if path.suffix.lower() == ".pdf":
            raw_text = load_pdf_text(path)
        else:
            raw_text = load_text_file(path)

        text = clean_text(raw_text)
        if not text:
            continue

        documents.append(
            Document(
                source_name=path.stem,
                source_path=str(path),
                raw_text=raw_text,
                text=text,
            )
        )
    return documents


def word_spans(text: str) -> list[tuple[int, int]]:
    return [match.span() for match in re.finditer(r"\S+", text)]


def chunk_text(
    text: str,
    *,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[str]:
    if chunk_words <= 0:
        raise ValueError("chunk_words must be greater than 0")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative")
    if overlap_words >= chunk_words:
        raise ValueError("overlap_words must be smaller than chunk_words")

    spans = word_spans(text)
    if not spans:
        return []

    chunks: list[str] = []
    start_word = 0
    step = chunk_words - overlap_words

    while start_word < len(spans):
        end_word = min(start_word + chunk_words, len(spans))
        start_char = spans[start_word][0]
        end_char = spans[end_word - 1][1]
        chunk = text[start_char:end_char].strip()
        if chunk:
            chunks.append(chunk)
        if end_word == len(spans):
            break
        start_word += step

    return chunks


def build_chunks(
    documents: Iterable[Document],
    *,
    chunk_words: int,
    overlap_words: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        document_chunks = chunk_text(
            document.text,
            chunk_words=chunk_words,
            overlap_words=overlap_words,
        )
        for chunk_index, text in enumerate(document_chunks):
            chunks.append(
                Chunk(
                    chunk_id=f"{Path(document.source_path).stem}-{chunk_index:04d}",
                    source_name=document.source_name,
                    source_path=document.source_path,
                    chunk_index=chunk_index,
                    word_count=len(word_spans(text)),
                    text=text,
                )
            )
    return chunks


def raw_document_record(document: Document) -> dict[str, str]:
    return {
        "source_name": document.source_name,
        "source_path": document.source_path,
        "raw_text": document.raw_text,
    }


def cleaned_document_record(document: Document) -> dict[str, str | int]:
    return {
        "source_name": document.source_name,
        "source_path": document.source_path,
        "word_count": len(word_spans(document.text)),
        "text": document.text,
    }


def write_jsonl(records: Iterable[object], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as output_file:
        for record in records:
            if hasattr(record, "__dataclass_fields__"):
                record = asdict(record)
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def print_excerpt(label: str, text: str, max_chars: int = 1200) -> None:
    divider = "=" * 80
    excerpt = text[:max_chars].strip()
    suffix = "\n..." if len(text) > max_chars else ""
    print(f"\n{divider}\n{label}\n{divider}\n{excerpt}{suffix}")


def print_representative_chunks(chunks: list[Chunk], sample_count: int = 5) -> None:
    if not chunks:
        return
    if len(chunks) <= sample_count:
        selected_indexes = list(range(len(chunks)))
    else:
        selected_indexes = [
            round(index * (len(chunks) - 1) / (sample_count - 1))
            for index in range(sample_count)
        ]

    for display_index, chunk_index in enumerate(selected_indexes, start=1):
        chunk = chunks[chunk_index]
        print_excerpt(
            f"Representative chunk {display_index}: "
            f"{chunk.chunk_id} ({chunk.word_count} words)",
            chunk.text,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load documents, clean extracted text, and write overlapping chunks."
    )
    parser.add_argument(
        "--documents-dir",
        type=Path,
        default=DEFAULT_DOCUMENTS_DIR,
        help="Folder containing source documents.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="JSONL output path for generated chunks.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=DEFAULT_RAW_OUTPUT_PATH,
        help="JSONL output path for raw extracted documents.",
    )
    parser.add_argument(
        "--clean-output",
        type=Path,
        default=DEFAULT_CLEAN_OUTPUT_PATH,
        help="JSONL output path for cleaned documents.",
    )
    parser.add_argument(
        "--chunk-words",
        type=int,
        default=DEFAULT_CHUNK_WORDS,
        help="Target words per chunk.",
    )
    parser.add_argument(
        "--overlap-words",
        type=int,
        default=DEFAULT_OVERLAP_WORDS,
        help="Words repeated between adjacent chunks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    documents = load_documents(args.documents_dir)
    raw_count = write_jsonl(
        (raw_document_record(document) for document in documents),
        args.raw_output,
    )
    clean_count = write_jsonl(
        (cleaned_document_record(document) for document in documents),
        args.clean_output,
    )
    chunks = build_chunks(
        documents,
        chunk_words=args.chunk_words,
        overlap_words=args.overlap_words,
    )
    count = write_jsonl(chunks, args.output)
    print(
        f"Loaded {len(documents)} document(s). Wrote {raw_count} raw document(s) "
        f"to {args.raw_output}, {clean_count} cleaned document(s) to "
        f"{args.clean_output}, and {count} chunk(s) to {args.output}."
    )
    if documents:
        print_excerpt(
            f"Cleaned document sample: {documents[0].source_name}",
            documents[0].text,
        )
    print_representative_chunks(chunks)


if __name__ == "__main__":
    main()
