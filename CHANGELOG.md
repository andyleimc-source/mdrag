# Changelog

## 0.3.0 (2026-04-16)

### Stability

- **S1 Watcher error tracking** — `watcher.py` now records `last_error_at`, `last_error_message`, `consecutive_errors` per vault. The MCP `list_vaults` tool surfaces any failing watcher with a ⚠️ line, so clients don't silently query stale data after a reindex breaks.
- **S2 File lock on reindex** — `build_index` holds a per-vault `FileLock` (`.mdrag.lock`) with a 300s timeout. Prevents LanceDB corruption when the CLI and the watcher race on the same vector dir. New dep: `filelock>=3.12`.
- **S3 Schema versioning** — each `.mdrag/` now carries `meta.json` with `schema_version` and `model`. Incremental reindex refuses to run against a mismatched schema or model with an actionable hint; `SchemaMismatchError` is raised and the CLI translates it into "Run: mdrag vault reindex <name> --full".
- **S4 BM25 delete-only drift** — `_rebuild_bm25_from_table` is now invoked on any table mutation (adds OR deletes). Previously a reindex that only deleted files left the BM25 store referencing vanished docs.

### Usability

- **E1 First-run model preflight** — `vault add` checks `huggingface_hub.try_to_load_from_cache` before indexing; if the model isn't cached, prints a heads-up about the ~100MB download and mentions `HF_ENDPOINT` for users behind GFW.
- **E2 `mdrag doctor`** — new command. Reports Python version, registry state, per-vault (schema, model, BM25 presence, freshness), total disk usage, and whether `mdrag` is on PATH. Exits non-zero if any issue is found. Meant to be the first thing users paste into issue reports.
- **E3 Match reason in search results** — hybrid results now include a `match_reason` field: `"vector+bm25"` (both sides agreed), `"bm25 (rare-term)"` (exact-match boost kicked in), `"bm25 only"`, `"vector only"`. MCP clients can use this for explainability or second-stage filtering.
- **E4 CI + regression test** — `.github/workflows/ci.yml` runs ruff + pytest on Python 3.10/3.11/3.12 for every PR. `test_eval_regression.py` runs BM25 and hybrid against the shipped sample vault with a deterministic fake embedder so retrieval plumbing can't silently break.

### Notes

- Version bump 0.2.0 → 0.3.0 (keep in sync: `pyproject.toml` + `src/mdrag/__init__.py`).
- No eval regression: hybrid Recall@5 still 100% (15/15) on the dev vault.

## 0.2.0 (2026-04-16)

### Highlights

Hybrid retrieval Recall@5 on the 15-query eval suite: **80% → 100%** (needle subset: 90% → 100%).

### Retrieval improvements (`retrieval.py`)

- **Rare-term query handling** — queries containing digit strings (e.g. "38 种字段") now use a
  BM25-priority fusion strategy: docs that BM25 ranks well but vector doesn't see at all are
  injected at their BM25 rank position instead of being buried by vector results. Fixes Q12.

- **Comparison query expansion** — queries containing comparison keywords ("区别", "对比",
  "compare", "vs", etc.) have their vector-side query expanded with cross-lingual synonyms before
  embedding, improving recall for bilingual comparison docs. Fixes Q3.

- **Overview chunk tiebreaker** — when two chunks from the same doc have identical scores during
  deduplication, the overview chunk (`chunk_id == 0`) is preferred, so broad conceptual queries
  surface doc-level signal rather than a mid-document section.

### Document quality

- Updated `summary` frontmatter on four high-value docs whose auto-generated summaries were noise
  (PPT slide text, image links, raw table rows):
  - `mingdao/intro/明道云伙伴introbook.md`
  - `mingdao/intro/明道云特性清单.md`
  - `mingdao/intro/主流零代码平台分析报告.md`
  - `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`

### Eval numbers (15 queries, K=5)

| Mode | Recall@5 | Needle (10q) | General (5q) | MRR |
|---|---|---|---|---|
| baseline (old 500-char index) | 13.3% | 0% | 40% | 0.10 |
| vector only | 80.0% | 80% | 80% | 0.644 |
| bm25 only | 93.3% | 100% | 80% | 0.817 |
| **hybrid (default)** | **100.0%** | **100%** | **100%** | **0.819** |

---

## 0.1.0 (2026-03-xx) — initial release

### Round 1 — chunking + multilingual default

- `chunking.py`: heading-split + sliding-window fallback (600 chars / 80 overlap), `MAX_CHUNKS_PER_DOC=30`
- Overview chunk (`chunk_id=0`) per doc containing title + frontmatter summary
- LanceDB schema: per-chunk rows `(doc_path, chunk_id, heading_path, chunk_text, title, summary, tags, mtime, vector)`
- Default model changed to `paraphrase-multilingual-MiniLM-L12-v2`
- `mdrag eval` command with Recall@K / MRR metrics

### Round 2 — hybrid retrieval

- Pure-Python BM25 with word-level latin/digit tokens + char-level CJK tokenization
- `best_rank_fuse`: take best rank from either list; agreement bonus of -1 rank
- `mdrag eval` spec: `label=path[:mode]` supporting `hybrid`, `vector`, `bm25`

### Round 3 — productization

- `.mdragignore` (gitignore syntax) for per-vault noise filtering
- `watcher.py`: watchdog observer per vault, 1.5s debounce, incremental reindex on file change
- Hardcoded `MAX_FILE_SIZE` filter removed; noise containment via `MAX_CHUNKS_PER_DOC=30`
