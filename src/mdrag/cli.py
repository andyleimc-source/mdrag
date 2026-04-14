"""mdrag CLI entry point."""

from __future__ import annotations


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
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Embedding model.")
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

    reg.update_stats(name, stats.total)
    click.echo(
        f"✅ Indexed {stats.total} docs ({stats.updated} updated) in {stats.elapsed_seconds:.1f}s"
    )


if __name__ == "__main__":
    main()
