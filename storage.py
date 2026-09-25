"""Хранилище объектов с адресацией по содержимому (SHA-256 + zlib)"""

import hashlib  # считаем хеш SHA-256
import zlib  # сжатие в zlib-формате как в Git
import tempfile
import os
from pathlib import Path
from . import config


class ObjectStore:
    """Хранилище объектов с адресацией по содержимому"""

    @staticmethod
    def _get_object_path(sha: str) -> Path:
        """Вычисляет путь на диске для объекта с хэшем sha-256"""
        # sha = "a3f5c9b7" -> objects/a3/f5c9b7
        return config.OBJECTS_DIR / sha[:2] / sha[2:]

    @classmethod
    def write_object(cls, obj_type: str, data: bytes) -> str:
        """Сохраняет объект в хранилище и возвращает его SHA-256 хэш"""
        # pаголовок предотвращает коллизии хэшей между объектами разных типов
        header = f"{obj_type} {len(data)}\0".encode("utf-8")  # "blob 3\0"
        store_data = header + data  # <тип> <размер>\0<тело>

        sha = hashlib.sha256(store_data).hexdigest()
        path = cls._get_object_path(sha)

        # пишем только если объекта ещё нет — дедупликация
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

            # cоздаём временный файл в той же папке
            fd, tmp_path = tempfile.mkstemp(dir=path.parent)
            # tmp_path = ".KoteikaGit/objects/ab/tmp_xyz123"
            try:
                # пишем данные во временный файл
                with os.fdopen(fd, "wb") as f:
                    f.write(zlib.compress(store_data))
                # атомарно перемещаем временный файл на место целевого
                os.replace(tmp_path, path)
            except Exception:
                # if что-то пошло не так - удаляем временный файл
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        return sha

    @classmethod
    def read_object(cls, sha: str) -> tuple[str, bytes]:
        """Читает объект из хранилища. Возвращает кортеж (type, data)"""
        path = cls._get_object_path(sha)
        if not path.exists():
            raise FileNotFoundError(f"Объект {sha} не найден в хранилище")

        with open(path, "rb") as f:
            # огр. весь объект грузится в память
            store_data = zlib.decompress(f.read())

        header, data = store_data.split(b"\0", 1)
        # "blob 3".split(" ") -> ["blob", "3"] -> [0] -> "blob"
        obj_type = header.decode("utf-8").split(" ")[0]
        return obj_type, data
