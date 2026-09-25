import pytest
import os
from pathlib import Path
from cvs.repo import Repository
from cvs import config

@pytest.fixture
def initialized_repo(temp_workspace):
    """Фикстура для инициализированного репозитория"""
    Repository.init()
    return Repository()

def test_init_creates_structure(temp_workspace):
    """Проверка создания структуры директорий при init"""
    Repository.init()

    assert config.CVS_DIR.exists()
    assert config.OBJECTS_DIR.exists()
    assert (config.REFS_DIR / "heads").exists()
    assert (config.REFS_DIR / "tags").exists()
    assert config.HEAD_FILE.exists()

    head_content = config.HEAD_FILE.read_text().strip()
    assert head_content == f"ref: refs/heads/{config.DEFAULT_BRANCH}"

def test_add_and_commit(initialized_repo):
    """Тест добавления файла и создания коммита"""
    # создаем файл
    test_file = Path("test.txt")
    test_file.write_text("Hello World")

    # добавляем
    initialized_repo.add(["test.txt"])
    assert "test.txt" in initialized_repo.index.entries

    # коммитим
    initialized_repo.commit("First commit")

    # проверяем, что HEAD указывает на коммит
    head_ref = initialized_repo._get_head_ref()
    ref_path = config.CVS_DIR / head_ref
    assert ref_path.exists()
    commit_sha = ref_path.read_text().strip()
    assert len(commit_sha) == 64

def test_checkout_restores_files(initialized_repo):
    """Тест восстановления файлов из коммита"""
    # коммит 1: файл A
    Path("a.txt").write_text("Content A")
    initialized_repo.add(["a.txt"])
    initialized_repo.commit("Add a.txt")

    # коммит 2: файл B (и удаление A из индекса, но не из рабочей директории)
    Path("b.txt").write_text("Content B")
    initialized_repo.add(["b.txt"])
    initialized_repo.commit("Add b.txt")

    # удаляем файлы физически
    Path("a.txt").unlink()
    Path("b.txt").unlink()
    assert not Path("a.txt").exists()
    assert not Path("b.txt").exists()

    # сheckout на первый коммит (по SHA)
    # получаем SHA первого коммита (родителя текущего)
    head_sha = initialized_repo._get_head_commit()
    _, commit_data = initialized_repo._get_object_store().read_object(head_sha)
    from cvs.object import Commit
    commit = Commit.deserialize(commit_data)
    first_commit_sha = commit.parent_sha

    initialized_repo.checkout(first_commit_sha)

    # проверяем, что a.txt вернулся, а b.txt нет
    assert Path("a.txt").exists()
    assert Path("a.txt").read_text() == "Content A"
    assert not Path("b.txt").exists()

def test_branch_and_checkout(initialized_repo):
    """Тест создания ветки и переключения"""
    Path("file.txt").write_text("v1")
    initialized_repo.add(["file.txt"])
    initialized_repo.commit("v1")

    # создаем ветку feature
    initialized_repo.branch("feature")

    # переключаемся на feature
    initialized_repo.checkout("feature")

    head_content = config.HEAD_FILE.read_text().strip()
    assert "refs/heads/feature" in head_content

    # пеняем файл и коммитим в ветку feature
    Path("file.txt").write_text("v2")
    initialized_repo.add(["file.txt"])
    initialized_repo.commit("v2 on feature")

    # аереключаемся обратно на main
    initialized_repo.checkout("main")

    # файл должен вернуться к v1
    assert Path("file.txt").read_text() == "v1"

def test_log_output(initialized_repo, capsys):
    """Тест вывода истории коммитов"""
    Path("f1.txt").write_text("1")
    initialized_repo.add(["f1.txt"])
    initialized_repo.commit("Commit 1")

    Path("f2.txt").write_text("2")
    initialized_repo.add(["f2.txt"])
    initialized_repo.commit("Commit 2")

    initialized_repo.log()

    captured = capsys.readouterr()
    assert "Commit 2" in captured.out
    assert "Commit 1" in captured.out
    assert "commit " in captured.out
