"""Evaluation harness: compare retrieval quality across indexes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import lancedb
import yaml
from sentence_transformers import SentenceTransformer

from .indexer import TABLE_NAME
from .retrieval import (
    BM25_FILENAME,
    BM25Store,
    bm25_search_docs,
    hybrid_search_docs,
    vector_search_docs,
)


@dataclass
class Query:
    q: str
    expect: list[str]
    kind: str = "general"


@dataclass
class QueryResult:
    query: Query
    ranked_paths: list[str]

    def first_hit_rank(self) -> int | None:
        for i, p in enumerate(self.ranked_paths, start=1):
            if p in self.query.expect:
                return i
        return None

    def hit_at_k(self, k: int) -> bool:
        rank = self.first_hit_rank()
        return rank is not None and rank <= k


def load_queries(path: Path) -> list[Query]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    out = []
    for entry in data:
        q = entry["q"]
        expect = entry.get("expect") or []
        if isinstance(expect, str):
            expect = [expect]
        kind = entry.get("kind", "general")
        out.append(Query(q=q, expect=list(expect), kind=kind))
    return out


_bm25_cache: dict[Path, BM25Store | None] = {}


def _load_bm25(db_path: Path) -> BM25Store | None:
    if db_path in _bm25_cache:
        return _bm25_cache[db_path]
    p = db_path / BM25_FILENAME
    store = BM25Store.load(p) if p.is_file() else None
    _bm25_cache[db_path] = store
    return store


def _search_index(
    db_path: Path,
    mode: str,
    model: SentenceTransformer,
    query: str,
    top_k: int,
) -> list[str]:
    db = lancedb.connect(str(db_path))
    table = db.open_table(TABLE_NAME)
    cols = set(table.schema.names)
    fetch_limit = max(top_k * 20, 100)

    if "chunk_id" not in cols:
        q_vec = model.encode(query).tolist()
        rows = table.search(q_vec).limit(fetch_limit).to_list()
        seen: dict[str, float] = {}
        for r in rows:
            p = r.get("path") or r.get("doc_path")
            if p is None:
                continue
            d = r.get("_distance", 0.0)
            if p not in seen or d < seen[p]:
                seen[p] = d
        return [p for p, _ in sorted(seen.items(), key=lambda kv: kv[1])[:top_k]]

    if mode == "hybrid":
        bm25 = _load_bm25(db_path)
        docs = hybrid_search_docs(table, bm25, model, query, fetch_limit)
    elif mode == "bm25":
        bm25 = _load_bm25(db_path)
        if bm25 is None:
            raise RuntimeError(f"no BM25 store at {db_path}; reindex required")
        docs = bm25_search_docs(bm25, query, fetch_limit)
    else:
        q_vec = model.encode(query).tolist()
        docs = vector_search_docs(table, q_vec, fetch_limit)

    return [r["doc_path"] for r in docs[:top_k]]


def run_eval(
    queries_path: Path,
    indexes: list[tuple[str, Path, str]],
    top_k: int,
    model_name: str,
    output_path: Path,
) -> None:
    queries = load_queries(queries_path)
    if not queries:
        raise RuntimeError(f"no queries loaded from {queries_path}")

    model = SentenceTransformer(model_name)

    results: dict[str, list[QueryResult]] = {}
    for label, db_path, mode in indexes:
        runs = []
        for q in queries:
            ranked = _search_index(db_path, mode, model, q.q, top_k)
            runs.append(QueryResult(query=q, ranked_paths=ranked))
        results[label] = runs

    report = _format_report(queries, indexes, results, top_k)
    output_path.write_text(report, encoding="utf-8")


def _metrics(runs: Iterable[QueryResult], top_k: int) -> dict[str, float]:
    runs = list(runs)
    if not runs:
        return {"recall": 0.0, "mrr": 0.0, "hits": 0, "total": 0}
    hits = sum(1 for r in runs if r.hit_at_k(top_k))
    reciprocal = 0.0
    for r in runs:
        rank = r.first_hit_rank()
        if rank is not None and rank <= top_k:
            reciprocal += 1 / rank
    return {
        "recall": hits / len(runs),
        "mrr": reciprocal / len(runs),
        "hits": hits,
        "total": len(runs),
    }


def _format_report(
    queries: list[Query],
    indexes: list[tuple[str, Path, str]],
    results: dict[str, list[QueryResult]],
    top_k: int,
) -> str:
    labels = [lbl for lbl, _, _ in indexes]

    lines: list[str] = []
    lines.append("# mdrag Evaluation Report\n")
    lines.append(f"- Top-K: **{top_k}**")
    lines.append(f"- Queries: **{len(queries)}**")
    lines.append(f"- Indexes compared: {', '.join(f'`{lbl}` ({m})' for lbl, _, m in indexes)}\n")

    if len(labels) == 2:
        base_label, new_label = labels
        base_m = _metrics(results[base_label], top_k)
        new_m = _metrics(results[new_label], top_k)
        recall_delta = (new_m["recall"] - base_m["recall"]) * 100
        mrr_delta = new_m["mrr"] - base_m["mrr"]
        lines.append("## TL;DR\n")
        lines.append(
            f"`{new_label}` vs `{base_label}`: "
            f"Recall@{top_k} **{base_m['recall']*100:.1f}% → {new_m['recall']*100:.1f}%** "
            f"(Δ {recall_delta:+.1f}pp), "
            f"MRR **{base_m['mrr']:.3f} → {new_m['mrr']:.3f}** (Δ {mrr_delta:+.3f}).\n"
        )

    kinds = sorted({q.kind for q in queries})

    lines.append("## Overall\n")
    header = ["Metric"] + labels
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    overall = {lbl: _metrics(results[lbl], top_k) for lbl in labels}
    recall_row = ["Recall@" + str(top_k)] + [f"{overall[lbl]['recall']*100:.1f}% ({overall[lbl]['hits']}/{overall[lbl]['total']})" for lbl in labels]
    mrr_row = ["MRR"] + [f"{overall[lbl]['mrr']:.3f}" for lbl in labels]
    lines.append("| " + " | ".join(recall_row) + " |")
    lines.append("| " + " | ".join(mrr_row) + " |")

    for kind in kinds:
        subset_results = {lbl: [r for r in results[lbl] if r.query.kind == kind] for lbl in labels}
        m = {lbl: _metrics(subset_results[lbl], top_k) for lbl in labels}
        lines.append(f"\n## Subset: `{kind}` ({m[labels[0]]['total']} queries)\n")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        lines.append("| " + " | ".join(["Recall@" + str(top_k)] + [f"{m[lbl]['recall']*100:.1f}% ({m[lbl]['hits']}/{m[lbl]['total']})" for lbl in labels]) + " |")
        lines.append("| " + " | ".join(["MRR"] + [f"{m[lbl]['mrr']:.3f}" for lbl in labels]) + " |")

    lines.append("\n## Per-Query Results\n")
    lines.append("Rank shown is the position of the first expected document (— = not in top-K).\n")
    header = ["#", "Kind", "Query"] + [f"{lbl} rank" for lbl in labels]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for i, q in enumerate(queries, 1):
        row = [str(i), q.kind, q.q]
        for lbl in labels:
            r = results[lbl][i - 1]
            rank = r.first_hit_rank()
            row.append("✅ #" + str(rank) if (rank is not None and rank <= top_k) else "—")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("\n## Expected vs. Returned\n")
    for i, q in enumerate(queries, 1):
        lines.append(f"\n### Q{i}. {q.q}\n")
        lines.append(f"- **Kind:** {q.kind}")
        lines.append(f"- **Expected:** {', '.join(f'`{e}`' for e in q.expect)}")
        for lbl in labels:
            r = results[lbl][i - 1]
            rank = r.first_hit_rank()
            lines.append(f"- **{lbl}** (rank: {rank if rank else '—'}):")
            for j, p in enumerate(r.ranked_paths, 1):
                marker = "👉" if p in q.expect else "  "
                lines.append(f"  {j}. {marker} `{p}`")

    return "\n".join(lines) + "\n"
