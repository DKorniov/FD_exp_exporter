# -*- coding: utf-8 -*-
from __future__ import absolute_import
import maya.cmds as cmds
import json
import os
from . import utils

class PropBaker(object):
    def __init__(self, anim_reader):
        self.anim_reader = anim_reader # Ссылка на AnimAssistantReader

    def bake_props_to_world(self, json_path):
        if not os.path.exists(json_path):
            utils.warn(u"Файл настроек не найден: %s" % json_path)
            return

        with open(json_path, "r") as f:
            config = json.load(f)

        # 1. Получаем реальные клипы из сцены через AnimAssistant
        scene_clips = self.anim_reader.read_clips()
        if not scene_clips:
            utils.warn(u"Клипы AnimAssistant не найдены в сцене.")
            return
        
        clip_map = {c.name: c for c in scene_clips}

        for prop_data in config.get("props_settings", []):
            self._process_single_prop(prop_data, clip_map)

    def _process_single_prop(self, data, clip_map):
        prop_name = data["prop_name"]
        ctrl_name = data["main_control"]
        
        # Ищем контрол с учетом неймспейсов
        found_ctrls = cmds.ls("*:" + ctrl_name, long=True) or cmds.ls(ctrl_name, long=True)
        if not found_ctrls:
            utils.warn(u"Контрол %s для пропса %s не найден." % (ctrl_name, prop_name))
            return
        
        full_ctrl = found_ctrls[0]
        
        # Фильтруем анимации, которые реально есть в сцене и указаны в JSON
        target_anims = []
        for anim_info in data["affected_animations"]:
            name = anim_info["anim_name"]
            if name in clip_map:
                target_anims.append({
                    "clip": clip_map[name],
                    "link_frame": anim_info["link_frame"]
                })

        if not target_anims:
            return

        # 2. Расчет временного диапазона (Start-1 до End+1)
        starts = [a["clip"].start for a in target_anims]
        ends = [a["clip"].end for a in target_anims]
        range_start = min(starts) - 1
        range_end = max(ends) + 1

        # 3. Создание локатора и линковка в указанном кадре первой анимации
        # Для примера берем линковку по первой анимации в списке
        first_setup = target_anims[0]
        actual_link_frame = first_setup["clip"].start + (first_setup["link_frame"] - 1)
        
        cmds.currentTime(actual_link_frame)
        loc = cmds.spaceLocator(name=prop_name + "_world_loc")[0]
        
        # Констрейним без офсета
        cmds.parentConstraint(full_ctrl, loc, mo=False)
        cmds.scaleConstraint(full_ctrl, loc, mo=False)

        # 4. Запекание
        utils.info(u"Запекание пропса: %s" % prop_name)
        cmds.bakeResults(loc, t=(range_start, range_end), 
                         simulation=True, 
                         sampleBy=1, 
                         oversamplingRate=1, 
                         disableImplicitControl=True, 
                         preserveOutsideKeys=True, 
                         sparseAnimCurveBake=False, 
                         removeBakedAttributeFromLayer=False, 
                         removeBakedAnimFromLayer=False, 
                         bakeOnOverrideLayer=False, 
                         minimizeRotation=True, 
                         controlPoints=False, 
                         shape=True)
        
        # Удаляем констрейнты после бейка (они удалятся сами при бейке в некоторых версиях, 
        # но лучше проверить/почистить)
        constraints = cmds.listRelatives(loc, type="constraint")
        if constraints:
            cmds.delete(constraints)
            
        utils.info(u"Пропс %s успешно запечен на локатор." % prop_name)