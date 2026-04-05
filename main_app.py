# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from .core import rig_tools

import os
import sys
import importlib
import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Импорт Qt (Maya 2022 использует PySide2)
from PySide2 import QtWidgets, QtCore, QtUiTools

# Импорт базовых утилит из текущего пакета
from . import utils

class FD_ExpExporter(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """
    Главное окно экспортера. 
    Использует MayaQWidgetDockableMixin для корректного родительского контроля в Maya.
    """
    WINDOW_ID = "FD_ExpExporter_UniqueWin"

    def __init__(self, parent=None):
        super(FD_ExpExporter, self).__init__(parent=parent)
        
        self.setObjectName(self.WINDOW_ID)
        self.setWindowTitle("FD Exp Exporter")
        
        # Динамические пути
        self.root_path = os.path.dirname(__file__)
        self.ui_path = os.path.join(self.root_path, "ui", "main_window.ui")
        
        # Загрузка интерфейса
        self.ui = self._load_ui_file()
        if self.ui:
            self.setCentralWidget(self.ui)
            self._setup_signals()
        
        utils.info(u"Интерфейс FD_exp_exporter загружен успешно")

    

    def _load_ui_file(self):
        """Загружает файл .ui и корректно извлекает содержимое."""
        if not os.path.exists(self.ui_path):
            cmds.warning(u"Файл интерфейса не найден: %s" % self.ui_path)
            return None
            
        loader = QtUiTools.QUiLoader()
        ui_file = QtCore.QFile(self.ui_path)
        ui_file.open(QtCore.QFile.ReadOnly)
        
        # Загружаем UI как отдельный объект (не передаем self вторым аргументом)
        ui_obj = loader.load(ui_file)
        ui_file.close()

        # Если в Designer создано "Main Window", нам нужно забрать только его центр
        if isinstance(ui_obj, QtWidgets.QMainWindow):
            content = ui_obj.centralWidget()
            # Важно: перепривязываем родителя, чтобы кнопки не удалились сборщиком мусора
            content.setParent(self)
            return content
            
        return ui_obj

    def _setup_signals(self):
        """Подключение кнопок через поиск дочерних элементов (findChild)."""
        # Так как мы вытащили только centralWidget, ищем кнопку внутри self.ui
        self.btn_delete_props = self.ui.findChild(QtWidgets.QPushButton, "btn_delete_props")
        
        if self.btn_delete_props:
            self.btn_delete_props.clicked.connect(self.action_delete_props)
            print("# [FD_exp_exporter] Button 'btn_delete_props' connected.")
        else:
            cmds.warning(u"Кнопка 'btn_delete_props' не найдена в .ui файле!")

    def action_delete_props(self):
        """Логика первой кнопки: Очистка рига."""
        # Подтверждение действия (опционально, но полезно)
        confirm = cmds.confirmDialog(
            title='Rig Cleaner',
            message=u'Вы уверены? Это удалит референсы и пересоберет Character Set.',
            button=['Yes', 'No'],
            defaultButton='Yes',
            cancelButton='No',
            dismissString='No'
        )
        
        if confirm == 'Yes':
            # Вызываем нашу новую функцию из core
            rig_tools.clean_rig_for_export()

def reload_package():
    """
    Удаляет модули скрипта из sys.modules, чтобы Maya перечитала файлы с диска.
    Это 'чистит кеш' при каждом запуске с шелфа.
    """
    package_name = "FD_exp_exporter"
    for module_name in list(sys.modules.keys()):
        if module_name.startswith(package_name):
            del sys.modules[module_name]
    print("# [FD_exp_exporter] Cache cleared.")

def show_window():
    """Точка входа для запуска с шелфа."""
    
    # 1. Очистка кеша (для разработки)
    reload_package()
    
    # 2. Удаление старого окна, если оно открыто (Singleton)
    if cmds.window(FD_ExpExporter.WINDOW_ID, exists=True):
        cmds.deleteUI(FD_ExpExporter.WINDOW_ID)
    
    if cmds.workspaceControl(FD_ExpExporter.WINDOW_ID + "WorkspaceControl", exists=True):
        cmds.deleteUI(FD_ExpExporter.WINDOW_ID + "WorkspaceControl")

    # 3. Создание и отображение
    global fd_main_window
    fd_main_window = FD_ExpExporter()
    fd_main_window.show(dockable=True) # Позволяет окну не перекрывать всё, а быть частью Maya