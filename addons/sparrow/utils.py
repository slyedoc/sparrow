import json
import os
import re
from typing import Any
import bpy
import uuid
import sys
import inspect

from bpy.props import (BoolProperty, StringProperty, CollectionProperty, IntProperty, PointerProperty, EnumProperty, FloatProperty,FloatVectorProperty )

INTERNAL_COMPONENTS = ['BlueprintInfos', 'blenvy::blueprints::materials::MaterialInfos']
HIDDEN_COMPONENTS = ['Parent', 'Children']

ITEM_TYPES =(
    ('OBJECT', "Object", ""),
    ('COLLECTION', "Collection", ""),
    #('MESH', "Mesh", ""),
    #('MATERIAL', "Material", ""),
    ('SCENE', "Scene", ""),
)

GLTF_FORMATS = (
    ('GLB', 'glTF Binary (.glb)', 'Exports single file, with all data packed in binary form. Most efficient and protable, but more difficult to edit later'),
    ('GLTF_SEPARATE', 'glTF Separate (.gltf + .bin + textures)', 'Exports multiple files, with separate JSON, binary and texture data. Easiest to edit later'),
    ('GLTF_EMBEDDED', 'glTF Embedded (.gltf + .bin)', 'Exports with all data packed in JSON. Less efficient, but easier to edit later'),
)

VALUE_TYPES_DEFAULTS = {
    "string":" ",
    "boolean": True,
    "float": 0.0,
    "uint": 0,
    "int":0,

    # todo : we are re-doing the work of the bevy /rust side here, but it seems more pratical to alway look for the same field name on the blender side for matches
    "bool": True,

    "u8": 0,
    "u16":0,
    "u32":0,
    "u64":0,
    "u128":0,
    "usize":0,

    "i8": 0,
    "i16":0,
    "i32":0,
    "i64":0,
    "i128":0,
    "isize":0,

    "f32": 0.0,
    "f64":0.0,

    "char": " ",
    "str": " ",
    "alloc::string::String": " ",
    "alloc::borrow::Cow<str>":  " ",

    "glam::Vec2": [0.0, 0.0],
    "glam::DVec2":  [0.0, 0.0],
    "glam::UVec2": [0, 0],

    "glam::Vec3": [0.0, 0.0, 0.0],
    "glam::Vec3A":[0.0, 0.0, 0.0],
    "glam::UVec3": [0, 0, 0],

    "glam::Vec4": [0.0, 0.0, 0.0, 0.0], 
    "glam::DVec4": [0.0, 0.0, 0.0, 0.0], 
    "glam::UVec4": [0, 0, 0, 0], 

    "glam::Quat":  [0.0, 0.0, 0.0, 0.0], 

    "bevy_render::color::Color": [1.0, 1.0, 0.0, 1.0],

    'bevy_ecs::entity::Entity': 0,#4294967295, # this is the same as Bevy's Entity::Placeholder, too big for Blender..sigh
    'bevy_utils::Uuid': '"'+str(uuid.uuid4())+'"'
}

TYPE_MAPPINGS = {
    "bool": lambda value: True if value == "true" else False,

    "u8": lambda value: int(value),
    "u16": lambda value: int(value),
    "u32": lambda value: int(value),
    "u64": lambda value: int(value),
    "u128": lambda value: int(value),
    "u64": lambda value: int(value),
    "usize": lambda value: int(value),

    "i8": lambda value: int(value),
    "i16": lambda value: int(value),
    "i32": lambda value: int(value),
    "i64": lambda value: int(value),
    "i128": lambda value: int(value),
    "isize": lambda value: int(value),

    'f32': lambda value: float(value),
    'f64': lambda value: float(value),

    "glam::Vec2": lambda value: parse_vec2(value, float, "Vec2"),
    "glam::DVec2": lambda value: parse_vec2(value, float, "DVec2"),
    "glam::UVec2": lambda value: parse_vec2(value, to_int, "UVec2"),

    'glam::Vec3': lambda value: parse_vec3(value, float, "Vec3"),
    "glam::Vec3A": lambda value: parse_vec3(value, float, "Vec3A"),
    "glam::UVec3": lambda value: parse_vec3(value, to_int, "UVec3"),

    "glam::Vec4": lambda value: parse_vec4(value, float, "Vec4"),
    "glam::DVec4": lambda value: parse_vec4(value, float, "DVec4"),
    "glam::UVec4": lambda value: parse_vec4(value, to_int, "UVec4"),

    "glam::Quat": lambda value: parse_vec4(value, float, "Quat"),

    'alloc::string::String': lambda value: str(value.replace('"', "")),
    'alloc::borrow::Cow<str>': lambda value: str(value.replace('"', "")),

    'bevy_render::color::Color': lambda value: parse_color(value, float, "Rgba"),
    'bevy_ecs::entity::Entity': lambda value: int(value),
}

CONVERSION_TABLES = {
    "bool": lambda value: value,

    "char": lambda value: '"'+value+'"',
    "str": lambda value: '"'+value+'"',
    "alloc::string::String": lambda value: '"'+str(value)+'"',
    "alloc::borrow::Cow<str>": lambda value: '"'+str(value)+'"',

    "glam::Vec2": lambda value: "Vec2(x:"+str(value[0])+ ", y:"+str(value[1])+")",
    "glam::DVec2": lambda value: "DVec2(x:"+str(value[0])+ ", y:"+str(value[1])+")",
    "glam::UVec2": lambda value: "UVec2(x:"+str(int(value[0]))+ ", y:"+str(int(value[1]))+")",


    "glam::Vec3": lambda value: "Vec3(x:"+str(value[0])+ ", y:"+str(value[1])+ ", z:"+str(value[2])+")",
    "glam::Vec3A": lambda value: "Vec3A(x:"+str(value[0])+ ", y:"+str(value[1])+ ", z:"+str(value[2])+")",
    "glam::UVec3": lambda value: "UVec3(x:"+str(int(value[0]))+ ", y:"+str(int(value[1]))+ ", z:"+str(int(value[2]))+")",

    "glam::Vec4": lambda value: "Vec4(x:"+str(value[0])+ ", y:"+str(value[1])+ ", z:"+str(value[2])+ ", w:"+str(value[3])+")",
    "glam::DVec4": lambda value: "DVec4(x:"+str(value[0])+ ", y:"+str(value[1])+ ", z:"+str(value[2])+ ", w:"+str(value[3])+")",
    "glam::UVec4": lambda value: "UVec4(x:"+str(int(value[0]))+ ", y:"+str(int(value[1]))+ ", z:"+str(int(value[2]))+ ", w:"+str(int(value[3]))+")",

    "glam::Quat":  lambda value: "Quat(x:"+str(value[0])+ ", y:"+str(value[1])+ ", z:"+str(value[2])+ ", w:"+str(value[3])+")",

    "bevy_render::color::Color": lambda value: "Rgba(red:"+str(value[0])+ ", green:"+str(value[1])+ ", blue:"+str(value[2])+ ", alpha:"+str(value[3])+   ")",
}

def recurLayerCollection(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found
        
def set_active_collection(scene, collection_name):
    layer_collection = scene.view_layers['ViewLayer'].layer_collection
    layerColl = recurLayerCollection(layer_collection, collection_name)
    # set active collection to the collection
    bpy.context.view_layer.active_layer_collection = layerColl

def full_stack_lines(tb=None):
    text = []
    try:
        if tb is None:
            tb = sys.exc_info()[2]

        text.append('Traceback (most recent call last):')
        for item in reversed(inspect.getouterframes(tb.tb_frame)[1:]):
            text.append('   File "{1}", line {2}, in {3}\n'.format(*item))
            for line in item[4]:
                text.append('       ' + line.lstrip())
        for item in inspect.getinnerframes(tb):
            text.append('   File "{1}", line {2}, in {3}\n'.format(*item))
            for line in item[4]:
                text.append('       ' + line.lstrip())
    except: pass
    return text

def exception_traceback(error):
    traceback_formated = [str(error)]
    traceback_formated += full_stack_lines()
    return traceback_formated

def show_message_box(title = "Message Box", icon = 'INFO', lines=""):
    myLines=lines
    def draw(self, context):
        for n in myLines:
            self.layout.label(text=n)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def is_def_value_type(definition):
    if definition == None:
        return True    
    long_name = definition["long_name"]
    is_value_type = long_name in VALUE_TYPES_DEFAULTS
    return is_value_type

def parse_struct_string(string, start_nesting=0):
    #print("processing struct string", string, "start_nesting", start_nesting)
    fields = {}
    buff = []
    current_fieldName = None
    nesting_level = 0 

    start_offset = 0
    end_offset = 0

    for index, char in enumerate(string):
        buff.append(char)
        if char == "," and nesting_level == start_nesting:
            #print("first case", end_offset)
            end_offset = index
            end_offset = len(string) if end_offset == 0 else end_offset

            val = "".join(string[start_offset:end_offset])
            fields[current_fieldName] = val.strip()
            start_offset = index + 1
            #print("done with field name", current_fieldName, "value", fields[current_fieldName])

        if char == "[" or char == "(":
            nesting_level  += 1
            if nesting_level == start_nesting:
                start_offset = index + 1 
                #print("nesting & setting start offset", start_offset)
            #print("nesting down", nesting_level)

        if char == "]" or char == ")" :
            #print("nesting up", nesting_level)
            if nesting_level == start_nesting:
                end_offset = index
                #print("unesting & setting end offset", end_offset)
            nesting_level  -= 1


        if char == ":" and nesting_level == start_nesting:
            end_offset = index
            fieldName = "".join(string[start_offset:end_offset])
            current_fieldName = fieldName.strip()
            start_offset = index + 1
            end_offset = 0 #hack
            #print("starting field name", fieldName, "index", index)
            buff = []
            
    end_offset = len(string) if end_offset == 0 else end_offset
    #print("final start and end offset", start_offset, end_offset, "total length", len(string))

    val = "".join(string[start_offset:end_offset])

    fields[current_fieldName] = val.strip()
    #print("done with all fields", fields)
    return fields

def parse_tuplestruct_string(string, start_nesting=0):
    #print("processing tuppleStruct", string, "start_nesting", start_nesting)
    fields = []
    buff = []
    nesting_level = 0 
    field_index = 0

    start_offset = 0
    end_offset = 0
    # todo: strip all stuff before start_nesting

    for index, char in enumerate(string):
        buff.append(char)
        if char == "," and nesting_level == start_nesting:
            end_offset = index
            end_offset = len(string) if end_offset == 0 else end_offset

            val = "".join(string[start_offset:end_offset])
            fields.append(val.strip())
            field_index += 1
            #print("start and end offset", start_offset, end_offset, "total length", len(string))
            #print("done with field name", field_index, "value", fields)
            start_offset = index + 1
            end_offset = 0 # hack

        if char == "[" or char == "(":
            nesting_level  += 1
            if nesting_level == start_nesting:
                start_offset = index + 1 
                #print("nesting & setting start offset", start_offset)
            #print("nesting down", nesting_level)

        if char == "]" or char == ")" :
            if nesting_level == start_nesting:
                end_offset = index
                #print("unesting & setting end offset", end_offset)
            #print("nesting up", nesting_level)
            nesting_level  -= 1


    end_offset = len(string) if end_offset == 0 else end_offset
    #print("final start and end offset", start_offset, end_offset, "total length", len(string))

    val = "".join(string[start_offset:end_offset]) #if end_offset != 0 else buff)
    fields.append(val.strip())
    fields = list(filter(lambda entry: entry != '', fields))
    #print("done with all fields", fields)
    return fields

def parse_vec2(value, caster, typeName):
    parsed = parse_struct_string(value.replace(typeName,"").replace("(", "").replace(")","") )
    return [caster(parsed['x']), caster(parsed['y'])]

def parse_vec3(value, caster, typeName):
    parsed = parse_struct_string(value.replace(typeName,"").replace("(", "").replace(")","") )
    return [caster(parsed['x']), caster(parsed['y']), caster(parsed['z'])]

def parse_vec4(value, caster, typeName):
    parsed = parse_struct_string(value.replace(typeName,"").replace("(", "").replace(")","") )
    return [caster(parsed['x']), caster(parsed['y']), caster(parsed['z']), caster(parsed['w'])]

def parse_color(value, caster, typeName):
    parsed = parse_struct_string(value.replace(typeName,"").replace("(", "").replace(")","") )
    return [caster(parsed['red']), caster(parsed['green']), caster(parsed['blue']), caster(parsed['alpha'])]

def to_int(input):
    return int(float(input))

#------------------------------------------------------------------------------------
#   Bevy Component Functions

def get_bevy_components(object):
    if 'bevy_components' in object:
        bevy_components = json.loads(object['bevy_components'])
        return bevy_components
    return {}

def get_bevy_component_value_by_long_name(object, long_name: str):
    bevy_components = get_bevy_components(object)
    if len(bevy_components.keys()) == 0 :
        return None
    return bevy_components.get(long_name, None)

def upsert_bevy_component(item, long_name: str, value):
    if not 'bevy_components' in item:
        item['bevy_components'] = '{}'
    bevy_components = json.loads(item['bevy_components'])
    bevy_components[long_name] = value
    item['bevy_components'] = json.dumps(bevy_components)

def remove_bevy_component(item, long_name):
    if 'bevy_components' in item:
        bevy_components = json.loads(item['bevy_components'])
        if long_name in bevy_components:
            del bevy_components[long_name]
            item['bevy_components'] = json.dumps(bevy_components)
    if long_name in item:
        del item[long_name]

###################################################################
# Selection Type Functions


def get_selected_item(context):
    if context.space_data.context == 'SCENE':
        return context.scene
    if context.space_data.context == 'OBJECT':
        return context.object
    if context.space_data.context == 'COLLECTION':
        return context.collection
    print("ERROR: could not get selected item")
    return None
    

def get_selection_type(selection):
    #print("bla mesh", isinstance(selection, bpy.types.Mesh), "bli bli", selection.type)
    if isinstance(selection, bpy.types.Material):
        return 'MATERIAL'
    if isinstance(selection, bpy.types.Mesh):
        return 'MESH'
    if isinstance(selection, bpy.types.Object):
        return 'OBJECT'
    if isinstance(selection, bpy.types.Collection):
        return 'COLLECTION'
    if isinstance(selection, bpy.types.Scene):
        return 'SCENE'

def get_item_by_type(item_type, item_name):
    item = None
    print(f"item type: {item_type} {item_name}")
    if item_type == 'OBJECT':
        item = bpy.data.objects[item_name]
    elif item_type == 'COLLECTION':
        item = bpy.data.collections[item_name]
    elif item_type == "MESH":
        item = bpy.data.meshes[item_name]
    elif item_type == 'MATERIAL':
        item = bpy.data.materials[item_name]
    elif item_type == 'SCENE':
        item = bpy.data.scenes[item_name]
    return item

#------------------------------------------------------------------------------------
#   Functions (Global)
def obj_bake_ready(self, context, target_obj, selected_obj):
    scene = context.scene
    bake = scene.render.bake
    abp = scene.autobake_properties
    
# Is Mesh
    if target_obj.type != "MESH":
        if abp.ab_report_bake_error:
            self.report({'ERROR'}, f"Auto Bake: Target object '{target_obj.name}' is a {target_obj.type} not a mesh.")
        return 'Object is not a mesh!'
    
# Has UV
    if not target_obj.data.uv_layers:
        if abp.ab_report_bake_error:
            self.report({'ERROR'}, f"Auto Bake: Target object '{target_obj.name}' has no active UV layer.")
        return 'Object has no UV Map!'
    
# Is Visible
    for obj in selected_obj:
        if obj.hide_render or obj.hide_viewport:
            if abp.ab_report_bake_error:
                self.report({'ERROR'}, f"Auto Bake: Object '{obj.name}' must be visible in the viewport and must be enabled for renders.")
                print(f"ERROR: Auto Bake: Object '{obj.name}' must be visible in the viewport and must be enabled for renders.")
            return 'Object is disabled in the viewport!'

# Filepath
    if abp.ab_texture_export and bool(os.path.exists(abp.ab_filepath)) == False:
        if abp.ab_report_bake_error:
            self.report({'ERROR'}, f"Auto Bake: Filepath '{abp.ab_filepath}' is invalid.")
        return 'Filepath is invalid!'
        
# Material
    if not any(slot.material is not None and slot.material.use_nodes for slot in target_obj.material_slots):
        if bake.use_selected_to_active:
            new_mat = bpy.data.materials.new(name=target_obj.name)
            if new_mat.name != target_obj.name:
                switch_name = str(new_mat.name)
                new_mat.name = ''
                bpy.data.materials[target_obj.name].name = switch_name
                new_mat.name = target_obj.name
            target_obj.data.materials.append(new_mat)
            new_mat.use_nodes = True
            if abp.ab_report_bake_error:
                self.report({'INFO'}, f"Auto Bake: Target object '{target_obj.name}' had no bake compatible material, '{new_mat.name}' was created and added to '{target_obj.name}'")
        else:
            if abp.ab_report_bake_error:
                self.report({'ERROR'}, f"Auto Bake: Target object '{target_obj.name}' must have a material to bake from with 'Use Nodes' enabled.")
            return 'Object must have a material!'
            
# Selected to Active
    if bake.use_selected_to_active:
        
    # Has Cage
        if bake.use_cage and bake.cage_object is None:
            if abp.ab_report_bake_error:
                self.report({'ERROR'}, "Auto Bake: Must have a set 'Cage Object' if 'Cage' is 'True'.")
            return "Must have set a 'Cage Object' if 'Cage' is 'True'"
    
    return True

def remove_handlers_timers():
    if bpy.app.timers.is_registered(restore_nodes):
        bpy.app.timers.unregister(restore_nodes)
        
    for handler in bpy.app.handlers.object_bake_cancel:
        if handler.__name__ == "ab_bake_cancel":
            bpy.app.handlers.object_bake_cancel.remove(handler)
            break
    for handler in bpy.app.handlers.object_bake_complete:
        if handler.__name__ == "ab_bake_complete":
            bpy.app.handlers.object_bake_complete.remove(handler)
            break
        

def restore_nodes():
    global delete_nodes
    global reconnect_nodes
    
    for item in reversed(reconnect_nodes):
        item[0].links.new(item[1], item[2])
        reconnect_nodes.remove(item)

    for item in reversed(delete_nodes):
        if (node := item[0].nodes.get(item[1].name, None)) is not None:
            item[0].nodes.remove(item[1])
        delete_nodes.remove(item)

def export_texture(self, context, img, export_name, type, label, prefix):
    scene = context.scene
    abp = scene.autobake_properties
    image_settings = scene.render.image_settings

    if prefix == '':
        prefix = "Auto Bake Export"

# Folder
    foldername = re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', prefix)
    foldername = foldername.strip()
    mainpath = os.path.join(abp.ab_filepath, foldername)
    
    if not os.path.isdir(mainpath):
        os.makedirs(mainpath)
    
    if not abp.ab_subfolders:
        ab_filepath = mainpath
    else:
        if abp.ab_subfolder_use_prefix:
            subpath = os.path.join(mainpath, (foldername+'.'+type))
        else:
            subpath = os.path.join(mainpath, (type))
            
        if os.path.isdir(subpath):
            ab_filepath = subpath
        else:
            os.makedirs(subpath)
            ab_filepath = subpath

# Color Mode
    image_settings.color_mode = 'BW' if label in ['Float', 'AO', 'Ambient Occlusion', 'Pointiness'] else 'RGB'
        
# Color Override
    if not abp.ab_custom_color_management:
        stored_color_management = {
            'Color Management': scene.render.image_settings.color_management,
            'Display Device': scene.render.image_settings.display_settings.display_device,
            'View': scene.render.image_settings.view_settings.view_transform,
            'Look': scene.render.image_settings.view_settings.look,
            'Exposure': scene.render.image_settings.view_settings.exposure,
            'Gamma': scene.render.image_settings.view_settings.gamma,
            'Use Curves': scene.render.image_settings.view_settings.use_curve_mapping}
            
        scene.render.image_settings.color_management = 'OVERRIDE'
        scene.render.image_settings.display_settings.display_device = 'sRGB'
        scene.render.image_settings.view_settings.view_transform = 'Raw'
        scene.render.image_settings.view_settings.look = 'None'
        scene.render.image_settings.view_settings.exposure = 0
        scene.render.image_settings.view_settings.gamma = 1
        scene.render.image_settings.view_settings.use_curve_mapping = False

# File Format
    image_settings.file_format = abp.ab_fileformat
    
    file_extensions = {'BMP': 'bmp',
                       'IRIS': 'rgb',
                       'PNG': 'png',
                       'JPEG': 'jpg',
                       'JPEG2000': 'jp2' if image_settings.jpeg2k_codec == "JP2" else 'j2c',
                       'TARGA': 'tga',
                       'TARGA_RAW': 'tga',
                       'CINEON': 'cin',
                       'DPX': 'dpx',
                       'OPEN_EXR_MULTILAYER': 'exr',
                       'OPEN_EXR': 'exr',
                       'HDR': 'hdr',
                       'TIFF': 'tif',
                       'WEBP': 'webp'}
    file_extension = file_extensions[abp.ab_fileformat]

# Export
    img.filepath_raw = os.path.join(ab_filepath, f"{export_name}.{file_extension}")
    img.save_render(filepath = img.filepath_raw)

# Info
    if abp.ab_report_texture_export:
        self.report({'INFO'}, f"Auto Bake: '{img.name}' successfully exported to: {ab_filepath}")
        
# Restore Color Override
    if not abp.ab_custom_color_management:
        scene.render.image_settings.color_management = stored_color_management['Color Management']
        scene.render.image_settings.display_settings.display_device = stored_color_management['Display Device']
        scene.render.image_settings.view_settings.view_transform = stored_color_management['View']
        scene.render.image_settings.view_settings.look = stored_color_management['Look']
        scene.render.image_settings.view_settings.exposure = stored_color_management['Exposure']
        scene.render.image_settings.view_settings.gamma = stored_color_management['Gamma']
        scene.render.image_settings.view_settings.use_curve_mapping = stored_color_management['Use Curves']



SCENE_FOLDER = 'scenes'
BLUEPRINT_FOLDER = 'blueprints'

bake_status = "IDLE"
is_udim_bake = False
next_object_bake = False
finished_bake_count = 0
reconnect_nodes = []
delete_nodes = []
bake_results = {}
bake_order = []

bake_items = [
    ('', "Shader", "", -1),
    ('Base Color', "Base Color", "Bakes input sockets named 'Base Color', 'Color', and 'Tint' for shader nodes", 1),
    ('Metallic', "Metallic", "Bakes input sockets named 'Metallic' for shader nodes", 2),
    ('Roughness', "Roughness", "Bakes input sockets named 'Roughness' for shader nodes", 3),
    ('IOR', "IOR", "Bakes input sockets named 'IOR' for shader nodes", 4),
    ('Alpha', "Alpha", "Bakes input sockets named 'Alpha' and 'Transparency' for shader nodes", 5),
    ('Normal', "Normal", "Bakes input sockets named 'Normal' for shader nodes", 6),

    ('', "* Subsurface", "", -1),
    ('Subsurface Weight', "Subsurface Weight", "Bakes input sockets named 'Subsurface Weight' for shader nodes", 7),
    ('Subsurface Radius', "Subsurface Radius", "Bakes input sockets named 'Subsurface Radius' and 'Radius' for shader nodes", 8),
    ('Subsurface Scale', "Subsurface Scale", "Bakes input sockets named 'Subsurface Scale' for shader nodes", 9),
    ('Subsurface IOR', "Subsurface IOR", "Bakes input sockets named 'Subsurface IOR' for shader nodes", 10),
    ('Subsurface Anisotropy', "Subsurface Anisotropy", "Bakes input sockets named 'Subsurface Anisotropy' and 'Anisotropy' for shader nodes", 11),

    ('', "* Specular", "", -1),
    ('Specular IOR Level', "Specular IOR Level", "Bakes input sockets named 'Specular IOR Level' for shader nodes", 12),
    ('Specular Tint', "Specular Tint", "Bakes input sockets named 'Specular Tint' for shader nodes", 13),
    ('Anisotropic', "Anisotropic", "Bakes input sockets named 'Anisotropic' for shader nodes", 14),
    ('Anisotropic Rotation', 'Anisotropic Rotation', "Bakes input sockets named 'Anisotropic Rotation' for shader nodes", 15),
    ('Tangent', "Tangent", "Bakes input sockets named 'Tangent' for shader nodes", 16),

    ('', "* Coat", "", -1),
    ('Coat Weight', 'Coat Weight', "Bakes input sockets named 'Coat Weight' and 'Clear Coat' for shader nodes", 17),
    ('Coat Roughness', 'Coat Roughness', "Bakes input sockets named 'Coat Roughness' and 'Clear Coat Roughness' for shader nodes", 18),
    ('Coat IOR', 'Coat IOR', "Bakes input sockets named 'Coat IOR' for shader nodes", 19),
    ('Coat Tint', 'Coat Tint', "Bakes input sockets named 'Coat Tint' for shader nodes", 20),
    ('Coat Normal', 'Coat Normal', "Bakes input sockets named 'Coat Normal' and 'Clear Coat Normal' for shader nodes", 21),

    ('', "*", "", -1),
    ('Transmission Weight', "Transmission Weight", "Bakes input sockets named 'Transmission Weight' for shader nodes", 22),
    ('Sheen Weight', "Sheen Weight", "Bakes input sockets named 'Sheen Weight' for shader nodes", 23),
    ('Sheen Roughness', "Sheen Roughness", "Bakes input sockets named 'Sheen Roughness' for shader nodes", 24),
    ('Sheen Tint', 'Sheen Tint', "Bakes input sockets named 'Sheen Tint' for shader nodes", 25),
    ('Emission Color', "Emission Color", "Bakes input sockets named 'Emission Color' and 'Emissive Color' for shader nodes", 26),
    ('Emission Strength', "Emission Strength", "Bakes input sockets named 'Emission Strength' for shader nodes", 27),

    ('', "Miscellaneous", "", -1),
    ('Channel Packing', "Channel Packing", "Bakes up to 3 different BW bake types into a single RGB texture", 28),
    ('Color Attribute', "Color Attribute", "Bakes the set or available color attribute", 29),
    ('Ambient Occlusion', 'Ambient Occlusion', "Bakes ambient occlusion using the 'Ambient Occlusion' node", 30),
    ('Pointiness', 'Pointiness', "Bakes pointiness using the 'Geometry' node's 'Pointiness' socket, with a 'Brightness/Contrast' node", 31),
    ('Displacement ', "Displacement ", "Bakes socket values of the 'Displacement' input socket node of the 'Material Output'", 32),

    ('', "Multires", "", -1),
    ('Normals', "Normals", "Bakes normal data from the object's 'Multiresolution' modifier", 33),
    ('Displacement', "Displacement", "Bakes displacement data from the object's 'Multiresolution' modifier", 34),

    ('', "Standard", "", -1),
    ('Combined', 'Combined', "Blender's default 'Combined' bake pass. Bakes all materials, textures, and lighting except specularity. The passes that contribute to the combined pass can be toggled individually to form the final map", 35),
    ('Ambient Occlusion ', "Ambient Occlusion ", "Blender's default 'Ambient Occlusion' bake pass. Bakes ambient occlusion as specified in the World panels. Ignores all lights in the scene", 36),
    ('Normal ', 'Normal ', "Blender's default 'Normal' bake pass. Bakes the normal pass of the materials", 37),
    ('Roughness ', 'Roughness ', "Blender's default 'Roughness' bake pass. Bakes the roughness pass of the materials", 38),
    ('Glossy', 'Glossy', "Blender's default 'Glossy' bake pass. Bakes the glossiness pass of the materials", 39),
    ('Position', 'Position', "Blender's default 'Position' bake pass. Bakes the mesh's position data", 40),

    ('', "*", "", -1),
    ('Shadow', "Shadow", "Blender's default 'Shadow' bake pass. Bakes shadows and lighting", 41),
    ('Diffuse', "Diffuse", "Blender's default 'Diffuse' bake pass. Bakes the diffuse pass of the materials", 42),
    ('UV', "UV", "Blender's default 'UV' bake pass. Mapped UV coordinates, used to represent where on a mesh a texture gets mapped to", 43),
    ('Transmission', "Transmission", "Blender's default 'Transmission' bake pass. Bakes the transmission pass of the materials", 44),
    ('Environment', "Environment", "Blender's default 'Environment' bake pass. Bakes the environment (i.e. the world surface shader defined for the scene) onto the selected object(s) as seen by rays cast from the world origin", 45),
    ('Emit', "Emit", "Blender's default 'Emit' bake pass. Bakes Emission, or the Glow color of materials", 46),

    ] if bpy.app.version >= (4, 0, 0) else [
    
    ('', "Shader", "", -1),
    ('Base Color', "Base Color", "Bakes input sockets named 'Base Color', 'Color', and 'Tint' for shader nodes", 1),
    ('Subsurface', "Subsurface", "Bakes input sockets named 'Subsurface' for shader nodes", 7),
    ('Subsurface Radius', "Subsurface Radius", "Bakes input sockets named 'Subsurface Radius' and 'Radius' for shader nodes", 8),
    ('Subsurface Color', "Subsurface Color", "Bakes input sockets named 'Subsurface Color' for shader nodes", 51),
    ('Subsurface IOR', "Subsurface IOR", "Bakes input sockets named 'Subsurface IOR' for shader nodes", 10),
    ('Subsurface Anisotropy', "Subsurface Anisotropy", "Bakes input sockets named 'Subsurface Anisotropy' and 'Anisotropy' for shader nodes", 11),
    ('Metallic', "Metallic", "Bakes input sockets named 'Metallic' for shader nodes", 2),
    ('Specular', "Specular", "Bakes input sockets named 'Specular' for shader nodes", 12),
    ('Specular Tint', "Specular Tint", "Bakes input sockets named 'Specular Tint' for shader nodes", 13),

    ('', "*", "", -1),
    ('Roughness', "Roughness", "Bakes input sockets named 'Roughness' for shader nodes", 3),
    ('Anisotropic', "Anisotropic", "Bakes input sockets named 'Anisotropic' for shader nodes", 14),
    ('Anisotropic Rotation', "Anisotropic Rotation", "Bakes input sockets named 'Anisotropic Rotation' for shader nodes", 15),
    ('Sheen', "Sheen", "Bakes input sockets named 'Sheen' for shader nodes", 23),
    ('Sheen Tint', 'Sheen Tint', "Bakes input sockets named 'Sheen Tint' for shader nodes", 25),
    ('Clearcoat', 'Clearcoat', "Bakes input sockets named 'Clearcoat' and 'Clear Coat' for shader nodes", 17),
    ('Clearcoat Roughness', 'Clearcoat Roughness', "Bakes input sockets named 'Clearcoat Roughness' and 'Clear Coat Roughness' for shader nodes", 18),
    ('IOR', "IOR", "Bakes input sockets named 'IOR' for shader nodes", 4),
    ('Transmission', "Transmission", "Bakes input sockets named 'Transmission' for shader nodes", 22),

    ('', "*", "", -1),
    ('Transmission Roughness', "Transmission Roughness", "Bakes input sockets named 'Transmission Roughness' for shader nodes", 50),
    ('Emission', "Emission", "Bakes input sockets named 'Emission', 'Emissive Color', and 'Emission Color' for shader nodes", 26),
    ('Emission Strength', "Emission Strength", "Bakes input sockets named 'Emission Strength' for shader nodes", 27),
    ('Alpha', "Alpha", "Bakes input sockets named 'Alpha' and 'Transparency' for shader nodes", 5),
    ('Normal', "Normal", "Bakes input sockets named 'Normal' for shader nodes", 6),
    ('Clearcoat Normal', 'Clearcoat Normal', "Bakes input sockets named 'Clearcoat Normal' and 'Clear Coat Normal' for shader nodes", 21),
    ('Tangent', "Tangent", "Bakes input sockets named 'Tangent' for shader nodes", 16),

    ('', "Miscellaneous", "", -1),
    ('Channel Packing', "Channel Packing", "Bakes up to 3 different BW bake types into a single RGB texture", 28),
    ('Color Attribute', "Color Attribute", "Bakes the set or available color attribute", 29),
    ('Ambient Occlusion', 'Ambient Occlusion', "Bakes ambient occlusion using the 'Ambient Occlusion' node", 30),
    ('Pointiness', 'Pointiness', "Bakes pointiness using the 'Geometry' node's 'Pointiness' socket, with a 'Brightness/Contrast' node", 31),
    ('Displacement ', "Displacement ", "Bakes socket values of the 'Displacement' input socket node of the 'Material Output'", 32),

    ('', "Multires", "", -1),
    ('Normals', "Normals", "Bakes normal data from the object's 'Multiresolution' modifier", 33),
    ('Displacement', "Displacement", "Bakes displacement data from the object's 'Multiresolution' modifier", 34),

    ('', "Standard", "", -1),
    ('Combined', 'Combined', "Blender's default 'Combined' bake pass. Bakes all materials, textures, and lighting except specularity. The passes that contribute to the combined pass can be toggled individually to form the final map", 35),
    ('Ambient Occlusion ', "Ambient Occlusion ", "Blender's default 'Ambient Occlusion' bake pass. Bakes ambient occlusion as specified in the World panels. Ignores all lights in the scene", 36),
    ('Normal ', 'Normal ', "Blender's default 'Normal' bake pass. Bakes the normal pass of the materials", 37),
    ('Roughness ', 'Roughness ', "Blender's default 'Roughness' bake pass. Bakes the roughness pass of the materials", 38),
    ('Glossy', 'Glossy', "Blender's default 'Glossy' bake pass. Bakes the glossiness pass of the materials", 39),
    ('Position', 'Position', "Blender's default 'Position' bake pass. Bakes the mesh's position data", 40),
    ('Shadow', "Shadow", "Blender's default 'Shadow' bake pass. Bakes shadows and lighting", 41),
    ('Diffuse', "Diffuse", "Blender's default 'Diffuse' bake pass. Bakes the diffuse pass of the materials", 42),
    ('UV', "UV", "Blender's default 'UV' bake pass. Mapped UV coordinates, used to represent where on a mesh a texture gets mapped to", 43),

    ('', "*", "", -1),
    ('Transmission', "Transmission", "Blender's default 'Transmission' bake pass. Bakes the transmission pass of the materials", 44),
    ('Environment', "Environment", "Blender's default 'Environment' bake pass. Bakes the environment (i.e. the world surface shader defined for the scene) onto the selected object(s) as seen by rays cast from the world origin", 45),
    ('Emit', "Emit", "Blender's default 'Emit' bake pass. Bakes Emission, or the Glow color of materials", 46)
    ]
    
channel_packing_items = [
    ('', "Shader", "", -1),
    ('Metallic', "Metallic", "Bakes input sockets named 'Metallic' for shader nodes", 2),
    ('Roughness', "Roughness", "Bakes input sockets named 'Roughness' for shader nodes", 3),
    ('IOR', "IOR", "Bakes input sockets named 'IOR' for shader nodes", 4),
    ('Alpha', "Alpha", "Bakes input sockets named 'Alpha' and 'Transparency' for shader nodes", 5),
    
    ('', "Subsurface", "", -1),
    ('Subsurface Weight', "Subsurface Weight", "Bakes input sockets named 'Subsurface Weight' for shader nodes", 7),
    ('Subsurface Scale', "Subsurface Scale", "Bakes input sockets named 'Subsurface Scale' for shader nodes", 9),
    ('Subsurface IOR', "Subsurface IOR", "Bakes input sockets named 'Subsurface IOR' for shader nodes", 10),
    ('Subsurface Anisotropy', "Subsurface Anisotropy", "Bakes input sockets named 'Subsurface Anisotropy' and 'Anisotropy' for shader nodes", 11),
    
    ('', "Specular", "", -1),
    ('Specular IOR Level', "Specular IOR Level", "Bakes input sockets named 'Specular IOR Level' for shader nodes", 12),
    ('Anisotropic', "Anisotropic", "Bakes input sockets named 'Anisotropic' for shader nodes", 14),
    ('Anisotropic Rotation', "Anisotropic Rotation", "Bakes input sockets named 'Anisotropic Rotation' for shader nodes", 15),
    
    ('', "Coat", "", -1),
    ('Coat Weight', 'Coat Weight', "Bakes input sockets named 'Coat Weight' and 'Clear Coat' for shader nodes", 17),
    ('Coat Roughness', 'Coat Roughness', "Bakes input sockets named 'Coat Roughness' and 'Clear Coat Roughness' for shader nodes", 18),
    ('Coat IOR', 'Coat IOR', "Bakes input sockets named 'Coat IOR' for shader nodes", 19),
    
    ('', "Sheen", "", -1),
    ('Sheen Weight', "Sheen Weight", "Bakes input sockets named 'Sheen Weight' for shader nodes", 23),
    ('Sheen Roughness', "Sheen Roughness", "Bakes input sockets named 'Sheen Roughness' for shader nodes", 24),
    
    ('', "*", "", -1),
    ('Transmission Weight', "Transmission Weight", "Bakes input sockets named 'Transmission Weight' for shader nodes", 22),
    ('Emission Strength', "Emission Strength", "Bakes input sockets named 'Emission Strength' for shader nodes", 27),
    
    ('', "Miscellaneous", "", -1),
    ('Ambient Occlusion', 'Ambient Occlusion', "Bakes ambient occlusion using the 'Ambient Occlusion' node", 30),
    ('Pointiness', 'Pointiness', "Bakes pointiness using the 'Geometry' node's 'Pointiness' socket, with a 'Brightness/Contrast' node", 31),

    ('', "None", "", -1),
    ('None', "None", "Nothing will be baked on this channel", 0)
    
    ] if bpy.app.version >= (4, 0, 0) else [

    ('', "Principled BSDF", "", -1),
    ('Metallic', "Metallic", "Bakes input sockets named 'Metallic' for shader nodes", 2),
    ('Roughness', "Roughness", "Bakes input sockets named 'Roughness' for shader nodes", 3),
    ('Alpha', "Alpha", "Bakes input sockets named 'Alpha' and 'Transparency' for shader nodes", 5),
    ('IOR', "IOR", "Bakes input sockets named 'IOR' for shader nodes", 4),
    ('Specular', "Specular", "Bakes input sockets named 'Specular' for shader nodes", 12),
    ('Specular Tint', "Specular Tint", "Bakes input sockets named 'Specular Tint' for shader nodes", 13),
    
    ('', "", "", -1), 
    ('Subsurface', "Subsurface", "Bakes input sockets named 'Subsurface' for shader nodes", 7),
    ('Subsurface IOR', "Subsurface IOR", "Bakes input sockets named 'Subsurface IOR' for shader nodes", 10),
    ('Subsurface Anisotropy', "Subsurface Anisotropy", "Bakes input sockets named 'Subsurface Anisotropy' and 'Anisotropy' for shader nodes", 11),
    ('Anisotropic', "Anisotropic", "Bakes input sockets named 'Anisotropic' for shader nodes", 14),
    ('Anisotropic Rotation', "Anisotropic Rotation", "Bakes input sockets named 'Anisotropic Rotation' for shader nodes", 15),
    ('Emission Strength', "Emission Strength", "Bakes input sockets named 'Emission Strength' for shader nodes", 27),
    
    ('', "", "", -1),
    ('Sheen', "Sheen", "Bakes input sockets named 'Sheen' for shader nodes", 23),
    ('Sheen Tint', 'Sheen Tint', "Bakes input sockets named 'Sheen Tint' for shader nodes", 25),
    ('Clearcoat', 'Clearcoat', "Bakes input sockets named 'Clearcoat' and 'Clear Coat' for shader nodes", 17),
    ('Clearcoat Roughness', 'Clearcoat Roughness', "Bakes input sockets named 'Clearcoat Roughness' and 'Clear Coat Roughness' for shader nodes", 18),
    ('Transmission', "Transmission", "Bakes input sockets named 'Transmission' for shader nodes", 22),
    ('Transmission Roughness', "Transmission Roughness", "Bakes input sockets named 'Transmission Roughness' for shader nodes", 50),

    ('', "Miscellaneous", "", -1),
    ('Ambient Occlusion', 'Ambient Occlusion', "Bakes ambient occlusion using the 'Ambient Occlusion' node", 30),
    ('Pointiness', 'Pointiness', "Bakes pointiness using the 'Geometry' node's 'Pointiness' socket, with a 'Brightness/Contrast' node", 31),

    ('', "None", "", -1),
    ('None', "None", "Nothing will be baked on this channel", 0)
    ]

type_aliases = {
    'Base Color': ['Color', 'Tint'],
    'Alpha': ['Transparency'],
    'Subsurface Anisotropy': ['Anisotropy'],
    'Subsurface Radius': ['Radius'],
    'Coat Weight': ['Clear Coat'],
    'Clearcoat': ['Clear Coat'],
    'Coat Normal': ['Clear Coat Normal'],
    'Clearcoat Normal': ['Clear Coat Normal'],
    'Coat Roughness': ['Clear Coat Roughness'],
    'Clearcoat Roughness': ['Clear Coat Roughness'],
    'Emission': ['Emission Color', 'Emissive Color'],
    'Emission Color': ['Emissive Color', 'Color'],
    'Emission Strength': ['Strength'],
    }

color_space = [
    ('', "Color Space", ""),
    ("ACES2065-1", "ACES2065-1", ""),
    ("ACEScg", "ACEScg", ""),
    ("AgX Base Display P3", "AgX Base Display P3", ""),
    ("AgX Base Rec.1886", "AgX Base Rec.1886", ""),
    ("AgX Base Rec.2020", "AgX Base Rec.2020", ""),
    ("AgX Base sRGB", "AgX Base sRGB", ""),
    ("AgX Log", "AgX Log", ""),
    ("Display P3", "Display P3", ""),
    ("Filmic Log", "Filmic Log", ""),
    ("Filmic sRGB", "Filmic sRGB", ""),
    ('', "", ""),
    ("Linear CIE-XYZ D65", "Linear CIE-XYZ D65", ""),
    ("Linear CIE-XYZ E", "Linear CIE-XYZ E", ""),
    ("Linear DCI-P3 D65", "Linear DCI-P3 D65", ""),
    ("Linear FilmLight E-Gamut", "Linear FilmLight E-Gamut", ""),
    ("Linear Rec.2020", "Linear Rec.2020", ""),
    ("Linear Rec.709", "Linear Rec.709", ""),
    ("Non-Color", "Non-Color", ""),
    ("Rec.1886", "Rec.1886", ""),
    ("Rec.2020", "Rec.2020", ""),
    ("sRGB", "sRGB", "")
    
    ] if bpy.app.version >= (4, 0, 0) else [

    ('', "Input Color Space", ""),
    ("XYZ", "XYZ", ""),
    ("sRGB", "sRGB", ""),
    ("Raw", "Raw", ""),
    ("Non-Color", "Non-Color", ""),
    ("Linear ACEScg", "Linear ACEScg", ""),
    ("Linear ACES", "Linear ACES", ""),
    ("Linear", "Linear", ""),
    ("Filmic sRGB", "Filmic sRGB", ""),
    ("Filmic Log", "Filmic Log", "")
    ]