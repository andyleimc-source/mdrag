"""Build and update LanceDB vector index for a vault."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import lancedb
import yaml
from filelock import FileLock, Timeout
from pathspec import PathSpec
from sentence_transformers import SentenceTransformer

from .chunking import split_markdown
from .retrieval import BM25_FILENAME, BM25Store

LOCK_FILENAME = ".mdrag.lock"
LOCK_TIMEOUT_SECONDS = 300  # 5 min — long enough for a full reindex on a large vault

TABLE_NAME = "docs"
DEFAULT_EXCLUDES = (".mdrag", ".git", "node_modules", ".venv", "__pycache__")
IGNORE_FILENAME = ".mdragignore"
META_FILENAME = "meta.json"
SCHEMA_VERSION = 2  # bump when the LanceDB row shape or embedding pipeline changes


def read_meta(vector_dir: Path) -> dict:
    p = vector_dir / META_FILENAME
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_meta(vector_dir: Path, model_name: str) -> None:
    vector_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "model": model_name,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (vector_dir / META_FILENAME).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


class SchemaMismatchError(RuntimeError):
    """Raised when an on-disk index is incompatible with the current code."""


@dataclass
class IndexStats:
    total_docs: int
    total_chunks: int
    updated_docs: int
    ignored_docs: int
    elapsed_seconds: float


def load_ignore_spec(root: Path) -> PathSpec | None:
    ignore_file = root / IGNORE_FILENAME
    if not ignore_file.is_file():
        return None
    lines = ignore_file.read_text(encoding="utf-8").splitlines()
    return PathSpec.from_lines("gitignore", lines)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    return meta, text[m.end():]


def _walk_markdown(
    root: Path,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
) -> Iterable[Path]:
    exclude_set = set(excludes)
    for path in sorted(root.rglob("*.md")):
        if any(part in exclude_set for part in path.relative_to(root).parts):
            continue
        yield path


def iter_markdown_files(
    root: Path,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
) -> Iterable[Path]:
    spec = load_ignore_spec(root)
    for path in _walk_markdown(root, excludes):
        rel = path.relative_to(root)
        if spec and spec.match_file(str(rel)):
            continue
        yield path


def partition_by_ignore(
    root: Path,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
) -> tuple[list[Path], list[Path]]:
    spec = load_ignore_spec(root)
    kept: list[Path] = []
    ignored: list[Path] = []
    for path in _walk_markdown(root, excludes):
        rel = path.relative_to(root)
        if spec and spec.match_file(str(rel)):
            ignored.append(path)
        else:
            kept.append(path)
    return kept, ignored


def _doc_chunks(md_path: Path, vault_root: Path) -> list[dict]:
    rel = str(md_path.relative_to(vault_root))
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    meta, body = parse_frontmatter(text)

    title = str(meta.get("title") or md_path.stem)
    summary = str(meta.get("summary") or "")
    tags = meta.get("tags", [])
    tags_str = json.dumps(tags, ensure_ascii=False) if isinstance(tags, list) else str(tags)
    mtime = md_path.stat().st_mtime

    body_clean = re.sub(r"\n{3,}", "\n\n", body).strip()
    chunks = split_markdown(body_clean)

    rows = []
    overview_text = summary.strip() if summary.strip() else body_clean[:500]
    rows.append({
        "doc_path": rel,
        "chunk_id": 0,
        "heading_path": "(overview)",
        "chunk_text": overview_text,
        "title": title,
        "summary": summary,
        "tags": tags_str,
        "mtime": mtime,
        "embed_input": f"{title}\n{overview_text}",
    })
    for c in chunks:
        prefix = f"{title} › {c.heading_path}" if c.heading_path else title
        rows.append({
            "doc_path": rel,
            "chunk_id": c.chunk_id + 1,
            "heading_path": c.heading_path,
            "chunk_text": c.text,
            "title": title,
            "summary": summary,
            "tags": tags_str,
            "mtime": mtime,
            "embed_input": f"{prefix}\n{c.text}",
        })
    return rows


def _embed_rows(rows: list[dict], model: SentenceTransformer) -> list[dict]:
    embeddings = model.encode([r["embed_input"] for r in rows], show_progress_bar=False)
    out = []
    for r, vec in zip(rows, embeddings):
        r = dict(r)
        r.pop("embed_input")
        r["vector"] = vec.tolist()
        out.append(r)
    return out


def _rebuild_bm25_from_table(table, vector_dir: Path) -> None:
    arrow = table.to_arrow()
    cols = arrow.column_names
    needed = ("doc_path", "chunk_id", "title", "heading_path", "chunk_text")
    if not all(c in cols for c in needed):
        return
    chunks = [
        {k: row[k] for k in needed}
        for row in arrow.select(list(needed)).to_pylist()
    ]
    BM25Store.build(chunks).save(vector_dir / BM25_FILENAME)


def build_index(
    vault_path: Path,
    vector_dir: Path,
    model_name: str,
    full_rebuild: bool = False,
) -> IndexStats:
    """Build or update the chunk-level vector index for a vault.

    Holds a per-vault file lock so concurrent CLI + watcher reindexes don't corrupt
    LanceDB state. The lock lives at `<vector_dir>/.mdrag.lock`. If another process
    already holds it, this call will block up to LOCK_TIMEOUT_SECONDS before raising.
    """
    t0 = time.time()
    vault_path = vault_path.expanduser().resolve()
    vector_dir.mkdir(parents=True, exist_ok=True)

    lock = FileLock(str(vector_dir / LOCK_FILENAME), timeout=LOCK_TIMEOUT_SECONDS)
    try:
        with lock:
            return _build_index_locked(vault_path, vector_dir, model_name, full_rebuild, t0)
    except Timeout as e:
        raise RuntimeError(
            f"could not acquire index lock on {vector_dir} within {LOCK_TIMEOUT_SECONDS}s; "
            f"another reindex may be running"
        ) from e


def _build_index_locked(
    vault_path: Path,
    vector_dir: Path,
    model_name: str,
    full_rebuild: bool,
    t0: float,
) -> IndexStats:

    md_files, ignored = partition_by_ignore(vault_path)
    db = lancedb.connect(str(vector_dir))

    existing_table = TABLE_NAME in db.table_names()
    needs_rebuild = full_rebuild or not existing_table
    if existing_table and not full_rebuild:
        existing_cols = set(db.open_table(TABLE_NAME).schema.names)
        if "chunk_id" not in existing_cols:
            needs_rebuild = True

        meta = read_meta(vector_dir)
        disk_version = meta.get("schema_version")
        if disk_version is not None and disk_version != SCHEMA_VERSION:
            raise SchemaMismatchError(
                f"index schema v{disk_version} is incompatible with code v{SCHEMA_VERSION}. "
                f"Run: mdrag vault reindex <name> --full"
            )
        disk_model = meta.get("model")
        if disk_model and disk_model != model_name:
            raise SchemaMismatchError(
                f"index was built with model '{disk_model}' but requested '{model_name}'. "
                f"Run: mdrag vault reindex <name> --full"
            )

    model = SentenceTransformer(model_name)

    if needs_rebuild:
        all_rows: list[dict] = []
        for p in md_files:
            all_rows.extend(_doc_chunks(p, vault_path))

        if not all_rows:
            if existing_table:
                db.drop_table(TABLE_NAME)
            return IndexStats(0, 0, 0, len(ignored), time.time() - t0)

        rows = _embed_rows(all_rows, model)
        if existing_table:
            db.drop_table(TABLE_NAME)
        table = db.create_table(TABLE_NAME, rows)
        _rebuild_bm25_from_table(table, vector_dir)
        write_meta(vector_dir, model_name)
        return IndexStats(
            total_docs=len(md_files),
            total_chunks=len(rows),
            updated_docs=len(md_files),
            ignored_docs=len(ignored),
            elapsed_seconds=time.time() - t0,
        )

    table = db.open_table(TABLE_NAME)
    arrow = table.to_arrow()
    existing_mtime: dict[str, float] = {}
    for path, mt in zip(arrow.column("doc_path").to_pylist(), arrow.column("mtime").to_pylist()):
        prev = existing_mtime.get(path)
        if prev is None or mt > prev:
            existing_mtime[path] = mt

    current_paths = {str(p.relative_to(vault_path)) for p in md_files}
    deleted = [p for p in existing_mtime if p not in current_paths]
    if deleted:
        quoted = ",".join(f"'{p.replace(chr(39), chr(39)*2)}'" for p in deleted)
        table.delete(f"doc_path IN ({quoted})")

    changed_docs: list[Path] = []
    for p in md_files:
        rel = str(p.relative_to(vault_path))
        prev_mtime = existing_mtime.get(rel)
        if prev_mtime is None or p.stat().st_mtime > prev_mtime:
            changed_docs.append(p)

    if not changed_docs and not deleted:
        total_chunks = table.count_rows()
        return IndexStats(
            total_docs=len(md_files),
            total_chunks=total_chunks,
            updated_docs=0,
            ignored_docs=len(ignored),
            elapsed_seconds=time.time() - t0,
        )

    new_rows: list[dict] = []
    for p in changed_docs:
        new_rows.extend(_doc_chunks(p, vault_path))

    if changed_docs:
        changed_paths = {str(p.relative_to(vault_path)) for p in changed_docs}
        quoted = ",".join(f"'{p.replace(chr(39), chr(39)*2)}'" for p in changed_paths)
        table.delete(f"doc_path IN ({quoted})")

    if new_rows:
        table.add(_embed_rows(new_rows, model))

    # BM25 must be rebuilt whenever the table changed — adds OR deletes.
    # Previously only rebuilt in the changed_docs branch, leaving stale entries
    # when a reindex only deleted files.
    _rebuild_bm25_from_table(table, vector_dir)
    write_meta(vector_dir, model_name)

    return IndexStats(
        total_docs=len(md_files),
        total_chunks=table.count_rows(),
        updated_docs=len(changed_docs),
        ignored_docs=len(ignored),
        elapsed_seconds=time.time() - t0,
    )
