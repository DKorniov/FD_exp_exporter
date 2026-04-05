# -*- coding: utf-8 -*-
from __future__ import print_function
import os, re, shutil

# Обеспечение совместимости типов строк для Python 2 и 3
try:
    unicode  # Py2
except NameError:
    unicode = str

def u(s):
    """Приведение строки к unicode для корректного отображения кириллицы."""
    if isinstance(s, unicode):
        return s
    try:
        return s.decode("utf-8")
    except Exception:
        try:
            return unicode(s)
        except Exception:
            return u""

def nice_name(s):
    """Очистка имени от спецсимволов для путей и нод (только буквы, цифры, тире и нижнее подчеркивание)."""
    return re.sub(r"[^\w\-]+", "_", (s or "").strip().lower())

def ensure_dir(p):
    """Создание директории, если она не существует."""
    if not os.path.exists(p):
        os.makedirs(p)
    return p

def safe_rmtree(path):
    """Безопасное удаление папки со всем содержимым."""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
    except Exception:
        pass

def lowercase_index(names):
    """Создание словаря {нижний_регистр: оригинал} для поиска файлов без учета регистра."""
    return {n.lower(): n for n in names}

def warn(msg):
    """Вывод предупреждения в Command Line / Script Editor Maya."""
    try:
        from maya import cmds
        cmds.warning(u(msg))
    except Exception:
        print("# Warning:", u(msg))

def info(msg):
    """Вывод информационного сообщения в In-View Message (в центре экрана) Maya."""
    try:
        from maya import cmds
        # Используем <hl> теги для подсветки, если они переданы в строке
        cmds.inViewMessage(amg=u(msg), pos="topCenter", fade=True)
    except Exception:
        print(u(msg))