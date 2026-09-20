"""Staging area: сопоставление пути файла с SHA blob"""

import json
from pathlib import Path
from . import config
from .storage import ObjectStore


class Index:
    """Управляет областью подготовки (staging area) изменений"""

    def __init__(self):
        # { "relative/path": "blob_sha" }
        self.entries: dict[str, str] = {}
        self._load()

    def _load(self):
        """Читает индекс из файла .KoteikaGit/index в self.entries"""
        if config.INDEX_FILE.exists():
            with open(config.INDEX_FILE, "r") as f:
                self.entries = json.load(f)

    def save(self):
        """Записывает self.entries в файл .KoteikaGit/index"""
        # w - if файл существует - перезапишется, if нет — создадим
        with open(config.INDEX_FILE, "w") as f:
            json.dump(self.entries, f, indent=2)

    def add_path(self, path: Path):
        """Добавляет файл или рекурсивно обходит директорию"""
        path = path.resolve()
        cwd = Path.cwd().resolve()

        if path.is_file():
            self._add_file(path, cwd)

        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file() and config.MYCVS_DIR not in file_path.parts:
                    self._add_file(file_path, cwd)

    def _add_file(self, file_path: Path, cwd: Path):
        """Сохраняет файл как blob в ObjectStore и кладёт его SHA в индекс"""
        # используем as_posix() для единообразия путей в индексе (всегда "/")
        rel_path = file_path.relative_to(cwd).as_posix()
        with open(file_path, "rb") as f:
            data = f.read()

        # сохраняем содержимое в ObjectStore и получаем хэш
        sha = ObjectStore.write_object("blob", data)
        self.entries[rel_path] = sha
