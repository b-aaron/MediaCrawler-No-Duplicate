# -*- coding: utf-8 -*-

import pytest

import config
from media_platform.weibo.core import WeiboCrawler
from media_platform.weibo.help import is_weibo_video_note
from store import weibo as weibo_store


def test_is_weibo_video_note_returns_false_for_plain_note():
    note_item = {
        "mblog": {
            "id": "plain",
            "text": "plain text",
            "page_info": {"type": "article"},
        }
    }

    assert is_weibo_video_note(note_item) is False


def test_is_weibo_video_note_detects_page_info_type_video():
    note_item = {
        "mblog": {
            "id": "video",
            "page_info": {"type": "video"},
        }
    }

    assert is_weibo_video_note(note_item) is True


def test_is_weibo_video_note_detects_page_info_object_type_video():
    note_item = {
        "mblog": {
            "id": "video",
            "page_info": {"object_type": "video_component"},
        }
    }

    assert is_weibo_video_note(note_item) is True


@pytest.mark.asyncio
async def test_weibo_search_filters_video_before_save_and_comment(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", "keyword")
    monkeypatch.setattr(config, "START_PAGE", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)
    monkeypatch.setattr(config, "WEIBO_SEARCH_TYPE", "default")
    monkeypatch.setattr(config, "FILTER_WEIBO_VIDEO", True)
    monkeypatch.setattr(config, "ENABLE_WEIBO_FULL_TEXT", False)

    class FakeWeiboClient:
        async def get_note_by_keyword(self, keyword, page, search_type):
            if page > 1:
                return {"cards": []}
            return {
                "cards": [
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": "video-note",
                            "page_info": {"type": "video"},
                        },
                    },
                    {
                        "card_type": 9,
                        "mblog": {
                            "id": "plain-note",
                            "text": "plain text",
                            "created_at": "Sat Dec 23 17:12:54 +0800 2023",
                            "attitudes_count": 1,
                            "comments_count": 2,
                            "reposts_count": 3,
                            "region_name": "发布于 上海",
                            "user": {
                                "id": "u1",
                                "screen_name": "plain user",
                                "gender": "m",
                                "profile_url": "https://example.com/u1",
                                "profile_image_url": "https://example.com/u1.jpg",
                            },
                        },
                    },
                ]
            }

    saved_note_ids = []
    comment_note_ids = []

    async def update_weibo_note(note_item):
        saved_note_ids.append(note_item["mblog"]["id"])

    async def is_cached_weibo_note(note_id):
        return False

    async def batch_get_notes_comments(note_ids):
        comment_note_ids.extend(note_ids)

    async def get_note_images(mblog):
        return None

    monkeypatch.setattr(weibo_store, "update_weibo_note", update_weibo_note)
    monkeypatch.setattr(weibo_store, "is_cached_weibo_note", is_cached_weibo_note)

    crawler = WeiboCrawler()
    crawler.wb_client = FakeWeiboClient()
    monkeypatch.setattr(crawler, "batch_get_notes_comments", batch_get_notes_comments)
    monkeypatch.setattr(crawler, "get_note_images", get_note_images)

    await crawler.search()

    assert saved_note_ids == ["plain-note"]
    assert comment_note_ids == ["plain-note"]
