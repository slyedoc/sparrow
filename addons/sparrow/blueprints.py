from dataclasses import dataclass
from types import SimpleNamespace
from typing import List
import bpy

from .utils import *


# blueprints: any collections in scene that are marked as assets
# https://blender.stackexchange.com/questions/167878/how-to-get-all-collections-of-the-current-scene
def scan_blueprints(scene: bpy.types.Scene ):
    collections: List[bpy.types.Collection] = []
    for collection in bpy.data.collections:         
        if scene.user_of_id(collection) == 0 or collection.asset_data is None: 
            continue
        collections.append(collection)
    return collections


@dataclass
class BlueprintInstance:    
    object: bpy.types.Object
    collection: bpy.types.Collection
    

def scan_blueprint_instances(scene: bpy.types.Scene ):
    instances: List[BlueprintInstance] = []
    for obj in bpy.data.objects:         
        if scene.user_of_id(obj) == 0 or obj.instance_collection is None or obj.instance_collection.asset_data is None: 
            continue
        inst = BlueprintInstance(obj, obj.instance_collection)
        instances.append(inst)
    return instances

# matches my rust build script
def sanitize_file_name(name: str) -> str:
    parts = re.split(r'\W+', name)  # Split on non-alphanumeric characters
    sanitized_parts = [
        part.capitalize() for part in parts if part  # Capitalize each part
    ]
    return ''.join(sanitized_parts)