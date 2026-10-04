import json

import pytest

from qwen_agent.tools import ExtractDocVocabulary


def test_extract_doc_vocabulary_cache_roundtrip(tmp_path, monkeypatch):
    """Regression test: the cached vocabulary must be identical to the freshly
    computed one. The cache is written with json.dumps but read back verbatim
    by Storage.get, so the second call returned an extra pair of quotes."""
    pytest.importorskip("sklearn.feature_extraction.text")

    tool = ExtractDocVocabulary(cfg={"path": str(tmp_path)})

    def fake_parse(params, **kwargs):
        return "alpha beta gamma alpha beta"

    monkeypatch.setattr(tool, "simple_doc_parse", type("Stub", (), {"call": staticmethod(fake_parse)})())

    files = ["fake_a.txt", "fake_b.txt"]
    first = tool.call({"files": files})
    second = tool.call({"files": files})

    assert second == first
    assert not (second.startswith('"') and second.endswith('"'))


def test_extract_doc_vocabulary_migrates_legacy_quoted_cache(tmp_path, monkeypatch):
    """Regression test: cache entries written by the old code (json.dumps-encoded)
    must be decoded and migrated on read, instead of being returned quoted forever."""
    pytest.importorskip("sklearn.feature_extraction.text")

    tool = ExtractDocVocabulary(cfg={"path": str(tmp_path)})

    def fake_parse(params, **kwargs):
        return "alpha beta gamma alpha beta"

    monkeypatch.setattr(tool, "simple_doc_parse", type("Stub", (), {"call": staticmethod(fake_parse)})())

    files = ["fake_a.txt", "fake_b.txt"]
    fresh = tool.call({"files": files})
    assert not fresh.startswith('"')

    # 预填旧格式缓存，精确模拟旧版本写入的 json.dumps 编码值
    legacy = json.dumps(fresh, ensure_ascii=False)
    tool.db.call({"operate": "put", "key": str(files), "value": legacy})

    migrated = tool.call({"files": files})
    assert migrated == fresh
    assert not (migrated.startswith('"') and migrated.endswith('"'))

    # 回写迁移后，缓存内容已是纯文本，再次读取结果保持一致
    assert tool.call({"files": files}) == fresh
