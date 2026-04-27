# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/weibo/help.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/24 17:37
# @Desc    :

from typing import Dict, List


def filter_search_result_card(card_list: List[Dict]) -> List[Dict]:
    """
    Filter Weibo search results, only keep data with card_type of 9
    :param card_list: List of card items from search results
    :return: Filtered list of note items
    """
    note_list: List[Dict] = []
    for card_item in card_list:
        if card_item.get("card_type") == 9:
            note_list.append(card_item)
        if len(card_item.get("card_group", [])) > 0:
            card_group = card_item.get("card_group")
            for card_group_item in card_group:
                if card_group_item.get("card_type") == 9:
                    note_list.append(card_group_item)

    return note_list


def is_weibo_video_note(note_item: Dict) -> bool:
    """
    Check whether a Weibo search note item is a video post.
    Args:
        note_item: Search result note item, usually contains mblog.

    Returns:

    """
    if not note_item:
        return False

    mblog: Dict = note_item.get("mblog") or {}
    if not mblog:
        return False

    page_info: Dict = mblog.get("page_info") or {}
    page_type = str(page_info.get("type", "")).lower()
    object_type = str(page_info.get("object_type", "")).lower()
    if page_type == "video" or "video" in object_type:
        return True

    media_info = page_info.get("media_info")
    if media_info:
        return True

    if mblog.get("video_info") or mblog.get("mix_media_info"):
        return True

    url_struct = mblog.get("url_struct")
    if isinstance(url_struct, list):
        for url_item in url_struct:
            if not isinstance(url_item, dict):
                continue
            url_object_type = str(url_item.get("object_type", "")).lower()
            url_type = str(url_item.get("type", "")).lower()
            if "video" in url_object_type or url_type == "video":
                return True

    pic_video = page_info.get("pic_info", {}).get("pic_video") if isinstance(page_info.get("pic_info"), dict) else None
    return bool(pic_video)
