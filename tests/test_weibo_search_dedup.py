# -*- coding: utf-8 -*-

import pytest

import config
from store import weibo as weibo_store
from store.weibo.search_dedup import WeiboSearchDeduplicator
from var import crawler_type_var


class MemoryWeiboStore:
    def __init__(self):
        self.contents = []
        self.comments = []

    async def store_content(self, content_item):
        self.contents.append(dict(content_item))

    async def store_comment(self, comment_item):
        self.comments.append(dict(comment_item))


@pytest.mark.asyncio
async def test_weibo_search_dedup_reloads_and_copies_note_comments(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(config, "ENABLE_WEIBO_SEARCH_DEDUP", True)
    crawler_type_var.set("search")
    WeiboSearchDeduplicator._instance = None

    deduplicator = WeiboSearchDeduplicator.get_instance()
    await deduplicator.record_note(
        {
            "note_id": "123456",
            "content": "cached note",
            "source_keyword": "old keyword",
            "last_modify_ts": 1,
        }
    )
    await deduplicator.record_comment(
        "123456",
        {
            "comment_id": "999",
            "note_id": "123456",
            "content": "cached comment",
            "last_modify_ts": 1,
        },
    )

    WeiboSearchDeduplicator._instance = None
    memory_store = MemoryWeiboStore()
    monkeypatch.setattr(
        weibo_store.WeibostoreFactory,
        "create_store",
        staticmethod(lambda: memory_store),
    )

    assert await weibo_store.is_cached_weibo_note("123456") is True
    copied_count = await weibo_store.copy_cached_weibo_note_and_comments("123456", "new keyword")

    assert copied_count == 1
    assert memory_store.contents[0]["note_id"] == "123456"
    assert memory_store.contents[0]["source_keyword"] == "new keyword"
    assert memory_store.comments[0]["comment_id"] == "999"


@pytest.mark.asyncio
async def test_weibo_search_dedup_skips_same_keyword_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(config, "ENABLE_WEIBO_SEARCH_DEDUP", True)
    crawler_type_var.set("search")
    WeiboSearchDeduplicator._instance = None

    await WeiboSearchDeduplicator.get_instance().record_note(
        {
            "note_id": "123456",
            "content": "cached note",
            "source_keyword": "same keyword",
        }
    )

    memory_store = MemoryWeiboStore()
    monkeypatch.setattr(
        weibo_store.WeibostoreFactory,
        "create_store",
        staticmethod(lambda: memory_store),
    )

    copied_count = await weibo_store.copy_cached_weibo_note_and_comments("123456", "same keyword")

    assert copied_count == -2
    assert memory_store.contents == []
    assert memory_store.comments == []
