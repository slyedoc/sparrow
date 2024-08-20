import bpy


from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty)
from bpy.types import (Panel, Operator, PropertyGroup, UIList, Menu)


class SPARROW_PG_Global(PropertyGroup):
    last_scene: PointerProperty(Scene, name="last scene", description="used to go back") # type: ignore
    assets_path: StringProperty(
        name='Export folder',
        description='The root folder for all exports(relative to the root folder/path) Defaults to "assets" ',
        default='./assets',
        options={'HIDDEN'},
    ) # type: ignore
    registry_file: StringProperty(
        name='Registry File',
        description='The registry.json file',
        default='./assets/registry.json',
        options={'HIDDEN'},
    ) # type: ignore
    component_info: PointerProperty(
        name='Component Info',
        description='The component info',
        default='{}',
        options={'HIDDEN'},
    ) # type: ignore

class SPARROW_PG_Scene(PropertyGroup):    
    export: BoolProperty(name="Export", description="Automatically export scene as level", default = False, options = set()) # type: ignore    

class SPARROW_PG_Collection(PropertyGroup):    
    export: BoolProperty(name="Export", description="Automatically export scene as level", default = False, options = set()) # type: ignore    


