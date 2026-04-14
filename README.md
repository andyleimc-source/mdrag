# mdrag

> Give any local Markdown folder a semantic-search MCP server. Runs entirely offline.

Turn `~/Desktop/sales/`, `~/Desktop/notes/`, or any directory full of Markdown files into a searchable knowledge base that [Claude Code](https://claude.ai/code), Cursor, Cline, and other MCP clients can query with natural-language questions.

- 🗂 **Multi-vault**: one MCP server manages many doc folders, each a separate "vault"
- 🔒 **Fully local**: no API keys, no cloud — embeddings run on your machine
- ⚡ **Incremental indexing**: only re-embed files that changed
- 🧠 **Any embedding model**: default is Chinese-optimized `bge-small-zh-v1.5`; English / multilingual models work too
- 📦 **Self-contained**: each vault's vector DB lives inside the folder (`.mdrag/`), move it anywhere

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
| `search(vault, query, top_k=5, tags="")` | Semantic search within a vault, optional tag filter |
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
| Chinese | `BAAI/bge-small-zh-v1.5` (default) | ~100MB, CPU-friendly |
| English | `BAAI/bge-small-en-v1.5` | Same family, English |
| Multilingual | `paraphrase-multilingual-MiniLM-L12-v2` | For mixed-language vaults |
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
```bash
mdrag vault reindex sales
```
It's incremental — only files with changed `mtime` are re-embedded.

### Can I automate re-indexing?
Yes. Add to cron (Linux/macOS):
```
0 * * * * /path/to/mdrag vault reindex sales
```
Or use `launchd` on macOS / Task Scheduler on Windows.

### Does it support PDF, DOCX, etc.?
Not yet. Convert to Markdown first (e.g. with [pandoc](https://pandoc.org/)) and point mdrag at the result.

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
