# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
import maya.cmds as cmds
import json
import os
import re
from .. import utils

class PropBaker(object):
    def __init__(self):
        self.node = "AnimAssistant" # Нода из MEL скрипта [cite: 807, 133, 140]
        self.root_path = os.path.dirname(os.path.dirname(__file__))
        self.etalon_path = os.path.join(self.root_path, "data", "animation_etalon.json") # 

    def get_canonical_name(self, name):
        """Нормализация имен: '001|machete_10-20' -> 'machete'."""
        if not name: return ""
        clean = name.split('|')[-1]
        clean = re.sub(r'_\d+-\d+$', '', clean)
        return clean.strip().lower()

    def load_etalon_list(self):
        """Загрузка списка разрешенных анимаций[cite: 1393, 143]."""
        if not os.path.exists(self.etalon_path): return []
        try:
            with open(self.etalon_path, 'r') as f:
                data = json.load(f)
            return [n.lower() for n in data.get("props_animations_etalon", [])]
        except: return []

    def _prepare_attr_name(self, raw_name):
        """Превращает 'Machete Parent' в 'machete_parent'[cite: 140, 141]."""
        return raw_name.replace(" ", "_").lower()

    def _force_make_writable(self, ctrl, channels):
        """Разблокирует каналы и отключает их от Character Set."""
        is_ref = cmds.referenceQuery(ctrl, isNodeReferenced=True)
        for ch in channels:
            full_attr = f"{ctrl}.{ch}"
            if not cmds.objExists(full_attr): continue
            
            if not is_ref:
                if cmds.getAttr(full_attr, lock=True):
                    cmds.setAttr(full_attr, lock=False)
            
            connections = cmds.listConnections(full_attr, type="character", plugs=True)
            if connections:
                for conn in connections:
                    try:
                        cmds.disconnectAttr(conn, full_attr)
                        print(f"# [PropBaker] Disconnected {full_attr} from Character Set.")
                    except: pass

    def _get_scene_data(self):
        """Сбор данных из ноды AnimAssistant[cite: 885, 910, 140]."""
        if not cmds.objExists(self.node): return {}
        etalon = self.load_etalon_list()
        
        names = (cmds.getAttr(f"{self.node}.AnimationClipName") or "").split()
        starts = (cmds.getAttr(f"{self.node}.StartFrame") or "").split()
        ends = (cmds.getAttr(f"{self.node}.EndFrame") or "").split()

        res = {}
        for i in range(len(names)):
            canon = self.get_canonical_name(names[i])
            if canon in etalon:
                res[canon] = {"start": float(starts[i]), "end": float(ends[i])}
        return res

    def run_bake_process(self, props_config_path):
        """Основной цикл запекания."""
        if not os.path.exists(props_config_path): return
        with open(props_config_path, "r") as f:
            config = json.load(f)

        scene_clips = self._get_scene_data()
        if not scene_clips: return

        for prop_data in config.get("props_settings", []):
            try:
                self._process_single_prop(prop_data, scene_clips)
            except Exception as e:
                print(f"# [PropBaker] Error processing {prop_data.get('prop_name')}: {str(e)}")

    def _process_single_prop(self, data, scene_clips):
        """Полный процесс запекания пропса[cite: 141, 142]."""
        prop_label = data["prop_name"]
        ctrl_name = data["main_control"]
        
        found = cmds.ls(f"*:{ctrl_name}") or cmds.ls(ctrl_name)
        if not found: return
        ctrl = found[0]

        used = [self.get_canonical_name(a) for a in data.get("used_animations", [])]
        relevant = [scene_clips[c] for c in used if c in scene_clips]
        if not relevant: return

        link_cfg = data["linked_animation"]
        base_clip = scene_clips.get(self.get_canonical_name(link_cfg["anim_name"]))
        if not base_clip: return
        
        actual_link = base_clip["start"] + (link_cfg["link_frame"] - 1)
        r_start, r_end = min([c["start"] for c in relevant]) - 1, max([c["end"] for c in relevant]) + 1

        # Список всех атрибутов для жесткого запекания
        bake_attrs = ['tx','ty','tz','rx','ry','rz','sx','sy','sz']

        # --- ШАГ 1: Запекание на локатор ---
        cmds.currentTime(actual_link)
        loc = cmds.spaceLocator(n=f"LOC_{prop_label}_BAKE")[0]
        p_loc = cmds.parentConstraint(ctrl, loc, mo=False)[0]
        s_loc = cmds.scaleConstraint(ctrl, loc, mo=False)[0]
        
        # Запекаем локатор (здесь можно без явных атрибутов, локатор пустой)
        cmds.bakeResults(loc, t=(r_start, r_end), simulation=True)
        cmds.delete(p_loc, s_loc)

        # --- ШАГ 2: Перманентная смена пространства в 0 (World) ---
        space_attr = self._prepare_attr_name(data.get("space_attribute", ""))
        full_space_path = f"{ctrl}.{space_attr}"
        if cmds.objExists(full_space_path):
            # 1. Удаляем все ключи на атрибуте пространства, чтобы он не прыгал
            cmds.cutKey(ctrl, attribute=space_attr, clear=True)
            # 2. Ставим его в 0 (World) навсегда
            try:
                cmds.setAttr(full_space_path, 0)
                print(f"# [PropBaker] {full_space_path} cleared and permanently set to 0 (World)")
            except: pass

        # Подготовка каналов к записи (unlock + Character Set)
        self._force_make_writable(ctrl, bake_attrs)

        # --- ШАГ 3: Обратное запекание на контрол ---
        cmds.currentTime(actual_link)
        try:
            p_ctrl = cmds.parentConstraint(loc, ctrl, mo=False)[0]
            s_ctrl = cmds.scaleConstraint(loc, ctrl, mo=False)[0]
            
            # ВАЖНО: Явно указываем bake_attrs, чтобы запечь даже неподвижные каналы (как Translate X)
            cmds.bakeResults(ctrl, t=(r_start, r_end), simulation=True, attribute=bake_attrs)
            cmds.delete(p_ctrl, s_ctrl)
        except Exception as e:
            print(f"# [PropBaker] Back-bake failed for {ctrl}: {e}")
        
        cmds.delete(loc)
        utils.info(u"Пропс %s: Запекание завершено." % prop_label)