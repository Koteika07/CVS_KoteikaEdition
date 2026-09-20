"""Высокоуровневая логика репозитория: init, add, commit, checkout, log, branch, tag (обёртка над Index, ObjectStore, Tree, Commit)"""

import shutil
import time
from pathlib import Path
from . import config
from .storage import ObjectStore
from .objects import Tree, Commit
from .index import Index


class Repository:
    """Высокоуровневая логика работы с репозиторием"""

    def __init__(self):
        if not config.CVS_DIR.exists():
            raise RuntimeError("Not a cvs repository. Run 'init' first")
        self.index = Index()

    def init(self):
        """Инициализирует новый репозиторий"""
        config.OBJECTS_DIR.mkdir(parents=True, exist_ok=True)
        (config.REFS_DIR / "heads").mkdir(parents=True, exist_ok=True)
        (config.REFS_DIR / "tags").mkdir(parents=True, exist_ok=True)

    with open(config.HEAD_FILE, "w") as f:
        f.write(f'ref: refs/heads/{config.DEFAULT_BRANCH}')
        print(f"Initialized empty CVS repository in {config.CVS_DIR}")

    def add(self, paths: list[str]):
        """Добавляет файлы в индекс"""
        for p in paths:
            self.index.add_path(Path(p))
        self.index.save()
        print(f"Added {len(paths)} path to index")

    def commit(self, message: str):
        """Создает коммит из текущего индекса"""
        if not self.index.entries:
            print("Nothing to commit (empty index)")
            return

        # cтроим Tree из плоского индекса
        root_tree_sha = self._build_tree(self.index.entries)
        # получаем хэш родительского коммита
        parent_sha = self._get_head_commit()
        # cоздаем и сохраняем объект коммита
        commit_obj = Commit(tree_sha=root_tree_sha, message=message, parent_sha=parent_sha)
        commit_sha = ObjectStore.write_object("commit", commit_obj.serialize())
        # обновляем ссылку текущей ветки
        ref = self._get_head_ref()
        self._update_ref(ref, commit_sha)

        print(f"[{ref.split('/')[-1]} {commit_sha[:7]}] {message}")

    def checkout(self, target: str):
        """Переключается на ветку, тег или конкретный коммит"""
        target_sha = self._resolve_ref(target)
        if not target_sha:
            print(f"Error: pathspec '{target}' did not match any known versions")
            return

        # очищаем рабочую директорию
        self._clean_working_dir()
        # восстанавливаем файлы из коммита
        _, commit_data = ObjectStore.read_object(target_sha)
        commit = Commit.deserialize(commit_data)
        self._restore_tree(commit.tree_sha, Path("."))
        # обновляем HEAD
        if self._is_branch(target) or self._is_tag(target):
            ref_type = "heads" if self._is_branch(target) else "tags"
            with open(config.HEAD_FILE, "w") as f:
                f.write(f'ref: refs/{ref_type}/{target}')
        else:
            # detached HEAD
            with open(config.HEAD_FILE, "w") as f:
                f.write(target_sha)

        print(f"Switched to {target[:7]}")

    def log(self):
        """Выводит историю коммитов"""
        commit_sha = self._get_head_commit()
        if not commit_sha:
            print("No commits yet")
            return

        while commit_sha:
            _, data = ObjectStore.read_object(commit_sha)
            commit = Commit.deserialize(data)

            date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(commit.timestamp))
            print(f"commit {commit_sha}")
            print(f"Date:   {date_str}")
            print(f"\n    {commit.message}\n")

            print("Files in this snapshot:")
            self._print_tree_files(commit.tree_sha, "")
            print("-" * 40)

            commit_sha = commit.parent_sha

    def branch(self, name: str):
        """Создает новую ветку"""
        commit_sha = self._get_head_commit()
        if not commit_sha:
            print("Error: Cannot create branch without commits")
            return

        self._update_ref(f'refs/heads/{name}', commit_sha)
        print(f"Branch '{name}' created at {commit_sha[:7]}")

    def tag(self, name: str):
        """Создает новый тег"""
        commit_sha = self._get_head_commit()
        if not commit_sha:
            print("Error: Cannot create tag without commits")
            return

        self._update_ref(f'refs/tags/{name}', commit_sha)
        print(f"Tag '{name}' created at {commit_sha[:7]}")

    def _build_tree(self, file_index: dict) -> str:
        """Рекурсивно строит объекты Tree из плоского словаря индекса"""
        tree_dict = {}
        for filepath, blob_sha in file_index.items():
            parts = Path(filepath).parts
            current_level = tree_dict

            for part in parts[:-1]:
                current_level = current_level.setdefault(part, {})

            current_level[parts[-1]] = ("blob", blob_sha)

        return self._save_tree_recursive(tree_dict)

    def _save_tree_recursive(self, tree_dict: dict) -> str:
        """Сохраняет словарь как объект tree и возвращает его хэш"""
        entries = {}
        for name, value in tree_dict.items():
            if isinstance(value, dict):
                sub_tree_sha = self._save_tree_recursive(value)
                entries[name] = ("tree", sub_tree_sha)
            else:
                entries[name] = value

        tree_obj = Tree(entries=entries)
        return ObjectStore.write_object("tree", tree_obj.serialize())

    def _get_head_ref(self) -> str:
        """Ссылка из HEAD ('refs/heads/main') или SHA при detached HEAD"""
        with open(config.HEAD_FILE, "r") as f:
            ref = f.read().strip()
        return ref[5:] if ref.startswith("ref: ") else ref

    def _get_head_commit(self) -> str | None:
        """SHA коммита, на который указывает HEAD (или None)"""
        ref = self._get_head_ref()
        ref_path = config.MYCVS_DIR / ref
        if ref_path.exists():
            return ref_path.read_text().strip()
        return None

    def _update_ref(self, ref: str, commit_sha: str):
        """Пишет SHA в файл ссылки, создавая директории"""
        ref_path = config.MYCVS_DIR / ref
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(commit_sha)

    def _resolve_ref(self, ref: str) -> str | None:
        """Имя ветки/тега/SHA → полный SHA (или None)"""
        # if передан полный хэш
        if len(ref) == 64 and all(c in "0123456789abcdef" for c in ref):
            return ref
        # search в ветках и тегах
        for ref_type in ["heads", "tags"]:
            path = config.REFS_DIR / ref_type / ref
            if path.exists():
                return path.read_text().strip()
        return None

    def _is_branch(self, name: str) -> bool:
        """Существует ли ветка с таким именем"""
        return (config.REFS_DIR / "heads" / name).exists()

    def _is_tag(self, name: str) -> bool:
        """Существует ли тег с таким именем"""
        return (config.REFS_DIR / "tags" / name).exists()

    def _clean_working_dir(self):
        """Удаляет все файлы в рабочей директории, кроме .KoteikaGit"""
        for item in Path(".").iterdir():
            if item.name == config.MYCVS_DIR.name:
                continue
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    def _restore_tree(self, tree_sha: str, current_path: Path):
        """Рекурсивно восстанавливает файлы и папки из объекта Tree"""
        _, tree_data = ObjectStore.read_object(tree_sha)
        tree = Tree.deserialize(tree_data)

        for name, (obj_type, sha) in tree.entries.items():
            full_path = current_path / name
            if obj_type == "blob":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                _, blob_data = ObjectStore.read_object(sha)
                full_path.write_bytes(blob_data)
            elif obj_type == "tree":
                full_path.mkdir(parents=True, exist_ok=True)
                self._restore_tree(sha, full_path)

    def _print_tree_files(self, tree_sha: str, prefix: str):
        """Рекурсивно выводит список файлов в дереве"""
        _, tree_data = ObjectStore.read_object(tree_sha)
        tree = Tree.deserialize(tree_data)
        for name, (obj_type, sha) in tree.entries.items():
            path = f"{prefix}/{name}" if prefix else name
            if obj_type == "tree":
                self._print_tree_files(sha, path)
            else:
                print(f"  {path}")
