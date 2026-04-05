# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
import os
import re
import maya.cmds as cmds
import maya.mel as mel
from .. import utils

def optimize_materials_by_texture():
    """Объединяет материалы с одинаковыми текстурами."""
    print(u"--- [Material Optimizer] Analyzing textures... ---")
    texture_groups = {}
    shading_groups = cmds.ls(type='shadingEngine')
    
    for sg in shading_groups:
        if sg in ['initialShadingGroup', 'initialParticleSE']: continue
        shaders = cmds.listConnections(sg + ".surfaceShader")
        if not shaders: continue
        
        history = cmds.listHistory(shaders[0]) or []
        file_nodes = cmds.ls(history, type='file')
        if not file_nodes: continue
            
        tex_path = os.path.normpath(cmds.getAttr(file_nodes[0] + ".fileTextureName") or "").lower()
        if not tex_path: continue
        
        if tex_path not in texture_groups: texture_groups[tex_path] = []
        texture_groups[tex_path].append(sg)

    for path, groups in texture_groups.items():
        if len(groups) > 1:
            print(u"  > Found duplicate texture: %s" % os.path.basename(path))
            master_sg = next((g for g in groups if 'opaque' in g.lower()), groups[0])
            for old_sg in [g for g in groups if g != master_sg]:
                members = cmds.sets(old_sg, q=True)
                if members:
                    cmds.sets(members, edit=True, forceElement=master_sg)
                    print(u"    Reassigned meshes from %s -> %s" % (old_sg, master_sg))

def safe_scene_cleanup():
    """Безопасная очистка сцены на Python согласно скриншоту."""
    print(u"--- [Safe Cleanup] Starting Targeted Optimization ---")

    # 1. Unknown nodes
    unknown = cmds.ls(type='unknown')
    if unknown:
        try: 
            cmds.delete(unknown)
            print(u"  - Removed %d unknown nodes" % len(unknown))
        except: pass

    # 2. Rendering nodes
    mel.eval('MLdeleteUnused')

    # 3. Empty Transforms
    transforms = cmds.ls(type='transform', long=True)
    tr_count = 0
    for tr in reversed(transforms):
        if not cmds.objExists(tr): continue
        children = cmds.listRelatives(tr, children=True) or []
        if not children and cmds.nodeType(tr) != 'joint':
            if not cmds.listConnections(tr):
                try: 
                    cmds.delete(tr)
                    tr_count += 1
                except: pass
    if tr_count: print(u"  - Removed %d empty transforms" % tr_count)

    # 4. Empty Sets
    sets_count = 0
    for s in cmds.ls(type='objectSet'):
        if s in ['defaultSceneAddressPoint', 'ControlSet', 'DeformSet']: continue
        if not cmds.sets(s, q=True) and not cmds.listConnections(s, destination=True):
            try: 
                cmds.delete(s)
                sets_count += 1
            except: pass
    if sets_count: print(u"  - Removed %d empty sets" % sets_count)

    # 5. Empty Layers
    for layer_type in ['displayLayer', 'renderLayer']:
        layers = cmds.ls(type=layer_type)
        for lyr in layers:
            if lyr in ['defaultLayer', 'defaultRenderLayer']: continue
            members = cmds.editDisplayLayerMembers(lyr, q=True) if layer_type == 'displayLayer' else cmds.editRenderLayerMembers(lyr, q=True)
            if not members:
                try: 
                    cmds.delete(lyr)
                    print(u"  - Removed empty layer: %s" % lyr)
                except: pass

    # 6. Unused Anim/System nodes
    unused_types = ['animCurve', 'animClip', 'pose', 'expression', 'pairBlend', 'snapshot', 'unitConversion', 'brush']
    for n_type in unused_types:
        nodes = cmds.ls(type=n_type)
        deleted_in_type = 0
        for n in nodes:
            if not cmds.listConnections(n):
                try: 
                    cmds.delete(n)
                    deleted_in_type += 1
                except: pass
        if deleted_in_type: print(u"  - Removed %d unused nodes of type %s" % (deleted_in_type, n_type))

    # 7. Referenced items
    mel.eval('RNdeleteUnused')
    print(u"--- [Safe Cleanup] Finished ---")

def clean_rig_for_export():
    """Полный цикл подготовки рига с финальным пересохранением по паттерну."""
    current_file_path = cmds.file(q=True, sn=True)
    if not current_file_path:
        utils.warn(u"Файл не сохранен! Сначала сохраните сцену.")
        return

    file_dir = os.path.dirname(current_file_path)
    file_name = os.path.basename(current_file_path)

    print(u"\n--- [Rig Cleaner] Start ---")
    print(u"Project Path: %s" % file_dir)
    print(u"Source File:  %s" % file_name)
    print(u"-----------------------------------")

    # 1. Skeleton Check (ROOT_M)
    if cmds.objExists('ROOT_M'):
        parents = cmds.listRelatives('ROOT_M', parent=True) or []
        if 'DEformation_system' not in parents:
            print(u"!!! ВНИМАНИЕ: Кость ROOT_M вне DEformation_system. Рекомендуется пересборка.")
        else:
            print(u"Hierarchy Status: ROOT_M OK.")

    # 2. Удаление старого Character Set
    char_sets = cmds.ls(type='character')
    old_char_set_name = char_sets[0] if char_sets else "Character_Set"
    if char_sets: cmds.delete(char_sets)

    # 3. Референсы и fosterParent
    refs = cmds.ls(references=True)
    for ref in refs:
        try:
            rf = cmds.referenceQuery(ref, filename=True)
            cmds.file(rf, removeReference=True)
        except: pass
    
    for fn in cmds.ls("*fosterParent*", type='transform'):
        try: cmds.delete(fn)
        except: pass

    # 4. Обработка Volume
    target_ik = ['IKLeg_R', 'IKLeg_L', 'IKArm_R', 'IKArm_L', 'IKSpine3_M']
    for ik in target_ik:
        for node in cmds.ls("*" + ik, type='transform'):
            for av in ['volume', 'Volume']:
                if cmds.attributeQuery(av, node=node, exists=True):
                    cmds.setAttr(node + "." + av, 0, keyable=False, channelBox=True)

    # 5. Оптимизация материалов
    optimize_materials_by_texture()

    # 6. Пересоздание Character Set (БЕЗ Visibility и Volume)
    all_ctrls = cmds.ls(type='nurbsCurve', long=True)
    ctrl_transforms = list(set([cmds.listRelatives(c, parent=True, fullPath=True)[0] for c in all_ctrls]))
    if ctrl_transforms:
        attrs = []
        for node in ctrl_transforms:
            k_attrs = cmds.listAttr(node, keyable=True) or []
            for a in k_attrs:
                if a.lower() not in ['visibility', 'volume']:
                    attrs.append(node + "." + a)
        if attrs: cmds.character(attrs, name=old_char_set_name)

    # 7. Безопасная оптимизация
    safe_scene_cleanup()

    # 8. ФИНАЛЬНОЕ СОХРАНЕНИЕ С НОВЫМ ИМЕНЕМ
    # Ищем имя персонажа между первым подчеркиванием и _rig (Lora из Exp_Lora_rig_08.ma)
    # Флаг re.IGNORECASE позволяет ловить rig, Rig, RIG
    match = re.search(r'([A-Za-z0-9]+)_[Rr][Ii][Gg]', file_name)
    
    if match:
        extracted_name = match.group(1)
        new_name = "{}_rig.ma".format(extracted_name)
        new_path = os.path.join(file_dir, new_name)
        
        # Переименовываем и сохраняем (force=True перезапишет, если файл есть)
        cmds.file(rename=new_path)
        cmds.file(save=True, force=True, type='mayaAscii')
        
        print(u"-----------------------------------")
        print(u"SUCCESS: File saved as -> %s" % new_name)
        utils.info(u"Готово! Риг очищен и сохранен как %s" % new_name)
    else:
        print(u"-----------------------------------")
        print(u"WARNING: Could not parse name from '%s'. File NOT renamed." % file_name)
        utils.warn(u"Риг очищен, но имя файла не соответствует паттерну *_name_rig*")

    print(u"--- [Rig Cleaner] Finished ---")