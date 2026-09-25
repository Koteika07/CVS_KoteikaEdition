"""Объекты Tree и Commit: сериализация в JSON для хранилища"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional  # nulable type c#


@dataclass
class Tree:
    """Представляет директорию. Содержит имена файлов/папок и их хэши"""
    # entries: { "name": ("blob"|"tree", "sha256") }
    # default_factory=dict -> вызывай dict() при создании каждого экземпляра
    entries: dict = field(default_factory=dict)

    def serialize(self) -> bytes:
        return json.dumps(self.entries).encode("utf-8")

    @classmethod
    def deserialize(cls, data: bytes) -> "Tree":
        raw_entries = json.loads(data.decode("utf-8"))
        entries = {k: tuple(v) for k, v in raw_entries.items()}
        return cls(entries=entries)


@dataclass
class Commit:
    """Представляет коммит (снимок состояния + метаданные)"""
    tree_sha: str
    message: str
    timestamp: float = field(default_factory=time.time)
    parent_sha: Optional[str] = None
    author: str = "User"

    def serialize(self) -> bytes:
        data = {
            "tree": self.tree_sha,
            "parent": self.parent_sha,
            "author": self.author,
            "timestamp": self.timestamp,
            "message": self.message
        }
        return json.dumps(data).encode("utf-8")

    @classmethod
    def deserialize(cls, data: bytes) -> "Commit":
        data = json.loads(data.decode("utf-8"))
        return cls(
            tree_sha=data["tree"],
            parent_sha=data.get("parent"),
            author=data.get("author", "User"),
            timestamp=data["timestamp"],
            message=data["message"]
        )
