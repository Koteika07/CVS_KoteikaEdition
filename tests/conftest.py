import pytest
from pathlib import Path
from cvs import config

@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    # фикстура - функция, которая готовит окружение для теста и передаёт в него нужные данные
    # CWD (Current Working Directory) - текущая рабочая директория процесса
    """
    фикстура для создания временной рабочей директории
    изолирует тесты, меняя CWD и пути конфигурации на временные
    """
    # cохраняем оригинальные пути
    original_cvs_dir = config.CVS_DIR
    original_objects_dir = config.OBJECTS_DIR
    original_refs_dir = config.REFS_DIR
    original_head_file = config.HEAD_FILE
    original_index_file = config.INDEX_FILE

    # меняем CWD на временную папку
    monkeypatch.chdir(tmp_path)

    # переопределяем пути в конфиге, чтобы они указывали внутрь tmp_path
    monkeypatch.setattr(config, "CVS_DIR", tmp_path / ".KoteikaGit")
    monkeypatch.setattr(config, "OBJECTS_DIR", tmp_path / ".KoteikaGit" / "objects")
    monkeypatch.setattr(config, "REFS_DIR", tmp_path / ".KoteikaGit" / "refs")
    monkeypatch.setattr(config, "HEAD_FILE", tmp_path / ".KoteikaGit" / "HEAD")
    monkeypatch.setattr(config, "INDEX_FILE", tmp_path / ".KoteikaGit" / "index")

    yield tmp_path

    # восстановление не требуется, так как monkeypatch делает это автоматически
