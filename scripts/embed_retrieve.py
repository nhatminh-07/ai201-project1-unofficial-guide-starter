"""Embed document chunks into ChromaDB and retrieve relevant passages.

This is the embedding + retrieval stage from planning.md:
chunks.jsonl -> all-MiniLM-L6-v2 embeddings -> ChromaDB -> top-k retrieval.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# SentenceTransformers does not need TensorFlow here. These flags prevent
# transformers from importing a locally broken TensorFlow/protobuf stack.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer


DEFAULT_CHUNKS_PATH = Path("data/chunks.jsonl")
DEFAULT_CHROMA_PATH = Path("chroma_db")
DEFAULT_COLLECTION_NAME = "unofficial_guide_chunks"
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 5
DEFAULT_BATCH_SIZE = 64


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_name: str
    source_path: str
    chunk_index: int
    word_count: int
    text: str

    @classmethod
    def from_json(cls, record: dict[str, Any]) -> "ChunkRecord":
        return cls(
            chunk_id=str(record["chunk_id"]),
            source_name=str(record["source_name"]),
            source_path=str(record["source_path"]),
            chunk_index=int(record["chunk_index"]),
            word_count=int(record["word_count"]),
            text=str(record["text"]),
        )

    def metadata(self) -> dict[str, str | int]:
        return {
            "source_name": self.source_name,
            "source_path": self.source_path,
            "chunk_index": self.chunk_index,
            "word_count": self.word_count,
        }


def load_chunks(chunks_path: Path) -> list[ChunkRecord]:
    if not chunks_path.exists():
        raise FileNotFoundError(
            f"Missing {chunks_path}. Run `python scripts/chunk_documents.py` first."
        )

    chunks: list[ChunkRecord] = []
    with chunks_path.open("r", encoding="utf-8") as chunks_file:
        for line_number, line in enumerate(chunks_file, start=1):
            if not line.strip():
                continue
            try:
                chunks.append(ChunkRecord.from_json(json.loads(line)))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"Invalid chunk record in {chunks_path} on line {line_number}."
                ) from exc
    return chunks


def batched(records: list[ChunkRecord], batch_size: int) -> Iterable[list[ChunkRecord]]:
    for start in range(0, len(records), batch_size):
        yield records[start : start + batch_size]


def load_embedding_model(model_name: str = DEFAULT_MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def get_collection(
    chroma_path: Path = DEFAULT_CHROMA_PATH,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Collection:
    client = chromadb.PersistentClient(path=str(chroma_path))
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def index_chunks(
    chunks: list[ChunkRecord],
    *,
    collection: Collection,
    model: SentenceTransformer,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """Embed chunks and upsert them into ChromaDB with attribution metadata."""
    indexed = 0
    for batch in batched(chunks, batch_size):
        texts = [chunk.text for chunk in batch]
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        collection.upsert(
            ids=[chunk.chunk_id for chunk in batch],
            documents=texts,
            metadatas=[chunk.metadata() for chunk in batch],
            embeddings=embeddings.tolist(),
        )
        indexed += len(batch)
    return indexed


def retrieve(
    query: str,
    *,
    collection: Collection,
    model: SentenceTransformer,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Return top-k relevant chunks with source metadata and cosine distance."""
    if not query.strip():
        raise ValueError("query cannot be empty")

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: list[dict[str, Any]] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for chunk_id, document, metadata, distance in zip(
        ids,
        documents,
        metadatas,
        distances,
    ):
        retrieved.append(
            {
                "chunk_id": chunk_id,
                "source_name": metadata["source_name"],
                "source_path": metadata["source_path"],
                "chunk_index": metadata["chunk_index"],
                "word_count": metadata["word_count"],
                "distance": distance,
                "text": document,
            }
        )
    return retrieved


def print_results(results: list[dict[str, Any]]) -> None:
    for rank, result in enumerate(results, start=1):
        print("=" * 80)
        print(
            f"Rank {rank} | {result['source_name']} | "
            f"chunk {result['chunk_index']} | distance {result['distance']:.4f}"
        )
        print("=" * 80)
        print(result["text"][:1200].strip())
        if len(result["text"]) > 1200:
            print("...")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embed chunks into ChromaDB and retrieve relevant passages."
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=DEFAULT_CHUNKS_PATH,
        help="Path to chunks JSONL from scripts/chunk_documents.py.",
    )
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=DEFAULT_CHROMA_PATH,
        help="Persistent ChromaDB storage directory.",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION_NAME,
        help="ChromaDB collection name.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help="SentenceTransformer embedding model name.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of chunks to embed per batch.",
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Embed all chunks and upsert them into ChromaDB.",
    )
    parser.add_argument(
        "--query",
        help="Optional query to retrieve after loading the model/collection.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Number of chunks to retrieve.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_embedding_model(args.model)
    collection = get_collection(args.chroma_path, args.collection)

    if args.build_index:
        chunks = load_chunks(args.chunks)
        indexed = index_chunks(
            chunks,
            collection=collection,
            model=model,
            batch_size=args.batch_size,
        )
        print(
            f"Indexed {indexed} chunk(s) into Chroma collection "
            f"`{args.collection}` at {args.chroma_path}."
        )

    if args.query:
        results = retrieve(
            args.query,
            collection=collection,
            model=model,
            top_k=args.top_k,
        )
        print_results(results)

    if not args.build_index and not args.query:
        print("Nothing to do. Use --build-index, --query, or both.")


if __name__ == "__main__":
    main()
