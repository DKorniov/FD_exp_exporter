# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
import os
import sys
import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Импорт Qt
from PySide2 import QtWidgets, QtCore, QtUiTools

# Импорт внутренних модулей
from . import utils
from .core import rig_tools
from .core.prop_baker import PropBaker

class FD_ExpExporter(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """Главное окно экспортера."""
    WINDOW_ID = "FD_ExpExporter_UniqueWin"

    def __init__(self, parent=None):
        super(FD_ExpExporter, self).__init__(parent=parent)
        
        self.setObjectName(self.WINDOW_ID)
        self.setWindowTitle("FD Exp Exporter")
        
        self.root_path = os.path.dirname(__file__)
        self.ui_path = os.path.join(self.root_path, "ui", "main_window.ui")
        # Путь к конфигу пропсов
        self.config_path = os.path.join(self.root_path, "data", "props_config.json")
        
        self.ui = self._load_ui_file()
        if self.ui:
            self.setCentralWidget(self.ui)
            self._setup_signals()
        
        # Инициализация пекаря
        self.baker = PropBaker()
        
        utils.info(u"Интерфейс FD_exp_exporter загружен успешно")

    def _load_ui_file(self):
        """Загружает файл .ui."""
        if not os.path.exists(self.ui_path):
            cmds.warning(u"Файл интерфейса не найден: %s" % self.ui_path)
            return None
            
        loader = QtUiTools.QUiLoader()
        ui_file = QtCore.QFile(self.ui_path)
        ui_file.open(QtCore.QFile.ReadOnly)
        ui_obj = loader.load(ui_file)
        ui_file.close()

        if isinstance(ui_obj, QtWidgets.QMainWindow):
            content = ui_obj.centralWidget()
            content.setParent(self)
            return content
        return ui_obj

    def _setup_signals(self):
        """Подключение сигналов кнопок."""
        self.btn_delete_props = self.ui.findChild(QtWidgets.QPushButton, "btn_delete_props")
        if self.btn_delete_props:
            self.btn_delete_props.clicked.connect(self.action_delete_props)

        # Новая кнопка: Запекание пропсов
        self.btn_bake_props_anims = self.ui.findChild(QtWidgets.QPushButton, "btn_bake_props_anims")
        if self.btn_bake_props_anims:
            self.btn_bake_props_anims.clicked.connect(self.action_bake_props_anims)
            print("# [FD_exp_exporter] Button 'btn_bake_props_anims' connected.")
        else:
            cmds.warning(u"Кнопка 'btn_bake_props_anims' не найдена в UI! Добавьте её в Qt Designer.")

    def action_delete_props(self):
        """Логика очистки рига."""
        confirm = cmds.confirmDialog(
            title='Rig Cleaner',
            message=u'Вы уверены? Это удалит референсы и пересоберет Character Set.',
            button=['Yes', 'No'],
            defaultButton='Yes',
            cancelButton='No',
            dismissString='No'
        )
        if confirm == 'Yes':
            rig_tools.clean_rig_for_export()

    def action_bake_props_anims(self):
        """Логика кнопки 'Запекание анимации пропсов'."""
        utils.info(u"Начинаю запекание пропсов на локаторы...")
        try:
            self.baker.run_bake_process(self.config_path)
            utils.info(u"Запекание успешно завершено.")
        except Exception as e:
            cmds.warning(u"Ошибка при запекании: %s" % str(e))

def reload_package():
    package_name = "FD_exp_exporter"
    for module_name in list(sys.modules.keys()):
        if module_name.startswith(package_name):
            del sys.modules[module_name]
    print("# [FD_exp_exporter] Cache cleared.")

def show_window():
    reload_package()
    if cmds.window(FD_ExpExporter.WINDOW_ID, exists=True):
        cmds.deleteUI(FD_ExpExporter.WINDOW_ID)
    if cmds.workspaceControl(FD_ExpExporter.WINDOW_ID + "WorkspaceControl", exists=True):
        cmds.deleteUI(FD_ExpExporter.WINDOW_ID + "WorkspaceControl")

    global fd_main_window
    fd_main_window = FD_ExpExporter()
    fd_main_window.show(dockable=True)