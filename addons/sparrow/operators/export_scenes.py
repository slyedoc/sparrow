
import os
import time
from typing import Any, Dict
import bpy

from ..utils import SCENE_FOLDER

from ..properties import SPARROW_PG_Global, SPARROW_PG_Scene

class ExportScenes(bpy.types.Operator):
    """Export Enabled Scenes"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "sparrow.export_scenes"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Export Scense"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):          
        settings = bpy.context.window_manager.sparrow # type: SPARROW_PG_Global      
        p = os.path.join(settings.assets_path, SCENE_FOLDER)
        if not os.path.exists(p):
            print(f"Creating {settings.assets_path}")
            os.makedirs(p)

        for scene in bpy.data.scenes:
            scene_settings = scene.sparrow # type: SPARROW_PG_Scene
            if scene_settings.export:                                
                gltf_path = os.path.abspath(os.path.join(p, scene.name))
                print(f"Exporting {scene.name} to {gltf_path + '.glb'}")
                tmp_time = time.time()
                export_scene(scene, {}, gltf_path) #{'export_materials': 'PLACEHOLDER'}
                print(f"exported {scene.name} in {time.time() - tmp_time:6.2f}s")

        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

# export scene to gltf with io_scene_gltf
def export_scene(scene: bpy.types.Scene, settings: Dict[str, Any], gltf_output_path: str):
    #https://docs.blender.org/api/current/bpy.ops.export_scene.html#bpy.ops.export_scene.gltf        
    export_settings = dict(   
        **settings,
        filepath = gltf_output_path,
        
        #log_info=False, # limit the output, was blowing up my console        
        check_existing=False,

        # Export collections as empty, keeping full hierarchy. If an object is in multiple collections, it will be exported it only once, in the first collection it is found.
        export_hierarchy_full_collections=False,
        export_hierarchy_flatten_objs=False, # note: breakes any collection hierarchy


        export_apply=True, # prevents exporting shape keys
        export_cameras=True,
        export_extras=True, # For custom exported properties.
        export_lights=True,            
        export_yup=True,
        
        export_animations=True,
        export_animation_mode='ACTIONS',
        export_gn_mesh=True,
        export_attributes=True,


        # use only one of these at a time
        use_active_collection_with_nested=False,
        use_active_collection=False,
        use_active_scene=True, 

        # other filters
        use_selection=False,
        use_visible=True, # Export visible and hidden objects
        use_renderable=False,    
        export_normals=True,
        
        #export_draco_mesh_compression_enable=True,
        #export_skins=True,
        #export_morph=False,
        #export_optimize_animation_size=False    
        #export_keep_originals=True,
        #export_shared_accessors=True,
       
        #export_texcoords=True, # used by material info and uv sets
        #export_tangents=True, # used by meshlets
        
        #export_materials
        #export_colors=True,
        #use_mesh_edges
        #use_mesh_vertices
    )        
    # we set our active scene to be this one
    bpy.context.window.scene = scene              
    layer_collection = scene.view_layers['ViewLayer'].layer_collection
    bpy.context.view_layer.active_layer_collection = recurLayerCollection(layer_collection, scene.collection.name)
    bpy.ops.export_scene.gltf(**export_settings)

#Recursivly transverse layer_collection for a particular name
def recurLayerCollection(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found