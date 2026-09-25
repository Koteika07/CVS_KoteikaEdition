import pytest
import zlib
from cvs.storage import ObjectStore
from cvs import config

def test_write_and_read_object(temp_workspace):
    """Проверка записи и чтения объекта"""
    obj_type = "blob"
    data = b"Hello, Koteika!"

    # запись
    sha = ObjectStore.write_object(obj_type, data)
    # SHA-256 hexdigest
    assert len(sha) == 64

    # проверка существования файла
    obj_path = config.OBJECTS_DIR / sha[:2] / sha[2:]
    assert obj_path.exists()

    # чтение
    read_type, read_data = ObjectStore.read_object(sha)
    assert read_type == obj_type
    assert read_data == data

def test_deduplication(temp_workspace):
    """Проверка дедупликации: одинаковые данные -> одинаковый хэш"""
    data1 = b"Duplicate content"
    data2 = b"Duplicate content"

    sha1 = ObjectStore.write_object("blob", data1)
    sha2 = ObjectStore.write_object("blob", data2)

    assert sha1 == sha2

    # проверяем, что файл только один
    obj_path = config.OBJECTS_DIR / sha1[:2] / sha1[2:]
    assert obj_path.exists()

def test_read_nonexistent_object(temp_workspace):
    """Проверка ошибки при чтении несуществующего объекта"""
    with pytest.raises(FileNotFoundError):
        ObjectStore.read_object("a" * 64)

def test_zlib_compression(temp_workspace):
    """Проверка, что данные действительно сжаты"""
    data = b"A" * 1000
    sha = ObjectStore.write_object("blob", data)

    obj_path = config.OBJECTS_DIR / sha[:2] / sha[2:]
    raw_content = obj_path.read_bytes()

    # сырые данные должны быть меньше исходных (с учетом заголовка)
    # zlib сжимает "A"*1000 очень хорошо
    assert len(raw_content) < len(data)

    # проверка распаковки
    decompressed = zlib.decompress(raw_content)
    header, body = decompressed.split(b"\0", 1)
    assert body == data
