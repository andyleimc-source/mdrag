"""File-system watcher: auto-reindex vaults when their .md files change."""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config import Vault, VaultRegistry
from .indexer import DEFAULT_EXCLUDES, build_index

DEBOUNCE_SECONDS = 1.5


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
        try:
            stats = build_index(
                vault_path=self.vault.root,
                vector_dir=self.vault.vector_dir,
                model_name=self.vault.model,
                full_rebuild=False,
            )
            print(
                f"[mdrag] auto-reindexed '{self.vault.name}': "
                f"{stats.updated_docs} docs updated ({stats.total_chunks} chunks)",
                file=sys.stderr,
            )
            if self._on_reindex:
                self._on_reindex(self.vault.name)
        except Exception as e:
            print(f"[mdrag] watcher error on '{self.vault.name}': {e}", file=sys.stderr)


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
