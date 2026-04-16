"""Shared retrieval: vector, BM25, and hybrid (RRF-fused) search."""

from __future__ import annotations

import math
import pickle
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

BM25_FILENAME = "bm25.pkl"
RRF_K = 60

_TOKEN_RE = re.compile(r"[a-zA-Z]+|[0-9]+|[\u4e00-\u9fff]")

# Rare-term detection: query contains digits or rare CJK numeric patterns
_RARE_TERM_RE = re.compile(r"\d+|[一二三四五六七八九十百千万亿]{2,}")

# Simple synonym/expansion map for comparison queries
_EXPANSION_MAP = {
    "区别": "区别 difference vs comparison 对比",
    "对比": "对比 comparison difference vs 区别",
    "比较": "比较 compare vs difference 区别",
    "difference": "difference 区别 对比 comparison",
    "compare": "compare comparison 区别 对比",
    "vs": "vs versus 区别 对比",
}


def _has_rare_terms(query: str) -> bool:
    """Return True if query contains digit strings or multi-char CJK numerals."""
    return bool(_RARE_TERM_RE.search(query))


def _expand_query(query: str) -> str:
    """Append synonyms for comparison/difference keywords found in the query."""
    expanded = query
    lower = query.lower()
    for kw, expansion in _EXPANSION_MAP.items():
        if kw in lower and expansion not in expanded:
            expanded = expanded + " " + expansion
    return expanded


def tokenize(text: str) -> list[str]:
    """Word-level for latin/digits, char-level for CJK."""
    return _TOKEN_RE.findall(text.lower())


class BM25:
    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.N = len(corpus)
        self.doc_lens = [len(d) for d in corpus]
        self.avgdl = sum(self.doc_lens) / self.N if self.N else 0.0
        self.freqs = [Counter(d) for d in corpus]
        df: Counter[str] = Counter()
        for freq in self.freqs:
            for term in freq:
                df[term] += 1
        self.idf = {
            term: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for term, n in df.items()
        }
        self.inverted: dict[str, list[int]] = defaultdict(list)
        for i, freq in enumerate(self.freqs):
            for term in freq:
                self.inverted[term].append(i)

    def _score(self, query_tokens: list[str], idx: int) -> float:
        score = 0.0
        freq = self.freqs[idx]
        dl = self.doc_lens[idx]
        for q in query_tokens:
            idf = self.idf.get(q)
            if idf is None:
                continue
            tf = freq.get(q, 0)
            if tf == 0:
                continue
            num = idf * tf * (self.k1 + 1)
            den = tf + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            score += num / den
        return score

    def top_k(self, query_tokens: list[str], k: int) -> list[tuple[int, float]]:
        candidates: set[int] = set()
        for q in query_tokens:
            candidates.update(self.inverted.get(q, ()))
        if not candidates:
            return []
        scored = [(i, self._score(query_tokens, i)) for i in candidates]
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


@dataclass
class BM25Store:
    bm25: BM25
    chunks: list[dict]

    @classmethod
    def build(cls, chunks: list[dict]) -> "BM25Store":
        corpus = []
        for c in chunks:
            text = " ".join([
                str(c.get("title", "")),
                str(c.get("heading_path", "")),
                str(c.get("chunk_text", "")),
            ])
            corpus.append(tokenize(text))
        return cls(bm25=BM25(corpus), chunks=chunks)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path) -> "BM25Store":
        with open(path, "rb") as f:
            return pickle.load(f)

    def search(self, query: str, k: int) -> list[tuple[dict, float]]:
        tokens = tokenize(query)
        hits = self.bm25.top_k(tokens, k)
        return [(self.chunks[i], score) for i, score in hits]


def rrf_fuse(rank_lists: list[list], k: int = RRF_K) -> list[tuple]:
    """Reciprocal Rank Fusion. Each rank_list is a sequence of keys in rank order."""
    scores: dict = {}
    for rl in rank_lists:
        for rank, key in enumerate(rl, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def best_rank_fuse(rank_lists: list[list], agreement_bonus: int = 1) -> list[tuple]:
    """Fuse by best rank either list achieves for each item; agreement between lists bumps up.

    Docs ranked high in at least one list win, even if absent from the other.
    Docs present in multiple lists get their rank reduced by `agreement_bonus`.
    """
    best: dict = {}
    appearances: dict = {}
    for rl in rank_lists:
        seen = set()
        for rank, key in enumerate(rl, start=1):
            if key in seen:
                continue
            seen.add(key)
            if key not in best or rank < best[key]:
                best[key] = rank
            appearances[key] = appearances.get(key, 0) + 1
    final = {k: best[k] - (appearances[k] - 1) * agreement_bonus for k in best}
    return sorted(final.items(), key=lambda x: x[1])


def vector_search_chunks(table, query_vec: list[float], fetch: int) -> list[dict]:
    return table.search(query_vec).limit(fetch).to_list()


def _dedupe_chunks_to_doc_ranking(
    rows: list[dict],
    score_key: str,
    higher_is_better: bool = False,
) -> list[dict]:
    """Pick the best-scoring chunk per doc.

    Overview chunks (chunk_id == 0) act as a tiebreaker: when two chunks have
    identical scores, prefer the overview so broad conceptual queries surface the
    doc-level signal over a specific sub-section.
    """
    best: dict[str, dict] = {}
    for r in rows:
        dp = r.get("doc_path")
        if dp is None:
            continue
        cur = best.get(dp)
        if cur is None:
            best[dp] = r
            continue
        cur_score = cur.get(score_key, 0 if higher_is_better else float("inf"))
        new_score = r.get(score_key, 0 if higher_is_better else float("inf"))
        strictly_better = (
            (higher_is_better and new_score > cur_score)
            or (not higher_is_better and new_score < cur_score)
        )
        # On a tie, prefer overview chunk (chunk_id == 0) for broad coverage
        tied = cur_score == new_score
        overview_wins = tied and r.get("chunk_id", -1) == 0 and cur.get("chunk_id", -1) != 0
        if strictly_better or overview_wins:
            best[dp] = r
    return sorted(
        best.values(),
        key=lambda r: -r.get(score_key, 0) if higher_is_better else r.get(score_key, float("inf")),
    )


def hybrid_search_docs(
    table,
    bm25_store: BM25Store | None,
    model,
    query: str,
    fetch: int,
) -> list[dict]:
    """Return doc-level ranked rows (best chunk per doc), fused by best-rank of vector + BM25.

    Two query-adaptive behaviours:
    - Comparison queries (containing "区别"/"compare"/etc.) have their vector query
      expanded with synonyms so the embedding captures both languages.
    - Rare-term queries (containing digit strings) double the BM25 rank list in the
      fusion input, giving BM25 stronger pull for exact-match lookups.
    """
    expanded_query = _expand_query(query)
    query_vec = model.encode(expanded_query).tolist()
    vec_hits = vector_search_chunks(table, query_vec, fetch)
    vec_docs = _dedupe_chunks_to_doc_ranking(vec_hits, "_distance", higher_is_better=False)

    if bm25_store is None:
        return vec_docs

    bm25_hits = bm25_store.search(query, fetch)
    bm25_rows = [dict(c, _bm25=s) for c, s in bm25_hits]
    bm25_docs = _dedupe_chunks_to_doc_ranking(bm25_rows, "_bm25", higher_is_better=True)

    vec_keys = [r["doc_path"] for r in vec_docs]
    bm25_keys = [r["doc_path"] for r in bm25_docs]
    vec_set = set(vec_keys)
    bm25_set = set(bm25_keys)

    row_index: dict[str, dict] = {}
    for r in vec_docs:
        row_index[r["doc_path"]] = r
    for r in bm25_docs:
        row_index.setdefault(r["doc_path"], dict(r))

    rare_term_mode = _has_rare_terms(query)
    if rare_term_mode:
        # Rare-term queries (e.g. "38 种字段"): vector often has zero signal for the exact doc.
        # Strategy: fuse only the docs that both sides agree on (shared), then inject BM25-only
        # docs at their BM25 rank position so exact-match results aren't buried.
        shared_bm25 = [k for k in bm25_keys if k in vec_set]
        fused_shared = best_rank_fuse([vec_keys, shared_bm25, shared_bm25])
        bm25_only = [(k, i + 1) for i, k in enumerate(bm25_keys) if k not in vec_set]
        result: list[tuple] = list(fused_shared)
        for doc, bm25_pos in bm25_only:
            insert_at = min(bm25_pos - 1, len(result))
            result.insert(insert_at, (doc, bm25_pos))
        fused = result
    else:
        fused = best_rank_fuse([vec_keys, bm25_keys])

    out = []
    for doc_path, fused_rank in fused:
        row = dict(row_index[doc_path])
        row["_rrf"] = 1.0 / fused_rank if fused_rank > 0 else 0
        row["_match_reason"] = _match_reason(doc_path, vec_set, bm25_set, rare_term_mode)
        out.append(row)
    return out


def _match_reason(doc_path: str, vec_set: set, bm25_set: set, rare_term_mode: bool) -> str:
    """Explain why a doc ended up in the hybrid result, in client-readable form."""
    in_vec = doc_path in vec_set
    in_bm25 = doc_path in bm25_set
    if in_vec and in_bm25:
        return "vector+bm25"
    if in_bm25 and rare_term_mode:
        return "bm25 (rare-term)"
    if in_bm25:
        return "bm25 only"
    if in_vec:
        return "vector only"
    return "unknown"


def vector_search_docs(table, query_vec: list[float], fetch: int) -> list[dict]:
    rows = vector_search_chunks(table, query_vec, fetch)
    return _dedupe_chunks_to_doc_ranking(rows, "_distance", higher_is_better=False)


def bm25_search_docs(bm25_store: BM25Store, query: str, fetch: int) -> list[dict]:
    hits = bm25_store.search(query, fetch)
    rows = [dict(c, _bm25=s) for c, s in hits]
    return _dedupe_chunks_to_doc_ranking(rows, "_bm25", higher_is_better=True)
