"""mdrag CLI entry point."""

from __future__ import annotations

from pathlib import Path

import click

from . import __version__
from .config import DEFAULT_MODEL, VaultRegistry


@click.group()
@click.version_option(__version__, prog_name="mdrag")
def main() -> None:
    """Give any local Markdown folder a semantic-search MCP server."""


@main.command()
def serve() -> None:
    """Start the MCP stdio server (used by Claude Code, Cursor, etc.)."""
    from .server import run
    run()


@main.group()
def vault() -> None:
    """Manage vaults (registered document directories)."""


@vault.command("add")
@click.argument("name")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help=(
        "Embedding model. Recommended: "
        "'paraphrase-multilingual-MiniLM-L12-v2' (multilingual, default), "
        "'BAAI/bge-small-zh-v1.5' (Chinese), "
        "'BAAI/bge-small-en-v1.5' (English). "
        "Any sentence-transformers model on HuggingFace works."
    ),
)
@click.option("--no-index", is_flag=True, help="Skip initial indexing.")
def vault_add(name: str, path: str, model: str, no_index: bool) -> None:
    """Register a Markdown directory as a vault and index it."""
    reg = VaultRegistry()
    try:
        v = reg.add(name, path, model=model)
    except ValueError as e:
        raise click.ClickException(str(e))

    click.echo(f"✅ Registered vault '{name}' → {v.path}")
    click.echo(f"   Model: {model}")
    click.echo(f"   Data dir: {v.vector_dir}")

    if no_index:
        click.echo("Skipped indexing (--no-index). Run: mdrag vault reindex " + name)
        return

    _run_index(reg, name, full=True)


@vault.command("list")
def vault_list() -> None:
    """List all registered vaults."""
    reg = VaultRegistry()
    vaults = reg.list()
    if not vaults:
        click.echo("No vaults. Add one: mdrag vault add <name> <path>")
        return
    click.echo(f"{'NAME':<20} {'DOCS':>6} {'INDEXED':<20} PATH")
    for v in vaults:
        click.echo(f"{v.name:<20} {v.doc_count:>6} {(v.indexed_at or '-'):<20} {v.path}")


@vault.command("reindex")
@click.argument("name")
@click.option("--full", is_flag=True, help="Rebuild from scratch.")
def vault_reindex(name: str, full: bool) -> None:
    """Re-index a vault (incremental by default)."""
    reg = VaultRegistry()
    _run_index(reg, name, full=full)


@vault.command("remove")
@click.argument("name")
@click.option("--purge", is_flag=True, help="Also delete the .mdrag/ data dir.")
def vault_remove(name: str, purge: bool) -> None:
    """Unregister a vault."""
    import shutil

    reg = VaultRegistry()
    try:
        v = reg.get(name)
    except KeyError as e:
        raise click.ClickException(str(e))

    reg.remove(name)
    reg.save()
    click.echo(f"✅ Unregistered '{name}'")

    if purge and v.vector_dir.is_dir():
        shutil.rmtree(v.vector_dir)
        click.echo(f"🗑  Removed {v.vector_dir}")


@vault.command("info")
@click.argument("name")
def vault_info(name: str) -> None:
    """Show details of a single vault."""
    reg = VaultRegistry()
    try:
        v = reg.get(name)
    except KeyError as e:
        raise click.ClickException(str(e))
    click.echo(f"Name:       {v.name}")
    click.echo(f"Path:       {v.path}")
    click.echo(f"Model:      {v.model}")
    click.echo(f"Doc count:  {v.doc_count}")
    click.echo(f"Indexed at: {v.indexed_at or '(never)'}")
    click.echo(f"Data dir:   {v.vector_dir}")


@main.command("eval")
@click.argument("queries_yaml", type=click.Path(exists=True, dir_okay=False))
@click.argument("index_specs", nargs=-1, required=True)
@click.option("--top-k", default=5, show_default=True, type=int)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Embedding model (must match the one used to build each index).",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    default="EVAL_REPORT.md",
    show_default=True,
    help="Where to write the markdown report.",
)
def eval_cmd(
    queries_yaml: str,
    index_specs: tuple[str, ...],
    top_k: int,
    model: str,
    output: str,
) -> None:
    """Compare search quality across multiple LanceDB indexes.

    INDEX_SPECS are "label=/path[:mode]" tuples. `mode` is one of
    `hybrid` (default for chunked indexes), `vector`, or `bm25`.

    \b
    Example:
      mdrag eval queries.yaml \\
        baseline=/tmp/mdrag-baseline \\
        vector=/Users/me/docs/.mdrag:vector \\
        hybrid=/Users/me/docs/.mdrag:hybrid \\
        --output report.md
    """
    from .evaluator import run_eval

    indexes = []
    for spec in index_specs:
        if "=" not in spec:
            raise click.ClickException(f"expected 'label=path[:mode]', got: {spec}")
        label, rest = spec.split("=", 1)
        if ":" in rest:
            path, mode = rest.rsplit(":", 1)
        else:
            path, mode = rest, "hybrid"
        if mode not in ("hybrid", "vector", "bm25"):
            raise click.ClickException(f"invalid mode '{mode}' (use hybrid/vector/bm25)")
        p = Path(path).expanduser().resolve()
        if not p.is_dir():
            raise click.ClickException(f"index dir not found: {p}")
        indexes.append((label.strip(), p, mode))

    run_eval(
        queries_path=Path(queries_yaml),
        indexes=indexes,
        top_k=top_k,
        model_name=model,
        output_path=Path(output),
    )
    click.echo(f"✅ Report written to {output}")


def _run_index(reg: VaultRegistry, name: str, full: bool) -> None:
    from .indexer import build_index

    try:
        v = reg.get(name)
    except KeyError as e:
        raise click.ClickException(str(e))

    click.echo(f"Indexing '{name}' ({'full rebuild' if full else 'incremental'})...")
    try:
        stats = build_index(
            vault_path=v.root,
            vector_dir=v.vector_dir,
            model_name=v.model,
            full_rebuild=full,
        )
    except Exception as e:
        raise click.ClickException(f"indexing failed: {e}")

    reg.update_stats(name, stats.total_docs)
    click.echo(
        f"✅ Indexed {stats.total_docs} docs → {stats.total_chunks} chunks "
        f"({stats.updated_docs} docs updated) in {stats.elapsed_seconds:.1f}s"
    )
    if stats.ignored_docs:
        click.echo(f"ℹ️  Ignored {stats.ignored_docs} file(s) per .mdragignore")


if __name__ == "__main__":
    main()
