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

from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty)
from bpy.types import (Panel, Operator, PropertyGroup, UIList, Menu)




from .properties import *

from .operators.edit_collection_instance import *
from .operators.export_scenes import ExportScenes
from .operators.select_asset_folder import OT_OpenAssetsFolderBrowser

from .ui.output_panel import SPARROW_PT_OutputPanel
from .ui.object_panel import SPARROW_PT_ObjectPanel 
from .ui.collection_panel import SPARROW_PT_CollectionPanel
from .ui.scene_panel import SPARROW_PT_ScenePanel


classes = [
    # Properties
    SPARROW_PG_Global,
    SPARROW_PG_Scene,

    # Panels
    SPARROW_PT_ObjectPanel,
    SPARROW_PT_CollectionPanel,
    SPARROW_PT_OutputPanel,
    SPARROW_PT_ScenePanel,
    #SPARROW_PT_Output,

    # Operators
    ExportScenes,
    EditCollectionInstance,
    ExitCollectionInstance,
    OT_OpenAssetsFolderBrowser,
]

addon_keymaps = []

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        #print(f"Registered {cls.__name__}")

    bpy.types.Scene.sparrow = bpy.props.PointerProperty(type=SPARROW_PG_Scene)
    bpy.types.WindowManager.sparrow = bpy.props.PointerProperty(type=SPARROW_PG_Global)

    bpy.types.VIEW3D_MT_object.append(edit_collection_menu)
    bpy.types.VIEW3D_MT_object_context_menu.append(edit_collection_menu)
    bpy.types.VIEW3D_MT_object.append(exit_collection_instance)
    bpy.types.VIEW3D_MT_object_context_menu.append(exit_collection_instance)
    

def unregister():
    for cls in reversed(classes):    
        try:               
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            print(f"Failed to unregister {cls.__name__}, Error: {e}")
            pass
    
    del bpy.types.Scene.sparrow
    del bpy.types.WindowManager.sparrow

    bpy.types.VIEW3D_MT_object.remove(edit_collection_menu)
    bpy.types.VIEW3D_MT_object_context_menu.remove(edit_collection_menu)
    bpy.types.VIEW3D_MT_object.remove(exit_collection_instance)
    bpy.types.VIEW3D_MT_object_context_menu.remove(exit_collection_instance)
    
if __name__ == "__main__":
    register()
  