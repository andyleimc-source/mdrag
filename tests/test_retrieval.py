from mdrag.retrieval import BM25, BM25Store, best_rank_fuse, rrf_fuse, tokenize


def test_tokenize_english_lowercase():
    assert tokenize("Hello World 123") == ["hello", "world", "123"]


def test_tokenize_chinese_char_level():
    assert tokenize("明道云") == ["明", "道", "云"]


def test_tokenize_mixed():
    assert tokenize("明道云 HAP v2") == ["明", "道", "云", "hap", "v", "2"]


def test_bm25_basic_ranking():
    corpus = [
        ["hap", "platform", "low", "code"],
        ["明", "道", "云", "低", "代", "码"],
        ["random", "unrelated", "document"],
    ]
    bm25 = BM25(corpus)
    hits = bm25.top_k(["hap"], k=3)
    assert hits[0][0] == 0
    assert hits[0][1] > 0


def test_bm25_unknown_terms_return_nothing():
    corpus = [["hap"], ["low", "code"]]
    bm25 = BM25(corpus)
    assert bm25.top_k(["unknownterm"], k=5) == []


def test_bm25store_roundtrip(tmp_path):
    chunks = [
        {"doc_path": "a.md", "chunk_id": 0, "title": "A", "heading_path": "", "chunk_text": "hap platform"},
        {"doc_path": "b.md", "chunk_id": 0, "title": "B", "heading_path": "", "chunk_text": "unrelated content"},
    ]
    store = BM25Store.build(chunks)
    p = tmp_path / "bm25.pkl"
    store.save(p)
    loaded = BM25Store.load(p)
    hits = loaded.search("hap", k=5)
    assert hits[0][0]["doc_path"] == "a.md"


def test_rrf_prefers_consistently_ranked():
    vec = [("doc1", 0), ("doc2", 0), ("doc3", 0)]
    bm25 = [("doc2", 0), ("doc1", 0), ("doc3", 0)]
    fused = rrf_fuse([vec, bm25])
    keys = [k for k, _ in fused]
    assert keys[0] in [("doc1", 0), ("doc2", 0)]
    assert keys[-1] == ("doc3", 0)


def test_rrf_recovers_unique_hits():
    vec = [("doc1", 0), ("doc2", 0)]
    bm25 = [("doc3", 0), ("doc4", 0)]
    fused = rrf_fuse([vec, bm25])
    keys = {k for k, _ in fused}
    assert keys == {("doc1", 0), ("doc2", 0), ("doc3", 0), ("doc4", 0)}


def test_best_rank_fuse_preserves_strong_single_signal():
    vec = ["a", "b", "c"]
    bm25 = ["x", "y", "a"]
    fused = best_rank_fuse([vec, bm25])
    assert fused[0][0] == "a"


def test_best_rank_fuse_rewards_agreement():
    vec = ["a", "b", "c"]
    bm25 = ["b", "a", "c"]
    fused = best_rank_fuse([vec, bm25])
    keys_ranked = [k for k, _ in fused]
    assert keys_ranked[0] in ("a", "b")
