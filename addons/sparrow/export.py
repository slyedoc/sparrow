import bpy
import os
import time

from .utils import *
from .blueprints import *
from .properties import SPARROW_PG_Settings

def export_scene(settings: SPARROW_PG_Settings, area, region, scene) -> bool:
    success = False
    path = os.path.join(settings.assets_path, SCENE_FOLDER)
    os.makedirs(path, exist_ok=True)

    if settings.gltf_format == 'GLB':
        gltf_path = os.path.join(path, f"{scene.name}.glb")
        # remove existing file
        if os.path.exists(gltf_path):
            os.remove(gltf_path)
    else:
        gltf_path = os.path.join(path, f"{scene.name }")
        
    #print(f"Exporting {scene.name} to {gltf_path}")
    
    # export gravity settings
    if scene.use_gravity:
        scene['SceneGravity'] = '(' + CONVERSION_TABLES['glam::Vec3']( [scene.gravity[0], scene.gravity[2], scene.gravity[1]] ) + ')'
    else:
        scene['SceneGravity'] = '(' + CONVERSION_TABLES['glam::Vec3']( [0,0,0] ) + ')'
    
    tmp_time = time.time()

    # we set our active scene to active
    bpy.context.window.scene = scene
    layer_collection = scene.view_layers['ViewLayer'].layer_collection
    bpy.context.view_layer.active_layer_collection = recurLayerCollection(layer_collection, scene.collection.name)
        
    # find collection instances to be replaced with empty with blueprint name
    blueprints_instances: List[BlueprintInstance] = []        
    for obj in bpy.data.objects:         
        if scene.user_of_id(obj) == 0 or obj.instance_collection is None or obj.instance_collection.asset_data is None: 
            continue
        blueprints_instances.append(BlueprintInstance(obj, obj.instance_collection))
    
    # matches my rust build script
    def sanitize_file_name(name: str) -> str:
        parts = re.split(r'\W+', name)  # Split on non-alphanumeric characters
        sanitized_parts = [
            part.capitalize() for part in parts if part  # Capitalize each part
        ]
        return ''.join(sanitized_parts)
    
    # clear instance collection and set blueprint name
    for inst in blueprints_instances:
        obj = inst.object
        obj.instance_collection = None            
        obj['blueprint'] = sanitize_file_name(inst.collection.name)

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

# returens success and failure lists of blueprints
def export_scene_blueprints(settings: SPARROW_PG_Settings, area, region, scene) -> tuple[list[str], list[str]]:
    path = os.path.join(settings.assets_path, BLUEPRINT_FOLDER)  
    os.makedirs(path, exist_ok=True)

    success = []
    failure = []
    
    # iterate over all collections
    for col in bpy.data.collections:         
        # filter collections that are not assets and not in the scene
        if scene.user_of_id(col) == 0 or col.asset_data is None: 
            continue

        tmp_time = time.time()

        # build file path
        if settings.gltf_format == 'GLB':
            gltf_path = os.path.join(path, f"{col.name}.glb")
        else:
            gltf_path = os.path.join(path, f"{col.name}")
        
        # create temp scene: this is needed otherwise the stand-in empties get generated in the wrong scene
        temp_scene = bpy.data.scenes.new(name=col.name+"_temp")

        if 'bevy_components' in col:
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
                    success.append(col.name)
                except Exception as error:
                    failure.append(col.name)
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