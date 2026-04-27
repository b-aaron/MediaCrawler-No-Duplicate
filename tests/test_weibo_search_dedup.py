# -*- coding: utf-8 -*-

import pytest

import config
from store import weibo as weibo_store
from store.weibo.search_dedup import WeiboSearchDeduplicator
from var import crawler_type_var, source_keyword_var


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
    assert memory_store.comments[0]["source_keyword"] == "new keyword"


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


@pytest.mark.asyncio
async def test_weibo_save_outputs_source_keyword(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_WEIBO_SEARCH_DEDUP", False)
    source_keyword_var.set("keyword from search")
    memory_store = MemoryWeiboStore()
    monkeypatch.setattr(
        weibo_store.WeibostoreFactory,
        "create_store",
        staticmethod(lambda: memory_store),
    )

    note_item = {
        "mblog": {
            "id": "123456",
            "text": "<span>note content</span>",
            "created_at": "Sat Dec 23 17:12:54 +0800 2023",
            "attitudes_count": 1,
            "comments_count": 2,
            "reposts_count": 3,
            "region_name": "发布于 上海",
            "user": {
                "id": "u1",
                "screen_name": "note user",
                "gender": "m",
                "profile_url": "https://example.com/u1",
                "profile_image_url": "https://example.com/u1.jpg",
            },
        }
    }
    comment_item = {
        "id": "c1",
        "text": "<span>comment content</span>",
        "created_at": "Sat Dec 23 17:12:54 +0800 2023",
        "total_number": 0,
        "like_count": 4,
        "source": "来自北京",
        "rootid": "0",
        "user": {
            "id": "u2",
            "screen_name": "comment user",
            "gender": "f",
            "profile_url": "https://example.com/u2",
            "profile_image_url": "https://example.com/u2.jpg",
        },
    }

    await weibo_store.update_weibo_note(note_item)
    await weibo_store.update_weibo_note_comment("123456", comment_item)

    assert memory_store.contents[0]["source_keyword"] == "keyword from search"
    assert memory_store.comments[0]["source_keyword"] == "keyword from search"
