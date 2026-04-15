import time
from pathlib import Path

from mdrag.config import VaultRegistry
from mdrag.watcher import start_watchers, stop_watchers


def test_watcher_detects_change(tmp_path: Path, monkeypatch):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "hello.md").write_text("---\ntitle: hi\n---\nbody")

    registry = VaultRegistry(path=tmp_path / "registry.yaml")
    registry.add("t", str(vault_dir))

    calls: list[tuple[str]] = []

    def fake_build_index(vault_path, vector_dir, model_name, full_rebuild):
        calls.append((str(vault_path),))

        class S:
            updated_docs = 1
            total_chunks = 1

        return S()

    monkeypatch.setattr("mdrag.watcher.build_index", fake_build_index)
    monkeypatch.setattr("mdrag.watcher.DEBOUNCE_SECONDS", 0.1)

    observers = start_watchers(registry)
    try:
        time.sleep(0.2)
        (vault_dir / "hello.md").write_text("---\ntitle: hi\n---\nupdated body")
        time.sleep(0.6)
    finally:
        stop_watchers(observers)

    assert len(calls) >= 1


def test_watcher_skips_non_md(tmp_path: Path, monkeypatch):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()

    registry = VaultRegistry(path=tmp_path / "registry.yaml")
    registry.add("t", str(vault_dir))

    calls = []
    monkeypatch.setattr(
        "mdrag.watcher.build_index",
        lambda **_: calls.append(1) or type("S", (), {"updated_docs": 0, "total_chunks": 0})(),
    )
    monkeypatch.setattr("mdrag.watcher.DEBOUNCE_SECONDS", 0.1)

    observers = start_watchers(registry)
    try:
        time.sleep(0.2)
        (vault_dir / "note.txt").write_text("not markdown")
        time.sleep(0.4)
    finally:
        stop_watchers(observers)

    assert len(calls) == 0
