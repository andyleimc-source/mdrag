"""Vault registry: reads/writes ~/.mdrag/vaults.yaml."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

CONFIG_DIR = Path.home() / ".mdrag"
REGISTRY_FILE = CONFIG_DIR / "vaults.yaml"
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
VAULT_DATA_DIR = ".mdrag"


@dataclass
class Vault:
    name: str
    path: str
    model: str = DEFAULT_MODEL
    indexed_at: Optional[str] = None
    doc_count: int = 0

    @property
    def root(self) -> Path:
        return Path(self.path).expanduser().resolve()

    @property
    def vector_dir(self) -> Path:
        return self.root / VAULT_DATA_DIR


class VaultRegistry:
    def __init__(self, path: Path = REGISTRY_FILE):
        self.path = path
        self.vaults: dict[str, Vault] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        for name, info in (data.get("vaults") or {}).items():
            self.vaults[name] = Vault(name=name, **info)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"vaults": {v.name: {k: val for k, val in asdict(v).items() if k != "name"} for v in self.vaults.values()}}
        self.path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=True), encoding="utf-8")

    def add(self, name: str, path: str, model: str = DEFAULT_MODEL) -> Vault:
        if name in self.vaults:
            raise ValueError(f"vault '{name}' already exists")
        root = Path(path).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"path is not a directory: {root}")
        vault = Vault(name=name, path=str(root), model=model)
        self.vaults[name] = vault
        self.save()
        return vault

    def get(self, name: str) -> Vault:
        if name not in self.vaults:
            raise KeyError(f"vault '{name}' not found (registered: {list(self.vaults)})")
        return self.vaults[name]

    def remove(self, name: str) -> Vault:
        return self.vaults.pop(name)

    def update_stats(self, name: str, doc_count: int) -> None:
        v = self.get(name)
        v.doc_count = doc_count
        v.indexed_at = datetime.now().isoformat(timespec="seconds")
        self.save()

    def list(self) -> list[Vault]:
        return list(self.vaults.values())
