# -*- coding: utf-8 -*-

import asyncio
import copy
import json
import os
import pathlib
from typing import Dict, List, Optional

import aiofiles

import config
from tools import utils


class WeiboSearchDeduplicator:
    """Persistent note/comment cache for Weibo search duplicate handling."""

    _instance: Optional["WeiboSearchDeduplicator"] = None

    def __init__(self):
        self._lock = asyncio.Lock()
        self._loaded = False
        self._notes: Dict[str, Dict] = {}
        self._comments: Dict[str, Dict[str, Dict]] = {}

    @classmethod
    def get_instance(cls) -> "WeiboSearchDeduplicator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _cache_dir() -> pathlib.Path:
        if config.SAVE_DATA_PATH:
            base_path = pathlib.Path(config.SAVE_DATA_PATH) / "weibo" / "cache"
        else:
            base_path = pathlib.Path("data") / "weibo" / "cache"
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path

    @property
    def _notes_path(self) -> pathlib.Path:
        return self._cache_dir() / "search_notes.jsonl"

    @property
    def _comments_path(self) -> pathlib.Path:
        return self._cache_dir() / "search_comments.jsonl"

    async def load(self) -> None:
        if self._loaded:
            return

        async with self._lock:
            if self._loaded:
                return
            await self._load_notes()
            await self._load_comments()
            self._loaded = True

    async def _load_notes(self) -> None:
        notes_path = self._notes_path
        if not notes_path.exists():
            return

        async with aiofiles.open(notes_path, "r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                note_id = str(record.get("note_id", ""))
                content_item = record.get("content_item")
                if note_id and isinstance(content_item, dict):
                    self._notes[note_id] = content_item

    async def _load_comments(self) -> None:
        comments_path = self._comments_path
        if not comments_path.exists():
            return

        async with aiofiles.open(comments_path, "r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                note_id = str(record.get("note_id", ""))
                comment_item = record.get("comment_item")
                if not note_id or not isinstance(comment_item, dict):
                    continue

                comment_id = str(comment_item.get("comment_id", ""))
                if not comment_id:
                    continue
                self._comments.setdefault(note_id, {})[comment_id] = comment_item

    async def has_note(self, note_id: str) -> bool:
        await self.load()
        return str(note_id) in self._notes

    async def get_note(self, note_id: str) -> Optional[Dict]:
        await self.load()
        note_item = self._notes.get(str(note_id))
        return copy.deepcopy(note_item) if note_item else None

    async def get_comments(self, note_id: str) -> List[Dict]:
        await self.load()
        comments = self._comments.get(str(note_id), {})
        return [copy.deepcopy(comment_item) for comment_item in comments.values()]

    async def record_note(self, content_item: Dict) -> None:
        note_id = str(content_item.get("note_id", ""))
        if not note_id:
            return

        await self.load()
        cache_item = copy.deepcopy(content_item)
        async with self._lock:
            self._notes[note_id] = cache_item
            await self._append_jsonl(
                self._notes_path,
                {
                    "note_id": note_id,
                    "content_item": cache_item,
                    "cached_at": utils.get_current_timestamp(),
                },
            )

    async def record_comment(self, note_id: str, comment_item: Dict) -> None:
        note_id = str(note_id)
        comment_id = str(comment_item.get("comment_id", ""))
        if not note_id or not comment_id:
            return

        await self.load()
        cache_item = copy.deepcopy(comment_item)
        async with self._lock:
            self._comments.setdefault(note_id, {})[comment_id] = cache_item
            await self._append_jsonl(
                self._comments_path,
                {
                    "note_id": note_id,
                    "comment_id": comment_id,
                    "comment_item": cache_item,
                    "cached_at": utils.get_current_timestamp(),
                },
            )

    @staticmethod
    async def _append_jsonl(file_path: pathlib.Path, record: Dict) -> None:
        os.makedirs(file_path.parent, exist_ok=True)
        async with aiofiles.open(file_path, "a", encoding="utf-8") as f:
            await f.write(json.dumps(record, ensure_ascii=False) + "\n")
