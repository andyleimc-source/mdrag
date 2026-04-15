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
from sentence_transformers import SentenceTransformer

from .chunking import split_markdown
from .retrieval import BM25_FILENAME, BM25Store

TABLE_NAME = "docs"
DEFAULT_EXCLUDES = (".mdrag", ".git", "node_modules", ".venv", "__pycache__")
MAX_FILE_SIZE = 200_000


@dataclass
class IndexStats:
    total_docs: int
    total_chunks: int
    updated_docs: int
    skipped_oversize: int
    elapsed_seconds: float


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
    max_file_size: int = MAX_FILE_SIZE,
) -> Iterable[Path]:
    for path in _walk_markdown(root, excludes):
        if max_file_size and path.stat().st_size > max_file_size:
            continue
        yield path


def partition_by_size(
    root: Path,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
    max_file_size: int = MAX_FILE_SIZE,
) -> tuple[list[Path], list[Path]]:
    kept: list[Path] = []
    oversized: list[Path] = []
    for path in _walk_markdown(root, excludes):
        if max_file_size and path.stat().st_size > max_file_size:
            oversized.append(path)
        else:
            kept.append(path)
    return kept, oversized


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
    """Build or update the chunk-level vector index for a vault."""
    t0 = time.time()
    vault_path = vault_path.expanduser().resolve()
    vector_dir.mkdir(parents=True, exist_ok=True)

    md_files, oversized = partition_by_size(vault_path)
    db = lancedb.connect(str(vector_dir))

    existing_table = TABLE_NAME in db.table_names()
    needs_rebuild = full_rebuild or not existing_table
    if existing_table and not full_rebuild:
        existing_cols = set(db.open_table(TABLE_NAME).schema.names)
        if "chunk_id" not in existing_cols:
            needs_rebuild = True

    model = SentenceTransformer(model_name)

    if needs_rebuild:
        all_rows: list[dict] = []
        for p in md_files:
            all_rows.extend(_doc_chunks(p, vault_path))

        if not all_rows:
            if existing_table:
                db.drop_table(TABLE_NAME)
            return IndexStats(0, 0, 0, len(oversized), time.time() - t0)

        rows = _embed_rows(all_rows, model)
        if existing_table:
            db.drop_table(TABLE_NAME)
        table = db.create_table(TABLE_NAME, rows)
        _rebuild_bm25_from_table(table, vector_dir)
        return IndexStats(
            total_docs=len(md_files),
            total_chunks=len(rows),
            updated_docs=len(md_files),
            skipped_oversize=len(oversized),
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

    if not changed_docs:
        total_chunks = table.count_rows()
        return IndexStats(
            total_docs=len(md_files),
            total_chunks=total_chunks,
            updated_docs=0,
            skipped_oversize=len(oversized),
            elapsed_seconds=time.time() - t0,
        )

    new_rows: list[dict] = []
    for p in changed_docs:
        new_rows.extend(_doc_chunks(p, vault_path))

    changed_paths = {str(p.relative_to(vault_path)) for p in changed_docs}
    quoted = ",".join(f"'{p.replace(chr(39), chr(39)*2)}'" for p in changed_paths)
    table.delete(f"doc_path IN ({quoted})")

    if new_rows:
        table.add(_embed_rows(new_rows, model))

    _rebuild_bm25_from_table(table, vector_dir)

    return IndexStats(
        total_docs=len(md_files),
        total_chunks=table.count_rows(),
        updated_docs=len(changed_docs),
        skipped_oversize=len(oversized),
        elapsed_seconds=time.time() - t0,
    )
