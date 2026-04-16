# mdrag

> Give any local Markdown folder a semantic-search MCP server. Runs entirely offline.

Turn `~/Desktop/sales/`, `~/Desktop/notes/`, or any directory full of Markdown files into a searchable knowledge base that [Claude Code](https://claude.ai/code), Cursor, Cline, and other MCP clients can query with natural-language questions.

## Features

### Storage & indexing
- 🗂 **Multi-vault** — one MCP server manages many doc folders, each a separate "vault"
- 📦 **Self-contained** — each vault's vector DB lives inside the folder (`.mdrag/`), move it anywhere
- ⚡ **Incremental indexing** — only re-embed files whose `mtime` changed
- 👀 **Auto-reindex on save** — `mdrag serve` watches every registered vault with `watchdog`, 1.5s debounce; new/edited/deleted/moved `.md` files are picked up with no manual reindex, no cron
- 🙈 **`.mdragignore`** — gitignore-style file at the vault root excludes drafts, archives, or whole directories from the index

### Retrieval quality
- ✂️ **Chunk-level retrieval** — long docs are split by headings (sliding-window fallback at 600 chars / 80 overlap) so mid-doc content stays findable; each doc also gets an "overview" chunk for broad queries
- 🔀 **Hybrid search** — dense vector retrieval fused with BM25 keyword matching via best-rank fusion, so specific terms and semantic intent both get through
- 🎯 **Rare-term boost** — queries containing digit strings (e.g. "38 种字段") switch to a BM25-priority fusion so exact-match lookups aren't buried by vector results
- 🌐 **Cross-lingual query expansion** — comparison-style queries ("区别", "对比", "compare", "vs") get auto-expanded with bilingual synonyms before embedding, improving recall on mixed-language corpora
- 🧠 **Any embedding model** — default is multilingual `paraphrase-multilingual-MiniLM-L12-v2` (handles Chinese + English + 50 more); swap in any `sentence-transformers` model

### Stability
- 🔐 **File-locking** — concurrent CLI + watcher reindexes on the same vault are serialized via `filelock`, preventing LanceDB corruption
- 📋 **Schema versioning** — `meta.json` in each `.mdrag/` dir tracks schema version and model; mismatches are caught early with an actionable error
- 🩺 **`mdrag doctor`** — one command to check everything: Python, registry, per-vault health, model cache, disk usage, PATH; paste the output into bug reports
- 📡 **Watcher health in MCP** — `list_vaults` shows a ⚠️ if a vault's auto-reindex is failing (consecutive errors + message), instead of silently serving stale data

### Interface
- 🔒 **Fully local** — no API keys, no cloud; embeddings run on your machine
- 🛠 **MCP tools** — `list_vaults`, `search`, `get_doc`, `list_tags` exposed to Claude Code / Cursor / Cline over stdio
- 💡 **Match explainability** — each search result includes `match_reason` ("vector+bm25", "bm25 (rare-term)", "bm25 only", "vector only") so AI clients can explain or re-rank
- 📏 **Quality eval harness** — `mdrag eval` compares any set of indexes on a YAML query suite; Recall@K, MRR, per-query ranking diff
- 🏷 **Frontmatter-aware** — `title`, `tags`, `summary` from YAML frontmatter are indexed and searchable

---

## Installation

```bash
pip install mdrag
```

Requires Python ≥ 3.10.

---

## Quickstart (3 steps)

Let's say Bob has a folder `~/Desktop/sales/` full of meeting notes, proposals, and competitor research in Markdown.

### 1. Register the MCP server (once, globally)

```bash
claude mcp add mdrag --scope user -- mdrag serve
```

This tells Claude Code "there's an MCP server called `mdrag` — launch it with `mdrag serve` when needed". You'll only do this once per machine.

### 2. Register your doc folder as a vault

```bash
mdrag vault add sales ~/Desktop/sales
```

The first time you run this, a ~100MB embedding model downloads (once), then all `.md` files under `~/Desktop/sales/` get indexed. A `.mdrag/` subfolder is created inside `sales/` to hold the vector database.

### 3. Use it from Claude Code

Open Claude Code in any project. Ask:

> "Use the mdrag MCP to search my sales vault for the Q4 pipeline review"

Claude will call `mcp__mdrag__search(vault="sales", query="Q4 pipeline review")` and return the top matching documents.

---

## Adding another folder

No new MCP config needed — just register another vault:

```bash
mdrag vault add marketing ~/Desktop/marketing
mdrag vault add notes ~/Documents/notes
```

All vaults are visible through the same MCP server. Claude calls:
```
mcp__mdrag__list_vaults()                          → see all vaults
mcp__mdrag__search(vault="marketing", query="...")
mcp__mdrag__search(vault="notes", query="...")
```

---

## CLI reference

```
mdrag serve                          Start the MCP stdio server
mdrag vault add NAME PATH            Register a directory and index it
mdrag vault list                     Show all vaults
mdrag vault info NAME                Show vault details
mdrag vault reindex NAME [--full]    Re-index (incremental or full)
mdrag vault remove NAME [--purge]    Unregister (and optionally delete .mdrag/)
mdrag eval QUERIES INDEX_SPECS...    Compare retrieval quality across indexes
```

Common options:
- `--model MODEL_NAME` on `vault add` — pick a different embedding model
- `--no-index` on `vault add` — skip initial indexing (useful when first adding, want to index later)
- `--full` on `vault reindex` — rebuild from scratch (required after changing the model)

---

## MCP tools exposed

When `mdrag serve` is running, these tools are available to the AI client:

| Tool | Purpose |
|------|---------|
| `list_vaults()` | List all registered vaults with their stats |
| `search(vault, query, top_k=5, tags="")` | Semantic search within a vault; returns the best-matching chunk per doc with `heading_path` and `chunk_text` |
| `get_doc(vault, path)` | Read the full content of a document |
| `list_tags(vault)` | List all frontmatter tags in a vault with counts |

---

## Frontmatter (optional)

If your Markdown files have YAML frontmatter, mdrag will use it:

```markdown
---
title: Q4 Pipeline Review
tags: [sales, forecast, 2026-q4]
summary: Overview of deals in play for Q4 2026.
---

# Q4 Pipeline Review
...
```

- `title` — used as the result title (falls back to filename)
- `tags` — searchable via the `tags` parameter of `search`
- `summary` — shown in search results

No frontmatter? It still works — mdrag auto-generates a preview from the file body.

---

## Embedding models

| Language | Recommended model | Notes |
|----------|------------------|-------|
| Multilingual (default) | `paraphrase-multilingual-MiniLM-L12-v2` | ~120MB, handles Chinese + English + 50 more |
| Chinese-only | `BAAI/bge-small-zh-v1.5` | ~100MB, higher recall on pure Chinese |
| English-only | `BAAI/bge-small-en-v1.5` | ~100MB, higher recall on pure English |
| Higher accuracy | `BAAI/bge-base-zh-v1.5` or `-en` | ~400MB, noticeably slower |

Change the model when registering a vault:
```bash
mdrag vault add notes ~/Documents/notes --model BAAI/bge-small-en-v1.5
```

After changing the model on an existing vault (edit `~/.mdrag/vaults.yaml`), run a full rebuild:
```bash
mdrag vault reindex notes --full
```

---

## How it works

```
 ┌────────────────────┐        ┌──────────────────────┐
 │ ~/Desktop/sales/   │        │ ~/.mdrag/         │
 │   meeting-01.md    │        │   vaults.yaml        │  ← registry
 │   proposal.md      │        └──────────────────────┘
 │   .mdrag/       │ ← LanceDB vector store (per-vault)
 │     docs.lance/    │
 └──────────┬─────────┘
            │
            │ mdrag serve
            ▼
 ┌──────────────────────────┐
 │   FastMCP stdio server   │
 │   tools:                 │
 │     search / get_doc /   │
 │     list_vaults /        │
 │     list_tags            │
 └──────────┬───────────────┘
            │ MCP protocol (stdio / JSON-RPC)
            ▼
     Claude Code / Cursor / Cline
```

- Vault registry is at `~/.mdrag/vaults.yaml`
- Each vault's vector database lives inside the vault directory at `.mdrag/` — self-contained, portable
- Embeddings use `sentence-transformers`, stored in [LanceDB](https://lancedb.github.io/lancedb/)
- MCP server is built on [FastMCP](https://github.com/modelcontextprotocol/python-sdk)

---

## FAQ

### How do I update the index after editing files?
You don't have to. When `mdrag serve` is running (i.e. Claude Code / Cursor are connected), it watches every registered vault and auto-reindexes on save. A short debounce batches rapid edits.

If `serve` isn't running, run manual incremental:
```bash
mdrag vault reindex sales
```
Only files with changed `mtime` are re-embedded.

### How do I exclude files from the index?
Put a `.mdragignore` file at the root of your vault, using gitignore syntax:
```
# Example: drafts, archives, big log exports
drafts/
archive/**
**/sales-log-*.md
```
Takes effect on the next index run (auto-watch picks up the change too).

### Does it support PDF, DOCX, PPTX, XLSX, etc.?
Not directly — mdrag only indexes `.md`. This is by design: conversion is a messy, format-specific
problem, and keeping the core focused on Markdown keeps the index predictable. The recommended
workflow is to convert once, commit the `.md` output, and let mdrag watch it:

```bash
# One-off
pandoc meeting.docx -o docs/meeting.md
pandoc slides.pptx  -o docs/slides.md --extract-media=docs/_media

# Bulk conversion with Docling (best quality for PDF/PPTX)
pip install docling
docling raw/*.pdf --to markdown --output docs/

# CSV → MD table
python -c "import csv,sys; [print('|'+'|'.join(r)+'|') for r in csv.reader(open(sys.argv[1]))]" data.csv > docs/data.md
```

**Important**: strip inline base64 images before indexing. A `data:image/...;base64,...` payload
can inflate a `.md` file to multi-MB and break chunking. With pandoc use `--extract-media=<dir>` or
post-process with `sed -E 's/!\[[^]]*\]\(data:image[^)]*\)/<!-- image -->/g'`.

### Model download is slow / fails
If you're in China, set a HuggingFace mirror:
```bash
export HF_ENDPOINT=https://hf-mirror.com
mdrag vault add sales ~/Desktop/sales
```

### Where is the vector data stored?
- Vault registry: `~/.mdrag/vaults.yaml`
- Each vault's vectors: `<vault_path>/.mdrag/docs.lance/`

### Can I share a vault across machines?
Yes — the `.mdrag/` folder is self-contained. Sync the whole vault directory (via Dropbox, rsync, git-lfs, whatever) and `mdrag vault add <name> <path>` on the other machine. No re-indexing needed as long as the embedding model matches.

---

## Integrations

### Claude Code

```bash
claude mcp add mdrag --scope user -- mdrag serve
```

Or manually in `~/.mcp.json`:
```json
{
  "mcpServers": {
    "mdrag": {
      "command": "mdrag",
      "args": ["serve"]
    }
  }
}
```

### Cursor / Cline / other MCP clients

Add the same stdio command to your client's MCP configuration. The command is `mdrag serve` — it communicates over stdio following the MCP protocol.

---

## Development

```bash
git clone https://github.com/andyleimc-source/mdrag
cd mdrag
python -m venv .venv
.venv/bin/pip install -e .[dev]
.venv/bin/pytest
```

Try the example vault shipped in the repo:
```bash
mdrag vault add demo ./examples/sample-vault
mdrag vault list
```

---

## License

[MIT](./LICENSE) — do whatever you want with it.
