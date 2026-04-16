# mdrag Handoff

Snapshot of the current state of mdrag after three rounds of work. Written so the next contributor (possibly future-you, possibly a new Claude session) can pick up without re-deriving anything.

---

## What mdrag is

A local MCP server that turns any Markdown folder into a semantic-search vault. Fully offline, no API keys. See `README.md` for the user-facing pitch.

**Current version**: 0.3.0 (not yet built; previous `dist/mdrag-0.2.0*` is stale — rebuild before upload)
**Repo**: https://github.com/andyleimc-source/mdrag
**Author vault (dev target)**: `/Users/andy/Desktop/wiki/docs/` — 408 markdown docs, bilingual (Chinese + English)

---

## Architecture at a glance

```
src/mdrag/
├── cli.py          Click entry point: serve / vault {add,list,reindex,remove,info} / eval
├── config.py       VaultRegistry (~/.mdrag/vaults.yaml); Vault dataclass; DEFAULT_MODEL
├── chunking.py     split_markdown() — heading split + sliding-window fallback
├── indexer.py      build_index() — walks vault, chunks, embeds, writes LanceDB + BM25
├── retrieval.py    BM25 impl, RRF and best-rank fusion, unified search (vector/bm25/hybrid)
├── evaluator.py    run_eval() — multi-index comparison, Recall@K / MRR / per-query diff
├── server.py       FastMCP server exposing list_vaults / search / get_doc / list_tags
└── watcher.py      watchdog Observers that auto-reindex on file save
```

**On-disk layout**:
```
<vault>/.mdrag/
├── docs.lance/     LanceDB table (one row per chunk: doc_path, chunk_id, heading_path,
│                   chunk_text, title, summary, tags, mtime, vector)
└── bm25.pkl        Pickled BM25Store (inverted index + chunk payloads)
```

---

## What's been built (timeline)

### Round 1 — chunking + multilingual default (`b410f60`)

**Problem**: baseline was `embed_input = f"{title} {summary} {body_clean[:500]}"` — one vector per doc from the first 500 chars. Content past char 500 was invisible to search.

**Solution**:
- `chunking.py` splits on `^##+` headings; sections over 600 chars go through a 600-char / 80-char-overlap sliding window; `MAX_CHUNKS_PER_DOC = 30` caps a single doc
- Every doc also gets an **overview chunk** (`chunk_id=0`, `heading_path="(overview)"`) containing title + frontmatter summary (or first 500 chars if no summary). This is what catches broad conceptual queries after we moved to chunk-level indexing.
- LanceDB schema changed from `(path, title, summary, tags, text_preview, mtime, vector)` to `(doc_path, chunk_id, heading_path, chunk_text, title, summary, tags, mtime, vector)`. Requires `reindex --full` to upgrade.
- Default model changed to `paraphrase-multilingual-MiniLM-L12-v2` (handles Chinese + English) from `BAAI/bge-small-zh-v1.5`.
- `mdrag eval` command added, comparing any set of indexes. Metrics: Recall@K, MRR, per-query ranking diff.

### Round 2 — hybrid retrieval (`5a0a1af`)

**Problem**: vector search alone misses rare-keyword queries. Q12 ("明道云 38 种字段控件") — vector has no concept of the literal "38"; finds "UI / ease-of-use" docs instead of the one spec that actually lists 38 field types.

**Solution**:
- Pure-Python BM25 (`retrieval.py`): word-level tokens for latin/digits, char-level for CJK (so 明道云 → [明, 道, 云], matching how keyword users actually search)
- BM25Store pickle written next to `docs.lance` on every index run
- **Fusion strategy**: dedupe chunks to doc-level rankings first, then `best_rank_fuse` (take the better of either side's rank; agreement across both lists gets a -1 rank bonus). Tried plain RRF first; it averaged away single-side strong signals. Best-rank keeps Q12 findable via BM25 even when vector buries it.
- `mdrag eval` spec format extended: `label=path[:mode]` where `mode ∈ {hybrid, vector, bm25}`. Lets you isolate contributions.

### Round 5 — stability & UX hardening (v0.3.0)

**Problem**: v0.2.0 hit 100% on eval but had silent-failure modes. Watcher errors only went to stderr; concurrent reindex could corrupt LanceDB; BM25 drift after delete-only reindex; no schema version for future migrations; no regression protection.

**Solution**:
- `watcher.py` tracks per-vault `last_error_message` + `consecutive_errors`; `list_vaults` MCP tool shows failing watchers with ⚠️.
- `indexer.py` acquires `FileLock` on `<vector_dir>/.mdrag.lock` with 300s timeout. Two concurrent `build_index` calls now serialize instead of racing.
- `meta.json` (`schema_version=2`, `model=<name>`, `updated_at`) written on every reindex. Incremental runs against mismatched version/model raise `SchemaMismatchError` with an actionable hint.
- BM25 rebuilt on both add and delete paths (previously only on add).
- `mdrag doctor` command: end-to-end health check, exits non-zero on any issue.
- `vault add` preflights the embedding-model cache and warns about HF endpoint if not cached.
- `match_reason` added to `search()` results so AI clients can see why a doc matched.
- GitHub Actions CI (ruff + pytest on 3.10/3.11/3.12). `test_eval_regression.py` runs a deterministic fake-embedder hybrid search on the sample vault — catches plumbing regressions before full eval on the real vault.

Result: 47 tests pass (was 35). No eval regression (hybrid Recall@5 still 100%).

### Round 4 — eval-driven quality push to 100% (v0.2.0)

**Problem**: v0.1.0 hybrid Recall@5 stuck at 80% with three queries always failing (Q1 "核心功能介绍", Q3 "HAP 产品与低代码平台的区别", Q12 "38 种字段控件").

**Solution** (all in `retrieval.py`):
- **Rare-term handling**: queries containing digit strings detected via `_has_rare_terms`; fusion splits into docs-shared-by-both-sides (best-rank fused with double BM25) and BM25-only docs (injected at their BM25 rank position). Fixes Q12 — BM25-only strong hits no longer get buried.
- **Comparison query expansion**: `_expand_query` appends cross-lingual synonyms ("区别" → "difference vs comparison 对比") to the vector query before embedding. Fixes Q3.
- **Overview chunk tiebreaker**: in `_dedupe_chunks_to_doc_ranking`, ties broken in favor of `chunk_id == 0`.
- **Frontmatter cleanup** (non-code): four docs had summaries filled with PPT slide noise/table rows/image markdown. Rewrote summaries to real conceptual overviews — this is what unblocked Q1 on BM25.

Result: hybrid Recall@5 **80% → 100%**, MRR 0.619 → 0.819. Needle subset 90% → 100%.

### Round 3 — productization for OSS release (`17fd560`)

**Problem**: earlier rounds had a hardcoded `MAX_FILE_SIZE = 200_000` to filter out my personal noise files (5.5MB sales logs, WeChat group exports). Unacceptable for an OSS tool — other users' corpora look completely different.

**Solution**:
- `.mdragignore` at the vault root (gitignore syntax, parsed by `pathspec`). Missing file → index everything.
- `watcher.py`: one watchdog `Observer` per vault, 1.5s debounce, triggers incremental `build_index` on any .md change/create/delete/move. `server.run()` starts watchers at boot and invalidates in-memory table/BM25 caches on each reindex so MCP sees fresh data with no restart.
- Hardcoded size filter removed; noise containment is now carried entirely by `MAX_CHUNKS_PER_DOC=30` (per-doc cap prevents a 5MB log from dominating top-K). Verified on eval: including full sales logs didn't change a single metric.

---

## Quality bar — current eval numbers

Measured on `tests/eval-queries.yaml` (15 queries: 5 broad "general" + 10 deep "needle" targeting content past char 500 of long docs). See `EVAL_REPORT.md` for the full per-query breakdown.

| Mode | Recall@5 overall | Needle (10q) | General (5q) | MRR |
|---|---|---|---|---|
| baseline (old 500-char index) | 13.3% | 0% | 40% | 0.10 |
| vector only (v0.2.0) | 80.0% | 80% | 80% | 0.64 |
| bm25 only (v0.2.0) | 93.3% | 100% | 80% | 0.82 |
| **hybrid (default, v0.2.0)** | **100.0%** | **100%** | **100%** | **0.82** |

Hybrid is now strictly dominant on this suite. BM25 alone is almost as good on needle queries (exact terms) but misses some general/conceptual queries that the overview chunk catches.

**How to re-run the eval** (always do this before claiming an improvement):
```bash
mdrag eval tests/eval-queries.yaml \
  "baseline=/tmp/mdrag-baseline:vector" \
  "vector=/Users/andy/Desktop/wiki/docs/.mdrag:vector" \
  "bm25=/Users/andy/Desktop/wiki/docs/.mdrag:bm25" \
  "hybrid=/Users/andy/Desktop/wiki/docs/.mdrag:hybrid" \
  --output EVAL_REPORT.md
```

`/tmp/mdrag-baseline` is a preserved snapshot of the pre-chunking single-vector-per-doc index. Don't delete it — it's the A/B control for future quality changes.

---

## Open issues

The v0.1.0 failures (Q1 / Q3 / Q12) are all resolved in v0.2.0 — see Round 4 above. The suite is now at 100% hybrid Recall@5. **Expand the eval suite** before declaring anything "done" based on these numbers; 15 queries is thin and any structural change should be validated against a larger set.

Known gaps not covered by the current eval:
- **Non-Markdown source formats** (PDF / DOCX / PPTX / XLSX) — intentional non-feature. Convert upstream with pandoc / Docling / markitdown and point mdrag at the resulting `.md`. See the FAQ in `README.md` for the recommended workflow.
- **Cross-vault search** — `search(vaults=[...], ...)`. Still useful; still blocked on not having an eval query that demonstrates the gap.
- **Multi-hop / reasoning queries** — not in the eval suite at all. If users report failures here, extend `tests/eval-queries.yaml` first, then decide on a re-ranker.

---

## How to run things

**Set up from a fresh clone**:
```bash
cd mdrag
pipx install -e ".[dev]"
# or: python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

**Run tests** (35 tests, all should pass):
```bash
/Users/andy/.local/pipx/venvs/mdrag/bin/pytest tests/
```

**Reindex the dev vault** after code changes to `chunking.py` / `indexer.py` / `retrieval.py`:
```bash
mdrag vault reindex wiki --full
```
Note: `--full` rebuilds from scratch (~25s on the 408-doc wiki). Incremental-only runs (no `--full`) won't rebuild BM25 from changed chunks' sibling chunks, so after schema-affecting changes always use `--full`.

**Iterate on retrieval quality**: edit code → `reindex --full` → `mdrag eval ...` → read `EVAL_REPORT.md`. That's the whole loop.

**Register MCP with Claude Code** (already done on author's machine):
```bash
claude mcp add mdrag --scope user -- mdrag serve
```

---

## Dev conventions worth knowing

- **Commit messages** follow what's in `git log`: `type: imperative summary`, then a bullet list of *what* + *why* + a numeric result line when relevant. See `5a0a1af` / `17fd560` for the house style.
- **Feature tracking**: no issue tracker; eval report is the truth. If a behavior change doesn't move an eval number, either write a query that would catch it or reconsider the change.
- **Editable install via pipx**: the CLI (`mdrag`) on this machine is wired to `src/mdrag/` through `pipx install -e .` — code edits take effect immediately, no reinstall needed.

---

## Where things live outside the repo

- **Vault registry**: `~/.mdrag/vaults.yaml`
- **Author's dev vault**: `/Users/andy/Desktop/wiki/docs/` (vault name: `wiki`)
- **Baseline index snapshot**: `/tmp/mdrag-baseline/docs.lance/` (do not delete)
- **Sample vault for tests**: `examples/sample-vault/`

---

## Next up — recommended priorities

1. **Ship v0.3.0 to PyPI** — rebuild dist (`python -m build`), `twine check`, `twine upload`. CHANGELOG.md is up to date through v0.3.0.
2. **Grow the eval suite to ≥50 queries** — add multi-hop queries, English-only queries against bilingual docs, negation/exclusion queries, queries where the expected doc has sparse frontmatter. Current 15 is too thin for statistical claims. Consider semi-automating via a small LLM generating candidate queries from the corpus, human-filtered.
3. **E5: vault-level config overrides** — `MAX_CHARS=600`, `RRF_K=60`, `DEBOUNCE_SECONDS=1.5` are hardcoded. Add optional `config:` block in `vaults.yaml` per-vault; `mdrag vault config NAME KEY VAL` CLI. Low urgency, but unblocks power users tuning per-corpus.
4. **Optional: reranker (bge-reranker-base)** — only revisit if the expanded eval suite uncovers cases hybrid can't solve. ~200ms latency tax per query.
5. **Optional: multi-vault search** — `search(vaults=["a","b"], ...)`. Trivial given doc-level fusion already exists; blocked on lack of a cross-vault eval query.
6. **Optional: incremental BM25** — currently rebuilt full on every reindex. Fine up to a few thousand docs; worth patching the inverted index incrementally once a vault crosses ~10K docs.

Don't commit to 4, 5, or 6 without an eval query demonstrating the gap they'd close.
