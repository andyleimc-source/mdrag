"""MCP server: exposes vault search tools over stdio."""

from __future__ import annotations

import json

import lancedb
from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer

from .config import VaultRegistry, Vault
from .indexer import TABLE_NAME
from .retrieval import (
    BM25_FILENAME,
    BM25Store,
    hybrid_search_docs,
)

mcp = FastMCP("mdrag")

_registry: VaultRegistry | None = None
_models: dict[str, SentenceTransformer] = {}
_tables: dict[str, "lancedb.table.Table"] = {}
_bm25_stores: dict[str, BM25Store | None] = {}


def _get_registry() -> VaultRegistry:
    global _registry
    if _registry is None:
        _registry = VaultRegistry()
    return _registry


def _get_model(model_name: str) -> SentenceTransformer:
    if model_name not in _models:
        _models[model_name] = SentenceTransformer(model_name)
    return _models[model_name]


def _get_table(vault: Vault):
    if vault.name not in _tables:
        db = lancedb.connect(str(vault.vector_dir))
        if TABLE_NAME not in db.table_names():
            raise RuntimeError(
                f"vault '{vault.name}' has no index. Run: mdrag vault reindex {vault.name}"
            )
        table = db.open_table(TABLE_NAME)
        if "chunk_id" not in set(table.schema.names):
            raise RuntimeError(
                f"vault '{vault.name}' uses an old index schema. "
                f"Run: mdrag vault reindex {vault.name} --full"
            )
        _tables[vault.name] = table
    return _tables[vault.name]


def _get_bm25(vault: Vault) -> BM25Store | None:
    if vault.name not in _bm25_stores:
        path = vault.vector_dir / BM25_FILENAME
        _bm25_stores[vault.name] = BM25Store.load(path) if path.is_file() else None
    return _bm25_stores[vault.name]


@mcp.tool()
def list_vaults() -> str:
    """列出所有已注册的 vault（name / path / 文档数 / 上次索引时间）。"""
    vaults = _get_registry().list()
    if not vaults:
        return "No vaults registered. Run: mdrag vault add <name> <path>"
    lines = []
    for v in vaults:
        lines.append(
            f"- {v.name}: {v.path} ({v.doc_count} docs, model={v.model}, indexed={v.indexed_at or 'never'})"
        )
    return "\n".join(lines)


@mcp.tool()
def search(vault: str, query: str, top_k: int = 5, tags: str = "") -> str:
    """在指定 vault 中语义搜索 Markdown 文档。返回每篇文档最相关的片段。

    Args:
        vault: vault 名称（通过 list_vaults 查看）
        query: 搜索关键词或自然语言描述
        top_k: 返回文档数量，默认 5
        tags: 可选，按标签过滤，逗号分隔（如 "case-study,product"）
    """
    v = _get_registry().get(vault)
    model = _get_model(v.model)
    table = _get_table(v)
    bm25 = _get_bm25(v)

    fetch_limit = max(top_k * 20, 100)
    docs = hybrid_search_docs(table, bm25, model, query, fetch_limit)

    if tags.strip():
        tag_filters = [t.strip().strip('"') for t in tags.split(",") if t.strip()]
        def _has_tag(row):
            try:
                raw = row.get("tags") or "[]"
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                return False
            return any(t in parsed for t in tag_filters)
        docs = [r for r in docs if _has_tag(r)]

    score_key = "_rrf" if (docs and "_rrf" in docs[0]) else "_distance"
    ranked = docs[:top_k]

    results = []
    for r in ranked:
        try:
            parsed_tags = json.loads(r.get("tags", "[]"))
        except Exception:
            parsed_tags = []
        results.append({
            "title": r.get("title"),
            "path": r.get("doc_path"),
            "heading_path": r.get("heading_path") or "",
            "chunk_text": (r.get("chunk_text") or "")[:300],
            "summary": (r.get("summary") or "")[:200],
            "tags": parsed_tags,
            "score": round(r.get("_rrf", 0), 4) if score_key == "_rrf" else round(r.get("_distance", 0), 4),
        })
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def get_doc(vault: str, path: str) -> str:
    """读取 vault 中指定路径的文档全文。

    Args:
        vault: vault 名称
        path: 文档在 vault 内的相对路径（即 search 返回的 path 字段）
    """
    v = _get_registry().get(vault)
    full_path = v.root / path
    try:
        full_path.resolve().relative_to(v.root)
    except ValueError:
        raise ValueError(f"path escapes vault root: {path}")
    if not full_path.is_file():
        raise FileNotFoundError(f"not found: {path}")
    return full_path.read_text(encoding="utf-8", errors="ignore")


@mcp.tool()
def list_tags(vault: str) -> str:
    """列出 vault 中所有 frontmatter 标签及其文档数量。"""
    v = _get_registry().get(vault)
    table = _get_table(v)
    arrow = table.to_arrow()
    seen_per_doc: dict[str, set[str]] = {}
    for doc_path, tags_json in zip(
        arrow.column("doc_path").to_pylist(),
        arrow.column("tags").to_pylist(),
    ):
        if doc_path in seen_per_doc:
            continue
        try:
            tags = json.loads(tags_json or "[]")
        except Exception:
            tags = []
        seen_per_doc[doc_path] = set(tags)

    counts: dict[str, int] = {}
    for tags in seen_per_doc.values():
        for t in tags:
            counts[t] = counts.get(t, 0) + 1

    if not counts:
        return "No tags found (tags come from MD frontmatter)."
    return "\n".join(f"- {t}: {n}" for t, n in sorted(counts.items(), key=lambda x: -x[1]))


def run() -> None:
    """Entry point used by CLI."""
    mcp.run()
