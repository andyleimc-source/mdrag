"""Stability regression tests for S1-S4 (watcher errors, locking, schema, BM25 drift)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from mdrag.indexer import (
    META_FILENAME,
    SCHEMA_VERSION,
    SchemaMismatchError,
    build_index,
    read_meta,
    write_meta,
)
from mdrag.retrieval import BM25_FILENAME, BM25Store


def _write_vault(root: Path, files: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


# ---------------------------- S3: schema version ----------------------------

def test_meta_roundtrip(tmp_path: Path):
    write_meta(tmp_path, "some-model")
    meta = read_meta(tmp_path)
    assert meta["schema_version"] == SCHEMA_VERSION
    assert meta["model"] == "some-model"


def test_meta_missing_returns_empty(tmp_path: Path):
    assert read_meta(tmp_path) == {}


def test_meta_corrupt_returns_empty(tmp_path: Path):
    (tmp_path / META_FILENAME).write_text("not json {{{")
    assert read_meta(tmp_path) == {}


def test_schema_mismatch_raises(tmp_path: Path):
    """If meta.json says schema v99 but code is v2, we must refuse to open."""
    vault = tmp_path / "v"
    vec = tmp_path / "vec"
    _write_vault(vault, {"a.md": "# hi\nbody"})
    vec.mkdir()
    (vec / META_FILENAME).write_text(
        json.dumps({"schema_version": 99, "model": "paraphrase-multilingual-MiniLM-L12-v2"})
    )
    import lancedb
    db = lancedb.connect(str(vec))
    db.create_table(
        "docs",
        [{"doc_path": "a.md", "chunk_id": 0, "chunk_text": "x", "vector": [0.0] * 8}],
    )
    with pytest.raises(SchemaMismatchError, match="schema v99"):
        build_index(vault, vec, "paraphrase-multilingual-MiniLM-L12-v2", full_rebuild=False)


def test_model_mismatch_raises(tmp_path: Path):
    """Switching embedding model on an existing index must refuse incremental."""
    vault = tmp_path / "v"
    vec = tmp_path / "vec"
    _write_vault(vault, {"a.md": "# hi"})
    vec.mkdir()
    (vec / META_FILENAME).write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "model": "model-A"})
    )
    import lancedb
    db = lancedb.connect(str(vec))
    db.create_table(
        "docs",
        [{"doc_path": "a.md", "chunk_id": 0, "chunk_text": "x", "vector": [0.0] * 8}],
    )
    with pytest.raises(SchemaMismatchError, match="model-A"):
        build_index(vault, vec, "model-B", full_rebuild=False)


# ---------------------------- S2: file locking ----------------------------

def test_concurrent_reindex_serialized(tmp_path: Path, monkeypatch):
    """Two threads calling build_index on the same vector_dir must not overlap."""
    vault = tmp_path / "v"
    vec = tmp_path / "vec"
    _write_vault(vault, {"a.md": "# hi\nbody " * 20})

    in_progress = {"count": 0, "max": 0}
    counter_lock = threading.Lock()

    def fake_locked(*args, **kwargs):
        with counter_lock:
            in_progress["count"] += 1
            in_progress["max"] = max(in_progress["max"], in_progress["count"])
        import time as _t
        _t.sleep(0.2)
        with counter_lock:
            in_progress["count"] -= 1

        class S:
            total_docs = 0
            total_chunks = 0
            updated_docs = 0
            ignored_docs = 0
            elapsed_seconds = 0.2
        return S()

    monkeypatch.setattr("mdrag.indexer._build_index_locked", fake_locked)

    def run():
        build_index(vault, vec, "irrelevant", full_rebuild=True)

    t1 = threading.Thread(target=run)
    t2 = threading.Thread(target=run)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert in_progress["max"] == 1, "file lock failed to serialize concurrent reindexes"


# ---------------------------- S4: BM25 delete-only drift ----------------------------

def test_bm25_rebuilt_after_delete_only_reindex(tmp_path: Path, monkeypatch):
    """Deleting a file and reindexing (no new docs) must drop it from BM25 too."""
    class FakeModel:
        def encode(self, inputs, show_progress_bar=False):
            import numpy as np
            if isinstance(inputs, str):
                inputs = [inputs]
            return np.zeros((len(inputs), 8), dtype=float)

    monkeypatch.setattr("mdrag.indexer.SentenceTransformer", lambda name: FakeModel())

    vault = tmp_path / "v"
    vec = tmp_path / "vec"
    _write_vault(vault, {
        "keep.md": "# keep\nkept content about cats",
        "gone.md": "# gone\nsecret rabbit content",
    })

    build_index(vault, vec, "fake", full_rebuild=True)

    bm25_before = BM25Store.load(vec / BM25_FILENAME)
    paths_before = {c["doc_path"] for c in bm25_before.chunks}
    assert paths_before == {"keep.md", "gone.md"}

    (vault / "gone.md").unlink()
    build_index(vault, vec, "fake", full_rebuild=False)

    bm25_after = BM25Store.load(vec / BM25_FILENAME)
    paths_after = {c["doc_path"] for c in bm25_after.chunks}
    assert paths_after == {"keep.md"}, (
        f"BM25 still references deleted doc: {paths_after}"
    )


# ---------------------------- S1: watcher error tracking ----------------------------

def test_watcher_records_consecutive_errors(tmp_path: Path, monkeypatch):
    """When build_index raises, watcher status should reflect the failure."""
    from mdrag.config import VaultRegistry
    from mdrag.watcher import STATUS, _VaultWatcher

    registry = VaultRegistry(path=tmp_path / "reg.yaml")
    vault_dir = tmp_path / "v"
    vault_dir.mkdir()
    registry.add("t", str(vault_dir))
    v = registry.get("t")

    def boom(**_):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("mdrag.watcher.build_index", boom)
    STATUS.pop("t", None)

    watcher = _VaultWatcher(v, on_reindex=None)
    watcher._reindex()
    watcher._reindex()

    status = STATUS["t"]
    assert status.consecutive_errors == 2
    assert "disk on fire" in status.last_error_message
    assert status.last_success_at is None


def test_watcher_clears_errors_on_success(tmp_path: Path, monkeypatch):
    from mdrag.config import VaultRegistry
    from mdrag.watcher import STATUS, _VaultWatcher

    registry = VaultRegistry(path=tmp_path / "reg.yaml")
    vault_dir = tmp_path / "v"
    vault_dir.mkdir()
    registry.add("t", str(vault_dir))
    v = registry.get("t")
    STATUS.pop("t", None)

    calls = {"n": 0}

    def flaky(**_):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")

        class S:
            total_docs = 1
            total_chunks = 1
            updated_docs = 1
            ignored_docs = 0
            elapsed_seconds = 0.1
        return S()

    monkeypatch.setattr("mdrag.watcher.build_index", flaky)

    watcher = _VaultWatcher(v, on_reindex=None)
    watcher._reindex()
    assert STATUS["t"].consecutive_errors == 1

    watcher._reindex()
    assert STATUS["t"].consecutive_errors == 0
    assert STATUS["t"].last_error_message is None
    assert STATUS["t"].last_success_at is not None
