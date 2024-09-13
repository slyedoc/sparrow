import bpy

from .properties import SPARROW_PG_Settings

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
            use_active_collection_with_nested=False, # different for blueprints
            use_active_collection=False, # different for blueprints
            use_active_scene=True, 
            # filters                                                                                                        
            use_visible=True,
        )