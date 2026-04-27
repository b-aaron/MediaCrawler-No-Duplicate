# -*- coding: utf-8 -*-

import pytest

import config
from api.schemas.crawler import CrawlerStartRequest, PlatformEnum
from api.services.crawler_manager import CrawlerManager
from cmd_arg.arg import parse_cmd
from media_platform.weibo.client import WeiboClient


@pytest.mark.asyncio
async def test_parse_cmd_sets_crawler_limit_options(monkeypatch):
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 20)
    monkeypatch.setattr(config, "CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES", 20)
    monkeypatch.setattr(config, "CRAWLER_MAX_SUB_COMMENTS_COUNT_SINGLE_COMMENT", 10)
    monkeypatch.setattr(config, "ENABLE_GET_SUB_COMMENTS", False)
    monkeypatch.setattr(config, "FILTER_WEIBO_VIDEO", True)

    result = await parse_cmd(
        [
            "--platform",
            "wb",
            "--type",
            "search",
            "--max_notes_count",
            "7",
            "--max_comments_count",
            "8",
            "--get_sub_comment",
            "true",
            "--max_sub_comments_count",
            "9",
            "--filter_weibo_video",
            "false",
        ]
    )

    assert config.CRAWLER_MAX_NOTES_COUNT == 7
    assert config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES == 8
    assert config.ENABLE_GET_SUB_COMMENTS is True
    assert config.CRAWLER_MAX_SUB_COMMENTS_COUNT_SINGLE_COMMENT == 9
    assert config.FILTER_WEIBO_VIDEO is False
    assert result.max_notes_count == 7
    assert result.max_comments_count_singlenotes == 8
    assert result.max_sub_comments_count_single_comment == 9
    assert result.filter_weibo_video is False


def test_crawler_manager_passes_limit_options_to_command():
    request = CrawlerStartRequest(
        platform=PlatformEnum.WEIBO,
        keywords="keyword",
        max_notes_count=7,
        max_comments_count=8,
        enable_sub_comments=True,
        max_sub_comments_count=9,
        filter_weibo_video=False,
    )

    cmd = CrawlerManager()._build_command(request)

    assert "--max_notes_count" in cmd
    assert cmd[cmd.index("--max_notes_count") + 1] == "7"
    assert "--max_comments_count" in cmd
    assert cmd[cmd.index("--max_comments_count") + 1] == "8"
    assert "--get_sub_comment" in cmd
    assert cmd[cmd.index("--get_sub_comment") + 1] == "true"
    assert "--max_sub_comments_count" in cmd
    assert cmd[cmd.index("--max_sub_comments_count") + 1] == "9"
    assert "--filter_weibo_video" in cmd
    assert cmd[cmd.index("--filter_weibo_video") + 1] == "false"


def test_weibo_empty_content_response_is_treated_as_empty_result():
    data = {"ok": 0, "msg": "这里还没有内容", "data": {"cards": []}}

    assert WeiboClient._is_empty_content_response(data) is True


def test_weibo_non_empty_content_error_is_not_treated_as_empty_result():
    data = {"ok": 0, "msg": "登录失败", "data": {"cards": []}}

    assert WeiboClient._is_empty_content_response(data) is False


def test_weibo_empty_comments_response_is_treated_as_empty_result():
    data = {"ok": 0, "msg": "还没有人评论哦~快来抢沙发！"}

    assert WeiboClient._is_empty_comments_response(data) is True


@pytest.mark.asyncio
async def test_weibo_sub_comments_are_limited_per_comment(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GET_SUB_COMMENTS", True)
    monkeypatch.setattr(config, "CRAWLER_MAX_SUB_COMMENTS_COUNT_SINGLE_COMMENT", 2)
    saved_batches = []

    async def callback(note_id, comments):
        saved_batches.append((note_id, comments))

    result = await WeiboClient.get_comments_all_sub_comments(
        "note1",
        [
            {"comments": [{"id": "1"}, {"id": "2"}, {"id": "3"}]},
            {"comments": [{"id": "4"}, {"id": "5"}, {"id": "6"}]},
        ],
        callback,
    )

    assert [comment["id"] for comment in result] == ["1", "2", "4", "5"]
    assert [[comment["id"] for comment in batch] for _, batch in saved_batches] == [
        ["1", "2"],
        ["4", "5"],
    ]


@pytest.mark.asyncio
async def test_weibo_empty_comment_tip_stops_comment_crawling():
    class EmptyCommentClient(WeiboClient):
        async def get_note_comments(self, note_id, max_id, max_id_type=0):
            self.request_count += 1
            return {
                "data": "还没有人评论哦~快来抢沙发！",
                "max_id": 1,
                "max_id_type": 0,
            }

    client = object.__new__(EmptyCommentClient)
    client.request_count = 0
    saved_batches = []

    async def callback(note_id, comments):
        saved_batches.append((note_id, comments))

    result = await client.get_note_all_comments(
        note_id="note-without-comments",
        crawl_interval=0,
        callback=callback,
        max_count=20,
    )

    assert result == []
    assert saved_batches == []
    assert client.request_count == 1


@pytest.mark.asyncio
async def test_weibo_empty_comment_tip_card_stops_comment_crawling():
    class EmptyCommentClient(WeiboClient):
        async def get_note_comments(self, note_id, max_id, max_id_type=0):
            return {
                "data": [{"text": "<span>还没有人评论哦~快来抢沙发！</span>"}],
                "max_id": 1,
                "max_id_type": 0,
            }

    client = object.__new__(EmptyCommentClient)

    result = await client.get_note_all_comments(
        note_id="note-without-comments",
        crawl_interval=0,
        callback=None,
        max_count=20,
    )

    assert result == []
