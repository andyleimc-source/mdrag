"""File-system watcher: auto-reindex vaults when their .md files change."""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import Vault, VaultRegistry
from .indexer import DEFAULT_EXCLUDES, build_index

DEBOUNCE_SECONDS = 1.5


@dataclass
class WatcherStatus:
    """Tracks per-vault reindex health so MCP tools can surface failures."""
    last_success_at: str | None = None
    last_error_at: str | None = None
    last_error_message: str | None = None
    consecutive_errors: int = 0


# Global status map: vault name → latest watcher health.
# Read by server.list_vaults so clients see watcher failures instead of silently
# querying stale data.
STATUS: dict[str, WatcherStatus] = {}


def get_status(vault_name: str) -> WatcherStatus:
    return STATUS.setdefault(vault_name, WatcherStatus())


class _VaultWatcher:
    def __init__(self, vault: Vault, on_reindex: Callable[[str], None] | None):
        self.vault = vault
        self._exclude_set = set(DEFAULT_EXCLUDES)
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._on_reindex = on_reindex

    def _is_relevant(self, path: str) -> bool:
        p = Path(path)
        if p.suffix != ".md":
            return False
        try:
            rel = p.relative_to(self.vault.root)
        except ValueError:
            return False
        return not any(part in self._exclude_set for part in rel.parts)

    def handle(self, path: str) -> None:
        if not self._is_relevant(path):
            return
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._reindex)
            self._timer.daemon = True
            self._timer.start()

    def _reindex(self) -> None:
        status = get_status(self.vault.name)
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            stats = build_index(
                vault_path=self.vault.root,
                vector_dir=self.vault.vector_dir,
                model_name=self.vault.model,
                full_rebuild=False,
            )
            status.last_success_at = now
            status.last_error_at = None
            status.last_error_message = None
            status.consecutive_errors = 0
            print(
                f"[mdrag] auto-reindexed '{self.vault.name}': "
                f"{stats.updated_docs} docs updated ({stats.total_chunks} chunks)",
                file=sys.stderr,
            )
            if self._on_reindex:
                self._on_reindex(self.vault.name)
        except Exception as e:
            status.last_error_at = now
            status.last_error_message = f"{type(e).__name__}: {e}"
            status.consecutive_errors += 1
            print(
                f"[mdrag] watcher error on '{self.vault.name}' "
                f"(consecutive={status.consecutive_errors}): {e}",
                file=sys.stderr,
            )


class _Handler(FileSystemEventHandler):
    def __init__(self, watcher: _VaultWatcher):
        self.watcher = watcher

    def _dispatch(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self.watcher.handle(event.src_path)

    def on_created(self, event):
        self._dispatch(event)

    def on_modified(self, event):
        self._dispatch(event)

    def on_deleted(self, event):
        self._dispatch(event)

    def on_moved(self, event):
        self._dispatch(event)
        if getattr(event, "dest_path", None):
            self.watcher.handle(event.dest_path)


def start_watchers(
    registry: VaultRegistry,
    on_reindex: Callable[[str], None] | None = None,
) -> list[Observer]:
    """Start one watchdog Observer per registered vault. Returns list for later shutdown."""
    observers: list[Observer] = []
    for v in registry.list():
        if not v.root.is_dir():
            print(
                f"[mdrag] skipping watcher for '{v.name}': path not found ({v.root})",
                file=sys.stderr,
            )
            continue
        watcher = _VaultWatcher(v, on_reindex)
        observer = Observer()
        observer.schedule(_Handler(watcher), str(v.root), recursive=True)
        observer.daemon = True
        observer.start()
        print(f"[mdrag] watching '{v.name}' at {v.root}", file=sys.stderr)
        observers.append(observer)
    return observers


def stop_watchers(observers: list[Observer]) -> None:
    for o in observers:
        try:
            o.stop()
            o.join(timeout=2)
        except Exception:
            pass
