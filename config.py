from pathlib import Path

CVS_DIR = Path(".KoteikaGit")  # . - скрытая директория a.k.a .git
# в pathlib / - работает как оператор склейки путей
OBJECTS_DIR = CVS_DIR / "objects"   # в git здесь лежат сжатые блобы <- SHA-хэш
REFS_DIR = CVS_DIR / "refs"     # ссылки на коммиты: ветки, теги
HEAD_FILE = CVS_DIR / 'HEAD'
INDEX_FILE = CVS_DIR / 'index'  # staging area
DEFAULT_BRANCH = 'main'
