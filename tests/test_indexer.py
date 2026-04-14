"""Basic indexer tests — run on the sample vault shipped with the repo."""

from pathlib import Path

import pytest

from wiki_mcp.indexer import iter_markdown_files, parse_frontmatter, DEFAULT_EXCLUDES


REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_VAULT = REPO_ROOT / "examples" / "sample-vault"


def test_iter_markdown_files_finds_sample_vault():
    files = list(iter_markdown_files(SAMPLE_VAULT))
    assert len(files) >= 3
    assert all(p.suffix == ".md" for p in files)


def test_iter_markdown_files_excludes_default_dirs(tmp_path: Path):
    (tmp_path / "keep.md").write_text("# keep")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "skip.md").write_text("# skip")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.md").write_text("# skip")

    found = {p.name for p in iter_markdown_files(tmp_path)}
    assert found == {"keep.md"}


def test_parse_frontmatter_roundtrip():
    text = "---\ntitle: Hello\ntags: [a, b]\n---\n\nBody"
    meta, body = parse_frontmatter(text)
    assert meta == {"title": "Hello", "tags": ["a", "b"]}
    assert body.strip() == "Body"


def test_parse_frontmatter_without_frontmatter():
    text = "# Just a heading\n\nBody"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_default_excludes_includes_expected():
    assert ".wiki-mcp" in DEFAULT_EXCLUDES
    assert ".git" in DEFAULT_EXCLUDES
    assert "node_modules" in DEFAULT_EXCLUDES
