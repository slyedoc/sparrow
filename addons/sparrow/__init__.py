# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK ####

bl_info = {
    "name": "Sparrow",
    "description": "Tooling for Bevy",
    "author": "slyedoc",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "warning": "",
    "wiki_url": "https://github.com/slyedoc/sparrow",
    "tracker_url": "https://github.com/slyedoc/sparrow",
    "category": "Import-Export"
}

import bpy
import os
import platform
import re
import math
import mathutils
import functools

from bpy.app.handlers import persistent

from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty)
from bpy.types import (Panel, Operator, PropertyGroup, UIList, Menu)

from .utils import *
from .properties import *
from .panels import *
from .operators import *
from .ui_lists import *
from .menu import *

classes = [
    # Operators
    SPARROW_OT_ExportScenes,
    SPARROW_OT_ExportCurrentScene,
    SPARROW_OT_EditCollectionInstance,
    SPARROW_OT_ExitCollectionInstance,
    SPARROW_OT_OpenAssetsFolderBrowser,
    SPARROW_OT_OpenRegistryFileBrowser,
    SPARROW_OT_LoadRegistry,
    SPARROW_OT_AddComponent,    
    SPARROW_OT_PasteComponent,
    SPARROW_OT_CopyComponent,
    SPARROW_OT_RemoveComponent,
    SPARROW_OT_ToggleComponentVisibility,
    SPARROW_OT_components_refresh_custom_properties_all,

    SPARROW_OT_component_map_actions,
    SPARROW_OT_component_list_actions,
    # Generic_LIST_OT_AddItem,
    # Generic_LIST_OT_RemoveItem,
    # Generic_LIST_OT_SelectItem,
    # GENERIC_LIST_OT_actions,

    # Scene, Object, Collection Properties
    ComponentMetadata, 
    ComponentsMeta,
    
    MissingBevyType,
    ComponentsRegistry,

    # Global Properties
    SPARROW_PG_SceneProps,
    SPARROW_PG_Component,    
    SPARROW_PG_ComponentDropdown,
    SPARROW_PG_Settings,

    # Properties
    SPARROW_PG_Autobake, SPARROW_PG_Bake, SPARROW_PG_BakeQueue, SPARROW_PG_UDIMType, SPARROW_PG_SourceObjects, SPARROW_PG_ImageExport, SPARROW_PG_ObjectQueue,
    # Operator
    SPARROW_OT_BakeStart, SPARROW_OT_CancelBake, SPARROW_OT_PauseBake, SPARROW_OT_ResumeBake,
    SPARROW_OT_Add, SPARROW_OT_Remove, SPARROW_OT_Up, SPARROW_OT_Down, SPARROW_OT_ScaleDown, SPARROW_OT_ScaleUp, SPARROW_OT_LoadLinked,
    SPARROW_OT_Add_UDIM, SPARROW_OT_Remove_UDIM, SPARROW_OT_Down_UDIM, SPARROW_OT_Up_UDIM, SPARROW_OT_MoveTop_UDIM, SPARROW_OT_MoveBottom_UDIM,
    SPARROW_OT_RemoveDisabled, SPARROW_OT_RemoveDuplicates, SPARROW_OT_RemoveAll, SPARROW_OT_EnableAll, SPARROW_OT_DisableAll, SPARROW_OT_InvertAll, SPARROW_OT_MoveTop, SPARROW_OT_MoveBottom, SPARROW_PG_UDIMTile, 
    SPARROW_OT_RemoveDisabled_UDIM, SPARROW_OT_RemoveDuplicates_UDIM, SPARROW_OT_RemoveAll_UDIM, SPARROW_OT_EnableAll_UDIM, SPARROW_OT_DisableAll_UDIM, SPARROW_OT_InvertAll_UDIM, SPARROW_OT_Sort_UDIM, SPARROW_OT_ImportTiles_UDIM,
    SPARROW_OT_ToggleQueueItem, SPARROW_OT_ToggleObjectQueueItem, SPARROW_OT_BakeConfirm, SPARROW_OT_NextObject, SPARROW_OT_ExportTextures, SPARROW_OT_Sort, SPARROW_OT_NameStructure, SPARROW_OT_FolderExplorer,
    SPARROW_OT_SelectFromList, SPARROW_OT_LoadFromSelected,
    # UIList
    SPARROW_UL_Bake, SPARROW_UL_BakeQueue, SPARROW_UL_UDIMTile, SPARROW_UL_UDIMType, SPARROW_UL_SourceObjects, SPARROW_UL_ImageExport, SPARROW_UL_ObjectQueue,
    # Menu
    SPARROW_MT_BakeList, SPARROW_MT_UDIMList, SPARROW_MT_ItemEdit, SPARROW_MT_ItemEdit_UDIM, SPARROW_MT_Confirms, SPARROW_MT_Alerts, SPARROW_MT_ColorSpace, SPARROW_MT_StartPopupSettings,SPARROW_MT_Reports,

    # Panels
    SPARROW_PT_ObjectPanel, SPARROW_PT_CollectionPanel, SPARROW_PT_OutputPanel, SPARROW_PT_ScenePanel,

    # Auto Bake Panels
    SPARROW_PT_Bake, SPARROW_PT_Lists, SPARROW_PT_List_UDIM,
    SPARROW_PT_Image, SPARROW_PT_Name, SPARROW_PT_Format, SPARROW_PT_Export, SPARROW_PT_ColorOverride,
    SPARROW_PT_Settings, SPARROW_PT_Margin, SPARROW_PT_SelectedToActive, SPARROW_PT_SelectionHelp, SPARROW_PT_Sampling, SPARROW_PT_Denoise, SPARROW_PT_Sampling_Low, SPARROW_PT_Denoise_Low, SPARROW_PT_Sampling_High, SPARROW_PT_Denoise_High,
    SPARROW_PT_Addon, SPARROW_PT_ImageSettings, SPARROW_PT_Materials, SPARROW_PT_Objects, SPARROW_PT_ObjectExport, SPARROW_PT_BakeList, SPARROW_PT_BakeQueue, SPARROW_PT_Miscellaneous,
    SPARROW_PT_Transform, SPARROW_PT_Geometry, SPARROW_PT_Compression_GLTF, SPARROW_PT_ShapeKeys_GTLF, SPARROW_PT_Images_GLTF            
]

@persistent
def post_load(file_name):
    settings = bpy.context.window_manager.sparrow_settings # type: SPARROW_PG_Settings    
    settings.load_settings()
    settings.load_registry()

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Global settings
    bpy.types.WindowManager.sparrow_settings = bpy.props.PointerProperty(type=SPARROW_PG_Settings)
    bpy.types.Scene.sparrow_scene_props = bpy.props.PointerProperty(type=SPARROW_PG_SceneProps)

    bpy.types.Scene.components_meta = PointerProperty(type=ComponentsMeta)
    bpy.types.Object.components_meta = PointerProperty(type=ComponentsMeta)
    bpy.types.Collection.components_meta = PointerProperty(type=ComponentsMeta)
    #bpy.types.Mesh.components_meta = PointerProperty(type=ComponentsMeta)
    #bpy.types.Material.components_meta = PointerProperty(type=ComponentsMeta)

    # handled in classmethod
    #bpy.types.WindowManager.components_registry = PointerProperty(type=ComponentsRegistry)

    # from autobake
    bpy.types.Scene.autobake_properties = PointerProperty(type=SPARROW_PG_Autobake)

    bpy.types.Scene.autobake_bakelist = CollectionProperty(type=SPARROW_PG_Bake)
    bpy.types.Scene.autobake_bakelist_index = IntProperty(name="Bake Item", default=0, update=name_by_index)

    bpy.types.Scene.autobake_udimlist = CollectionProperty(type=SPARROW_PG_UDIMType)
    bpy.types.Scene.autobake_udimlist_index = IntProperty(name="Bake Item", default=0, update=name_by_index)

    bpy.types.Scene.autobake_udimtilelist = CollectionProperty(type=SPARROW_PG_UDIMTile)
    bpy.types.Scene.autobake_udimtilelist_index = IntProperty(name="UDIM Tile", default=0)

    bpy.types.Scene.autobake_imageexport = CollectionProperty(type=SPARROW_PG_ImageExport)
    bpy.types.Scene.autobake_imageexport_index = IntProperty(name="Image", default=0)

    bpy.types.Scene.autobake_sourceobject = CollectionProperty(type=SPARROW_PG_SourceObjects)
    bpy.types.Scene.autobake_sourceobject_index = IntProperty(name="Source Object", default=0)

    bpy.types.Scene.autobake_queuelist = CollectionProperty(type=SPARROW_PG_BakeQueue)
    bpy.types.Scene.autobake_queuelist_index = IntProperty(name="Queue Item", default=0)
    
    bpy.types.Scene.autobake_objectqueuelist = CollectionProperty(type=SPARROW_PG_ObjectQueue)
    bpy.types.Scene.autobake_objectqueuelist_index = IntProperty(name="Object Bake Item", default=0, update=bake_result)

    # Auto Bake end
    bpy.app.handlers.load_post.append(post_load)
    bpy.types.VIEW3D_MT_object.append(edit_collection_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(edit_collection_menu)
    bpy.types.VIEW3D_MT_object.append(exit_collection_instance)
    bpy.types.VIEW3D_MT_object_context_menu.append(exit_collection_instance)

def unregister():    

    if bpy.app.timers.is_registered(watch_registry):
        bpy.app.timers.unregister(watch_registry)

    bpy.app.handlers.load_post.remove(post_load)

    bpy.types.VIEW3D_MT_object.remove(edit_collection_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(edit_collection_menu)

    bpy.types.VIEW3D_MT_object.remove(exit_collection_instance)
    bpy.types.VIEW3D_MT_object_context_menu.remove(exit_collection_instance)
    
    for cls in classes:
        bpy.utils.unregister_class(cls)


    del bpy.types.WindowManager.sparrow_settings
    del bpy.types.Scene.sparrow_scene_props

    del bpy.types.Scene.components_meta
    del bpy.types.Object.components_meta
    del bpy.types.Collection.components_meta


    # from autobake
    del bpy.types.Scene.autobake_properties
    
    del bpy.types.Scene.autobake_bakelist
    del bpy.types.Scene.autobake_bakelist_index
    
    del bpy.types.Scene.autobake_udimlist
    del bpy.types.Scene.autobake_udimlist_index
    
    del bpy.types.Scene.autobake_udimtilelist
    del bpy.types.Scene.autobake_udimtilelist_index
    
    del bpy.types.Scene.autobake_imageexport
    del bpy.types.Scene.autobake_imageexport_index
    
    del bpy.types.Scene.autobake_sourceobject
    del bpy.types.Scene.autobake_sourceobject_index
    
    del bpy.types.Scene.autobake_queuelist
    del bpy.types.Scene.autobake_queuelist_index
    
    del bpy.types.Scene.autobake_objectqueuelist
    del bpy.types.Scene.autobake_objectqueuelist_index

def name_by_index(self, context):
    scene = context.scene
    abp = scene.autobake_properties
    
    list = scene.autobake_udimlist if abp.ab_udim_bake else scene.autobake_bakelist
    
    if len(list):
        index = scene.autobake_udimlist_index if abp.ab_udim_bake else scene.autobake_bakelist_index
    
        type_names = {}
        for item in abp.ab_baketype_name_all.split(', '):
            type_names[item.split(':')[0]] = item.split(':')[1]
            
        active_type = list[index].Type
        
        if active_type not in type_names:
            type_names[active_type] = active_type.strip()
        abp.ab_baketype_name = type_names[active_type]
        
        
def bake_result(self, context):
    scene = context.scene
    abp = scene.autobake_properties
    
    if len(scene.autobake_objectqueuelist) > 0:
        obj = scene.autobake_objectqueuelist[scene.autobake_objectqueuelist_index].Object
        
        if obj.name in context.scene.objects:
            for selected in context.selected_objects:
                selected.select_set(False)

            obj.select_set(True)
            context.view_layer.objects.active = obj
    
        if bake_status == 'IDLE' and len(scene.autobake_queuelist) > 0 and obj.name in bake_results:
            obj_bakes = bake_results[obj.name]
            stored_values = {key: value for dictionary in obj_bakes for key, value in dictionary.items()}
            
            for item in scene.autobake_queuelist:
                queue_item = f"{item.Type} " + (f"{item.Multiplier:.2f}" if is_udim_bake else f"{item.Size}")
                item.Status = stored_values[queue_item]['Status']
                item.Icon = stored_values[queue_item]['Icon']
                item.Error = stored_values[queue_item]['Error']
                item.Cancel = stored_values[queue_item]['Cancel']


if __name__ == "__main__":
    register()
  