"""Basic indexer tests — run on the sample vault shipped with the repo."""

from pathlib import Path


from mdrag.indexer import (
    DEFAULT_EXCLUDES,
    iter_markdown_files,
    load_ignore_spec,
    parse_frontmatter,
    partition_by_ignore,
)


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
    assert ".mdrag" in DEFAULT_EXCLUDES
    assert ".git" in DEFAULT_EXCLUDES
    assert "node_modules" in DEFAULT_EXCLUDES


def test_ignore_spec_missing_returns_none(tmp_path: Path):
    assert load_ignore_spec(tmp_path) is None


def test_ignore_spec_filters_files(tmp_path: Path):
    (tmp_path / "keep.md").write_text("# keep")
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "wip.md").write_text("# wip")
    (tmp_path / "ignore-me.md").write_text("# noise")
    (tmp_path / ".mdragignore").write_text("drafts/\nignore-me.md\n")

    kept = {p.name for p in iter_markdown_files(tmp_path)}
    assert kept == {"keep.md"}

    kept_list, ignored_list = partition_by_ignore(tmp_path)
    assert {p.name for p in ignored_list} == {"wip.md", "ignore-me.md"}
    assert {p.name for p in kept_list} == {"keep.md"}


def test_ignore_spec_glob_patterns(tmp_path: Path):
    (tmp_path / "a.md").write_text("# a")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "meeting-2024-01.md").write_text("# old")
    (tmp_path / "notes" / "meeting-2026-01.md").write_text("# new")
    (tmp_path / ".mdragignore").write_text("notes/meeting-2024-*.md\n")

    kept = {p.relative_to(tmp_path).as_posix() for p in iter_markdown_files(tmp_path)}
    assert kept == {"a.md", "notes/meeting-2026-01.md"}
