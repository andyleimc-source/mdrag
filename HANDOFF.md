# mdrag Handoff

Snapshot of the current state of mdrag after three rounds of work. Written so the next contributor (possibly future-you, possibly a new Claude session) can pick up without re-deriving anything.

---

## What mdrag is

A local MCP server that turns any Markdown folder into a semantic-search vault. Fully offline, no API keys. See `README.md` for the user-facing pitch.

**Current version**: 0.1.0 (not yet published to PyPI)
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
| vector only (new chunked) | 73.3% | 80% | 60% | 0.54 |
| bm25 only | 80.0% | 100% | 40% | 0.64 |
| **hybrid (default)** | **80.0%** | 90% | 60% | 0.62 |

Hybrid is the balanced default: never loses big on either query type. BM25 alone peaks on needle but regresses general. Vector alone is the opposite.

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

## Open issues — things eval still flags

These are the rows in `EVAL_REPORT.md` that come back as `—` for every mode. Real signal for what to work on next.

- **Q1 "明道云核心功能介绍"** — all chunked modes miss this. Broad concept query where baseline's single-vector-per-doc design accidentally helped (the overview chunk gets diluted by many specific-feature chunks from other docs). Likely fix: boost overview chunks' score in ranking, or switch to a larger model with longer context.
- **Q3 "HAP 产品与低代码平台的区别"** — comparison query, no mode finds the specific doc because "comparison" as a semantic intent is broadly distributed across the corpus. Probably needs either a comparison-oriented query expansion step or a re-ranker.
- **Q12 "明道云 38 种字段控件类型易用性设计"** — BM25 finds at #3 but hybrid pushes it out of top-5 because vector's top picks crowd. Worth experimenting with a smaller RRF k or giving BM25 higher weight for queries with rare-term signatures.

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

1. **Chase down Q1/Q3/Q12 misses** — real failures the eval flags. Overview-chunk score boost is the cheapest first attempt (~5 lines in `retrieval.py`). Validation is free: rerun eval.
2. **PyPI release** — nothing blocks it. Bump version in `pyproject.toml`, write a CHANGELOG section covering the three feature rounds, `python -m build && twine upload`. README is already user-facing.
3. **Optional: reranker (bge-reranker-base)** — was in the P2 pile. Worth it only if we can't push hybrid past 85% with cheaper tweaks. ~200ms latency tax per query.
4. **Optional: multi-vault search** — `search(vaults=["a","b"], ...)`. Popular ask in RAG tools; trivial to implement given the doc-level fusion we already have.

Don't commit to 3 or 4 without an eval query demonstrating the gap they'd close.
