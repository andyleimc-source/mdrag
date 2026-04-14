"""Vault registry tests using a temporary registry file."""

from pathlib import Path

import pytest

from mdrag.config import VaultRegistry, DEFAULT_MODEL


def _reg(tmp_path: Path) -> VaultRegistry:
    return VaultRegistry(path=tmp_path / "vaults.yaml")


def test_add_and_list(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    reg = _reg(tmp_path)
    v = reg.add("mynotes", str(docs))
    assert v.name == "mynotes"
    assert v.path == str(docs.resolve())
    assert v.model == DEFAULT_MODEL
    assert len(reg.list()) == 1


def test_add_duplicate_raises(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    reg = _reg(tmp_path)
    reg.add("x", str(docs))
    with pytest.raises(ValueError):
        reg.add("x", str(docs))


def test_add_missing_dir_raises(tmp_path: Path):
    reg = _reg(tmp_path)
    with pytest.raises(ValueError):
        reg.add("bad", str(tmp_path / "nonexistent"))


def test_persistence(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    reg = _reg(tmp_path)
    reg.add("mynotes", str(docs))

    reg2 = VaultRegistry(path=tmp_path / "vaults.yaml")
    assert "mynotes" in reg2.vaults
    assert reg2.get("mynotes").path == str(docs.resolve())


def test_remove(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    reg = _reg(tmp_path)
    reg.add("mynotes", str(docs))
    reg.remove("mynotes")
    reg.save()
    assert reg.list() == []


def test_get_missing_raises(tmp_path: Path):
    reg = _reg(tmp_path)
    with pytest.raises(KeyError):
        reg.get("nope")
