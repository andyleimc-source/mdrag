"""Eval regression test: protect retrieval quality on the shipped sample vault.

Unlike the full eval harness (which needs the real multilingual model and a 408-doc
corpus), this test runs on the repo's 3-doc sample vault using BM25 only — that's
deterministic, fast, and catches any regression in the retrieval plumbing.

The full eval suite at `tests/eval-queries.yaml` is for manual validation against
the author's dev vault; this test is what CI runs on every PR.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mdrag.indexer import build_index
from mdrag.retrieval import BM25_FILENAME, BM25Store, bm25_search_docs, hybrid_search_docs


REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_VAULT = REPO_ROOT / "examples" / "sample-vault"


class _FakeModel:
    """Deterministic hash-based embedding so hybrid mode runs without downloading a model."""

    def __init__(self, dim: int = 64):
        self.dim = dim

    def encode(self, inputs, show_progress_bar=False):
        if isinstance(inputs, str):
            inputs = [inputs]
        out = np.zeros((len(inputs), self.dim), dtype=float)
        for i, text in enumerate(inputs):
            for tok in str(text).lower().split():
                h = hash(tok) % self.dim
                out[i, h] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return out / norms


@pytest.fixture
def sample_index(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("mdrag.indexer.SentenceTransformer", lambda name: _FakeModel())
    vec = tmp_path / ".mdrag"
    build_index(SAMPLE_VAULT, vec, "fake-test-model", full_rebuild=True)
    import lancedb
    table = lancedb.connect(str(vec)).open_table("docs")
    bm25 = BM25Store.load(vec / BM25_FILENAME)
    return table, bm25


# ---- Query → expected top match fixtures ----
# Kept tiny because sample-vault is tiny; the goal is to detect plumbing regressions,
# not to measure retrieval quality on real data.

EXPECTED_TOP = {
    "产品周会 OKR":     "notes/meeting-2026-01-15.md",
    "竞品 Notion":       "research/competitor-analysis.md",
    "Obsidian 插件":     "research/competitor-analysis.md",
    "mdrag 是什么":      "welcome.md",
}


def test_bm25_finds_expected_docs(sample_index):
    _, bm25 = sample_index
    for query, expected in EXPECTED_TOP.items():
        hits = bm25_search_docs(bm25, query, fetch=5)
        paths = [h["doc_path"] for h in hits]
        assert expected in paths[:3], (
            f"BM25 regression on '{query}': expected {expected} in top-3, got {paths}"
        )


def test_hybrid_finds_expected_docs(sample_index):
    table, bm25 = sample_index
    model = _FakeModel()
    for query, expected in EXPECTED_TOP.items():
        hits = hybrid_search_docs(table, bm25, model, query, fetch=10)
        paths = [h["doc_path"] for h in hits]
        assert expected in paths[:3], (
            f"Hybrid regression on '{query}': expected {expected} in top-3, got {paths}"
        )


def test_hybrid_returns_ranked_rows(sample_index):
    """Sanity: hybrid output must carry _rrf scores and doc_path keys."""
    table, bm25 = sample_index
    model = _FakeModel()
    hits = hybrid_search_docs(table, bm25, model, "meeting", fetch=5)
    assert hits, "hybrid returned no results for a query with matches"
    assert "_rrf" in hits[0] and "doc_path" in hits[0]
    assert "_match_reason" in hits[0]
    assert hits[0]["_match_reason"] in (
        "vector+bm25", "bm25 only", "bm25 (rare-term)", "vector only", "unknown"
    )
