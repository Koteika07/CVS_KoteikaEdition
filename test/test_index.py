import pytest
import json
from pathlib import Path
from cvs.index import Index
from cvs import config
from cvs.storage import ObjectStore


def test_index_starts_empty_when_no_file(temp_workspace):
    """Если файла индекса нет — entries пустой, исключений не возникает"""
    assert not config.INDEX_FILE.exists()

    idx = Index()
    assert idx.entries == {}


def test_index_save_creates_file(temp_workspace):
    """Проверка, что save() создаёт файл индекса на диске"""
    config.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    idx = Index()
    idx.entries["a.txt"] = "sha_a"
    idx.save()

    assert config.INDEX_FILE.exists()


def test_index_save_and_load_round_trip(temp_workspace):
    """Данные должны пережить save() → новый Index()"""
    config.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    idx1 = Index()
    idx1.entries = {"a.txt": "sha_a", "dir/b.txt": "sha_b"}
    idx1.save()

    # новый экземпляр должен подхватить данные с диска
    idx2 = Index()
    assert idx2.entries == {"a.txt": "sha_a", "dir/b.txt": "sha_b"}


def test_index_save_overwrites_previous(temp_workspace):
    """Повторный save() перезаписывает файл, а не дописывает"""
    config.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    idx = Index()
    idx.entries = {"a.txt": "sha_a"}
    idx.save()

    idx.entries = {"b.txt": "sha_b"}
    idx.save()

    idx2 = Index()
    assert idx2.entries == {"b.txt": "sha_b"}


def test_index_saved_as_valid_json(temp_workspace):
    """Файл индекса должен быть корректным JSON"""
    config.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    idx = Index()
    idx.entries = {"x": "y"}
    idx.save()

    # проверка, что файл читается как валидный JSON
    content = config.INDEX_FILE.read_text()
    parsed = json.loads(content)
    assert parsed == {"x": "y"}


def test_add_single_file_records_entry(temp_workspace):
    """add_path для файла добавляет одну запись"""
    Path("a.txt").write_text("hello")

    idx = Index()
    idx.add_path(Path("a.txt"))

    assert "a.txt" in idx.entries
    assert len(idx.entries) == 1


def test_add_file_records_correct_blob_sha(temp_workspace):
    """SHA в индексе должен указывать на реальный blob в ObjectStore"""
    Path("a.txt").write_text("content")

    idx = Index()
    idx.add_path(Path("a.txt"))

    # проверка, что sha в индексе соответствует реальному объекту
    obj_type, data = ObjectStore.read_object(idx.entries["a.txt"])
    assert obj_type == "blob"
    assert data == b"content"


def test_add_file_normalizes_path_to_posix(temp_workspace):
    """Пути в индексе всегда в posix-формате (со слешами)"""
    Path("sub").mkdir()
    Path("sub/a.txt").write_text("x")

    idx = Index()
    idx.add_path(Path("sub/a.txt"))

    keys = list(idx.entries.keys())
    assert keys == ["sub/a.txt"]
    # на Windows обратные слеши не должны попасть
    assert "\\" not in keys[0]


def test_add_file_from_nested_cwd_uses_relative_path(temp_workspace, monkeypatch):
    """add_path должен строить путь относительно CWD, а не от корня репо"""
    Path("root").mkdir()
    Path("root/file.txt").write_text("hi")

    # меняем CWD на вложенную директорию
    monkeypatch.chdir("root")

    idx = Index()
    idx.add_path(Path("file.txt"))

    # несмотря на то что CWD внутри root/, ключ должен быть "file.txt"
    assert "file.txt" in idx.entries


def test_add_file_twice_is_idempotent(temp_workspace):
    """Повторное добавление того же файла не создаёт дублей"""
    Path("a.txt").write_text("same")

    idx = Index()
    idx.add_path(Path("a.txt"))
    sha_first = idx.entries["a.txt"]

    idx.add_path(Path("a.txt"))

    assert len(idx.entries) == 1
    assert idx.entries["a.txt"] == sha_first


def test_add_file_with_updated_content_changes_sha(temp_workspace):
    """Изменение файла приводит к новому blob_sha в индексе"""
    Path("a.txt").write_text("v1")

    idx = Index()
    idx.add_path(Path("a.txt"))
    sha_v1 = idx.entries["a.txt"]

    Path("a.txt").write_text("v2")
    idx.add_path(Path("a.txt"))
    sha_v2 = idx.entries["a.txt"]

    assert sha_v1 != sha_v2


def test_add_directory_recursively(temp_workspace):
    """add_path на директорию обходит все вложенные файлы"""
    Path("d/nested/deep").mkdir(parents=True)
    Path("d/a.txt").write_text("a")
    Path("d/nested/b.txt").write_text("b")
    Path("d/nested/deep/c.txt").write_text("c")

    idx = Index()
    idx.add_path(Path("d"))

    assert set(idx.entries.keys()) == {
        "d/a.txt",
        "d/nested/b.txt",
        "d/nested/deep/c.txt",
    }


def test_add_directory_skips_cvs_dir(temp_workspace):
    """Файлы внутри .KoteikaGit не должны попадать в индекс"""
    config.CVS_DIR.mkdir(parents=True, exist_ok=True)
    (config.CVS_DIR / "junk.txt").write_text("junk")
    (config.CVS_DIR / "objects").mkdir(exist_ok=True)
    (config.CVS_DIR / "objects" / "blob").write_text("data")
    Path("normal.txt").write_text("ok")

    idx = Index()
    idx.add_path(Path("."))

    assert "normal.txt" in idx.entries
    # ни один путь не должен содержать .KoteikaGit
    assert all(".KoteikaGit" not in p for p in idx.entries)


def test_add_empty_directory_adds_nothing(temp_workspace):
    """Пустая директория не должна давать записей в индексе"""
    Path("empty").mkdir()

    idx = Index()
    idx.add_path(Path("empty"))

    assert idx.entries == {}


def test_add_directory_with_same_content_dedup(temp_workspace):
    """Одинаковое содержимое в разных файлах даёт один blob_sha"""
    Path("d").mkdir()
    Path("d/a.txt").write_text("same")
    Path("d/b.txt").write_text("same")

    idx = Index()
    idx.add_path(Path("d"))

    # оба файла ссылаются на один и тот же blob (дедупликация)
    assert idx.entries["d/a.txt"] == idx.entries["d/b.txt"]


def test_add_directory_preserves_nested_structure(temp_workspace):
    """Ключи в индексе должны сохранять относительный путь внутри директории"""
    Path("pkg/sub").mkdir(parents=True)
    Path("pkg/__init__.py").write_text("")
    Path("pkg/sub/mod.py").write_text("x = 1")

    idx = Index()
    idx.add_path(Path("pkg"))

    assert "pkg/__init__.py" in idx.entries
    assert "pkg/sub/mod.py" in idx.entries


def test_index_persists_after_reload(temp_workspace):
    """После save() и создания нового Index данные сохраняются"""
    config.INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    Path("a.txt").write_text("x")

    idx1 = Index()
    idx1.add_path(Path("a.txt"))
    idx1.save()

    # новый экземпляр читает тот же файл
    idx2 = Index()
    assert "a.txt" in idx2.entries
    assert idx2.entries["a.txt"] == idx1.entries["a.txt"]


def test_index_does_not_touch_working_directory(temp_workspace):
    """Index не должен удалять или менять файлы в рабочей директории"""
    Path("a.txt").write_text("original")

    idx = Index()
    idx.add_path(Path("a.txt"))
    idx.save()

    # содержимое файла не изменилось
    assert Path("a.txt").read_text() == "original"
