import bpy
import os
import time

from .utils import *
from .blueprints import *
from .properties import SPARROW_PG_Settings

def export_scene(settings: SPARROW_PG_Settings, path, area, region, scene) -> bool:
    success = False
    if settings.gltf_format == 'GLB':
        gltf_path = os.path.join(path, f"{scene.name}.glb")
        # remove existing file
        if os.path.exists(gltf_path):
            os.remove(gltf_path)
    else:
        gltf_path = os.path.join(path, f"{scene.name }")
        
    print(f"Exporting {scene.name} to {gltf_path}")
    tmp_time = time.time()

    # we set our active scene to active
    bpy.context.window.scene = scene
    layer_collection = scene.view_layers['ViewLayer'].layer_collection
    bpy.context.view_layer.active_layer_collection = recurLayerCollection(layer_collection, scene.collection.name)
        
    # find blueprints
    blueprints_instances = scan_blueprint_instances(scene)
    print(f"blueprints instances in scene {scene.name}: {len(blueprints_instances)}")

    # clear instance collection and set blueprint name
    for inst in blueprints_instances:
        obj = inst.object
        col = inst.collection
        obj.instance_collection = None
            #if not 'blueprint' in obj:
        obj['blueprint'] = sanitize_file_name(col.name)

    with bpy.context.temp_override(scene=scene, area=area, region=region):
            # detect scene mistmatch
        scene_mismatch = bpy.context.scene.name != bpy.context.window.scene.name
        if scene_mismatch:
            show_message_box("Error in Gltf Exporter", icon="ERROR", lines=[f"Context scene mismatch, aborting: {bpy.context.scene.name} vs {bpy.context.window.scene.name}"])
        else:
            try:
                export_gltf(settings, gltf_path, blueprint=False)
                success = True
            except Exception as error:
                print("failed to export scene gltf !", error) 
                show_message_box("Error in Gltf Exporter", icon="ERROR", lines=exception_traceback(error))
            finally:
                    # restore collection instances
                for inst in blueprints_instances:
                    obj = inst.object
                    col = inst.collection
                    obj.instance_collection = col

    print(f"{scene.name:30} {time.time() - tmp_time:.2f}s")
    return success


def export_gltf(settings: SPARROW_PG_Settings, gltf_path: str, blueprint: bool):
    bpy.ops.export_scene.gltf(
            filepath=gltf_path,
            export_format=settings.gltf_format,
            will_save_settings=False,
            check_existing=False,
            
            export_apply=True, # prevents exporting shape keys
            export_cameras=True,
            export_lights=True,            
            export_yup=True,                    
            #export_materials='EXPORT',
            export_extras=True, # For custom exported properties.
            export_animations=True,
            export_animation_mode='ACTIONS',
            export_gn_mesh=True,                    
            export_normals=True,
            export_texcoords=True,

            use_selection = False,
            use_active_collection_with_nested=True, # different for blueprints
            use_active_collection=True, # different for blueprints
            use_active_scene=True, 
            # filters                                                                                                        
            use_visible=True,
        )