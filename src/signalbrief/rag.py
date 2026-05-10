from __future__ import annotations

import math
import re
from collections import Counter

from signalbrief.models import EvidenceSnippet, SourceDocument

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def chunk_document(source: SourceDocument, max_chars: int = 420) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", source.content.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks


class EvidenceIndex:
    """A tiny TF-IDF retrieval layer so RAG works without heavyweight services."""

    def __init__(self, sources: list[SourceDocument]) -> None:
        self.records: list[tuple[SourceDocument, str, Counter[str]]] = []
        document_frequency: Counter[str] = Counter()
        for source in sources:
            for chunk in chunk_document(source):
                vector = Counter(tokenize(chunk))
                if not vector:
                    continue
                self.records.append((source, chunk, vector))
                document_frequency.update(vector.keys())

        self.idf = {
            term: math.log((1 + len(self.records)) / (1 + freq)) + 1
            for term, freq in document_frequency.items()
        }

    def search(self, query: str, k: int = 5) -> list[EvidenceSnippet]:
        query_vector = Counter(tokenize(query))
        if not query_vector or not self.records:
            return []

        scored: list[tuple[float, SourceDocument, str]] = []
        for source, chunk, vector in self.records:
            score = self._cosine(query_vector, vector) * source.credibility
            if score > 0:
                scored.append((score, source, chunk))

        scored.sort(key=lambda row: row[0], reverse=True)
        return [
            EvidenceSnippet(
                source_title=source.title,
                source_url=source.url,
                quote=chunk,
                relevance=min(1.0, score),
            )
            for score, source, chunk in scored[:k]
        ]

    def _cosine(self, left: Counter[str], right: Counter[str]) -> float:
        terms = set(left) | set(right)
        dot = 0.0
        left_norm = 0.0
        right_norm = 0.0
        for term in terms:
            weight = self.idf.get(term, 1.0)
            l_value = left.get(term, 0) * weight
            r_value = right.get(term, 0) * weight
            dot += l_value * r_value
            left_norm += l_value**2
            right_norm += r_value**2
        if not left_norm or not right_norm:
            return 0.0
        return dot / math.sqrt(left_norm * right_norm)

