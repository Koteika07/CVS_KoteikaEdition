import pytest
import json
import time
from cvs.object import Tree, Commit

def test_tree_serialization():
    """Проверка сериализации и десериализации Tree"""
    entries = {
        "file.txt": ("blob", "abc123"),
        "subdir": ("tree", "def456")
    }
    tree = Tree(entries=entries)

    # сериализация
    data = tree.serialize()
    assert isinstance(data, bytes)

    # десериализация
    restored_tree = Tree.deserialize(data)
    assert restored_tree.entries == entries

def test_commit_serialization():
    """Проверка сериализации и десериализации Commit"""
    commit = Commit(
        tree_sha="tree_sha_123",
        message="Initial commit",
        parent_sha="parent_sha_456",
        author="Test User"
    )

    # сериализация
    data = commit.serialize()
    assert isinstance(data, bytes)

    # десериализация
    restored_commit = Commit.deserialize(data)

    assert restored_commit.tree_sha == commit.tree_sha
    assert restored_commit.message == commit.message
    assert restored_commit.parent_sha == commit.parent_sha
    assert restored_commit.author == commit.author
    # Timestamp может незначительно отличаться, проверяем с допуском
    assert abs(restored_commit.timestamp - commit.timestamp) < 1.0

def test_commit_deserialize_defaults():
    """Проверка значений по умолчанию при десериализации"""
    data = json.dumps({
        "tree": "sha1",
        "timestamp": 12345.0,
        "message": "msg"
    }).encode("utf-8")

    commit = Commit.deserialize(data)
    assert commit.parent_sha is None
    assert commit.author == "User"
