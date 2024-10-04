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

def export_scene_blueprints(settings: SPARROW_PG_Settings, path, area, region, scene) -> (int, int):
    # scan scene for collections marked as assets
    blueprints = scan_blueprints(scene)
  
    print(f"Blueprints: {scene.name:20} {len(blueprints):3} ")
    success = 0
    failure = 0
    for col in blueprints:
        tmp_time = time.time()

        if settings.gltf_format == 'GLB':
            gltf_path = os.path.join(path, f"{col.name}.glb")
        else:
            gltf_path = os.path.join(path, f"{col.name}")
        
        # we set our active scene to temp: this is needed otherwise the stand-in empties get generated in the wrong scene
        temp_scene = bpy.data.scenes.new(name=col.name+"_temp")
        # copy collection instance components and 
        # adding scene prop so GltfSceneExtra is added, serves as marker to let us flatten the scene                    

        if 'bevy_components' in col:
            print("copying bevy components" , col['bevy_components'])
            temp_scene['bevy_components'] = col['bevy_components']
        else:
            # need to add something even if it has no components, so gltf scene extras is created (used to flatten)
            temp_scene['sparrow_blueprint'] = True
        
        
        temp_root_collection = temp_scene.collection
        bpy.context.window.scene = temp_scene

        with bpy.context.temp_override(scene=temp_scene, area=area, region=region):
            # detect scene mistmatch
            scene_mismatch = bpy.context.scene.name != bpy.context.window.scene.name
            if scene_mismatch:
                show_message_box("Error in Gltf Exporter", icon="ERROR", lines=[f"Context scene mismatch, aborting: {bpy.context.scene.name} vs {bpy.context.window.scene.name}"])
            else:
                # link the collection to the scene
                set_active_collection(bpy.context.scene, temp_root_collection.name)
                temp_root_collection.children.link(col)

                try:
                    export_gltf(settings, gltf_path, blueprint=True)
                    success += 1
                except Exception as error:
                    failure += 1
                    print("failed to export blueprint gltf !", error) 
                    show_message_box("Error in Gltf Exporter", icon="ERROR", lines=exception_traceback(error))
                finally:
                    # restore everything
                    bpy.data.scenes.remove(temp_scene, do_unlink=True)

        print(f"{col.name:30} {time.time() - tmp_time:6.2f}s")
    return success, failure

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