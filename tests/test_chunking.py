from mdrag.chunking import split_markdown


def test_short_doc_single_chunk():
    body = "# 标题\n这是一篇很短的文档，只有几十个字。"
    chunks = split_markdown(body)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == 0
    assert chunks[0].heading_path == ""


def test_empty_doc_returns_empty():
    assert split_markdown("") == []
    assert split_markdown("   \n\n   ") == []


def test_heading_based_split():
    body = (
        "## 第一部分\n" + "内容一" * 120 + "\n\n"
        "## 第二部分\n" + "内容二" * 120 + "\n\n"
        "## 第三部分\n" + "内容三" * 120
    )
    chunks = split_markdown(body)
    assert len(chunks) >= 3
    heading_paths = {c.heading_path for c in chunks}
    assert "第一部分" in heading_paths
    assert "第二部分" in heading_paths
    assert "第三部分" in heading_paths


def test_nested_heading_path():
    body = (
        "# 第一章\n" + "介绍" * 200 + "\n\n"
        "## 小节A\n" + "A内容" * 200 + "\n\n"
        "### 子节A1\n" + "A1内容" * 200
    )
    chunks = split_markdown(body)
    paths = [c.heading_path for c in chunks]
    assert any("第一章 › 小节A" in p for p in paths)
    assert any("第一章 › 小节A › 子节A1" in p for p in paths)


def test_long_section_window_split():
    body = "## 长节\n" + ("超长内容" * 500)
    chunks = split_markdown(body, max_chars=600, overlap=80)
    assert len(chunks) > 1
    for c in chunks:
        assert c.heading_path == "长节"
        assert len(c.text) <= 600


def test_no_headings_long_doc():
    body = "纯文本内容没有标题结构。" * 200
    chunks = split_markdown(body, max_chars=500, overlap=60)
    assert len(chunks) > 1
    for c in chunks:
        assert c.heading_path == ""


def test_chunk_ids_contiguous():
    body = "## A\n" + "x" * 800 + "\n\n## B\n" + "y" * 800
    chunks = split_markdown(body)
    ids = [c.chunk_id for c in chunks]
    assert ids == list(range(len(chunks)))


def test_heading_pop_on_same_level():
    body = (
        "## A\n" + "a" * 200 + "\n\n"
        "## B\n" + "b" * 200 + "\n\n"
        "## C\n" + "c" * 200
    )
    chunks = split_markdown(body)
    paths = [c.heading_path for c in chunks]
    assert paths == ["A", "B", "C"]


def test_min_split_threshold():
    body = "短文" * 50
    chunks = split_markdown(body, min_split_chars=400)
    assert len(chunks) == 1
