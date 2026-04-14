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

TABLE_NAME = "docs"
DEFAULT_EXCLUDES = (".wiki-mcp", ".git", "node_modules", ".venv", "__pycache__")


@dataclass
class IndexStats:
    total: int
    updated: int
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


def iter_markdown_files(root: Path, excludes: Iterable[str] = DEFAULT_EXCLUDES) -> Iterable[Path]:
    exclude_set = set(excludes)
    for path in sorted(root.rglob("*.md")):
        if any(part in exclude_set for part in path.relative_to(root).parts):
            continue
        yield path


def _load_document(md_path: Path, vault_root: Path) -> dict:
    rel = str(md_path.relative_to(vault_root))
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    meta, body = parse_frontmatter(text)

    title = meta.get("title") or md_path.stem
    summary = meta.get("summary", "")
    tags = meta.get("tags", [])
    if isinstance(tags, list):
        tags_str = json.dumps(tags, ensure_ascii=False)
    else:
        tags_str = str(tags)

    body_clean = re.sub(r"\n{3,}", "\n\n", body).strip()
    text_preview = body_clean[:200]
    embed_input = f"{title} {summary} {body_clean[:500]}"

    return {
        "path": rel,
        "title": title,
        "summary": summary or text_preview,
        "tags": tags_str,
        "text_preview": text_preview,
        "embed_input": embed_input,
        "mtime": md_path.stat().st_mtime,
    }


def build_index(
    vault_path: Path,
    vector_dir: Path,
    model_name: str,
    full_rebuild: bool = False,
) -> IndexStats:
    """Build or update the vector index for a vault. Returns stats."""
    t0 = time.time()
    vault_path = vault_path.expanduser().resolve()
    vector_dir.mkdir(parents=True, exist_ok=True)

    docs = [_load_document(p, vault_path) for p in iter_markdown_files(vault_path)]

    db = lancedb.connect(str(vector_dir))

    incremental = (not full_rebuild) and TABLE_NAME in db.table_names()

    if incremental:
        table = db.open_table(TABLE_NAME)
        arrow = table.to_arrow()
        existing = dict(zip(arrow.column("path").to_pylist(), arrow.column("mtime").to_pylist()))
        current_paths = {d["path"] for d in docs}

        deleted_paths = [p for p in existing if p not in current_paths]
        if deleted_paths:
            quoted = ",".join(f"'{p.replace(chr(39), chr(39)*2)}'" for p in deleted_paths)
            table.delete(f"path IN ({quoted})")

        new_docs = [d for d in docs if existing.get(d["path"]) is None or d["mtime"] > existing[d["path"]]]

        if not new_docs:
            return IndexStats(total=len(docs), updated=0, elapsed_seconds=time.time() - t0)

        model = SentenceTransformer(model_name)
        embeddings = model.encode([d["embed_input"] for d in new_docs], show_progress_bar=False)

        rows = []
        for d, vec in zip(new_docs, embeddings):
            d.pop("embed_input")
            d["vector"] = vec.tolist()
            rows.append(d)

        paths_quoted = ",".join(f"'{r['path'].replace(chr(39), chr(39)*2)}'" for r in rows)
        table.delete(f"path IN ({paths_quoted})")
        table.add(rows)
        return IndexStats(total=len(docs), updated=len(rows), elapsed_seconds=time.time() - t0)

    model = SentenceTransformer(model_name)
    if not docs:
        if TABLE_NAME in db.table_names():
            db.drop_table(TABLE_NAME)
        return IndexStats(total=0, updated=0, elapsed_seconds=time.time() - t0)

    embeddings = model.encode([d["embed_input"] for d in docs], show_progress_bar=False)

    rows = []
    for d, vec in zip(docs, embeddings):
        d.pop("embed_input")
        d["vector"] = vec.tolist()
        rows.append(d)

    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)
    db.create_table(TABLE_NAME, rows)
    return IndexStats(total=len(docs), updated=len(rows), elapsed_seconds=time.time() - t0)
