import json
import time
from typing import Any, Dict

from .export import export_scene, export_scene_blueprints
from .utils import *
from .properties import *
from .blueprints import *

import bpy
import os
import platform
import re
import math
import mathutils

from bpy_extras.io_utils import ImportHelper
from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty)
from bpy.types import (Panel, Operator, PropertyGroup, UIList, Menu) # 
from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty)
from bpy.types import (Panel, Operator, PropertyGroup, UIList, Menu)

from .utils import *

def edit_collection_menu(self, context):    
    self.layout.operator(SPARROW_OT_EditCollectionInstance.bl_idname, text="Edit Collection Instance")

class SPARROW_OT_EditCollectionInstance(Operator):
    """Goto Collection Instance Scene and isolate it"""
    bl_idname = "object.edit_collection_instance"
    bl_label = "Edit Instanced Collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):  
        settings: SPARROW_PG_Settings = context.window_manager.sparrow_settings         
        settings.last_scene = None
        coll = bpy.context.active_object.instance_collection

        if not coll:
            self.report({"WARNING"}, "Active item is not a collection instance")
            return {"CANCELLED"}
        
        # Save the current scene so we can return to it later
        settings.last_scene = bpy.context.scene

        # Find the scene that contains this collection and go to it       
        target_scene = None
        for scene in bpy.data.scenes:
            if scene.user_of_id(coll):
                target_scene = scene
                break

        if not target_scene:
            print("Cant find scene with collection {coll.name}")
            self.report({"WARNING"}, "Can't find scene with collection")
            return {"CANCELLED"}
        else:
            bpy.context.window.scene = target_scene        

        # Deselect all objects, then select the root object in the collection
        bpy.ops.object.select_all(action='DESELECT')

        root_obj = next((obj for obj in coll.objects if obj.parent is None), None)
        if root_obj:
            root_obj.select_set(True)
            bpy.context.view_layer.objects.active = root_obj

            # Trigger Local View (isolation mode) to isolate the selected object
            # Hotkey for this is / (forward slash) and is a toggle, 
            # this way you can see rest of the scene if needed
            #bpy.ops.view3d.localview()
            
            # Move focus to the Outliner and show the active object
            for area in bpy.context.window.screen.areas:
                if area.type == 'OUTLINER':
                    with context.temp_override(area=area):
                        bpy.ops.outliner.show_active()  # Focus the Outliner on the active object
                    break

            # Zoom to the selected object
            bpy.ops.view3d.view_selected()
        else:
            self.report({"WARNING"}, "No root object found in the collection")
            return {"CANCELLED"}

        return {"FINISHED"}

def exit_collection_instance(self, context):    
    self.layout.operator(SPARROW_OT_ExitCollectionInstance.bl_idname, text="Exit Collection Instance")
    
class SPARROW_OT_ExitCollectionInstance(Operator):    
     """Exit current scene and return to the previous scene"""
     bl_idname = "object.exit_collection_instance"
     bl_label = "Exit Collection Instance"
     bl_options = {"UNDO"}
   
     def execute(self, context):
        settings: SPARROW_PG_Settings  = bpy.context.window_manager.sparrow_settings  
       
        if not settings.last_scene:
            self.report({"WARNING"}, "No scene to return to")
            return {"CANCELLED"}
        
        if bpy.context.space_data.local_view: 
            bpy.ops.view3d.localview()

        bpy.context.window.scene = settings.last_scene
        settings.last_scene = None

        # Zoom to the selected object
        bpy.ops.view3d.view_selected()

        return {'FINISHED'}

class SPARROW_OT_ExportCurrentScene(Operator):
    """Export Current Scene"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "sparrow.export_current_scene"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Export Current Scene"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):       
        settings: SPARROW_PG_Settings  = bpy.context.window_manager.sparrow_settings  
 
        # Trigger the save operation
        if settings.save_on_export:
            bpy.ops.wm.save_mainfile()

        # save active scene
        active_scene = bpy.context.window.scene
        active_collection = bpy.context.view_layer.active_layer_collection
        active_mode = bpy.context.active_object.mode if bpy.context.active_object is not None else None
        debug_mode = bpy.app.debug_value
        bpy.app.debug_value = 2 # so only see warnings from gltf exporter
        # we change the mode to object mode, otherwise the gltf exporter is not happy
        if active_mode is not None and active_mode != 'OBJECT':
            print("setting to object mode", active_mode)
            bpy.ops.object.mode_set(mode='OBJECT')

        area = [area for area in bpy.context.screen.areas if area.type == "VIEW_3D"][0]
        region = [region for region in area.regions if region.type == 'WINDOW'][0]

        success_scene = []
        failure_scene = []

        success_blueprints = []
        failure_blueprints = []
        
        scene = bpy.context.window.scene
        scene_props: SPARROW_PG_SceneProps = scene.sparrow_scene_props

        if scene_props.scene_export:    
            if export_scene(settings, area, region, scene):
                success_scene.append(scene.name)
            else:
                failure_scene.append(scene.name)
        
        if scene_props.blueprint_export:
            (s, f) = export_scene_blueprints(settings, area, region, scene)
            success_blueprints.extend(s)
            failure_blueprints.extend(f)

        # reset active scene
        bpy.context.window.scene = active_scene
        # reset active collection
        bpy.context.view_layer.active_layer_collection = active_collection        
        # reset mode
        if active_mode is not None:
            bpy.ops.object.mode_set( mode = active_mode )
        
        bpy.app.debug_value = debug_mode

        if len(failure_scene)  > 0 or len(failure_blueprints) > 0:
            self.report({'ERROR'}, f"Exported {success_scene} scenes, {failure_scene} failed, exported {success_blueprints} blueprints, {failure_blueprints} failed")
        else:
            self.report({'INFO'}, f"Exported {success_scene} scenes and {success_blueprints} blueprints")

        return {'FINISHED'} 

# export all scenes that are marked for export
class SPARROW_OT_ExportSelectedScenes(Operator):
    """Export Selected Scenes"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "sparrow.export_selected_scenes"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Export Selected Scenes"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):       
        settings: SPARROW_PG_Settings  = bpy.context.window_manager.sparrow_settings  
        
        # Trigger the save operation
        if settings.save_on_export:
            bpy.ops.wm.save_mainfile()

        # save active scene
        active_scene = bpy.context.window.scene
        active_collection = bpy.context.view_layer.active_layer_collection
        active_mode = bpy.context.active_object.mode if bpy.context.active_object is not None else None
        debug_mode = bpy.app.debug_value
        bpy.app.debug_value = 2 # so only see warnings from gltf exporter
        # we change the mode to object mode, otherwise the gltf exporter is not happy
        if active_mode is not None and active_mode != 'OBJECT':
            print("setting to object mode", active_mode)
            bpy.ops.object.mode_set(mode='OBJECT')

        area = [area for area in bpy.context.screen.areas if area.type == "VIEW_3D"][0]
        region = [region for region in area.regions if region.type == 'WINDOW'][0]

        success_scene: list[str] = []
        failure_scene: list[str] = []

        success_blueprints: list[str] = []
        failure_blueprints: list[str] = []

        for scene in bpy.data.scenes:
            scene_props: SPARROW_PG_SceneProps = scene.sparrow_scene_props
            if not scene_props.export:
                continue

            if scene_props.scene_export:    
                if export_scene(settings, area, region, scene):
                    success_scene.append(scene.name)
                else:
                    failure_scene.append(scene.name)
            if scene_props.blueprint_export:
                (s, f) = export_scene_blueprints(settings, area, region, scene)
                success_blueprints.extend(s)
                failure_blueprints.extend(f)


        # reset active scene
        bpy.context.window.scene = active_scene
        # reset active collection
        bpy.context.view_layer.active_layer_collection = active_collection        
        # reset mode
        if active_mode is not None:
            bpy.ops.object.mode_set( mode = active_mode )
        
        bpy.app.debug_value = debug_mode

        if len(failure_scene) > 0 or len(failure_blueprints) > 0:
            self.report({'ERROR'}, f"Exported {success_scene} scenes, {failure_scene} failed, exported {success_blueprints} blueprints, {failure_blueprints} failed")
        else:
            self.report({'INFO'}, f"Exported {success_scene} scenes and {success_blueprints} blueprints")

        return {'FINISHED'} 

class SPARROW_OT_LoadRegistry(Operator):
    """Load the registry file"""
    bl_idname = "sparrow.load_registry"
    bl_label = "Load Registry"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings: SPARROW_PG_Settings  = bpy.context.window_manager.sparrow_settings  
        settings.load_registry()
        return {'FINISHED'}

class SPARROW_OT_OpenAssetsFolderBrowser(Operator, ImportHelper):
    """Assets folder's browser"""
    bl_idname = "sparrow.open_folderbrowser" 
    bl_label = "Select folder" 

    # Define this to tell 'fileselect_add' that we want a directoy
    directory: bpy.props.StringProperty(
        name="Outdir Path",
        description="selected folder"
        # subtype='DIR_PATH' is not needed to specify the selection mode.
    ) # type: ignore

    # Filters folders
    filter_folder: bpy.props.BoolProperty(
        default=True,
        options={"HIDDEN"}
    ) # type: ignore
    
    target_property: bpy.props.StringProperty(
        name="target_property",
        options={'HIDDEN'} 
    ) # type: ignore
    
    def execute(self, context): 
        """Do something with the selected file(s)."""
        settings: SPARROW_PG_Settings  = bpy.context.window_manager.sparrow_settings  
        setattr(settings, self.target_property, self.directory)
        return {'FINISHED'}

class SPARROW_OT_OpenRegistryFileBrowser(Operator, ImportHelper):
    """Browse for registry json file"""
    bl_idname = "sparrow.open_registryfilebrowser" 
    bl_label = "Open the file browser" 

    filter_glob: StringProperty( 
        default='*.json', 
        options={'HIDDEN'} 
    ) # type: ignore
    
    def execute(self, context): 
        """Do something with the selected file(s)."""
        settings: SPARROW_PG_Settings  = bpy.context.window_manager.sparrow_settings  
        settings.registry_file = self.filepath
        settings.load_registry()
        return {'FINISHED'}


# adds a component to an item (including metadata) using the provided component definition & optional value


class SPARROW_OT_AddComponent(Operator):
    """Add Bevy component"""
    bl_idname = "sparrow.add_component"
    bl_label = "Add component to object/collection"
    bl_options = {"UNDO"}

    component_type: StringProperty(
        name="component_type",
        description="component type to add",
    ) # type: ignore

    component_value: StringProperty(
        name="component_value",
        description="value of the newly added component"
    ) # type: ignore

    target_item_name: StringProperty(
        name="target item name",
        description="name of the object/collection/mesh/material to add the component to",
    ) # type: ignore

    target_item_type: EnumProperty(
        name="target item type",
        description="type of the object/collection/mesh/material to add the component to",
        items=ITEM_TYPES,
        default="OBJECT"
    ) # type: ignore

    def execute(self, context):
        registry: ComponentsRegistry = context.window_manager.components_registry


        if self.target_item_name == "" or self.target_item_type == "":
            target_item = get_selected_item(context)
            print(f"adding  component {self.component_type}, to target {self.target_item_type} - {target_item.name}")
        else:
            target_item = get_item_by_type(self.target_item_type, self.target_item_name)
            print("adding component ", self.component_type, "to target  '"+target_item.name+"'")

        has_component_type = self.component_type != ""
        if has_component_type and target_item is not None:
            type_infos = context.window_manager.components_registry.type_infos
            component_definition = type_infos[self.component_type]
            component_value = self.component_value if self.component_value != "" else None
            registry.add_component_to_item(target_item, component_definition, value=component_value)

        return {'FINISHED'}


class SPARROW_OT_PasteComponent(Operator):
    """Paste Bevy component to object"""
    bl_idname = "object.paste_bevy_component"
    bl_label = "Paste component to object Operator"
    bl_options = {"UNDO"}

    target_item_name: StringProperty(
        name="target item name",
        description="name of the object/collection/mesh/material to add the component to",
    ) # type: ignore

    target_item_type: EnumProperty(
        name="target item type",
        description="type of the object/collection/mesh/material to add the component to",
        items=ITEM_TYPES,
        default="OBJECT"
    ) # type: ignore

    def execute(self, context):
        settings: SPARROW_PG_Settings = bpy.context.window_manager.sparrow_settings
        registry: ComponentsRegistry = bpy.context.window_manager.components_registry

        source_item_name = settings.copied_source_item_name
        source_item_type = settings.copied_source_item_type
        source_item = get_item_by_type(source_item_type, source_item_name)
        
        if source_item is None:
            self.report({"ERROR"}, "The source object to copy a component from does not exist")
        else:
            component_name = settings.copied_source_component_name
            component_value = get_bevy_component_value_by_long_name(source_item, component_name)
            if component_value is None:
                self.report({"ERROR"}, "The source component to copy from does not exist")
            else:
                print("pasting component to item:", source_item, "component name:", str(component_name), "component value:" + str(component_value))
                registry = context.window_manager.components_registry
                target_item = get_selected_item(context)
                registry.copy_propertyGroup_values_to_another_item(source_item, target_item, component_name)

        return {'FINISHED'}

class SPARROW_OT_CopyComponent(Operator):
    """Copy Bevy component from object"""
    bl_idname = "object.copy_bevy_component"
    bl_label = "Copy component Operator"
    bl_options = {"UNDO"}

    source_component_name: StringProperty(
        name="source component_name (long)",
        description="name of the component to copy",
    ) # type: ignore

    source_item_name: StringProperty(
        name="source object name",
        description="name of the object to copy the component from",
    ) # type: ignore
    source_item_type: StringProperty(
        name="source object name",
        description="name of the object to copy the component from",
    ) # type: ignore


    def execute(self, context):
        settings: SPARROW_PG_Settings  = bpy.context.window_manager.sparrow_settings
        if self.source_component_name != '' and self.source_item_name != "":
            settings.copied_source_component_name = self.source_component_name
            settings.copied_source_item_name = self.source_item_name
            settings.copied_source_item_type = self.source_item_type
        else:
            self.report({"ERROR"}, "The source object name / component name to copy a component from have not been specified")

        return {'FINISHED'}

class SPARROW_OT_RemoveComponent(Operator):
    """Remove Bevy component from object"""
    bl_idname = "object.remove_bevy_component"
    bl_label = "Remove component from object Operator"
    bl_options = {"UNDO"}

    component_name: StringProperty(
        name="component name",
        description="component to delete",
    ) # type: ignore

    item_name: StringProperty(
        name="object name",
        description="object whose component to delete",
        default=""
    ) # type: ignore

    item_type : EnumProperty(
        name="item type",
        description="type of the item to select: object or collection",
        items=ITEM_TYPES,
        default="OBJECT"
    ) # type: ignore
    def execute(self, context):
        registry: ComponentsRegistry = context.window_manager.components_registry
        target = None
        if self.item_name == "":
            self.report({"ERROR"}, "The target to remove ("+ self.component_name +") from does not exist")
        else:
            target = get_item_by_type(self.item_type, self.item_name)

        print("removing component ", self.component_name, "from object  '"+target.name+"'")


        if target is not None:
            if 'bevy_components' in target:
                component_value = get_bevy_component_value_by_long_name(target, self.component_name)
                if component_value is not None:
                    registry.remove_component_from_item(target, self.component_name)
                else :
                    self.report({"ERROR"}, "The component to remove ("+ self.component_name +") does not exist")
            else:
                # for the classic "custom properties"
                if self.component_name in target:
                    del target[self.component_name]
                else:
                    self.report({"ERROR"}, "The component to remove ("+ self.component_name +") does not exist")

        else: 
            self.report({"ERROR"}, "The target to remove ("+ self.component_name +") from does not exist")
        return {'FINISHED'}

class SPARROW_OT_ToggleComponentVisibility(bpy.types.Operator):
    """Toggle Bevy component's visibility"""
    bl_idname = "object.toggle_bevy_component_visibility"
    bl_label = "Toggle component visibility"
    bl_options = {"UNDO"}

    component_name: StringProperty(
        name="component name",
        description="component to toggle",
    ) # type: ignore    
    item_name: StringProperty(
        name="source object name",
        description="name of the object to copy the component from",
    ) # type: ignore
    item_type: StringProperty(
        name="source object name",
        description="name of the object to copy the component from",
    ) # type: ignore


    def execute(self, context):
        registry: ComponentsRegistry = context.window_manager.components_registry
        item = get_item_by_type(self.item_type, self.item_name)
        if item is None:
            self.report({"ERROR"}, "The target to toggle ("+ self.component_name +") from does not exist")
            return {'CANCELLED'}

        components = next(filter(lambda component: component["long_name"] == self.component_name, item.components_meta.components), None)
        if components != None: 
            components.visible = not components.visible
        return {'FINISHED'}


class SPARROW_OT_components_refresh_custom_properties_all(Operator):
    """Apply registry to ALL objects: update the custom property values of all objects based on their definition, if any"""
    bl_idname = "object.refresh_custom_properties_all" # Update SPARROW_PG_Settings::load_registry if you change this
    bl_label = "Apply Registry to all objects"
    bl_options = {"UNDO"}

    @classmethod
    def register(cls):
        bpy.types.WindowManager.custom_properties_from_components_progress_all = bpy.props.FloatProperty(default=-1.0)

    @classmethod
    def unregister(cls):
        del bpy.types.WindowManager.custom_properties_from_components_progress_all

    def execute(self, context):

        registry: ComponentsRegistry = context.window_manager.components_registry

        total = len(bpy.data.objects)


        for index, object in enumerate(bpy.data.objects):
            registry.apply_propertyGroup_values_to_item_customProperties(object)

            progress = index / total
            #print(f"refreshing custom properties for {total}: {progress} {object.name}")

            context.window_manager.custom_properties_from_components_progress_all = progress
        
        # now force refresh the ui
        #bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        context.window_manager.custom_properties_from_components_progress_all = -1.0

        return {'FINISHED'}
    

class SPARROW_OT_component_map_actions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "sparrow.component_map_actions"
    bl_label = "Map Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options = {'REGISTER', 'UNDO'}

    action: EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", ""))) # type: ignore
    
    property_group_path: StringProperty(
        name="property group path",
        description="",
    ) # type: ignore

    component_name: StringProperty(
        name="component name",
        description="",
    ) # type: ignore

    target_index: IntProperty(name="target index", description="index of item to manipulate")# type: ignore

    item_type : EnumProperty(
        name="item type",
        description="type of the item to select: object or collection",
        items=(
            ('OBJECT', "Object", ""),
            ('COLLECTION', "Collection", ""),
            ('MESH', "Mesh", ""),
            ('MATERIAL', "Material", ""),
            ),
        default="OBJECT"
    ) # type: ignore

    item_name: StringProperty(
        name="object name",
        description="object whose component to delete",
        default=""
    ) # type: ignore

    def invoke(self, context, event):

        item = get_item_by_type(self.item_type, self.item_name)

        # information is stored in component meta
        components_in_item = item.components_meta.components
        component_meta =  next(filter(lambda component: component["long_name"] == self.component_name, components_in_item), None)

        propertyGroup = component_meta
        for path_item in json.loads(self.property_group_path):
            propertyGroup = getattr(propertyGroup, path_item)

        keys_list = getattr(propertyGroup, "list")
        index = getattr(propertyGroup, "list_index")

        values_list = getattr(propertyGroup, "values_list")
        values_index = getattr(propertyGroup, "values_list_index")

        key_setter = getattr(propertyGroup, "keys_setter")
        value_setter = getattr(propertyGroup, "values_setter")

        if self.action == 'DOWN' and index < len(keys_list) - 1:
            #item_next = scn.rule_list[index + 1].name
            keys_list.move(index, index + 1)
            propertyGroup.list_index += 1
        
        elif self.action == 'UP' and index >= 1:
            #item_prev = scn.rule_list[index - 1].name
            keys_list.move(index, index - 1)
            propertyGroup.list_index -= 1

        elif self.action == 'REMOVE':
            index = self.target_index
            keys_list.remove(index)
            values_list.remove(index)
            propertyGroup.list_index = min(max(0, index - 1), len(keys_list) - 1) 
            propertyGroup.values_index = min(max(0, index - 1), len(keys_list) - 1) 

        if self.action == 'ADD':            
            # first we gather all key/value pairs
            hashmap = {}
            for index, key in enumerate(keys_list):
                print("key", key)
                key_entry = {}
                for field_name in key.field_names:
                    key_entry[field_name] = getattr(key, field_name, None)
                """value_entry = {}
                for field_name in values_list[index].field_names:
                    value_entry[field_name] = values_list[index][field_name]"""
                hashmap[json.dumps(key_entry)] = index

            # then we need to find the index of a specific value if it exists
            key_entry = {}
            for field_name in key_setter.field_names:
                key_entry[field_name] = getattr(key_setter, field_name, None)
            key_to_add = json.dumps(key_entry)
            existing_index = hashmap.get(key_to_add, None)

            if existing_index is None:
                #print("adding new value", "key field names", key_setter.field_names, "value_setter", value_setter, "field names", value_setter.field_names)
                key = keys_list.add()
                # copy the values over 
                for field_name in key_setter.field_names:
                    val = getattr(key_setter, field_name, None)
                    if val is not None:
                        key[field_name] = val
                    # TODO: add error handling

                value = values_list.add()
                # copy the values over 
                is_enum = getattr(value_setter, "with_enum", False)
                if not is_enum:
                    for field_name in list(value_setter.field_names):
                        val = getattr(value_setter, field_name, None)
                        if val is not None:
                            value[field_name] = val
                else:
                    selection = getattr(value_setter, "selection", None)
                    setattr(value, 'selection', selection)
                    selector = "variant_" + selection
                    try:
                        val = getattr(value_setter, selector, None)
                        for field_name in val.field_names:
                            source = getattr(val, field_name)
                            setattr(getattr(value, selector), field_name, source)
                    except Exception as inst:
                        print("EROOR", inst)
                       
                    # TODO: add error handling
                propertyGroup.list_index = index + 1 # we use this to force the change detection
                propertyGroup.values_index = index + 1 # we use this to force the change detection
            else:
                for field_name in value_setter.field_names:
                    values_list[existing_index][field_name] = value_setter[field_name]


            #info = '"%s" added to list' % (item.name)
            #self.report({'INFO'}, info)

        return {"FINISHED"}

class SPARROW_OT_component_list_actions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "sparrow.component_list_actions"
    bl_label = "List Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options = {'REGISTER', 'UNDO'}

    action: EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", ""),
            ('SELECT', "Select", "")
        )
    ) # type: ignore
    
    property_group_path: StringProperty(
        name="property group path",
        description="",
    ) # type: ignore

    component_name: StringProperty(
        name="component name",
        description="",
    ) # type: ignore

    item_name: StringProperty(
        name="item name",
        description="item object/collections we are working on",
        default=""
    ) # type: ignore

    item_type : EnumProperty(
        name="item type",
        description="type of the item we are working on : object or collection",
        items=(
            ('OBJECT', "Object", ""),
            ('COLLECTION', "Collection", ""),
            ('MESH', "Mesh", ""),
            ('MATERIAL', "Material", ""),
            ),
        default="OBJECT"
    ) # type: ignore


    selection_index: IntProperty() # type: ignore

    def invoke(self, context, event):
        item = get_item_by_type(self.item_type, self.item_name)

        # information is stored in component meta
        components_in_item = item.components_meta.components
        component_meta =  next(filter(lambda component: component["long_name"] == self.component_name, components_in_item), None)

        propertyGroup = component_meta
        for path_item in json.loads(self.property_group_path):
            propertyGroup = getattr(propertyGroup, path_item)

        target_list = getattr(propertyGroup, "list")
        index = getattr(propertyGroup, "list_index")


        if self.action == 'DOWN' and index < len(target_list) - 1:
            #item_next = scn.rule_list[index + 1].name
            target_list.move(index, index + 1)
            propertyGroup.list_index += 1
        
        elif self.action == 'UP' and index >= 1:
            #item_prev = scn.rule_list[index - 1].name
            target_list.move(index, index - 1)
            propertyGroup.list_index -= 1

        elif self.action == 'REMOVE':
            target_list.remove(index)
            propertyGroup.list_index = min(max(0, index - 1), len(target_list) - 1) 

        if self.action == 'ADD':
            item = target_list.add()
            propertyGroup.list_index = index + 1 # we use this to force the change detection
            #info = '"%s" added to list' % (item.name)
            #self.report({'INFO'}, info)

        if self.action == 'SELECT':
            propertyGroup.list_index = self.selection_index


        return {"FINISHED"}

# class Generic_LIST_OT_AddItem(Operator): 
#     """Add a new item to the list.""" 
#     bl_idname = "generic_list.add_item" 
#     bl_label = "Add a new item" 

#     property_group_path: StringProperty(
#         name="property group path",
#         description="",
#     ) # type: ignore

#     component_name: StringProperty(
#         name="component name",
#         description="",
#     ) # type: ignore

#     def execute(self, context): 
#         print("")
#         object = context.object
#         # information is stored in component meta
#         components_in_object = object.components_meta.components
#         component_meta =  next(filter(lambda component: component["long_name"] == self.component_name, components_in_object), None)

#         propertyGroup = component_meta
#         for path_item in json.loads(self.property_group_path):
#             propertyGroup = getattr(propertyGroup, path_item)

#         print("list container", propertyGroup, dict(propertyGroup))
#         target_list = getattr(propertyGroup, "list")
#         index = getattr(propertyGroup, "list_index")
#         item = target_list.add()
#         propertyGroup.list_index = index + 1 # we use this to force the change detection

#         print("added item", item, item.field_names, getattr(item, "field_names"))
#         print("")
#         return{'FINISHED'}
    

# class Generic_LIST_OT_RemoveItem(Operator): 
#     """Remove an item to the list.""" 
#     bl_idname = "generic_list.remove_item" 
#     bl_label = "Remove selected item" 

#     property_group_path: StringProperty(
#         name="property group path",
#         description="",
#     ) # type: ignore

#     component_name: StringProperty(
#         name="component name",
#         description="",
#     ) # type: ignore
#     def execute(self, context): 
#         print("remove from list", context.object)

#         object = context.object
#         # information is stored in component meta
#         components_in_object = object.components_meta.components
#         component_meta =  next(filter(lambda component: component["long_name"] == self.component_name, components_in_object), None)

#         propertyGroup = component_meta
#         for path_item in json.loads(self.property_group_path):
#             propertyGroup = getattr(propertyGroup, path_item)

#         target_list = getattr(propertyGroup, "list")
#         index = getattr(propertyGroup, "list_index")
#         target_list.remove(index)
#         propertyGroup.list_index = min(max(0, index - 1), len(target_list) - 1) 
#         return{'FINISHED'}


# class Generic_LIST_OT_SelectItem(Operator): 
#     """Remove an item to the list.""" 
#     bl_idname = "generic_list.select_item" 
#     bl_label = "select an item" 


#     property_group_path: StringProperty(
#         name="property group path",
#         description="",
#     ) # type: ignore

#     component_name: StringProperty(
#         name="component name",
#         description="",
#     ) # type: ignore

#     selection_index: IntProperty() # type: ignore

#     def execute(self, context): 
#         print("select in list", context.object)

#         object = context.object
#         # information is stored in component meta
#         components_in_object = object.components_meta.components
#         component_meta =  next(filter(lambda component: component["long_name"] == self.component_name, components_in_object), None)

#         propertyGroup = component_meta
#         for path_item in json.loads(self.property_group_path):
#             propertyGroup = getattr(propertyGroup, path_item)

#         target_list = getattr(propertyGroup, "list")
#         index = getattr(propertyGroup, "list_index")

#         propertyGroup.list_index = self.selection_index
#         return{'FINISHED'}



# class GENERIC_LIST_OT_actions(Operator):
#     """Move items up and down, add and remove"""
#     bl_idname = "generic_list.list_action"
#     bl_label = "List Actions"
#     bl_description = "Move items up and down, add and remove"
#     bl_options = {'REGISTER', 'UNDO'}

#     action: EnumProperty(
#         items=(
#             ('UP', "Up", ""),
#             ('DOWN', "Down", ""),
#             ('REMOVE', "Remove", ""),
#             ('ADD', "Add", ""))) # type: ignore
    
#     property_group_path: StringProperty(
#         name="property group path",
#         description="",
#     ) # type: ignore

#     component_name: StringProperty(
#         name="component name",
#         description="",
#     ) # type: ignore

#     def invoke(self, context, event):
#         object = context.object
#         # information is stored in component meta
#         components_in_object = object.components_meta.components
#         component_meta =  next(filter(lambda component: component["long_name"] == self.component_name, components_in_object), None)

#         propertyGroup = component_meta
#         for path_item in json.loads(self.property_group_path):
#             propertyGroup = getattr(propertyGroup, path_item)

#         target_list = getattr(propertyGroup, "list")
#         index = getattr(propertyGroup, "list_index")


#         if self.action == 'DOWN' and index < len(target_list) - 1:
#             #item_next = scn.rule_list[index + 1].name
#             target_list.move(index, index + 1)
#             propertyGroup.list_index += 1
        
#         elif self.action == 'UP' and index >= 1:
#             #item_prev = scn.rule_list[index - 1].name
#             target_list.move(index, index - 1)
#             propertyGroup.list_index -= 1

#         elif self.action == 'REMOVE':
#             target_list.remove(index)
#             propertyGroup.list_index = min(max(0, index - 1), len(target_list) - 1) 

#         if self.action == 'ADD':
#             item = target_list.add()
#             propertyGroup.list_index = index + 1 # we use this to force the change detection
#             #info = '"%s" added to list' % (item.name)
#             #self.report({'INFO'}, info)

#         return {"FINISHED"}




#------------------------------------------------------------------------------------
#   Below here is from AutoBake

class SPARROW_OT_LoadLinked(Operator):
    bl_idname = "sparrow.bakelist_load_linked"
    bl_label = "Load by Linked"
    bl_description = "Add new items to the list based on the connected shader sockets"
    bl_options = {'INTERNAL', 'UNDO'}

    reset_source : BoolProperty(options = set(), default=True, description='Remove the selected source (material or object), and auto set a new one the next time')
    texture_size : IntProperty(options = set(), default=512, min=1, max=65536, name='Texture Scale', description='The texture scale for the new items')
    type_size : FloatProperty(options = set(), default=1, min=0.1, max=10.0, precision=2, step=1, name='Type Scale', description='The tile-scale multiplier')
    place_item : EnumProperty(options = set(), default="After", name="", description="Select how to place the new items in the list", items=[
                    ("Before", "Before", "New items will be placed before the currently selected item"),
                    ("After", "After", "New items will be placed after the currently selected item"),
                    ("First", "First", "New items will be placed at the top of the list"),
                    ("Last", "Last", "New items will be placed at the bottom of the list")])
    
    def invoke(self, context, event):
        scene = context.scene
        abp = scene.autobake_properties
        
        if self.reset_source:
            abp.ab_load_linked_material = None
            if context.active_object:
                for slot in context.active_object.material_slots:
                    if slot.material is not None and slot.material.use_nodes:
                        abp.ab_load_linked_material = slot.material
                        break
            abp.ab_load_linked_object = None
            if context.active_object:
                abp.ab_load_linked_object = context.active_object
                    
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        box = layout.box()
        col = box.column_flow(columns=1, align=True)
        
        split = col.split(factor=.4)
        split.label(text='Source Method')
        
        col2 = split.column()
        col2.row().prop(abp, 'ab_load_method', text=' ', expand=True)
        
        if abp.ab_load_method == 'Material':
            col2.prop(abp, 'ab_load_linked_material', text='')
        else:
            col2.prop(abp, 'ab_load_linked_object', text='')
        
        col2.prop(self, 'reset_source', text='Reset')
        
        split = col.split(factor=.4)
        if abp.ab_udim_bake:
            split.label(text='Type Scale')
            split.prop(self, 'type_size', text='')
        else:
            split.label(text='Texture Scale')
            split.prop(self, 'texture_size', text='')
            
        split = col.split(factor=.4)
        split.label(text="Placement")
        split.prop(self, "place_item")

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties

    # Collecting Default Node Trees
        node_trees = []
        
        if abp.ab_load_method == 'Material':
            if abp.ab_load_linked_material is None:
                self.report({'ERROR'}, "Auto Bake: Must select a source material!")
                return {'FINISHED'}
            else:
                if abp.ab_load_linked_material.use_nodes:
                    if abp.ab_load_linked_material.node_tree not in node_trees:
                        node_trees.append(abp.ab_load_linked_material.node_tree)
        
        elif abp.ab_load_method == 'Object':
            if abp.ab_load_linked_object is None:
                self.report({'ERROR'}, "Auto Bake: Must select a source object!")
                return {'FINISHED'}
            else:
                for slot in abp.ab_load_linked_object.material_slots:
                    if slot.material.use_nodes:
                        
                        if slot.material.node_tree not in node_trees:
                            node_trees.append(slot.material.node_tree)
                    
    # Branching
        shaders = []
        
        for tree in node_trees:
            branches = []
            for node in tree.nodes:
                
            # Looking for: Branch Start
                if node.type in ['OUTPUT_MATERIAL', 'GROUP_OUTPUT'] and node.is_active_output:
                    if node.inputs[0].is_linked:
                        if node.inputs[0].links[0].from_node.type in ['BSDF_PRINCIPLED', 'EMISSION', 'BSDF_TRANSLUCENT', 'BSDF_TRANSPARENT', 'BSDF_REFRACTION', 'BSDF_DIFFUSE', 'BSDF_GLASS', 'BSDF_SHEEN', 'BSDF_HAIR', 'BSDF_TOON', 'BSDF_GLOSSY', 'VOLUME_ABSORPTION', 'VOLUME_SCATTER', 'SUBSURFACE_SCATTERING', 'PRINCIPLED_VOLUME', 'BSDF_HAIR_PRINCIPLED', 'BSDF_VELVET', 'BSDF_ANISOTROPIC', 'EEVEE_SPECULAR']:
                            shaders.append(node.inputs[0].links[0].from_node)
                            
                        elif node.inputs[0].links[0].from_node.type == 'GROUP':
                            if node.inputs[0].links[0].from_node.node_tree not in node_trees:
                                node_trees.append(node.inputs[0].links[0].from_node.node_tree)
                            
                            if node.inputs[0].links[0].from_node not in branches:
                                branches.append(node.inputs[0].links[0].from_node)
                        else:
                            if node.inputs[0].links[0].from_node not in branches:
                                branches.append(node.inputs[0].links[0].from_node)
                    break
                
            # Looking for: New Branches & New Trees & Shader nodes
            for node in branches:
                for input in node.inputs:
                    if input.is_linked:
                        if input.links[0].from_node.type in ['BSDF_PRINCIPLED', 'EMISSION', 'BSDF_TRANSLUCENT', 'BSDF_TRANSPARENT', 'BSDF_REFRACTION', 'BSDF_DIFFUSE', 'BSDF_GLASS', 'BSDF_SHEEN', 'BSDF_HAIR', 'BSDF_TOON', 'BSDF_GLOSSY', 'VOLUME_ABSORPTION', 'VOLUME_SCATTER', 'SUBSURFACE_SCATTERING', 'PRINCIPLED_VOLUME', 'BSDF_HAIR_PRINCIPLED', 'BSDF_VELVET', 'BSDF_ANISOTROPIC', 'EEVEE_SPECULAR']:
                            shaders.append(input.links[0].from_node)
                            
                        elif input.links[0].from_node.type == 'GROUP':
                            if input.links[0].from_node.node_tree not in node_trees:
                                node_trees.append(input.links[0].from_node.node_tree)
                            if input.links[0].from_node not in branches:
                                branches.append(input.links[0].from_node)
                        else:
                            if input.links[0].from_node not in branches:
                                branches.append(input.links[0].from_node)
                           
   # Saved as Linked
        linked_sockets = []

        for shader in shaders:
            for input in shader.inputs:
                if input.is_linked:
                    input_aliases = [input.name,]
                    
                    socket_name = [key for key, aliases in type_aliases.items() if input.name in aliases]
                    
                    if socket_name != []:
                        for key in socket_name:
                            input_aliases.extend(type_aliases[key])
                            input_aliases.append(key)

                    for type in bake_items:
                        if type[0] in input_aliases and type[0] not in linked_sockets:
                            linked_sockets.append(type[0])
                    
        list = scene.autobake_udimlist if abp.ab_udim_bake else scene.autobake_bakelist
        item = None
        
        for socket in linked_sockets:
            item = list.add()
            item.Type = socket
            item.Size = self.type_size if abp.ab_udim_bake else self.texture_size
        
            if self.place_item == 'First':
                list.move(len(list)-1, 0)
                
            elif self.place_item == 'Before':
                if abp.ab_udim_bake:
                    list.move(len(list)-1, scene.autobake_udimlist_index)
                else:
                    list.move(len(list)-1, scene.autobake_bakelist_index)
                
            elif self.place_item == 'After':
                if abp.ab_udim_bake:
                    list.move(len(list)-1, scene.autobake_udimlist_index+1)
                else:
                    list.move(len(list)-1, scene.autobake_bakelist_index+1)
                
    # List Index
        if self.place_item == 'First':
            if abp.ab_udim_bake:
                scene.autobake_udimlist_index = min(len(linked_sockets)-1, len(list)-1)
            else:
                scene.autobake_bakelist_index = min(len(linked_sockets)-1, len(list)-1)

        elif self.place_item == 'Last':
            if abp.ab_udim_bake:
                scene.autobake_udimlist_index = len(list)-1
            else:
                scene.autobake_bakelist_index = len(list)-1
            
        elif self.place_item == 'Before':
            if abp.ab_udim_bake:
                scene.autobake_udimlist_index = max(scene.autobake_udimlist_index - 1 + len(linked_sockets), 0)
            else:
                scene.autobake_bakelist_index = max(scene.autobake_bakelist_index - 1 + len(linked_sockets), 0)
            
        elif self.place_item == 'After':
            if abp.ab_udim_bake:
                scene.autobake_udimlist_index = min(scene.autobake_udimlist_index + len(linked_sockets), len(list)-1)
            else:
                scene.autobake_bakelist_index = min(scene.autobake_bakelist_index + len(linked_sockets), len(list)-1)

    # List Count & Dupe Update
        if item is not None:
            item.Gate = False
            item.Gate = True                 
   
        return {'FINISHED'}


class SPARROW_OT_Add(Operator):
    bl_idname = "sparrow.bakelist_add"
    bl_label = "Add New"
    bl_description = "Add a new item to the list. Use 'CTRL + Click' to add more items"
    bl_options = {'INTERNAL', 'UNDO'}
        
    iteration : IntProperty(options = set(), name='', default=1, min=1, max=10, description='Choose how many items add to the list')
    scale_method : EnumProperty(options = set(), default='Multiply', name='Scale Method', description='Choose how the new items scale should change', items=[
        ('Copy', 'Copy', 'All the new items will share the same value'),
        ('Multiply', 'Multiply', "Each item's size will be multiplied"),
        ('Divide', 'Divide', "Each item's size will be divided")])
    multiply_value : FloatProperty(options = set(), name='Multiply Value', default=2, precision=2, step=1, min=1, max=10)
    divide_value : FloatProperty(options = set(), name='Divide Value', default=2, precision=2, step=1, min=1, max=10)
    use_ctrl : BoolProperty(options = set(), default=False)

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        abp = context.scene.autobake_properties

        if (abp.ab_new_item_method == 'Advanced' and not self.use_ctrl) or (abp.ab_new_item_method == 'Simple' and self.use_ctrl):
            
            return context.window_manager.invoke_props_dialog(self, width=185)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout   
        
        box = layout.box()
        col = box.column_flow(columns=1)
        
        row = col.row(align=True)
        row.label(text='New Items')
        row.prop(self, "iteration", text="")
        
        row = col.row(align=True)
        row.label(text='Scale')
        
        col = row.column(align=True)
        col.prop(self, "scale_method", text="")
        
        if self.scale_method == 'Multiply':
            col.prop(self, "multiply_value", text="")
        if self.scale_method == 'Divide':
            col.prop(self, "divide_value", text="")

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        list = scene.autobake_udimlist if abp.ab_udim_bake else scene.autobake_bakelist
        
    # Add Multiple
        if (abp.ab_new_item_method == 'Advanced' and not self.use_ctrl) or (abp.ab_new_item_method == 'Simple' and self.use_ctrl):
            self.use_ctrl = False
            
            for iteration in range(self.iteration):
                index = scene.autobake_udimlist_index if abp.ab_udim_bake else scene.autobake_bakelist_index
                
                item = list.add()

                if len(list) == 1:
                    if abp.ab_udim_bake:
                        scene.autobake_udimlist_index = 0
                    else:
                        scene.autobake_bakelist_index = 0
                else:
                    item.Type = list[index].Type
                    item.Size = list[index].Size

                    list.move(len(list)-1, index + 1)
                    
                    if abp.ab_udim_bake:
                        scene.autobake_udimlist_index = index + 1
                        abp.ab_udimtype_list_item_count = sum(1 for item in list if item.Gate)
                    else:
                        scene.autobake_bakelist_index = index + 1
                        abp.ab_bake_list_item_count = sum(1 for item in list if item.Gate)
                        
                    if self.scale_method == 'Multiply':
                        item.Size = int(list[index].Size * self.multiply_value)
                    elif self.scale_method == 'Divide':
                        item.Size = int(list[index].Size / self.divide_value)
    # Add One
        else:         
            index = scene.autobake_udimlist_index if abp.ab_udim_bake else scene.autobake_bakelist_index   
            item = list.add()

            if len(list) == 1:
                if abp.ab_udim_bake:
                    scene.autobake_udimlist_index = 0
                else:
                    scene.autobake_bakelist_index = 0
            else:
                item.Type = list[index].Type
                item.Size = list[index].Size

                list.move(len(list)-1, index + 1)
                
                if not abp.ab_udim_bake:
                    if scene.autobake_properties.ab_dynamic_scale != 'FALSE':
                        if len(list) > 2 and index > 0 and (list[index].Type == list[index-1].Type) and (list[index-1].Size*2 == list[index].Size):
                            item.Size = item.Size*2
                        elif len(list) > 2 and index > 0 and (list[index].Type == list[index-1].Type) and (list[index].Size*2 == list[index-1].Size):
                            item.Size = int(item.Size/2)
                            
                        if scene.autobake_properties.ab_dynamic_scale == 'ENABLED+':
                            if len(list) > 3 and index > 1 and (list[index].Size == list[index-1].Size) and (list[index-1].Size == list[index-2].Size*2) and (list[index].Type != list[index-1].Type) and (list[index-1].Type == list[index-2].Type):
                                item.Size = int(item.Size/2)
                                
                            elif len(list) > 3 and index > 1 and (list[index].Size == list[index-1].Size) and (list[index-1].Size == list[index-2].Size/2) and (list[index].Type != list[index-1].Type) and (list[index-1].Type == list[index-2].Type):
                                item.Size = item.Size*2
                
    # Item Count
        if abp.ab_udim_bake:
            scene.autobake_udimlist_index = min(index + 1, len(list)-1)
            abp.ab_udimtype_list_item_count = sum(1 for item in list if item.Gate)
        else:
            scene.autobake_bakelist_index = min(index + 1, len(list)-1)
            abp.ab_bake_list_item_count = sum(1 for item in list if item.Gate)
                                
    # Duplicate
        for item in list:
            item.IsDuplicate = sum(1 for item2 in list if (item.Type == item2.Type and item.Size == item2.Size)) > 1
            
        index = scene.autobake_udimlist_index if abp.ab_udim_bake else scene.autobake_bakelist_index
        if index > 0 and list[index].IsDuplicate and list[index].Type == list[index-1].Type and list[index].Size == list[index-1].Size and sum(1 for item in list if (item.Type == list[index].Type and item.Size == list[index].Size))<3:
            list[index].IsDuplicate = False
            list[index-1].IsDuplicate = False

    # Name
        for item in list:
            if abp.ab_udim_bake:
                item.name = f"{item.Type} {item.Size:.2f}" + (' Enabled' if item.Gate else ' Disabled') + (' Duplicated' if item.IsDuplicate else '')
            else:
                item.name = f"{item.Type} {item.Size}" + (' Enabled' if item.Gate else ' Disabled') + (' Duplicate' if item.IsDuplicate else '')
                
        return {'FINISHED'}


class SPARROW_OT_Remove(Operator):
    bl_idname = "sparrow.bakelist_remove"
    bl_label = "Remove Item"
    bl_description = "Remove the selected item from the list. Use 'CTRL + Click' to remove more items"
    bl_options = {'INTERNAL', 'UNDO'}

    use_ctrl : BoolProperty(options = set(), default=False)
    remove_method : EnumProperty(options = set(), name='Remove Method', default='All', description='Choose what items to remove from the list', items=[
        ("All", "All", "All items will be removed from the list"),
        ("Duplicated", "Duplicated", "Remove all the duplicated items from the list"),
        ("Disabled", "Disabled", "Remove all the disabled items from the list")])

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        
        if self.use_ctrl:
            return context.window_manager.invoke_props_dialog(self, width=175)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout   
        box = layout.box()
        split = box.split(factor=.4)
        
        split.label(text='Remove:')
        split.prop(self, 'remove_method', text='')
        
    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if self.use_ctrl:
            if self.remove_method == 'All':
                bpy.ops.autobake.remove_all()
            elif self.remove_method == 'Disabled':
                bpy.ops.autobake.remove_disabled()
            elif self.remove_method == 'Duplicated':
                bpy.ops.autobake.remove_duplicates()
            
        else:
            list = scene.autobake_udimlist if abp.ab_udim_bake else scene.autobake_bakelist
            index = scene.autobake_udimlist_index if abp.ab_udim_bake else scene.autobake_bakelist_index
            list.remove(index)

            if abp.ab_udim_bake:
                scene.autobake_udimlist_index = max(scene.autobake_udimlist_index - 1, 0)
                abp.ab_udimtype_list_item_count = sum(1 for item in list if item.Gate)
            else:
                scene.autobake_bakelist_index = max(scene.autobake_bakelist_index - 1, 0)
                abp.ab_bake_list_item_count = sum(1 for item in list if item.Gate)
                
            for item in list:
                item.IsDuplicate = sum(1 for item2 in list if (item.Type == item2.Type and item.Size == item2.Size)) > 1

                if abp.ab_udim_bake:
                    item.name = f"{item.Type} {item.Size:.2f}" + (' Enabled' if item.Gate else ' Disabled') + (' Duplicated' if item.IsDuplicate else '')
                else:
                    item.name = f"{item.Type} {item.Size}" + (' Enabled' if item.Gate else ' Disabled') + (' Duplicate' if item.IsDuplicate else '')
        return {'FINISHED'}

    
class SPARROW_OT_Up(Operator):
    bl_idname = "sparrow.bakelist_move_up"
    bl_label = "Move Up"
    bl_description = "Move item up in the list. Use 'CTRL + Click' to move it to the top"
    bl_options = {'INTERNAL', 'UNDO'}

    use_ctrl : BoolProperty(options = set(), default=False)

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        list = scene.autobake_udimlist if abp.ab_udim_bake else scene.autobake_bakelist
        index = scene.autobake_udimlist_index if abp.ab_udim_bake else scene.autobake_bakelist_index

        if self.use_ctrl:
            bpy.ops.autobake.move_to_top()
        else:
            if index > 0:
                list.move(index, index - 1)
                if abp.ab_udim_bake:
                    scene.autobake_udimlist_index -= 1
                else:
                    scene.autobake_bakelist_index -= 1
        return {'FINISHED'}


class SPARROW_OT_Down(Operator):
    bl_idname = "sparrow.bakelist_move_down"
    bl_label = "Move Down"
    bl_description = "Move item down in the list. Use 'CTRL + Click' to move it to the bottom"
    bl_options = {'INTERNAL', 'UNDO'}

    use_ctrl : BoolProperty(options = set(), default=False)

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        list = scene.autobake_udimlist if abp.ab_udim_bake else scene.autobake_bakelist
        index = scene.autobake_udimlist_index if abp.ab_udim_bake else scene.autobake_bakelist_index
        
        if self.use_ctrl:
            bpy.ops.autobake.move_to_bottom()
        else:
            if index < len(list) - 1:
                list.move(index, index + 1)
                if abp.ab_udim_bake:
                    scene.autobake_udimlist_index += 1
                else:
                    scene.autobake_bakelist_index += 1
        return {'FINISHED'}


class SPARROW_OT_MoveTop(Operator):
    bl_idname = "sparrow.move_to_top"
    bl_label = "Move To Top"
    bl_description = "Move the active item to the top of the list. Call this function with 'CTRL + Click' on the 'Move Up' button"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            scene.autobake_bakelist.move(scene.autobake_bakelist_index, 0)
            scene.autobake_bakelist_index = 0
        else:
            scene.autobake_udimlist.move(scene.autobake_udimlist_index, 0)
            scene.autobake_udimlist_index = 0
        return {'FINISHED'} 
    
    
class SPARROW_OT_MoveBottom(Operator):
    bl_idname = "sparrow.move_to_bottom"
    bl_label = "Move To Top"
    bl_description = "Move the active item to the top of the list. Call this function with 'CTRL + Click' on the 'Move Down' button"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            scene.autobake_bakelist.move(scene.autobake_bakelist_index, len(scene.autobake_bakelist)-1)
            scene.autobake_bakelist_index = len(scene.autobake_bakelist)-1
        else:
            scene.autobake_udimlist.move(scene.autobake_udimlist_index, len(scene.autobake_udimlist)-1)
            scene.autobake_udimlist_index = len(scene.autobake_udimlist)-1
        return {'FINISHED'}
    
    
class SPARROW_OT_RemoveDuplicates(Operator):
    bl_idname = "sparrow.remove_duplicates"
    bl_label = "Remove Duplicated"
    bl_description = "Remove all the duplicated items from the list. Call this function with 'CTRL + Click' on the 'Remove Item' button"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            for index in range(len(scene.autobake_bakelist)-1, -1, -1):
                if scene.autobake_bakelist[index].IsDuplicate:
                    scene.autobake_bakelist.remove(index)
                    if scene.autobake_bakelist_index > len(scene.autobake_bakelist)-1:
                        scene.autobake_bakelist_index = len(scene.autobake_bakelist)-1
                    for item in scene.autobake_bakelist:
                        item.IsDuplicate = sum(1 for Item in context.scene.autobake_bakelist if Item.Type == item.Type and Item.Size == item.Size) > 1
            scene.autobake_properties.ab_bake_list_item_count = sum(1 for item in scene.autobake_bakelist if item.Gate)
        else:
            for index in range(len(scene.autobake_udimlist)-1, -1, -1):
                if scene.autobake_udimlist[index].IsDuplicate:
                    scene.autobake_udimlist.remove(index)
                    if scene.autobake_udimlist_index > len(scene.autobake_udimlist)-1:
                        scene.autobake_udimlist_index = len(scene.autobake_udimlist)-1
                    for item in scene.autobake_udimlist:
                        item.IsDuplicate = sum(1 for Item in scene.autobake_udimlist if (item.Type == Item.Type and item.Size == Item.Size)) > 1
            abp.ab_bake_list_item_count = sum(1 for item in scene.autobake_udimlist if item.Gate)
        return {'FINISHED'}


class SPARROW_OT_RemoveDisabled(Operator):
    bl_idname = "sparrow.remove_disabled"
    bl_label = "Remove Disabled"
    bl_description = "Remove all the disabled items from the list. Call this function with 'CTRL + Click' on the 'Remove Item' button"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            for index in range(len(scene.autobake_bakelist)-1, -1, -1):
                if scene.autobake_bakelist[index].Gate == False:
                    scene.autobake_bakelist.remove(index)
            if scene.autobake_bakelist_index > len(scene.autobake_bakelist)-1:
                scene.autobake_bakelist_index = len(scene.autobake_bakelist)-1
            for item in scene.autobake_bakelist:
                item.IsDuplicate = sum(1 for Item in context.scene.autobake_bakelist if Item.Type == item.Type and Item.Size == item.Size) > 1
        else:
            for index in range(len(scene.autobake_udimlist)-1, -1, -1):
                if scene.autobake_udimlist[index].Gate == False:
                    scene.autobake_udimlist.remove(index)
            if scene.autobake_udimlist_index > len(scene.autobake_udimlist)-1:
                scene.autobake_udimlist_index = len(scene.autobake_udimlist)-1
            for item in scene.autobake_udimlist:
                item.IsDuplicate = sum(1 for Item in scene.autobake_udimlist if (item.Type == Item.Type and item.Size == Item.Size)) > 1
        return {'FINISHED'}
        
        
class SPARROW_OT_RemoveAll(Operator):
    bl_idname = "sparrow.remove_all"
    bl_label = "Remove All"
    bl_description = "Remove all the items from the list. Call this function with 'CTRL + Click' on the 'Remove Item' button"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            scene.autobake_bakelist.clear()
            abp.ab_bake_list_item_count = 0
        else:
            scene.autobake_udimlist.clear()
            abp.ab_bake_list_item_count = 0
        return {'FINISHED'}
    
    
class SPARROW_OT_EnableAll(Operator):
    bl_idname = "sparrow.enable_all"
    bl_label = "Enable All"
    bl_description = "Enable all the items in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            for item in scene.autobake_bakelist:
                item.Gate = True
        else:
            for item in scene.autobake_udimlist:
                item.Gate = True
        return {'FINISHED'}
    
    
class SPARROW_OT_DisableAll(Operator):
    bl_idname = "sparrow.disable_all"
    bl_label = "Enable All"
    bl_description = "Disable all the items in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            for item in scene.autobake_bakelist:
                item.Gate = False
        else:
            for item in scene.autobake_udimlist:
                item.Gate = False
        return {'FINISHED'}
    
    
class SPARROW_OT_InvertAll(Operator):
    bl_idname = "sparrow.invert_all"
    bl_label = "Invert All"
    bl_description = "Invert all the items in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            for item in scene.autobake_bakelist:
                item.Gate = not bool(item.Gate)
        else:
            for item in scene.autobake_udimlist:
                item.Gate = not bool(item.Gate)
        return {'FINISHED'}
    
    
class SPARROW_OT_Sort(Operator):
    bl_idname = "sparrow.reorder"
    bl_label = "Sort Items"
    bl_description = "Reorder all the items by type and scale"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if not abp.ab_udim_bake:
            autobake_bakelist = scene.autobake_bakelist
            types = []
            active_item = ((autobake_bakelist[scene.autobake_bakelist_index].Type, autobake_bakelist[scene.autobake_bakelist_index].Size, autobake_bakelist[scene.autobake_bakelist_index].Gate, autobake_bakelist[scene.autobake_bakelist_index].IsDuplicate))
            
            for index in range(len(autobake_bakelist)):
                item = autobake_bakelist[index]
                
                if item.Type not in types:
                    types.append(item.Type)
                elif item.Type in types:
                    adjust_index = 0
                    if autobake_bakelist[index].Type != autobake_bakelist[index-1].Type:
                        while autobake_bakelist[index-adjust_index].Type != autobake_bakelist[index-adjust_index-1].Type:
                            autobake_bakelist.move(index-adjust_index, index-adjust_index-1)
                            adjust_index = adjust_index+1
                            
            for index in range(len(autobake_bakelist)):
                item = autobake_bakelist[index]
                adjust_index = 0
                
                if autobake_bakelist[index].Type == autobake_bakelist[index-1].Type and autobake_bakelist[index].Size < autobake_bakelist[index-1].Size:
                    while autobake_bakelist[index-adjust_index].Type == autobake_bakelist[index-adjust_index-1].Type and autobake_bakelist[index-adjust_index].Size < autobake_bakelist[index-adjust_index-1].Size:
                        autobake_bakelist.move(index-adjust_index, index-adjust_index-1)
                        adjust_index = adjust_index+1
            
            for index in range(len(autobake_bakelist)):
                item = autobake_bakelist[index]
                if item.Type == active_item[0] and item.Size == active_item[1] and item.Gate == active_item[2] and item.IsDuplicate == active_item[3]:
                    scene.autobake_bakelist_index = index
        else:
            autobake_udimlist = scene.autobake_udimlist
            types = []
            active_item = ((autobake_udimlist[scene.autobake_udimlist_index].Type, autobake_udimlist[scene.autobake_udimlist_index].Size, autobake_udimlist[scene.autobake_udimlist_index].Gate, autobake_udimlist[scene.autobake_udimlist_index].IsDuplicate))
            
            for index in range(len(autobake_udimlist)):
                item = autobake_udimlist[index]
                
                if item.Type not in types:
                    types.append(item.Type)
                elif item.Type in types:
                    adjust_index = 0
                    if autobake_udimlist[index].Type != autobake_udimlist[index-1].Type:
                        while autobake_udimlist[index-adjust_index].Type != autobake_udimlist[index-adjust_index-1].Type:
                            autobake_udimlist.move(index-adjust_index, index-adjust_index-1)
                            adjust_index = adjust_index+1
                            
            for index in range(len(autobake_udimlist)):
                item = autobake_udimlist[index]
                adjust_index = 0
                
                if autobake_udimlist[index].Type == autobake_udimlist[index-1].Type and autobake_udimlist[index].Size < autobake_udimlist[index-1].Size:
                    while autobake_udimlist[index-adjust_index].Type == autobake_udimlist[index-adjust_index-1].Type and autobake_udimlist[index-adjust_index].Size < autobake_udimlist[index-adjust_index-1].Size:
                        autobake_udimlist.move(index-adjust_index, index-adjust_index-1)
                        adjust_index = adjust_index+1
            
            for index in range(len(autobake_udimlist)):
                item = autobake_udimlist[index]
                if item.Type == active_item[0] and item.Size == active_item[1] and item.Gate == active_item[2] and item.IsDuplicate == active_item[3]:
                    scene.autobake_udimlist_index = index
        return {'FINISHED'}


class SPARROW_OT_ScaleUp(Operator):
    bl_idname = "sparrow.scale_up"
    bl_label = "Scale Up"
    bl_description = "Multiplies the texture size by 2"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if abp.ab_udim_bake:
            item = scene.autobake_udimtilelist[scene.autobake_udimtilelist_index]
            item.Size = int(item.Size * 2)
        else:
            item = scene.autobake_bakelist[scene.autobake_bakelist_index]
            item.Size = int(item.Size * 2)
        return {'FINISHED'}


class SPARROW_OT_ScaleDown(Operator):
    bl_idname = "sparrow.scale_down"
    bl_label = "Scale Down"
    bl_description = "Divides the texture size by 2"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if abp.ab_udim_bake:
            item = scene.autobake_udimtilelist[scene.autobake_udimtilelist_index]
            item.Size = int(item.Size / 2)
        else:
            item = scene.autobake_bakelist[scene.autobake_bakelist_index]
            item.Size = int(item.Size / 2)
        return {'FINISHED'}
    
    
class SPARROW_OT_Add_UDIM(Operator):
    bl_idname = "sparrow.udimlist_add"
    bl_label = "New Item"
    bl_description = "Add a new item to the list"
    bl_options = {'INTERNAL', 'UNDO'}

    use_ctrl : BoolProperty(options = set(), default=False)
    new_items : IntProperty(options = set(), default=1, name='Item Count', description='Set how many items will be added to the list', min=1, max=100)
    start_tile : IntProperty(options = set(), default=1001, min=1001, max=2000, description='The new items will start with this tile')

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        scene = context.scene
        
        if event.ctrl or scene.autobake_properties.ab_new_item_method == 'Advanced':
            list = scene.autobake_udimtilelist
            if len(list) > 0:
                self.start_tile = list[scene.autobake_udimtilelist_index].UDIM + 1
            
            return context.window_manager.invoke_props_dialog(self, width=175)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout   
        box = layout.box()
        col = box.column_flow(columns=1)
        
        split = col.split(factor=.4)
        split.label(text='New Items')
        split.prop(self, 'new_items', text='')
        
        split = col.split(factor=.4)
        split.label(text='Start Tile')
        split.prop(self, 'start_tile', text='')
        
        split = col.split(factor=.4)
        split.active = False
        split.label(text='Last Tile')
        row = split.row()
        row.alignment = 'CENTER'
        row.label(text=str(self.start_tile+self.new_items-1))
        
    def execute(self, context):
        scene = context.scene
        list = scene.autobake_udimtilelist
        abp = scene.autobake_properties
        
        if self.use_ctrl or abp.ab_new_item_method == 'Advanced':
            for index in range(self.new_items):
                item = list.add()
                item.UDIM = self.start_tile + index
                if len(list)>1:
                    scene.autobake_udimtilelist_index += 1
                else:
                    scene.autobake_udimtilelist_index = 0
        else:
            item = list.add()
            if len(list)>1:
                scene.autobake_udimtilelist_index += 1
                item.UDIM = list[scene.autobake_udimtilelist_index-1].UDIM+1
                item.Size = list[scene.autobake_udimtilelist_index-1].Size
            else:
                scene.autobake_udimtilelist_index = 0
            
        scene.autobake_properties.ab_udim_list_item_count = sum(1 for item in context.scene.autobake_udimtilelist if item.Gate)

        for item in list:
            item.IsDuplicate = sum(1 for item2 in list if item.UDIM == item2.UDIM) > 1
            item.name = f"{item.UDIM} {item.Size} " + ('Enabled' if item.Gate else 'Disabled') + (' Duplicated' if item.IsDuplicate else '')
        return {'FINISHED'}
    
    
class SPARROW_OT_Remove_UDIM(Operator):
    bl_idname = "sparrow.udimlist_remove"
    bl_label = "Remove Item"
    bl_description = "Add a new item to the list"
    bl_options = {'INTERNAL', 'UNDO'}


    use_ctrl : BoolProperty(options = set(), default=False)
    remove_method : EnumProperty(options = set(), name='Remove Method', default='All', description='Choose what items to remove from the list', items=[
        ("All", "All", "All items will be removed from the list"),
        ("Duplicated", "Duplicated", "Remove all the duplicated items from the list"),
        ("Disabled", "Disabled", "Remove all the disabled items from the list")])

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        
        if self.use_ctrl:
            return context.window_manager.invoke_props_dialog(self, width=175)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout   
        box = layout.box()
        split = box.split(factor=.4)
        
        split.label(text='Remove:')
        split.prop(self, 'remove_method', text='')

    def execute(self, context):
        scene = context.scene
        list = scene.autobake_udimtilelist
        index = scene.autobake_udimtilelist_index
        
        if self.use_ctrl:
            if self.remove_method == 'All':
                bpy.ops.autobake.udimlist_remove()
            elif self.remove_method == 'Disabled':
                bpy.ops.autobake.udimlist_remove_disabled()
            elif self.remove_method == 'Duplicated':
                bpy.ops.autobake.udimlist_remove_duplicates()
        else:
            if index >=1:
                scene.autobake_udimtilelist_index-=1
            else:
                scene.autobake_udimtilelist_index=0
            list.remove(index)
            scene.autobake_properties.ab_udim_list_item_count = sum(1 for item in context.scene.autobake_udimtilelist if item.Gate)
            for item in list:
                item.IsDuplicate = sum(1 for item2 in list if item.UDIM == item2.UDIM) > 1
                item.name = f"{item.UDIM} {item.Size} " + ('Enabled' if item.Gate else 'Disabled') + (' Duplicated' if item.IsDuplicate else '')
        return {'FINISHED'}
    
    
class SPARROW_OT_Up_UDIM(Operator):
    bl_idname = "sparrow.udimlist_up"
    bl_label = "Move Up"
    bl_description = "Move item up in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    use_ctrl : BoolProperty(options = set(), default=False)

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        index = scene.autobake_udimtilelist_index
        
        if self.use_ctrl:
            bpy.ops.autobake.move_to_top_udim()
        else:
            if index >= 1:
                scene.autobake_udimtilelist.move(index, index - 1)
                scene.autobake_udimtilelist_index -= 1
     
        return {'FINISHED'}


class SPARROW_OT_Down_UDIM(Operator):
    bl_idname = "sparrow.udimlist_down"
    bl_label = "Move Down"
    bl_description = "Move item down in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    use_ctrl : BoolProperty(options = set(), default=False)

    def invoke(self, context, event):
        self.use_ctrl = event.ctrl
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        index = scene.autobake_udimtilelist_index
        
        if self.use_ctrl:
            bpy.ops.autobake.move_to_bottom_udim()
        else:
            if index < len(scene.autobake_udimtilelist) - 1:
                scene.autobake_udimtilelist.move(index, index + 1)
                scene.autobake_udimtilelist_index += 1
        return {'FINISHED'}


class SPARROW_OT_MoveTop_UDIM(Operator):
    bl_idname = "sparrow.move_to_top_udim"
    bl_label = "Move To Top"
    bl_description = "Move the active item to the top of the list. Call this function with 'CTRL + Click' on the 'Move Up' button"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.autobake_bakelist.move(scene.autobake_udimtilelist_index, 0)
        scene.autobake_udimtilelist_index = 0
        return {'FINISHED'} 
    
    
class SPARROW_OT_MoveBottom_UDIM(Operator):
    bl_idname = "sparrow.move_to_bottom_udim"
    bl_label = "Move To Bottom"
    bl_description = "Move the active item to the bottom of the list. Call this function with 'CTRL + Click' on the 'Move Down' button"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.autobake_udimtilelist.move(scene.autobake_udimtilelist_index, len(scene.autobake_udimtilelist)-1)
        scene.autobake_udimtilelist_index = len(scene.autobake_udimtilelist)-1
        return {'FINISHED'}


class SPARROW_OT_RemoveAll_UDIM(Operator):
    bl_idname = "sparrow.udimlist_remove_all"
    bl_label = "Remove All"
    bl_description = "Remove all the items from the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        scene.autobake_udimtilelist.clear()
        return {'FINISHED'}
    
    
class SPARROW_OT_RemoveDuplicates_UDIM(Operator):
    bl_idname = "sparrow.udimlist_remove_duplicates"
    bl_label = "Remove Duplicated"
    bl_description = "Remove all the duplicated items from the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        list = scene.autobake_udimtilelist
        
        for index in range(len(list)-1, -1, -1):
            if list[index].IsDuplicate:
                list.remove(index)
                if scene.autobake_udimtilelist_index > len(list)-1:
                    scene.autobake_udimtilelist_index = len(list)-1
                for item in list:
                    item.IsDuplicate = sum(1 for Item in list if (item.UDIM == Item.UDIM and item.UDIM == Item.UDIM)) > 1
        
        for item in list:
            item.IsDuplicate = sum(1 for item2 in list if item.UDIM == item2.UDIM) > 1

        return {'FINISHED'}
    

class SPARROW_OT_RemoveDisabled_UDIM(Operator):
    bl_idname = "sparrow.udimlist_remove_disabled"
    bl_label = "Remove Disabled"
    bl_description = "Remove all the disabled items from the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        list = scene.autobake_udimtilelist

        for index in range(len(list)-1, -1, -1):
            if list[index].Gate == False:
                list.remove(index)
        if scene.autobake_udimtilelist_index > len(list)-1:
            scene.autobake_udimtilelist_index = len(list)-1
        for item in list:
            item.IsDuplicate = sum(1 for item2 in list if item.UDIM == item2.UDIM) > 1
        return {'FINISHED'}


class SPARROW_OT_EnableAll_UDIM(Operator):
    bl_idname = "sparrow.udimlist_enable_all"
    bl_label = "Enable All"
    bl_description = "Enable all the items in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        for item in scene.autobake_udimtilelist:
            item.Gate = True
        return {'FINISHED'}
    
    
class SPARROW_OT_DisableAll_UDIM(Operator):
    bl_idname = "sparrow.udimlist_disable_all"
    bl_label = "Disable All"
    bl_description = "Disable all the items in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties

        for item in scene.autobake_udimtilelist:
            item.Gate = False
            
        return {'FINISHED'}
    
    
class SPARROW_OT_InvertAll_UDIM(Operator):
    bl_idname = "sparrow.udimlist_invert_all"
    bl_label = "Invert All"
    bl_description = "Invert all the items in the list"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        for item in scene.autobake_udimtilelist:
            item.Gate = not bool(item.Gate)
        return {'FINISHED'}
    
    
class SPARROW_OT_Sort_UDIM(Operator):
    bl_idname = "sparrow.udimlist_sort"
    bl_label = "Sort Items"
    bl_description = "Reorder all the items by type and scale"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        autobake_udimtilelist = scene.autobake_udimtilelist

        for index in range(len(autobake_udimtilelist)):
            item = autobake_udimtilelist[index]
            adjust_index = 0
            if autobake_udimtilelist[index].UDIM < autobake_udimtilelist[index-1].UDIM:
                while autobake_udimtilelist[index-adjust_index].UDIM < autobake_udimtilelist[index-adjust_index-1].UDIM:
                    autobake_udimtilelist.move(index-adjust_index, index-adjust_index-1)
                    adjust_index = adjust_index+1
        return {'FINISHED'}
    
    
class SPARROW_OT_ImportTiles_UDIM(Operator):
    bl_idname = "sparrow.udimlist_import"
    bl_label = "Source Image"
    bl_description = "Import the existing UDIM tiles from the selected image"
    bl_options = {'INTERNAL', 'UNDO'}
    
    clear_list : BoolProperty(options = set(), default=True, description="Clear the current items in the 'UDIM Tiles' list")
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene.autobake_properties, "ab_import_tiles", text="")
        layout.prop(self, 'clear_list', text='Clear List')
        

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        image = abp.ab_import_tiles
        list = scene.autobake_udimtilelist
        
        if image.source == 'TILED':
            if self.clear_list:
                list.clear()
            for tile in image.tiles:
                item = list.add()
                item.UDIM = tile.number
                item.Size = tile.size[0]
            abp.ab_import_tiles=None
            abp.ab_udim_list_item_count = sum(1 for item in context.scene.autobake_udimtilelist if item.Gate)
        else:
            self.report({'ERROR'}, "Source Image needs to be a UDIM image")

        return {'FINISHED'}
    
    
class SPARROW_OT_NameStructure(Operator):
    bl_idname = "sparrow.edit_name_structure"
    bl_label = "Name Structure Editor"
    bl_options = {'INTERNAL', 'UNDO'}
    bl_description = "Edit your textures' name structures"
   
    name_structure: StringProperty(options = set(), name="Name Structure", default="", description='Structure to use when creating and exporting non-udim images. Leave if empty for reset')
    name_structure_udim: StringProperty(options = set(), name="UDIM Name Structure", default="", description='Structure to use when creating UDIM images. Leave if empty for reset')
    name_structure_udim_export: StringProperty(options = set(), name="UDIM Name Structure: Export", default='', description="Structure to use when exporting UDIM images. Must contain the UDIM Number placeholder Leave if empty for reset")
    variable_values = {}
    variable_values_udim = {}
    udim_texture = BoolProperty(options = set(), default=False)
    
    def invoke(self, context, event):
        scene = context.scene
        abp = scene.autobake_properties
        
        self.name_structure = abp.ab_name_structure
        self.name_structure_udim = abp.ab_name_structure_udim
        self.name_structure_udim_export = abp.ab_name_structure_udim_export
        
        self.variable_values = {"prefix": abp.ab_prefix if abp.ab_prefix != '' else context.active_object.name if context.active_object is not None else 'Cube',
                                "bridge": abp.ab_bridge,
                                "suffix": abp.ab_suffix,
                                "type": 'Metallic',
                                "size": '512',
                                "udim": '1021',
                                "uvtile": 'u1_v3'}
                                
        self.variable_values_udim = {"prefix": abp.ab_prefix if abp.ab_prefix != '' else context.active_object.name if context.active_object is not None else 'Cube',
                                     "bridge": abp.ab_bridge,
                                     "suffix": abp.ab_suffix,
                                     "type": 'Metallic',
                                     "size": '1.00',
                                     "udim": '1021',
                                     "uvtile": 'u1_v3'}
                                
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

    # Name Structure
        row = layout.row()
        row.alignment = 'CENTER'
        row.label(text='• Name Structure •')
        layout.prop(self, 'name_structure', text='')
        box = layout.box()
        if self.name_structure == '':
            box.label(text='Structure will be reset!')
        else:
            try:
                result_string = self.name_structure.lower().format(**self.variable_values)
                if any(element in self.name_structure.lower() for element in ['{udim}', '{uvtile}']):
                    box.alert = True
                    box.label(text="Structure can't contain 'UDIM' and 'UVTILE' elements!")
                else:
                    box.label(text=f"Output: {result_string}")
                    box.label(text=f"Export: {result_string}.{abp.ab_fileformat}")
            except KeyError as e:
                box.alert = True
                box.label(text=f"Input error! Invalid Key: '{{{e.args[0]}}}'.")
        layout.separator()

    # Name Structure UDIM
        row=layout.row()
        row.alignment = 'CENTER'
        row.label(text='• UDIM Name Structure •')
        layout.prop(self, 'name_structure_udim', text='')
        box = layout.box()
        if self.name_structure_udim == '':
            box.label(text='Structure will be reset!')
        else:
            try:
                result_string_udim = self.name_structure_udim.lower().format(**self.variable_values_udim)
                if any(element in self.name_structure_udim.lower() for element in ['{udim}', '{uvtile}']):
                    box.alert = True
                    box.label(text="Structure can't contain 'UDIM' and 'UVTILE' elements!")
                else:
                    box.label(text=f"Output: {result_string_udim}")
            except KeyError as e:
                box.alert = True
                box.label(text=f"Input error! Invalid Key: '{{{e.args[0]}}}'.")
        layout.separator()
            
    # Name Structure UDIM Export
        row=layout.row()
        row.alignment = 'CENTER'
        row.label(text='• UDIM Export Name Structure •')
        layout.prop(self, 'name_structure_udim_export', text='')
        box = layout.box()
        if self.name_structure_udim_export == '':
            box.label(text='Structure will be reset!')
        else:
            try:
                result_string_udim_export = self.name_structure_udim_export.lower().format(**self.variable_values_udim)
                if '{udim}' not in self.name_structure_udim_export.lower() and '{uvtile}' not in self.name_structure_udim_export.lower():
                    box.alert = True
                    box.label(text="Missing 'UDIM' or 'UVTILE' element!")
                else:
                    box.label(text=f"Export: {result_string_udim_export}.{abp.ab_fileformat}")
            except KeyError as e:
                result_string_udim = f"Error: Invalid key: '{{{e.args[0]}}}'."      
        layout.separator()
        
    # Elements
        row=layout.row()
        row.alignment = 'CENTER'
        row.label(text='• Structure Elements •')
        box = layout.box()
        column = box.grid_flow(align=True, columns=2)
        column.label(text="Prefix: {prefix}", icon='DOT')
        column.label(text="Type: {type}", icon='DOT')
        column.label(text="Bridge: {bridge}", icon='DOT')
        column.label(text="Size: {size}", icon='DOT')
        column.label(text="Suffix: {suffix}", icon='DOT')
        column.label(text="UDIM: {udim}", icon='DOT')
        column.label(text="UVTILE: {uvtile}", icon='DOT')
      
    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
    
    # Single
        if self.name_structure == '':
            abp.ab_name_structure = '{prefix}{type}{bridge}{size}{suffix}'
            self.report({'INFO'}, f"Auto Bake: 'Name Structure' got reset!")
        else:
            try:
                result_string = self.name_structure.lower().format(**self.variable_values)
                if any(element in self.name_structure.lower() for element in ['{udim}', '{uvtile}']):
                    self.report({'ERROR'}, "Auto Bake: 'Name Structure' can't contain 'UDIM' and 'UVTILE' elements!")
                else:
                    abp.ab_name_structure = self.name_structure
            except KeyError as e:
                self.report({'ERROR'}, "Auto Bake: 'Name Structure' Input error! Invalid Key: '{{{e.args[0]}}}'.")
        
    # UDIM
        if self.name_structure_udim == '':
            abp.ab_name_structure_udim = '{prefix}{type}{bridge}{size}x'
            self.report({'INFO'}, f"Auto Bake: 'UDIM Name Structure' got reset!")
        else:
            try:
                result_string_udim = self.name_structure_udim.lower().format(**self.variable_values_udim)
                if any(element in self.name_structure_udim.lower() for element in ['{udim}', '{uvtile}']):
                    self.report({'ERROR'}, "Auto Bake: 'UDIM Name Structure' can't contain 'UDIM' and 'UVTILE' elements!")
                else:
                    abp.ab_name_structure_udim = self.name_structure_udim
            except KeyError as e:
                self.report({'ERROR'}, f"Auto Bake: Failed to edit 'UDIM Name Structure'. Invalid key: '{e.args[0]}'")
        
    # UDIM Export
        if self.name_structure_udim_export == '':
            abp.ab_name_structure_udim_export = '{prefix}{type}{bridge}{size}x.{udim}'
            self.report({'INFO'}, f"Auto Bake: 'UDIM Export Name Structure' got reset!")
        else:
            try:
                result_string_udim_export = self.name_structure_udim_export.lower().format(**self.variable_values_udim)
                if '{udim}' not in self.name_structure_udim_export.lower() and '{uvtile}' not in self.name_structure_udim_export.lower():
                    self.report({'ERROR'}, "Auto Bake: 'UDIM Export Name Structure' must contain 'UDIM' or 'UVTILE' element")
                else:
                    abp.ab_name_structure_udim_export = self.name_structure_udim_export
            except KeyError as e:
                self.report({'ERROR'}, f"Auto Bake: Failed to edit 'UDIM Export Name Structure'. Invalid key: '{e.args[0]}'")  
                
        return {'FINISHED'}


class SPARROW_OT_SelectFromList(Operator):
    bl_idname = "sparrow.select_from_list"
    bl_label = "Select Objects"
    bl_description = "Select the items in the 3D viewport from the list"
    bl_options = {'INTERNAL', 'UNDO'}

    clear : BoolProperty(options = set(), name='Deselect Selected', description='Deselect all the currently selected objects in the 3D viewport before selecting the objects from the list', default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'clear')

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
    
        if self.clear:
            for obj in reversed(bpy.context.selected_objects):
                obj.select_set(False)
                
        if abp.ab_source_object_method == 'LIST':
            for item in scene.autobake_sourceobject:
                if item.Object != None:
                    item.Object.select_set(True)
        else:
            for obj in abp.ab_source_collection.objects:
                if obj.type != 'LIGHT':
                    obj.select_set(True)

        abp.ab_target_object.select_set(True)
        context.view_layer.objects.active = abp.ab_target_object

        return {'FINISHED'}


class SPARROW_OT_LoadFromSelected(Operator):
    bl_idname = "sparrow.load_selected_objects"
    bl_label = "Load from Selected"
    bl_description = "Load the currently selected items from the 3D viewport to the list"
    bl_options = {'INTERNAL', 'UNDO'}

    clear : BoolProperty(options = set(), name='Clear List', description='Remove all the list items before loading them from the 3D viewport')
    active : BoolProperty(options = set(), name='Active as Target', description='Load the active object from the selection as the new target object')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row(align=True)
        row.prop(self, 'clear', toggle=True, icon='X', text='Clear Objects')
        row.prop(self, 'active', toggle=True, icon='OBJECT_DATAMODE')

    def execute(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        if self.clear:
            scene.autobake_sourceobject.clear()
            
        for obj in bpy.context.selected_objects:
            if not any(item.Object == obj for item in scene.autobake_sourceobject):
                item = scene.autobake_sourceobject.add()
                item.Object = obj
                
        if self.active and context.active_object != None and context.active_object.select_get():
            abp.ab_target_object = context.active_object
    
            for index, item in enumerate(scene.autobake_sourceobject):
                if item.Object == abp.ab_target_object:
                    scene.autobake_sourceobject.remove(index)
                    break
                
        if len(scene.autobake_sourceobject) == 0:
            scene.autobake_sourceobject.add()
            
        return {'FINISHED'}
    
    
class SPARROW_OT_ToggleQueueItem(Operator):
    bl_idname = "sparrow.toggle_queued"
    bl_label = "Enable / Disable"
    bl_description = "Enable or Disable the bake item in the queue"
    bl_options = {'INTERNAL', 'UNDO'}
    
    index : IntProperty(options = set(), )
    
    def invoke(self, context, event):
        if event.ctrl or not context.scene.autobake_properties.ab_confirm_queue_item_gate:
            return self.execute(context)
        else:
            return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        scene = context.scene
        item = scene.autobake_queuelist[self.index]
        if item.Status == 'Pending':
            item.Status = 'Canceled'
            item.Cancel = True
            item.Icon = 'CANCEL'
        elif item.Status == 'Canceled':
            item.Status = 'Pending'
            item.Cancel = False
            item.Icon = 'PREVIEW_RANGE'
            
        item.name = f"{item.Type} {item.Size} {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
        
        return {'FINISHED'}
    
    
class SPARROW_OT_ToggleObjectQueueItem(Operator):
    bl_idname = "sparrow.toggle_queued_object"
    bl_label = "Enable / Disable"
    bl_description = "Enable or Disable the bake item in the queue"
    bl_options = {'INTERNAL', 'UNDO'}
    
    index : IntProperty(options = set(), )
    
    def invoke(self, context, event):
        if event.ctrl or not context.scene.autobake_properties.ab_confirm_queue_item_gate:
            return self.execute(context)
        else:
            return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        scene = context.scene
        item = scene.autobake_objectqueuelist[self.index]
        if item.Status == 'Pending':
            item.Status = 'Canceled'
            item.Cancel = True
            item.Icon = 'CANCEL'
        elif item.Status == 'Canceled':
            item.Status = 'Pending'
            item.Cancel = False
            item.Icon = 'PREVIEW_RANGE'
            
        item.name = f"{item.Object.name} {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
        return {'FINISHED'}


class SPARROW_OT_ExportTextures(Operator):
    bl_idname = "sparrow.export_textures"
    bl_label = "Export List"
    bl_description = "Export the unsaved textures from the previous bakes"
    bl_options = {'INTERNAL', 'UNDO'}

    def toggle_all(self, context):
        scene = context.scene
        list = scene.autobake_imageexport
        
        for item in list:
            if item.Image.is_dirty:
                item.Gate = self.toggle_all

    toggle_all : BoolProperty(options = set(), default=True, update=toggle_all)

    def invoke(self, context, event):
        scene = context.scene
        list = scene.autobake_imageexport

        for index in reversed(range(len(list))):
            if list[index].Image is None:
                list.remove(index)
    
        for item in list:
            if item.Image.is_dirty:
                self.toggle_all = item.Gate
                break
             
        for item in list:
            if not item.Image.is_dirty:
                item.Gate = False
            
        return context.window_manager.invoke_props_dialog(self, width=375)
    

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        
        box = layout.box()
        
        split = box.split(factor=.3225, align=True)
        
        split.label(text='Folder', icon='FILE_FOLDER')
        
        row = split.row()
        
        row.label(text='Texture', icon='TEXTURE')
        row2 = row.row()
        row2.alignment = 'RIGHT'
        row2.label(text='Export')
        row.prop(self, 'toggle_all', text='')

        layout.template_list("SPARROW_UL_ImageExport", "Image_Export_List", scene, "autobake_imageexport", scene, "autobake_imageexport_index", rows=2)

        if any(item.Image and item.Image.is_dirty == False for item in scene.autobake_imageexport):
            layout.label(icon='ERROR', text='Unsaved image data is lost or already saved.')

    def execute(self, context):
        scene = context.scene
        
        for item in scene.autobake_imageexport:
            if item.Gate:
                export_texture(self, context, item.Image, item.Name, item.Type, item.Label, item.Prefix)
        scene.autobake_imageexport.clear()
        return {'FINISHED'}
    
    
class SPARROW_OT_FolderExplorer(Operator):
    bl_idname = "sparrow.file_explorer"
    bl_label = "Select Folder"
    bl_options = {'INTERNAL', 'UNDO'}
    
    directory: StringProperty(options = set(), )

    def execute(self, context):
        bpy.context.scene.autobake_properties.ab_filepath = os.path.dirname(self.directory)
        return {'FINISHED'}
        
    def invoke(self, context, event):
        if bool(os.path.exists(bpy.context.scene.autobake_properties.ab_filepath)):
            self.directory = bpy.context.scene.autobake_properties.ab_filepath
        context.window_manager.fileselect_add(self)
        
        return {'RUNNING_MODAL'} 


class SPARROW_OT_BakeConfirm(Operator):
    bl_idname = "sparrow.confirm_bakes"
    bl_label = "Confirm & Clear"
    bl_description = "Confirming the bakes will hide the panel above, and remove all its items"
    bl_options = {'INTERNAL', 'UNDO'}

    def invoke(self, context, event):
        if event.ctrl or not context.scene.autobake_properties.ab_confirm_bake_results:
            return self.execute(context)
        else:
            return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        scene.autobake_queuelist.clear()
        scene.autobake_objectqueuelist.clear()
        
        return {'FINISHED'}
    
    
class SPARROW_OT_NextObject(Operator):
    bl_idname = "sparrow.next_object"
    bl_label = "Next Object"
    bl_description = "Continue the bake with the next object in the queue"
    bl_options = {'INTERNAL', 'UNDO'}

    def invoke(self, context, event):
        if event.ctrl or not context.scene.autobake_properties.ab_confirm_next_object:
            return self.execute(context)
        else:
            return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        
    # Restore Bake Items
        for item in scene.autobake_queuelist:
            item.Enabled = True
            
            if item.Status in ['Baked', 'Exported', 'Failed']:
                item.Status = 'Pending'
                item.Icon = 'PREVIEW_RANGE'
                item.name = f"{item.Type} " + (f"{item.Multiplier:.2f}" if scene.autobake_properties.ab_udim_bake else f"{item.Size}") + f" {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')

    # Restore Bake Queue Order
        global bake_order
        for index, item in enumerate(bake_order):
            for index_, item_ in enumerate(scene.autobake_queuelist):
                if (f"{item_.Type} " + (f"{item_.Multiplier:.2f}" if is_udim_bake else f"{item_.Size}")) == item:
                    scene.autobake_queuelist.move(index_, index)
                    break


        global next_object_bake
        next_object_bake = True
        
        global bake_status
        if bake_status == 'PAUSED':
            bake_status = 'INPROGRESS'
        
        return {'FINISHED'}


class SPARROW_OT_CancelBake(Operator):
    bl_idname = "sparrow.cancel_bake"
    bl_label = "Cancel"
    bl_description = "Cancel all the pending items in the queue"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        if event.ctrl or not context.scene.autobake_properties.ab_confirm_cancel_bake:
            return self.execute(context)
        else:
            return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        
        for item in scene.autobake_queuelist:
            if item.Status == 'Pending':
                item.Enabled = False
                item.Status = 'Canceled'
                item.name = f"{item.Type} {item.Size} {item.Status} " + ('Enabled' if item.Enabled else 'Disabled')
                item.Icon = 'CANCEL'
                
        global bake_results   
         
        for item in scene.autobake_objectqueuelist:
            if item.Status == 'Pending':
                item.Enabled = False
                item.Status = 'Canceled'
                item.name = f"{item.Object.name} {item.Status} " + ('Enabled' if item.Enabled else 'Disabled')
                item.Icon = 'CANCEL'
        
                results = []
                for item_ in scene.autobake_queuelist:
                    results.append({f"{item_.Type} " + (f"{item_.Multiplier:.2f}" if is_udim_bake else f"{item_.Size}"): {'Status': 'Canceled', 'Icon': 'CANCEL', 'Error': '' ,'Cancel': True}})
                bake_results[item.Object.name] = results
        
        global next_object_bake
        next_object_bake = True
                
        global bake_status
        bake_status = 'INPROGRESS'
        
        return {'FINISHED'}                            


class SPARROW_OT_PauseBake(Operator):
    bl_idname = "sparrow.pause_bake"
    bl_label = "Pause"
    bl_description = "Waits for the current bake, then pauses the process and keeps the queue"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        global bake_status
        bake_status = 'PAUSED'
        return {'FINISHED'}


class SPARROW_OT_ResumeBake(Operator):
    bl_idname = "sparrow.resume_bake"
    bl_label = "Resume"
    bl_description = "Continues the queue"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        
        global next_object_bake
        global bake_status
        bake_status = 'INPROGRESS'
        
        if not next_object_bake:
            for item in scene.autobake_queuelist:
                item.Enabled = True
                if item.Status in ['Baked', 'Exported', 'Failed']:
                    item.Status = 'Pending'
                    item.Icon = 'PREVIEW_RANGE'
                    item.name = f"{item.Type} " + (f"{item.Multiplier:.2f}" if scene.autobake_properties.ab_udim_bake else f"{item.Size}") + f" {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')

            next_object_bake = True
        
        return {'FINISHED'}

class SPARROW_OT_BakeStart(Operator):
    bl_idname = "sparrow.start_bake"
    bl_label = "Start Bake"
    bl_description = "Generates a baking queue based on the 'Bake List' and initiates the texture baking process. Once a bake is completed, the texture will be automatically exported if the export checkbox is selected. Otherwise, the texture will be added to a list for future export using the 'Export' button below"
    bl_options = {'INTERNAL', 'UNDO'}

    clear_list : BoolProperty(options = set(), default=False, description='Remove all the unsaved textures from the export list')

    bake_type_info = {
                    "Base Color": ("EMIT", "Color"),
                      "Metallic": ("EMIT", "Float"),
                     "Roughness": ("EMIT", "Float"),
                           "IOR": ("EMIT", "Float"),
                         "Alpha": ("EMIT", "Float"),
                        "Normal": ("NORMAL", "Vector"),
                       "Tangent": ("NORMAL", "Vector"),
                       
                   "Anisotropic": ("EMIT", "Float"),
          "Anisotropic Rotation": ("EMIT", "Float"),
    
                         "Sheen": ("EMIT", "Float"),
                    "Sheen Tint": ("EMIT", "Color" if bpy.app.version >= (4, 0, 0) else "Float"),
                  "Sheen Weight": ("EMIT", "Float"),
               "Sheen Roughness": ("EMIT", "Float"),
                         
                      "Coat IOR": ("EMIT", "Float"),
                     "Coat Tint": ("EMIT", "Color"),
                   "Coat Weight": ("EMIT", "Float"),
                   "Coat Normal": ("NORMAL", "Vector"),
                "Coat Roughness": ("EMIT", "Float"),
                     "Clearcoat": ("EMIT", "Float"),
           "Clearcoat Roughness": ("EMIT", "Float"),
              "Clearcoat Normal": ("NORMAL", "Vector"),
                      
             "Subsurface Radius": ("NORMAL", "Vector"),
                "Subsurface IOR": ("EMIT", "Float"),
         "Subsurface Anisotropy": ("EMIT", "Float"),
                    "Subsurface": ("EMIT", "Float"),
              "Subsurface Scale": ("EMIT", "Float"),
              "Subsurface Color": ("EMIT", "Color"),
             "Subsurface Weight": ("EMIT", "Float"),
              
                  "Transmission": ("EMIT", "Float"),
           "Transmission Weight": ("EMIT", "Float"),
        "Transmission Roughness": ("EMIT", "Float"),
                      
                      "Specular": ("EMIT", "Float"),
                 "Specular Tint": ("EMIT", "Color" if bpy.app.version >= (4, 0, 0) else "Float"),
            "Specular IOR Level": ("EMIT", "Float"),
            
             "Emission Strength": ("EMIT", "Float"),
                      "Emission": ("EMIT", "Color"),
                "Emission Color": ("EMIT", "Color"),

               "Channel Packing": ("EMIT", "Channel Packing"),
               "Color Attribute": ("EMIT", "Color Attribute"),
             "Ambient Occlusion": ("EMIT", "Ambient Occlusion"),
                    "Pointiness": ("EMIT", "Pointiness"),
                 "Displacement ": ("EMIT", "Displacement"),

                       "Normals": ("NORMALS", "Multires"),
                  "Displacement": ("DISPLACEMENT", "Multires"),

                      "Combined": ("COMBINED", "Combined"),
            "Ambient Occlusion ": ("AO", "AO"),
                       "Normal ": ("NORMAL", "Standard"),
                    "Roughness ": ("ROUGHNESS", "Standard"),
                        "Glossy": ("GLOSSY", "Glossy"),
                      "Position": ("POSITION", "Standard"),
                        "Shadow": ("SHADOW", "Standard"),
                       "Diffuse": ("DIFFUSE", "Diffuse"),
                            "UV": ("UV", "UV"),
                  "Transmission": ("TRANSMISSION", "Transmission"),
                   "Environment": ("ENVIRONMENT", "Standard"),
                          "Emit": ("EMIT", "Standard")}
                      
    gridscalex = 0
    type_name = ""
    label = ()
    img = ()
    phase_bake_locked = False
    phase_export_locked = True
    phase_finished_locked = True
    bake_canceled = False
    item_index = 0
    render_disabled = {}
    node_tiling = []
    udim_tiles = []
    name_structure = {}
    image_scale_name = ''
    antialiasing_method = ''
    scale_reset = {}
    prefix = ''
    img_start_loc = {}
    source_objects = []
    selected_to_active = False
    bake_order = []
    final_material = None
    sampling = []
    margin_original = 8

    def ab_bake_complete_multires(self):
        if not self.img.is_dirty:
            return 0.5
        else:
            self.ab_bake_complete(None, None)
       
    def ab_bake_complete(self, obj, empty):
        context = bpy.context
        scene = context.scene
        abp = scene.autobake_properties
        
        if not self.bake_canceled:
            if abp.ab_report_bake_end:
                self.report({'INFO'}, f"Auto Bake: Texture '{self.img.name}' is finished baking.")
            
        remove_handlers_timers()
        restore_nodes()
        
        self.phase_export_locked = False

    def ab_bake_cancel(self, object, empty):
        self.bake_canceled = True
        context = bpy.context
        scene = context.scene
        abp = scene.autobake_properties
        
        if abp.ab_report_bake_end:
            self.report({'ERROR'}, f"Auto Bake: '{self.img.name}' was forced to stop baking...")
            
        self.update_queue_item(context, 'Baking', False, 'Failed', 'ERROR', fail_msg = 'Bake was forced to stop!')
        
        remove_handlers_timers()
        restore_nodes()
        
        self.phase_finished_locked = False
        
    def update_queue_item(self, context, edit_status, set_enabled, set_status, set_icon, fail_msg=''):
        scene = context.scene
        for item in scene.autobake_queuelist:
            if item.Status == edit_status:
                item.Enabled = set_enabled
                item.Status = set_status
                item.Error = fail_msg
                item.Icon = set_icon
                item.name = f"{item.Type} " + (f"{item.Multiplier:.2f}" if scene.autobake_properties.ab_udim_bake else f"{item.Size}") + f" {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
           
    def bake_item_check_fail(self, context, error):
        scene = context.scene
        abp = scene.autobake_properties
        
        self.phase_bake_locked = True
        self.phase_finished_locked = False
        self.update_queue_item(context, 'Baking', False, 'Failed', 'ERROR', fail_msg=error)
        
        if abp.ab_move_finished_bake:
            scene.autobake_queuelist.move(self.item_index, len(scene.autobake_queuelist)-1)
        
        
    def invoke(self, context, event):
        scene = context.scene
        abp = scene.autobake_properties
        
        if (abp.ab_export_list == 'Ask' and len(scene.autobake_imageexport) > 0) or (abp.ab_start_popup_settings and any(setting for setting in [abp.ab_start_popup_final_object, abp.ab_start_popup_object_offset, abp.ab_start_popup_final_material, abp.ab_start_popup_final_shader, abp.ab_start_popup_texture_apply, abp.ab_start_popup_export_textures, abp.ab_start_popup_export_objects, abp.ab_start_popup_selected_to_active, abp.ab_start_popup_keep_textures])):
            return context.window_manager.invoke_props_dialog(self, width=275)
        
        elif abp.ab_export_list == 'Clear':
            scene.autobake_imageexport.clear()
            
        if event.ctrl or not context.scene.autobake_properties.ab_confirm_start_bake:
            return self.execute(context)
        else:
            return context.window_manager.invoke_confirm(self, event)


    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

    # Settings
        if abp.ab_start_popup_settings and any(setting for setting in [abp.ab_start_popup_final_object, abp.ab_start_popup_object_offset, abp.ab_start_popup_final_material, abp.ab_start_popup_final_shader, abp.ab_start_popup_texture_apply, abp.ab_start_popup_export_textures, abp.ab_start_popup_export_objects, abp.ab_start_popup_selected_to_active, abp.ab_start_popup_keep_textures]):
            flow = layout.grid_flow(align=True, columns=1)

        # Material
            if abp.ab_start_popup_final_material:
                box = flow.box()
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text='• Material •')
                
                grid = box.grid_flow(align=False, columns=1)
                grid.prop(abp, 'ab_final_material', text='Create Final      ', icon='MATERIAL')
                
                if abp.ab_start_popup_final_shader:
                    row = grid.row(align=True)
                    row.active = abp.ab_final_material
                    row.prop(abp, 'ab_final_shader', text='')
                
                if abp.ab_start_popup_texture_apply:
                    row = grid.row(align=True)
                    row.active = abp.ab_final_material
                    row.prop(abp, 'ab_apply_textures', text='')
            
        # Object
            if abp.ab_start_popup_final_object:
                box = flow.box()
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text='• Object •')
                
                grid = box.grid_flow(align=False, columns=1)
                    
                grid.prop(abp, 'ab_final_object', text='Create Final      ', icon='OBJECT_DATAMODE')
                
                if abp.ab_start_popup_export_objects:
                    row = grid.row(align=True)
                    row.active = abp.ab_final_object
                    
                    row_b = row.row(align=True)
                    row_b.alignment = 'LEFT'
                    row_b.prop(abp, 'ab_offset_direction', text='')
                    row.prop(abp, 'ab_object_offset', text='')
            
                if abp.ab_start_popup_export_objects:
                    row = grid.row(align=True)
                    row.active = abp.ab_final_object
                    row.prop(abp, 'ab_export_object', text='Export Objects      ', icon='EXPORT')
                    
                if abp.ab_start_popup_selected_to_active:
                    grid.prop(scene.render.bake, 'use_selected_to_active', text='Selected to Active      ', icon='CHECKBOX_HLT' if scene.render.bake.use_selected_to_active else 'CHECKBOX_DEHLT')
            
        # Textures
            if abp.ab_start_popup_selected_to_active or abp.ab_start_popup_export_textures or abp.ab_start_popup_keep_textures:
                box = flow.box()
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text='• Texture •')
                
                grid = box.grid_flow(align=False, columns=1)
                    
                if abp.ab_start_popup_export_textures:
                    grid.prop(abp, 'ab_texture_export', text='Export Textures      ', icon='EXPORT')
                
                if abp.ab_start_popup_keep_textures:
                    grid.prop(abp, 'ab_remove_imagetextures', text='Remove Textures      ', icon='TRASH')
            
    # Clear List
            if len(scene.autobake_imageexport) > 0:
                grid.prop(self, 'clear_list', text='Clear Export List      ', icon='X')
        else:
            if len(scene.autobake_imageexport) > 0:
                layout.prop(self, 'clear_list', text='Clear Export List      ', icon='X')
            

    def execute(self, context):
        scene = context.scene
        abp: SPARROW_PG_Autobake  = scene.autobake_properties
        
    # Resets
        scene.autobake_queuelist.clear()
        scene.autobake_objectqueuelist.clear()
        
        self.node_tiling.clear()
        
        if self.clear_list:
            scene.autobake_imageexport.clear()
        
    # List has Item
        if abp.ab_udim_bake:
            if len(scene.autobake_udimlist) < 1:
                self.report({'ERROR'}, "Auto Bake: 'Bake List' is empty.")
                return {'CANCELLED'}
            if len(scene.autobake_udimtilelist) < 1:
                self.report({'ERROR'}, "Auto Bake: 'Bake List' is empty.")
                return {'CANCELLED'}
        else:
            if len(scene.autobake_bakelist) < 1:
                self.report({'ERROR'}, "Auto Bake: 'Bake List' is empty.")
                return {'CANCELLED'}
            
    # List has Enabled
        if abp.ab_udim_bake:
            if not any(item.Gate for item in scene.autobake_udimlist):
                self.report({'ERROR'}, "Auto Bake: 'Bake List' has no enabled item.")
                return {'CANCELLED'}
            if not any(item.Gate for item in scene.autobake_udimtilelist):
                self.report({'ERROR'}, "Auto Bake: 'UDIM Tiles' list has no enabled item.")
                return {'CANCELLED'}
        else:
            if not any(item.Gate for item in scene.autobake_bakelist):
                self.report({'ERROR'}, "Auto Bake: 'Bake List' has no enabled item.")
                return {'CANCELLED'}

    # Selected to Active
        self.selected_to_active = scene.render.bake.use_selected_to_active
            
    # Object Requests (Non StA)
        if not self.selected_to_active:
            if abp.ab_report_requests:
                self.report({'INFO'}, "Auto Bake: Collecting objects to bake...")
            for obj in bpy.context.selected_objects:
                print(obj.name)
                if obj.type == 'MESH':
                    item = scene.autobake_objectqueuelist.add()
                    item.Object = obj
                    item.name = f"{item.Object.name} {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
        
        # Object Requests Report (Non StA)
            if len(scene.autobake_objectqueuelist) > 0:
                if abp.ab_report_requests:
                    self.report({'INFO'}, f"Auto Bake: ...{len(scene.autobake_objectqueuelist)} objects are added to the object queue list.")
            else:
                print("Auto Bake: Could not collect any objects...must have objects selected in the viewport")
                self.report({'ERROR'}, f"Auto Bake: Could not collect any objects...must have objects selected in the viewport")
                return {'CANCELLED'}
                
    # Object Requests (StA)
        elif self.selected_to_active:
            if abp.ab_report_requests:
                self.report({'INFO'}, "Auto Bake: Collecting objects to bake...")
            if bpy.context.active_object in bpy.context.selected_objects and bpy.context.active_object.type == 'MESH':
                item = scene.autobake_objectqueuelist.add()
                item.Object = bpy.context.active_object
                item.name = f"{item.Object.name} {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
                
            self.source_objects = []
            for obj in bpy.context.selected_objects:
                if obj != bpy.context.active_object and obj.type in ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT']:
                    self.source_objects.append(obj)
            
        # Object Requests Report (StA)
            if len(scene.autobake_objectqueuelist) > 0 and len(self.source_objects) > 0:
                if abp.ab_report_requests:
                    self.report({'INFO'}, f"Auto Bake: 1 target with {len(self.source_objects)} source objects are added to the object queue list...")
            else:
                self.report({'ERROR'}, f"Auto Bake: Not enough selected objects... must have a target and one or more source objects selected")
                return {'CANCELLED'}
                
        # Has Cage
            if scene.render.bake.use_cage and scene.render.bake.cage_object is None:
                self.report({'ERROR'}, "Auto Bake: Must have a set 'Cage Object' if 'Cage' is 'True'.")
                return {'CANCELLED'}
    
    # Bake Requests
        if abp.ab_report_requests:
            self.report({'INFO'}, "Auto Bake: Collecting bake requests...")
        if abp.ab_udim_bake:
            for item in scene.autobake_udimlist:
                if item.Gate and not any(item.Type == queue.Type and item.Size == queue.Multiplier for queue in scene.autobake_queuelist):
                    item_new = scene.autobake_queuelist.add()
                    item_new.Type = item.Type
                    item_new.Multiplier = item.Size
                    item_new.name = f"{item_new.Type} {item_new.Multiplier:.2f} {item_new.Status} Enabled"
            self.udim_tiles = []
            for item in scene.autobake_udimtilelist:
                if item.Gate and not any(item.UDIM == tile[0] for tile in self.udim_tiles):
                    self.udim_tiles.append((item.UDIM, item.Size, item.Label))
        else:
            for item in scene.autobake_bakelist:
                if item.Gate and not any(item.Type == queue.Type and item.Size == queue.Size for queue in scene.autobake_queuelist):
                    item_new = scene.autobake_queuelist.add()
                    item_new.Type = item.Type
                    item_new.Size = item.Size
                    item_new.name = f"{item_new.Type} {item_new.Size} {item_new.Status} Enabled"
               
    # Bake Requests Report
        if len(scene.autobake_queuelist) > 0:
            if abp.ab_report_requests:
                self.report({'INFO'}, f"Auto Bake: ...{len(scene.autobake_queuelist)} bake requests are added to the queue.")
        else:
            self.report({'ERROR'}, f"Auto Bake: Could not collect any bake request...")
            return {'CANCELLED'}
        
    # Variable Set
        self.img_start_loc = {}
        self.gridscalex = math.ceil(math.sqrt(len(scene.autobake_queuelist)))
        self.scale_reset = {}
        
        global bake_status
        bake_status = 'INPROGRESS'
        
        global is_udim_bake
        is_udim_bake = abp.ab_udim_bake
        
        global next_object_bake
        next_object_bake = True
        
        global bake_results
        bake_results = {}
        
        global bake_order
        bake_order = []
        for item in scene.autobake_queuelist:
            bake_order.append(f"{item.Type} " + (f"{item.Multiplier:.2f}" if is_udim_bake else f"{item.Size}"))
        
    # Modal
        self._timer = bpy.context.window_manager.event_timer_add(.5, window=context.window)
        bpy.context.window_manager.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    

    def modal(self, context, event):
        if event.type == 'TIMER':
            scene = context.scene
            bake = scene.render.bake
            abp = scene.autobake_properties
            
            global bake_status
            global next_object_bake
            
# PHASE: Pause
            if (bake_status == 'PAUSED' or not next_object_bake) and self.phase_finished_locked and self.phase_export_locked:
                return{'PASS_THROUGH'}
            
            global bake_results
            
# PHASE: Bake
            if not self.phase_bake_locked and not bpy.app.is_job_running('OBJECT_BAKE'):
                
            # No Active Bake Item
                if not any(item.Enabled for item in scene.autobake_queuelist):
                    self.phase_bake_locked = True
                    self.phase_finished_locked = False
                    return {'PASS_THROUGH'}
                
            # Active Target Object
                if any(item.Status == 'Baking' for item in scene.autobake_objectqueuelist):
                    for item in scene.autobake_objectqueuelist:
                        if item.Status == 'Baking':
                            target_obj = item.Object
                            break
                        
                elif any(item.Enabled for item in scene.autobake_objectqueuelist):
                    for index, item in enumerate(scene.autobake_objectqueuelist):
                        if item.Enabled:
                            item.Enabled = False
                            
                            if item.Status == 'Pending':
                                item.Status = 'Baking'
                                item.Icon = 'RENDER_STILL'
                                item.name = f"{item.Object.name} {item.Status} " + ('Enabled' if item.Enabled else 'Disabled')
                                target_obj = item.Object
                                
                            # Start Report
                                if abp.ab_report_object_start:
                                    self.report({'INFO'}, f"Auto Bake: Object '{item.Object.name}' has been started baking.")

                            # Final Material
                                if abp.ab_final_material:
                                    if not abp.ab_shared_textures or all(item.Status in ['Baking', 'Pending'] for item in scene.autobake_objectqueuelist):
                                        final_mat_name = f"{target_obj.name}" if not abp.ab_shared_textures or abp.ab_prefix == '' else abp.ab_prefix
                                        self.final_material = bpy.data.materials.new(name=final_mat_name)
                                        if self.final_material.name != final_mat_name:
                                            name_switch = str(self.final_material.name)
                                            self.final_material.name = ''
                                            bpy.data.materials[final_mat_name].name = name_switch
                                            self.final_material.name = final_mat_name
                                        self.final_material.use_nodes = True
                                        
                                        if abp.ab_final_shader != 'BSDF_PRINCIPLED':
                                            for node in self.final_material.node_tree.nodes:
                                                if node.type == 'BSDF_PRINCIPLED':
                                                    final_shader = self.final_material.node_tree.nodes.new(abp.ab_final_shader)
                                                    final_shader.location = node.location
                                                    self.final_material.node_tree.links.new(final_shader.outputs[0], node.outputs[0].links[0].to_socket)
                                                    self.final_material.node_tree.nodes.remove(node)
                                                    break
                                else:
                                    self.final_material = None
                                    
                            # Move Active Bake
                                if abp.ab_move_active_bake:
                                    scene.autobake_objectqueuelist.move(index, 0)

                                break
                            
                            elif item.Status == 'Canceled':
                                item.name = f"{item.Object.name} {item.Status} " + ('Enabled' if item.Enabled else 'Disabled')
                                
                            # Store Bake Results
                                results = []
                                for item_ in scene.autobake_queuelist:
                                    if item_.Status == 'Pending':
                                        item_.Enabled = False
                                        item_.Status = 'Canceled'
                                        item_.Icon = 'CANCEL'
                                        item_.Error = ''
                                    
                                    results.append({f"{item_.Type} " + (f"{item_.Multiplier:.2f}" if is_udim_bake else f"{item_.Size}"): {'Status': item_.Status, 'Icon': item_.Icon, 'Error': item_.Error, 'Cancel': item_.Cancel}})
                                bake_results[item.Object.name] = results
                                
                            # Move Item
                                if abp.ab_move_finished_bake:
                                    scene.autobake_objectqueuelist.move(index, len(scene.autobake_objectqueuelist)-1)

                                return {'PASS_THROUGH'}
                        
                else:
                    self.phase_bake_locked = True
                    self.phase_finished_locked = False
                    
                    return {'PASS_THROUGH'}

            # Active Source Object
                if not self.selected_to_active:
                    self.source_objects = []
                    self.source_objects.append(target_obj)
                    
            # Is Object Ready
                is_object_ready = obj_bake_ready(self, context, target_obj, self.source_objects)
                
            # Not Ready
                if is_object_ready != True:
                    self.phase_bake_locked = True
                    self.phase_finished_locked = False
                    
                # Pending Items to Failed
                    for item in scene.autobake_queuelist:
                        self.update_queue_item(context, 'Pending', False, 'Failed', 'ERROR', is_object_ready)

                # Deactivating Canceled Items
                    for item in scene.autobake_queuelist:
                        self.update_queue_item(context, 'Canceled', False, 'Canceled', 'CANCEL', '')
                    
                    return {'PASS_THROUGH'}

            # Active Bake Item
                for index, item in enumerate(scene.autobake_queuelist):
                    if item.Enabled:
                        item.Enabled = False
                        if item.Status == 'Pending':
                            item.Status = 'Baking'
                            item.Icon = 'RENDER_STILL'
                            item.name = f"{item.Type} " + (f"{item.Multiplier:.2f}" if abp.ab_udim_bake else f"{item.Size}") + f" {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
                            
                            global finished_bake_count
                            finished_bake_count = len(scene.autobake_queuelist) - (sum(1 for item in scene.autobake_queuelist if item.Status == 'Pending'))
                            
                            baketype, label = self.bake_type_info[item.Type]
                            self.label = label
                            
                            self.image_scale_name = f"{item.Multiplier:.2f}" if is_udim_bake else f"{item.Size}"
                            
                            self.item_index = index
                            
                            if abp.ab_move_active_bake:
                                scene.autobake_queuelist.move(index, 0)
                                self.item_index = 0
                                item = scene.autobake_queuelist[self.item_index]
                                
                            self.phase_bake_locked = True
                            break
                        
                    # Not a valid bake item
                        elif item.Status == 'Canceled':
                            item.name = f"{item.Type} " + (f"{item.Multiplier:.2f}" if abp.ab_udim_bake else f"{item.Size}") + f" {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')

                            if abp.ab_move_finished_bake:
                                scene.autobake_queuelist.move(index, len(scene.autobake_queuelist)-1)
                                
                            return {'PASS_THROUGH'}
                        
            # Bake Item Check
                if label in ['Float', 'Color', 'Vector']:
                    pass
                        
            # Object specific
                elif label == "Color Attribute":
                    if not self.selected_to_active:
                        if (len(target_obj.data.color_attributes)) < 1:
                            if abp.ab_report_bake_error:
                                self.report({'ERROR'}, f"Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'... {target_obj.name} does not have any color attribute.")
                            self.bake_item_check_fail(context, error=f"Object does not have any color attribute!")
                            return{"PASS_THROUGH"}
                    else: # Selected to Active
                        if any((len(obj.data.color_attributes)) < 1 for obj in self.source_objects):
                            if abp.ab_report_bake_error:
                                self.report({'ERROR'}, f"Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'... All source object must have color attributes.")
                            self.bake_item_check_fail(context, error="All source object must have color attributes!")
                            return{"PASS_THROUGH"}

                elif label == "Multires":
                    if not self.selected_to_active:
                        if not any(modifier.type == 'MULTIRES' for modifier in target_obj.modifiers):
                            if abp.ab_report_bake_error:
                                self.report({'ERROR'}, f"Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'... Multires data bake requires multi-resolution object.")
                            self.bake_item_check_fail(context, error="Object must have 'Multiresolution' modifier!")
                            return{"PASS_THROUGH"}
                    else: # Selected to Active
                        if abp.ab_report_bake_error:
                            self.report({'ERROR'}, f"Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'... Can't use 'Selected to Active' for 'Multires' bakes.")
                        self.bake_item_check_fail(context, error="Can't use 'Selected to Active' for 'Multires' bakes!")
                        return{"PASS_THROUGH"}

            # Non-Object specific
                elif label == 'AO':
                    if self.selected_to_active and abp.ab_ao_local_only == 'COLLECTION':
                        if abp.ab_report_bake_error:
                            self.report({'ERROR'}, "Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'... Can't use 'Collection' for 'Local Only' with 'Selected to Active'")
                        self.bake_item_check_fail(context, error="Can't use 'Collection' for 'Local Only' with 'Selected to Active'!")
                        return{"PASS_THROUGH"}

                elif label == "Channel Packing":
                    if abp.ab_channel_pack_r == 'None' and abp.ab_channel_pack_g == 'None' and abp.ab_channel_pack_b == 'None':
                        if abp.ab_report_bake_error:
                            self.report({'ERROR'}, f"Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'... Can't bake 'Channel Packing' with all channels set to 'None'.")
                        self.bake_item_check_fail(context, error="All channels are set to 'None'!")
                        return{"PASS_THROUGH"}
                    
                elif label in ['Diffuse', 'Transmission', 'Glossy']:
                    if not (bake.use_pass_direct or bake.use_pass_indirect or bake.use_pass_color):
                        if abp.ab_report_bake_error:
                            self.report({'ERROR'}, f"Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'... Bake type requires Direct, Indirect, or Color contributions to be enabled")
                        self.bake_item_check_fail(context, error="Requires Direct, Indirect, or Color contributions!")
                        return{"PASS_THROUGH"}
                    
                elif label == "Combined":
                    if not (bake.use_pass_emit or ((bake.use_pass_indirect or bake.use_pass_direct) and (bake.use_pass_diffuse or bake.use_pass_glossy or bake.use_pass_transmission))):
                        if abp.ab_report_bake_error:
                            self.report({'ERROR'}, "Auto Bake: Skipping '{item.Type} - {self.image_scale_name}'...  Combined bake requires Emit, or a light pass with Direct or Indirect contributions enabled")
                        self.bake_item_check_fail(context, error="Requires Emit, or a light pass with Direct or Indirect contributions!")
                        return{"PASS_THROUGH"}
                                        
            # Anti-aliasing Method
                self.antialiasing_method = abp.ab_scaled_antialiasing
                    
            # Image
                if not abp.ab_shared_textures or item.Image is None:
                    
                # Prefix Name
                    self.prefix = str(target_obj.name) if abp.ab_prefix == '' or (len(scene.autobake_objectqueuelist) > 1 and not abp.ab_shared_textures) else str(abp.ab_prefix) if abp.ab_prefix not in ['""', "''"] else ''
                
                # Type Name
                    type_names = {}
                    for item_ in abp.ab_baketype_name_all.split(', '):
                        type_names[item_.split(':')[0]] = item_.split(':')[1]
                    self.type_name = type_names[item.Type]
                
                # Image Name
                    name_structure = {"prefix": self.prefix, "bridge": abp.ab_bridge, "suffix": abp.ab_suffix, "type": self.type_name, "size": self.image_scale_name, "udim": '<UDIM>', "uvtile": '<UVTILE>'}
                    texture_name = abp.ab_name_structure_udim if is_udim_bake else abp.ab_name_structure
                    texture_name = texture_name.lower().format(**name_structure)
                    texture_name = re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', texture_name)

                # New Image
                    if not is_udim_bake:
                        size_final = item.Size
                        if self.antialiasing_method == 'UPSCALED': 
                            size_final = min(int(item.Size * (abp.ab_antialiasing_upscaled/100)), 65536)
                        img = bpy.data.images.new(name=texture_name, width=size_final, height=size_final, alpha=False, float_buffer=abp.ab_floatbuffer, is_data=False, tiled=is_udim_bake)
                        self.scale_reset[img] = [item.Size]
                        
                # New UDIM Image
                    else:
                        if any(udim_item[0] == 1001 for udim_item in self.udim_tiles):
                            for tile in self.udim_tiles:
                                if tile[0] == 1001:
                                    size_adjusted = min(int(tile[1] * item.Multiplier), 65536)
                                    size_final = size_adjusted
                                    if self.antialiasing_method == 'UPSCALED':
                                        size_final = min(int(size_adjusted * (abp.ab_antialiasing_upscaled/100)), 65536)
                                    img = bpy.data.images.new(name=texture_name, width=size_final, height=size_final, tiled=True, alpha=False, float_buffer=abp.ab_floatbuffer)
                                    self.scale_reset[img] = [[tile[0], int(size_adjusted)]]
                                    break
                        else:
                            img = bpy.data.images.new(name=texture_name, width=1, height=1, tiled=True, alpha=False, float_buffer=abp.ab_floatbuffer)
                            self.scale_reset[img] = [[1001, 1]]

                    # UDIM Tiles
                        for udim_item in self.udim_tiles:
                            if udim_item[0] != 1001:
                                size_adjusted = min(int(udim_item[1] * item.Multiplier), 65536)
                                size_final = size_adjusted
                                if self.antialiasing_method == 'UPSCALED':
                                    size_final = min(int(size_adjusted * (abp.ab_antialiasing_upscaled/100)), 65536)
                                        
                                with context.temp_override(edit_image=img):
                                    bpy.ops.image.tile_add(number=udim_item[0], width=size_final, height=size_final, alpha=False, float=abp.ab_floatbuffer, fill=True)
                                    self.scale_reset[img].append([udim_item[0], int(size_adjusted)])

                        if not any(udim_item[0] == 1001 for udim_item in self.udim_tiles):
                            img.tiles.remove(img.tiles[0])
                            self.scale_reset[img].remove([1001, 1])

                    # Tile label
                        if abp.ab_udim_label:
                            for tile in self.udim_tiles:
                                if tile[2] != '#Unknown':
                                    for img_tile in img.tiles:
                                        if img_tile.number == tile[0]:
                                            img_tile.label = tile[2]
                                            
                # Color Space
                    if item.Type in ["Metallic", "Roughness", "IOR", "Alpha", "Subsurface Weight", "Subsurface Scale", "Subsurface IOR", "Subsurface Anisotropy", "Specular IOR Level", "Anisotropic", "Anisotropic Rotation", "Transmission Weight", "Coat Weight", "Coat Roughness", "Coat IOR", "Sheen Weight", "Sheen Roughness", "Emission Strength", "Displacement", "Roughness ", "Glossy", "Shadow", "Ambient Occlusion", "Subsurface", "Specular", "Sheen", "Clearcoat", "Clearcoat Roughness", "Transmission Roughness", "Channel Packing"]:
                        img.colorspace_settings.name = abp.ab_color_space_float
                    elif item.Type in ["Base Color", "Specular Tint", "Coat Tint", "Sheen Tint", "Emission Color", "Color Attribute", "Combined", "Diffuse", "Transmission", "Environment", "Emit", "Subsurface Color", "Emission"]:
                        img.colorspace_settings.name = abp.ab_color_space_color
                    elif item.Type in ["Normal", "Subsurface Radius", "Tangent", "Coat Normal", "Normals", "Normal ", "Position", "UV", "Displacement ", "Clearcoat Normal"]:
                        img.colorspace_settings.name = abp.ab_color_space_vector

                # Force Name
                    if img.name != texture_name:
                        name_switch = str(img.name)
                        img.name = ''
                        bpy.data.images[texture_name].name = name_switch
                        img.name = texture_name
                    
                # Texture Image
                    self.img = img

                # Fake User
                    self.img.use_fake_user = abp.ab_textures_fakeuser
                    
                # Shared Texture
                    if abp.ab_shared_textures:
                        item.Image = self.img
                        item.Prefix = self.prefix
                        item.Type_Name = self.type_name
                    
            # Shared Data
                else:
                    self.img = item.Image
                    self.prefix = item.Prefix
                    self.type_name = item.Type_Name

        # Shader Alerts
                frames = {}

        # Node Bake Setup: Source
                global delete_nodes
                global reconnect_nodes

                if label in ["Float", "Color", "Vector", "Channel Packing"]:
                    for obj in self.source_objects:
                        for slot in obj.material_slots:
                            if slot.material is not None and slot.material.use_nodes:
                                shader_nodes = []
                                
                                node_trees = []
                                node_trees.append(slot.material.node_tree)

                            # Searching: Node Trees
                                for tree in node_trees:
                                    branches = []
                                    
                                # Searching: Branch Start
                                    for node in tree.nodes:
                                        if node.type in ['OUTPUT_MATERIAL', 'GROUP_OUTPUT'] and node.is_active_output:
                                        # Material Output
                                            if node.type == 'OUTPUT_MATERIAL':
                                                
                                            # Material Output: Detach Displacement (Material Output)
                                                if node.inputs[2].is_linked:
                                                    reconnect_nodes.append((tree, node.inputs[2].links[0].from_socket, node.inputs[2]))
                                                    tree.links.remove(node.inputs[2].links[0])
                                            
                                            # Material Output: Add Branch
                                                if node.inputs[0].is_linked:
                                                    if node.inputs[0].links[0].from_node not in branches:
                                                        branches.append(node.inputs[0].links[0].from_node)
                                                    
                                        # Group Output
                                            elif node.type == 'GROUP_OUTPUT':
                                                
                                            # Group Output: Add Branch
                                                for input in node.inputs:
                                                    if input.is_linked:
                                                        if input.links[0].from_node not in branches:
                                                            branches.append(input.links[0].from_node)
                                            break
                                        
                                # Branching
                                    for branch in branches:
                                        
                                    # Shader Found
                                        if branch.type in ['BSDF_PRINCIPLED', 'EMISSION', 'BSDF_TRANSLUCENT', 'BSDF_TRANSPARENT', 'BSDF_REFRACTION', 'BSDF_DIFFUSE', 'BSDF_GLASS', 'BSDF_SHEEN', 'BSDF_HAIR', 'BSDF_TOON', 'BSDF_GLOSSY', 'VOLUME_ABSORPTION', 'VOLUME_SCATTER', 'SUBSURFACE_SCATTERING', 'PRINCIPLED_VOLUME', 'BSDF_HAIR_PRINCIPLED', 'BSDF_VELVET', 'BSDF_ANISOTROPIC', 'EEVEE_SPECULAR']:
                                            shader_nodes.append((branch, tree))
                                            
                                    # New Tree & Branch
                                        elif branch.type == 'GROUP':
                                            for input in branch.inputs:
                                                if input.is_linked:
                                                    if input.links[0].from_node not in branches:
                                                        branches.append(input.links[0].from_node)
                                                        
                                            if branch.node_tree not in node_trees:
                                                node_trees.append(branch.node_tree)
                                                    
                                     # New Branch   
                                        else:
                                            for input in branch.inputs:
                                                if input.is_linked:
                                                    if input.links[0].from_node not in branches:
                                                        branches.append(input.links[0].from_node)
                                
                            # Source BSDF
                                for shader_node_ in shader_nodes:
                                    shader_node = shader_node_[0]
                                    nodetree = shader_node_[1]
                         
                                # Save Output Links
                                    for link in shader_node.outputs[0].links:
                                        reconnect_nodes.append((nodetree, shader_node.outputs[0], link.to_socket))
                                        
                                # Channel Packing
                                    if label == "Channel Packing":
                                        channel_packing_node = nodetree.nodes.new('ShaderNodeCombineColor')
                                        channel_packing_node.location = shader_node.location + mathutils.Vector((0, 160))
                                        
                                        for index, channel in enumerate([abp.ab_channel_pack_r, abp.ab_channel_pack_g, abp.ab_channel_pack_b]):
                                            if channel in self.bake_type_info:
                                                
                                                if channel == 'Ambient Occlusion':
                                                    ao_node = nodetree.nodes.new('ShaderNodeAmbientOcclusion')
                                                    delete_nodes.append((nodetree, ao_node))
                                                    ao_node.location = channel_packing_node.location + mathutils.Vector((-200, 150-index*150))
                                                    
                                                    ao_node.samples = abp.ab_ao_sample if abp.ab_ao_sample_use else 0
                                                    ao_node.inside = abp.ab_ao_inside
                                                    ao_node.only_local = abp.ab_ao_only_local
                                                    ao_node.inputs[1].default_value = abp.ab_ao_distance

                                                    nodetree.links.new(ao_node.outputs[1], channel_packing_node.inputs[index])
                                        
                                                elif channel == "Pointiness":
                                                    geometry_node = nodetree.nodes.new('ShaderNodeNewGeometry')
                                                    delete_nodes.append((nodetree, geometry_node))
                                                    geometry_node.location = channel_packing_node.location + mathutils.Vector((-400, 150-index*150))

                                                    contrast_node = nodetree.nodes.new('ShaderNodeBrightContrast')
                                                    delete_nodes.append((nodetree, contrast_node))
                                                    contrast_node.location = channel_packing_node.location + mathutils.Vector((-200, 150-index*150))
                                                    
                                                    contrast_node.inputs[1].default_value = abp.ab_pointiness_brightness
                                                    contrast_node.inputs[2].default_value = abp.ab_pointiness_contrast
                                                    
                                                    nodetree.links.new(geometry_node.outputs[7], contrast_node.inputs[0])
                                                    nodetree.links.new(contrast_node.outputs[0], channel_packing_node.inputs[index])
                                        
                                                else:
                                                    aliases = [channel,]    
                                                    if channel in type_aliases:
                                                        aliases.extend(type_aliases[channel])
                                                         
                                                    socketindex_cp = None
                                                    for socket_index, input_socket in enumerate(shader_node.inputs):
                                                        if input_socket.name in aliases:
                                                            socketindex_cp = socket_index
                                                            break
                                                    
                                                    if socketindex_cp is not None:
                                                        if shader_node.inputs[socketindex_cp].is_linked:
                                                            nodetree.links.new(shader_node.inputs[socketindex_cp].links[0].from_socket, channel_packing_node.inputs[index])
                                                        else:
                                                            channel_packing_node.inputs[0].default_value = shader_node.inputs[socketindex_cp].default_value
                                                
                                    # Linking & Delete     
                                        for link in shader_node.outputs[0].links:
                                            nodetree.links.new(channel_packing_node.outputs[0], link.to_socket)
                                        delete_nodes.append((nodetree, channel_packing_node))
                                        
                                    else:
                                        
                                    # Aliases
                                        aliases = [item.Type,]    
                                        if item.Type in type_aliases:
                                            aliases.extend(type_aliases[item.Type])
                                             
                                    # Socket Index
                                        socketindex = None
                                        for socket_index, input_socket in enumerate(shader_node.inputs):
                                            if input_socket.name in aliases:
                                                socketindex = socket_index
                                                break
                                        
                                        if socketindex == None:
                                            for link in shader_node.outputs[0].links:
                                                nodetree.links.remove(link)
                                        
                                        else:
                                            
                                            if label in ["Float", "Color"]:
                                                if shader_node.inputs[socketindex].is_linked:
                                                    for link in shader_node.outputs[0].links:
                                                        nodetree.links.new(shader_node.inputs[socketindex].links[0].from_socket, link.to_socket)
                                                else:
                                                    if label == "Float":
                                                        value_node = nodetree.nodes.new('ShaderNodeValue')
                                                        value_node.location = shader_node.location + mathutils.Vector((0, 90))
                                                        value_node.outputs[0].default_value = shader_node.inputs[socketindex].default_value
                                                        
                                                        for link in shader_node.outputs[0].links:
                                                            nodetree.links.new(value_node.outputs[0], link.to_socket)
                                                            
                                                        delete_nodes.append((nodetree, value_node))
                                                        
                                                    elif label == "Color":
                                                        rgb_node = nodetree.nodes.new('ShaderNodeRGB')
                                                        rgb_node.location = shader_node.location + mathutils.Vector((0, 190))
                                                        rgb_node.outputs[0].default_value = shader_node.inputs[socketindex].default_value
                                                        
                                                        for link in shader_node.outputs[0].links:
                                                            nodetree.links.new(rgb_node.outputs[0], link.to_socket)
                                                            
                                                        delete_nodes.append((nodetree, rgb_node))

                                            elif label == "Vector":
                                                diffuse_node = nodetree.nodes.new('ShaderNodeBsdfDiffuse')
                                                diffuse_node.location = shader_node.location + mathutils.Vector((0, 130))

                                                if shader_node.inputs[socketindex].is_linked:
                                                    nodetree.links.new(shader_node.inputs[socketindex].links[0].from_socket, diffuse_node.inputs[2])

                                                for link in shader_node.outputs[0].links:
                                                    nodetree.links.new(diffuse_node.outputs[0], link.to_socket)
                                                    
                                                delete_nodes.append((nodetree, diffuse_node))
                                                 
                            # Node Alert
                                if abp.ab_nodealert:
                                    tree = slot.material.node_tree
                                    frame = tree.nodes.new('NodeFrame')
                                    delete_nodes.append((slot.material.node_tree, frame))
                                    frames[slot.material] = frame
                                    frame.label = "Please wait until the bake is over..."
                                    frame.use_custom_color = True
                                    frame.color = (1, .23, .23)
                                    frame.label_size = 30
                                    
                                    for node in tree.nodes:
                                        node.parent = frame

                elif label == "Displacement":
                    for obj in self.source_objects:
                        for slot in obj.material_slots:
                            if slot.material is not None and slot.material.use_nodes:
                                
                            # Displacement
                                if not abp.ab_displacement_source:
                                    tree = slot.material.node_tree
                                    for node in tree.nodes:
                                        if node.type == 'OUTPUT_MATERIAL' and node.is_active_output:
                                            if node.inputs[0].is_linked:
                                                reconnect_nodes.append((tree, node.inputs[0].links[0].from_socket, node.inputs[0]))
                                                tree.links.remove(node.inputs[0].links[0])
                                            if node.inputs[2].is_linked:
                                                tree.links.new(node.inputs[2].links[0].from_socket, node.inputs[0])
                                            break
                                    
                            # Source Only
                                else:
                                    displacements = []
                                    node_trees = []
                                    node_trees.append(slot.material.node_tree)

                                # Searching: Node Trees
                                    for tree in node_trees:
                                        branches = []
                                        
                                    # Searching: Branch Start
                                        for node in tree.nodes:
                                            if node.type in ['OUTPUT_MATERIAL', 'GROUP_OUTPUT'] and node.is_active_output:
                                                
                                            # Material Output
                                                if node.type == 'OUTPUT_MATERIAL':
                                                    
                                                # Material Output: Detach Surface (Material Output)
                                                    if node.inputs[0].is_linked:
                                                        reconnect_nodes.append((tree, node.inputs[0].links[0].from_socket, node.inputs[0]))
                                                        tree.links.remove(node.inputs[0].links[0])
                                                
                                                # Material Output: Add Branch
                                                    if node.inputs[2].is_linked:
                                                        if node.inputs[2].links[0].from_node not in branches:
                                                            branches.append(node.inputs[2].links[0].from_node)
                                                        tree.links.new(node.inputs[2].links[0].from_socket, node.inputs[0])
                                                        
                                            # Group Output
                                                elif node.type == 'GROUP_OUTPUT':
                                                    
                                                # Group Output: Add Branch
                                                    for input in node.inputs:
                                                        if input.is_linked:
                                                            if input.links[0].from_node not in branches:
                                                                branches.append(input.links[0].from_node)
                                                break
                                            
                                    # Branching
                                        for branch in branches:
                                            
                                        # Match
                                            if branch.type in ['DISPLACEMENT', 'VECTOR_DISPLACEMENT']:
                                                displacements.append((branch, tree))
                                                
                                        # New Tree & Branch
                                            elif branch.type == 'GROUP':
                                                for input in branch.inputs:
                                                    if input.is_linked:
                                                        if input.from_node not in branches:
                                                            branches.append(input.from_node)
                                                if branch.node_tree not in node_trees:
                                                    node_trees.append(branch.node_tree)
                                                        
                                         # New Branch   
                                            else:
                                                for input in branch.inputs:
                                                    if input.is_linked:
                                                        if input.links[0].from_node not in branches:
                                                            branches.append(input.links[0].from_node)
                                            
                                # Source Displacement
                                    for displacement in displacements:
                                        displacement_node = displacement[0]
                                        nodetree = displacement[1]
                                        
                                    # Save Linking
                                        for link in displacement_node.outputs[0].links:
                                            reconnect_nodes.append((nodetree, displacement_node.outputs[0], link.to_socket))
                                            
                                        # Source Linking
                                            if displacement_node.inputs[0].is_linked:
                                                nodetree.links.new(displacement_node.inputs[0].links[0].from_socket, link.to_socket)
                                                
                                        # Remove Linking
                                            else:
                                                nodetree.links.remove(link)
                              
                            # Node Alert
                                if abp.ab_nodealert:
                                    tree = slot.material.node_tree
                                    frame = tree.nodes.new('NodeFrame')
                                    delete_nodes.append((slot.material.node_tree, frame))
                                    frames[slot.material] = frame
                                    frame.label = "Please wait until the bake is over..."
                                    frame.use_custom_color = True
                                    frame.color = (1, .23, .23)
                                    frame.label_size = 30
                                    
                                    for node in tree.nodes:
                                        node.parent = frame

                elif label in ["UV", "Color Attribute", "AO", "Ambient Occlusion", "Pointiness"]:
                    for obj in self.source_objects:
                        for slot in obj.material_slots:
                            if slot.material is not None and slot.material.use_nodes:
                                tree = slot.material.node_tree
                                for node in tree.nodes:
                                    if node.type == 'OUTPUT_MATERIAL' and node.is_active_output:
                                        if node.inputs[0].is_linked:
                                            reconnect_nodes.append((tree, node.inputs[0].links[0].from_socket, node.inputs[0]))
                                        
                                        if label == "AO":
                                            if not abp.ab_ao_use_normal:
                                                tree.links.remove(node.inputs[0].links[0])
                                        
                                        elif label == 'Ambient Occlusion':
                                            ao_node = tree.nodes.new('ShaderNodeAmbientOcclusion')
                                            delete_nodes.append((tree, ao_node))
                                            ao_node.location = node.location + mathutils.Vector((-200, 0))
                                            
                                            ao_node.samples = abp.ab_ao_sample if abp.ab_ao_sample_use else 0
                                            ao_node.inside = abp.ab_ao_inside
                                            ao_node.only_local = abp.ab_ao_only_local
                                            ao_node.inputs[1].default_value = abp.ab_ao_distance

                                            tree.links.new(ao_node.outputs[1], node.inputs[0])
                                            
                                        elif label == "Pointiness":
                                            geometry_node = tree.nodes.new('ShaderNodeNewGeometry')
                                            delete_nodes.append((tree, geometry_node))
                                            geometry_node.location = node.location + mathutils.Vector((-400, 0))

                                            contrast_node = tree.nodes.new('ShaderNodeBrightContrast')
                                            delete_nodes.append((tree, contrast_node))
                                            contrast_node.location = node.location + mathutils.Vector((-200, 0))
                                            
                                            contrast_node.inputs[1].default_value = abp.ab_pointiness_brightness
                                            contrast_node.inputs[2].default_value = abp.ab_pointiness_contrast
                                            
                                            tree.links.new(geometry_node.outputs[7], contrast_node.inputs[0])
                                            tree.links.new(contrast_node.outputs[0], node.inputs[0])
                                            
                                        elif label == 'UV':
                                            uv_node = tree.nodes.new('ShaderNodeUVMap')
                                            delete_nodes.append((tree, uv_node))
                                            uv_node.location = node.location + mathutils.Vector((-200, 0))
                                            
                                            if len(obj.data.uv_layers) > 0:
                                                if abp.ab_uv_target in obj.data.uv_layers:
                                                    for index, uv in enumerate(obj.data.uv_layers):
                                                        if abp.ab_uv_target == uv.name:
                                                            obj.data.uv_layers.active_index = index
                                                else:
                                                    for index, uv in enumerate(obj.data.uv_layers):
                                                        if uv.active_render:
                                                            obj.data.uv_layers.active_index = index
                                                            
                                            tree.links.new(uv_node.outputs[0], node.inputs[0])
                                                         
                                        elif label == 'Color Attribute':
                                            attribute_node = tree.nodes.new('ShaderNodeVertexColor')
                                            delete_nodes.append((tree, attribute_node))
                                            attribute_node.location = node.location + mathutils.Vector((-200, 0))
                                            
                                            if len(obj.data.attributes) > 0:
                                                if abp.ab_attribute_target in obj.data.color_attributes:
                                                    attribute_node.layer_name = abp.ab_attribute_target
                                                else:
                                                    attribute_node.layer_name = obj.data.attributes[obj.data.attributes.render_color_index].name
                                                    
                                            tree.links.new(attribute_node.outputs[0], node.inputs[0])
                                            
                                        break

        # Node Bake Setup: Target
                target_materials = []
                for slot in target_obj.material_slots:
                    if slot.material is not None and slot.material.use_nodes:
                        target_materials.append(slot.material)
                
                if self.final_material is not None and (not abp.ab_shared_textures or all(item.Status in ['Baking', 'Pending'] for item in scene.autobake_objectqueuelist)):
                    target_materials.append(self.final_material)

            # Prepare Materials
                for mat in target_materials:

                # Deselect Nodes
                    for node in mat.node_tree.nodes:
                        node.select = False

                # Start Location
                    if mat in self.img_start_loc:
                        startloc = self.img_start_loc[mat]
                    else:
                        startloc = mathutils.Vector((0, 0))
                        for node in mat.node_tree.nodes:
                            if node.type == 'OUTPUT_MATERIAL' and node.is_active_output:
                                self.img_start_loc[mat] = mathutils.Vector((node.location.x, node.location.y - 160))
                                startloc = self.img_start_loc[mat]
                                break
                            
                # Image Texture
                    nodetree = mat.node_tree
                    img_node = nodetree.nodes.new('ShaderNodeTexImage')
                            
                # Node Label
                    img_node.label = item.Type if abp.ab_node_label == 'Type' else self.type_name if abp.ab_node_label == 'Name' else ''
                            
                # Remove Nodes
                    if abp.ab_remove_imagetextures:
                        if mat != self.final_material:
                            delete_nodes.append((nodetree, img_node))
                        
                # Update Nodes
                    img_node.image = self.img
                    nodetree.nodes.active = img_node
                    img_node.select = True
                
                # Image Shader Alert 
                    if abp.ab_nodealert:
                        if mat in frames:
                            img_node.parent = frames[mat]
                        else:
                            tree = mat.node_tree
                            frame = tree.nodes.new('NodeFrame')
                            delete_nodes.append((mat.node_tree, frame))
                            frames[mat] = frame
                            frame.label = "Please wait until the bake is over..."
                            frame.use_custom_color = True
                            frame.color = (1, .23, .23)
                            frame.label_size = 30
                            
                            for node in tree.nodes:
                                node.parent = frame
                            
                # Node location
                    if abp.ab_node_tiling == 'OFF':
                        img_node.location.x = startloc.x
                        img_node.location.y = startloc.y

                    if not abp.ab_remove_imagetextures or mat == self.final_material:
                        if abp.ab_node_tiling == 'GRID':
                            queue_place = sum(item.Status in ['Baked', 'Exported'] for item in scene.autobake_queuelist)

                            grid_x_new = math.ceil(math.sqrt(len(scene.autobake_queuelist) - (sum(1 for item in scene.autobake_queuelist if item.Status == 'Canceled' and not item.Enabled))))
                            self.gridscalex = grid_x_new if queue_place < grid_x_new+1 else self.gridscalex
                            img_node.location.x = startloc.x + 250 * ((queue_place)-(int((queue_place)/self.gridscalex))*self.gridscalex)
                            img_node.location.y = startloc.y + (280 if abp.ab_pack_texture else 255) - ((280 if abp.ab_pack_texture else 255) * ((math.ceil(((queue_place)+1)/self.gridscalex))))
                             
                        elif abp.ab_node_tiling == 'SINGLEROW':
                            img_node.location.x = startloc.x + 250 * (sum(1 for item in scene.autobake_queuelist if item.Status in ['Baked', 'Exported']))
                            img_node.location.y = startloc.y
                            
                        elif abp.ab_node_tiling == 'ROWBYTYPE':
                            baking_bake_type = next((item.Type for item in scene.autobake_queuelist if item.Status == 'Baking'), None)
                            img_node.location.x = startloc.x + 250 * (sum(1 for item in scene.autobake_queuelist if item.Type == baking_bake_type and item.Status in ['Baked', 'Exported']))

                            if baking_bake_type not in self.node_tiling:
                                self.node_tiling.append(baking_bake_type)
                            img_node.location.y = startloc.y - (280 if abp.ab_pack_texture else 255) * self.node_tiling.index(baking_bake_type)

                        elif abp.ab_node_tiling == 'ROWBYTYPECOMBINED':
                            baking_bake_type = next((item.Type for item in scene.autobake_queuelist if item.Status == 'Baking'), None)
                            img_node.location.x = startloc.x + 250 * (sum(1 for item in scene.autobake_queuelist if item.Type == baking_bake_type and item.Status in ['Baked', 'Exported']))
                            
                            if sum(1 for item in scene.autobake_queuelist if item.Type == baking_bake_type) == 1:
                                baking_bake_type = 'Combined'
                                img_node.location.x = startloc.x + 250 * (sum(1 for Item in scene.autobake_queuelist if sum(1 for item in scene.autobake_queuelist if item.Type == Item.Type) == 1 and Item.Status in ['Baked', 'Exported']))
                            
                            if baking_bake_type not in self.node_tiling:
                                self.node_tiling.append(baking_bake_type)                             
                            img_node.location.y = startloc.y - (280 if abp.ab_pack_texture else 255) * self.node_tiling.index(baking_bake_type)
                    
            # Disable Objects Render
                if label == "AO" and abp.ab_ao_local_only != 'FALSE':
                    for object in scene.objects:
                        self.render_disabled[object] = (object.hide_render)
                        
                        if abp.ab_ao_local_only == 'SELECTED':
                            object.hide_render = (object != target_obj) if (not self.selected_to_active) else (object not in self.source_objects and object != target_obj)

                        elif abp.ab_ao_local_only == 'COLLECTION':
                            object.hide_render = object.users_collection[0] != target_obj.users_collection[0]
                        
            # Material Index
                if not self.selected_to_active:
                    target_obj.active_material_index = 0
        
            # Render Engine
                scene.render.engine = 'CYCLES'
                
            # Margin
                self.margin_original = scene.render.bake.margin
                if abp.ab_adaptive_margin:
                    scene.render.bake.margin = int(scene.render.bake.margin * ((self.img.tiles[0].size[0] if is_udim_bake else self.img.size[0]) / 1024))
                
            # Sampling
                cycles = scene.cycles
                self.sampling = [cycles.use_adaptive_sampling, cycles.adaptive_threshold, cycles.samples, cycles.adaptive_min_samples, cycles.time_limit, cycles.use_denoising, cycles.denoiser, cycles.denoising_input_passes, cycles.denoising_prefilter]
     
                if not abp.ab_sampling_use_render:
                    pick_low_sample = True
                    
                    if abp.ab_auto_pick_sampling and (item.Type in ['Combined', 'Ambient Occlusion ', 'Glossy', 'Diffuse', 'Transmission', 'Shadow', 'Environment'] or (item.Type == 'Ambient Occlusion' and not abp.ab_ao_sample_use)):
                        pick_low_sample = False
                                                       
               # Set Sample
                    cycles.use_adaptive_sampling = abp.ab_sampling_low_adaptive if pick_low_sample else abp.ab_sampling_high_adaptive
                    cycles.adaptive_threshold = abp.ab_sampling_low_noise_threshold if pick_low_sample else abp.ab_sampling_high_noise_threshold
                    cycles.samples = abp.ab_sampling_low_max if pick_low_sample else abp.ab_sampling_high_max
                    cycles.adaptive_min_samples = abp.ab_sampling_low_min if pick_low_sample else abp.ab_sampling_high_min
                    cycles.time_limit = abp.ab_sampling_low_time_limit if pick_low_sample else abp.ab_sampling_high_time_limit
                    cycles.use_denoising = abp.ab_sampling_low_denoise if pick_low_sample else abp.ab_sampling_high_denoise
                    cycles.denoiser = abp.ab_sampling_low_denoiser if pick_low_sample else abp.ab_sampling_high_denoiser
                    cycles.denoising_input_passes = abp.ab_sampling_low_passes if pick_low_sample else abp.ab_sampling_high_passes
                    cycles.denoising_prefilter = abp.ab_sampling_low_prefilter if pick_low_sample else abp.ab_sampling_high_prefilter

            # Multires Bake 
                if label == "Multires":
                    
                    if abp.ab_multires_level != -1:
                        for modifier in target_obj.modifiers:
                            if modifier.type == 'MULTIRES':
                                multires_modifier = modifier
                                multires_level = int(modifier.levels)
                                modifier.levels = abp.ab_multires_level
                                break
                    
                    scene.render.bake_type = baketype
                    scene.render.use_bake_clear = False
                    scene.render.bake_margin = bake.margin
                    scene.render.bake_margin_type = bake.margin_type
                    
                # Bake Handler
                    bpy.app.timers.register(self.ab_bake_complete_multires)

                # Bake Start
                    with context.temp_override(selected_editable_objects=self.source_objects):
                        bpy.ops.object.bake_image('INVOKE_DEFAULT')
                    
                # Reset Viewport Level
                    if abp.ab_multires_level != -1:
                        modifier.levels = multires_level
                    
            # Diffuse Bake
                else:
                    
                # Bake Handlers
                    bpy.app.handlers.object_bake_complete.append(self.ab_bake_complete)
                    bpy.app.handlers.object_bake_cancel.append(self.ab_bake_cancel)
                    
                # Bake Start
                    with context.temp_override(active_object=target_obj, selected_objects=self.source_objects):
                        bpy.ops.object.bake('INVOKE_DEFAULT',
                            type = baketype,
                            pass_filter = bake.pass_filter,
                            margin = bake.margin,
                            margin_type = bake.margin_type,
                            use_selected_to_active = self.selected_to_active,
                            max_ray_distance = bake.max_ray_distance,
                            cage_extrusion = bake.cage_extrusion,
                            cage_object = bake.cage_object.name if self.selected_to_active and bake.use_cage else '',
                            normal_space = bake.normal_space,
                            normal_r = bake.normal_r,
                            normal_g = bake.normal_g,
                            normal_b = bake.normal_b,
                            target = "IMAGE_TEXTURES",
                            use_clear = False,
                            use_cage = bake.use_cage,
                            use_split_materials = False,
                            use_automatic_name = False,
                            uv_layer = '')
                            
                if abp.ab_report_bake_start:
                    self.report({'INFO'}, f"Auto Bake: Texture '{self.img.name}' is started baking.")
                
                return {'PASS_THROUGH'}
    
# PHASE: Export
            if not self.phase_export_locked and not bpy.app.is_job_running('OBJECT_BAKE'):
                self.phase_export_locked = True
                
            # Update Item
                item = scene.autobake_queuelist[self.item_index]
                item.Status = 'Baked'
                item.name = f"{item.Type} {item.Size} {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
                item.Icon = 'CHECKMARK'
                
            # Restore Disabled Renders 
                for obj in scene.objects:
                    if obj in self.render_disabled:
                        obj.hide_render = self.render_disabled[obj]
                self.render_disabled = {}
                        
            # Remove Timers
                if bpy.app.timers.is_registered(restore_nodes):
                    bpy.app.timers.unregister(restore_nodes)
                
            # Successful Bake
                if not self.bake_canceled:
                    
                # Anti Aliasing
                    if not abp.ab_shared_textures or not any(item.Status == 'Pending' for item in scene.autobake_objectqueuelist):
                        if self.antialiasing_method == 'UPSCALED':
                            if not is_udim_bake:
                                self.img.scale(self.scale_reset[self.img][0], self.scale_reset[self.img][0])
                            else:    
                                for index, tile in enumerate(self.img.tiles):
                                    self.img.tiles.active_index = index
                                    for tile_scale in self.scale_reset[self.img]:
                                        if tile_scale[0] == tile.number:
                                            with context.temp_override(edit_image=self.img):
                                                bpy.ops.image.resize(size=(tile_scale[1], tile_scale[1]))
                                            break
                        elif self.antialiasing_method == 'DOWNSCALED':
                            if not is_udim_bake:
                                for scale in range(abp.ab_antialiasing_repeat):
                                    self.img.scale(width=int(self.img.size[0] * (abp.ab_antialiasing_downscaled/100)), height=int(self.img.size[0] * (abp.ab_antialiasing_downscaled/100)))
                                    self.img.scale(self.scale_reset[self.img][0], self.scale_reset[self.img][0])
                            else:
                                for scale in range(abp.ab_antialiasing_repeat):
                                    for index, tile in enumerate(self.img.tiles):
                                        self.img.tiles.active_index = index
                                        for tile_scale in self.scale_reset[self.img]:
                                            if tile_scale[0] == tile.number:
                                                with context.temp_override(edit_image=self.img):
                                                    bpy.ops.image.resize(size=(int(tile.size[0] * (abp.ab_antialiasing_downscaled/100)), int(tile.size[0] * (abp.ab_antialiasing_downscaled/100))))
                                                    bpy.ops.image.resize(size=(tile_scale[1], tile_scale[1]))
                                                break

                # Connect Texture
                    if abp.ab_apply_textures != "False" and self.final_material is not None and (not abp.ab_shared_textures or all(item.Status in ['Baking', 'Pending'] for item in scene.autobake_objectqueuelist)):
                        for node in self.final_material.node_tree.nodes:
                            if node.type == 'OUTPUT_MATERIAL' and node.is_active_output and node.inputs[0].is_linked:
                                target_shader = node.inputs[0].links[0].from_node
                                
                                for index, input in enumerate(target_shader.inputs):
                                    item_aliases = [item.Type,]
                                    if item.Type in type_aliases:
                                        item_aliases.extend(type_aliases[item.Type])
                                
                                    if input.name in item_aliases:
                                        if input.is_linked:
                                            
                                            if abp.ab_apply_textures == 'Highest':
                                                if input.links[0].from_node.type == 'TEX_IMAGE' and (input.links[0].from_node.image.size[0] * input.links[0].from_node.image.size[1] < self.img.size[0] * self.img.size[1]):
                                                    input.links[0].from_node.image = self.img
                                                    
                                            elif abp.ab_apply_textures == 'Lowest':
                                                if input.links[0].from_node.type == 'TEX_IMAGE' and (input.links[0].from_node.image.size[0] * input.links[0].from_node.image.size[1] > self.img.size[0] * self.img.size[1]):
                                                    input.links[0].from_node.image = self.img
                                                
                                            elif abp.ab_apply_textures == 'First':
                                                pass
                                                
                                            elif abp.ab_apply_textures == 'Last':
                                                input.links[0].from_node.image = self.img
                                        
                                        else:
                                            img_node = self.final_material.node_tree.nodes.new('ShaderNodeTexImage')
                                            img_node.label = item.Type if abp.ab_node_label == 'Type' else self.type_name if abp.ab_node_label == 'Name' else ''
                                            img_node.image = self.img
                                            img_node.location = mathutils.Vector((target_shader.location.x - 400, target_shader.location.y))
                                            self.final_material.node_tree.links.new(img_node.outputs[0], target_shader.inputs[index])
                                        
                                        break
                                break
                            
                    if not abp.ab_shared_textures or not any(item.Status == 'Pending' for item in scene.autobake_objectqueuelist):
                        
                    # Pack Image
                        if abp.ab_pack_texture:
                            self.img.pack()

                    # Export Name
                        export_name_structure = {"prefix": self.prefix, "bridge": abp.ab_bridge, "suffix": abp.ab_suffix, "type": self.type_name, "size": self.image_scale_name, "udim": '<UDIM>', "uvtile": '<UVTILE>'}
                        export_name_structure_to_use = abp.ab_name_structure_udim_export if is_udim_bake else abp.ab_name_structure
                        export_name = export_name_structure_to_use.lower().format(**export_name_structure)
                        
                    # Export
                        if abp.ab_texture_export:
                            export_texture(self, context, self.img, export_name, self.type_name, self.label, self.prefix)
                                
                        # Update Item
                            item = scene.autobake_queuelist[self.item_index]
                            item.Status = 'Exported'
                            item.name = f"{item.Type} {item.Size} {item.Status} " + ('Enabled' if item.Enabled else 'Disabled')
                            item.Icon = 'EXPORT'
                            
                    # Export Later
                        else:
                            export_img = scene.autobake_imageexport.add()
                            export_img.name = export_name
                            export_img.Name = export_name
                            export_img.Image = self.img
                            export_img.Type = self.type_name
                            export_img.Label = self.label
                            export_img.Prefix = self.prefix

                # Move Item   
                    if abp.ab_move_finished_bake:
                        scene.autobake_queuelist.move(self.item_index, len(scene.autobake_queuelist)-1)

                self.phase_finished_locked = False

# PHASE: Finish
            elif not self.phase_finished_locked and not bpy.app.is_job_running('OBJECT_BAKE'):
                self.phase_finished_locked = True
        
            # Sampling Restore
                if self.sampling != []:
                    cycles = scene.cycles
                    cycles.use_adaptive_sampling = self.sampling[0]
                    cycles.adaptive_threshold = self.sampling[1]
                    cycles.samples = self.sampling[2]
                    cycles.adaptive_min_samples = self.sampling[3]
                    cycles.time_limit = self.sampling[4]
                    cycles.use_denoising = self.sampling[5]
                    cycles.denoiser = self.sampling[6]
                    cycles.denoising_input_passes = self.sampling[7]
                    cycles.denoising_prefilter = self.sampling[8]
                    self.sampling = []
                
            # Margin Restore
                scene.render.bake.margin = self.margin_original
                
            # Bake Check
                if any(item.Enabled for item in scene.autobake_queuelist):
                    self.phase_bake_locked = False
                else:
                        
                # Object Finished
                    for index, item in enumerate(scene.autobake_objectqueuelist):
                        if item.Status == 'Baking':
                            if any(item.Status in ['Baked', 'Exported'] for item in scene.autobake_queuelist):
                                if any(item.Status == 'Failed' for item in scene.autobake_queuelist):
                                    item.Status = 'Mixed'
                                    item.Icon = 'QUESTION'
                                    item.Error = 'Some bake items had failed for this object!'
                                else:
                                    item.Status = 'Baked'
                                    item.Icon = 'CHECKMARK'
                            else:
                                item.Status = 'Failed'
                                item.Icon = 'ERROR'
                                item.Error = 'All bake items had failed for this object!'
                            
                            item.name = f"{item.Object.name} {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
                            
                        # Finish Report
                            if abp.ab_report_object_end:
                                self.report({'INFO'},
                                    f"Auto Bake: Object '{item.Object.name}' is finished. " +
                                    (f"Baked & Exported: {sum(1 for item in scene.autobake_queuelist if item.Status in ['Baked', 'Exported'])}; " if sum(1 for item in scene.autobake_queuelist if item.Status in ['Baked', 'Exported']) == sum(1 for item in scene.autobake_queuelist if item.Status == 'Exported') else f"Baked: {sum(1 for item in scene.autobake_queuelist if item.Status in ['Baked', 'Exported'])}; Exported: {sum(1 for item in scene.autobake_queuelist if item.Status == 'Exported')}; ") +
                                    f"Canceled: {sum(1 for item in scene.autobake_queuelist if item.Status == 'Canceled')}; Failed: {sum(1 for item in scene.autobake_queuelist if item.Status == 'Failed')}")
                                
                        # Final Material
                            if abp.ab_apply_textures != 'False' and self.final_material is not None:
                                rearrange_nodes = []
                                shader_node = None
                                for node in self.final_material.node_tree.nodes:
                                    if node.type == 'OUTPUT_MATERIAL' and node.is_active_output and node.inputs[0].is_linked:
                                        shader_node = node.inputs[0].links[0].from_node
                                        for input in shader_node.inputs:
                                            if input.is_linked and input.links[0].from_node.type == 'TEX_IMAGE':
                                                rearrange_nodes.append(input.links[0].from_node)
                                        break

                            # Y Location
                                if len(rearrange_nodes) > 1:
                                    for index, tex_node in enumerate(rearrange_nodes):
                                        tex_node.location.y = (shader_node.location.y + index * (-275)) + ((len(rearrange_nodes)/2) * 275) - 130
                                        
                            # Normal Maps
                                if shader_node is not None:
                                    nodetree = self.final_material.node_tree
                                    for input in shader_node.inputs:
                                        if input.name in ['Normal', 'Clearcoat Normal', 'Coat Normal', 'Clear Coat Normal'] and input.is_linked:
                                            normal_node = nodetree.nodes.new('ShaderNodeNormalMap')
                                            tex_node = input.links[0].from_node
                                            
                                            normal_node.location = tex_node.location + mathutils.Vector((90, -40))
                                            tex_node.location.x -= 210
                                            
                                            nodetree.links.new(normal_node.outputs[0], tex_node.outputs[0].links[0].to_socket)
                                            nodetree.links.new(tex_node.outputs[0], normal_node.inputs[1])
                                            
                                            break

                        # Final Object
                            final_object = None
                            if self.selected_to_active and abp.ab_active_as_final:
                                final_object = item.Object
                            elif abp.ab_final_object:
                                
                            #Object Data
                                final_object = item.Object.copy()
                                final_object.data = item.Object.data.copy()
                                
                            # Clear Material
                                final_object.data.materials.clear()
            
                            # Object Rename
                                object_name = str(item.Object.name) if not item.Object.name.endswith(abp.ab_object_differentiator) else str(item.Object.name)[:-len(abp.ab_object_differentiator)]
                                if abp.ab_export_object:
                                    item.Object.name = ''
                                    item.Object.data.name = ''
                                    final_object.name = object_name
                                    final_object.data.name = object_name
                                    
                            # Location
                                if abp.ab_object_location == 'Copy' and abp.ab_object_offset != 0:
                                    if abp.ab_offset_direction == 'X':
                                        final_object.location.x += abp.ab_object_offset
                                    elif abp.ab_offset_direction == 'Y':
                                        final_object.location.y += abp.ab_object_offset
                                    elif abp.ab_offset_direction == 'Z':
                                        final_object.location.z += abp.ab_object_offset
                                elif abp.ab_object_location == 'Clear':
                                    final_object.location = (0, 0, 0)
                                
                            # Collection
                                if not abp.ab_export_object or not abp.ab_export_object_remove:
                                    if abp.ab_final_collection != '':
                                        if abp.ab_final_collection not in bpy.data.collections:
                                            final_collection = bpy.data.collections.new(abp.ab_final_collection)
                                            final_collection.color_tag = abp.ab_final_collection_color
                                            context.scene.collection.children.link(final_collection)
                                            final_collection.objects.link(final_object)
                                        else:
                                            bpy.data.collections[abp.ab_final_collection].objects.link(final_object)
                                    else:
                                        for collection in item.Object.users_collection:
                                            collection.objects.link(final_object)
                                else:
                                    context.scene.collection.objects.link(final_object)
                                    
                        # Final Object
                            if final_object is not None:
                                
                            # Final Material
                                if self.final_material is not None:
                                    if self.selected_to_active:
                                        final_object.data.materials.clear()
                                    final_object.data.materials.append(self.final_material)
                                    
                            # Export Object
                                if abp.ab_export_object and (abp.ab_export_always == 'Always' or not any(item.Status == "Failed" for item in scene.autobake_queuelist)):
                                    selected_ = [final_object,]
                        
                                # Store Transform
                                    stored_loc = mathutils.Vector(final_object.location)
                                    if abp.ab_export_clear_location:
                                        final_object.location = (0,0,0)
                                    stored_rot = mathutils.Vector(final_object.rotation_euler)
                                    if abp.ab_export_clear_rotation:
                                        final_object.rotation_euler = (0,0,0)
                                    stored_scale = mathutils.Vector(final_object.scale)
                                    if abp.ab_export_clear_scale:
                                        final_object.scale = (1,1,1)
                                    
                                # Folder
                                    foldername = re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', final_object.name)
                                    foldername = foldername.strip()
                                    mainpath = os.path.join(abp.ab_filepath, foldername)
                                    
                                    if not os.path.isdir(mainpath):
                                        os.makedirs(mainpath)

                                # Export FBX
                                    if abp.ab_export_object_as == 'FBX':
                                        path_ = os.path.join(mainpath, f"{final_object.name}.fbx")
                                        
                                        with context.temp_override(active_object=final_object, selected_objects=selected_):
                                            bpy.ops.export_scene.fbx(
                                                filepath = path_,
                                                path_mode = abp.ab_export_pathmode,
                                                embed_textures = abp.ab_export_embedtextures,
                                                
                                                global_scale = abp.ab_export_scale,
                                                apply_scale_options = abp.ab_fbx_apply_scaling,
                                                axis_forward = abp.ab_fbx_forward,
                                                axis_up = abp.ab_fbx_up,
                                                apply_unit_scale = abp.ab_export_applyunit,
                                                use_space_transform = abp.ab_export_usespacetransform,
                                                mesh_smooth_type = abp.ab_export_smoothing,
                                                use_subsurf = abp.ab_export_subdivisionsurface,
                                                use_mesh_modifiers = abp.ab_export_applymodifiers,
                                                use_mesh_modifiers_render = abp.ab_export_evalmode == 'DAG_EVAL_RENDER',
                                                use_mesh_edges = abp.ab_export_looseedges,
                                                use_triangles = abp.ab_export_triangulatefaces,
                                                use_tspace = abp.ab_export_tangentspace,
                                                colors_type = abp.ab_export_vertexcolors,
                                                prioritize_active_color = abp.ab_export_prioritizeactivecolor,
                                                use_custom_props = abp.ab_export_customprops,
                                                
                                                use_selection = True,
                                                object_types = {'MESH'},
                                                bake_anim = False,
                                                use_visible = False,
                                                use_active_collection = False,
                                                batch_mode = 'OFF',
                                                use_metadata = True,
                                                bake_space_transform = False)
                                    
                                # Export OBJ
                                    elif abp.ab_export_object_as == 'OBJ':
                                        stored_selection = list(context.selected_objects)
                                        for obj in reversed(context.selected_objects):
                                            obj.select_set(False)
                                        final_object.select_set(True)
                                        
                                        path_ = os.path.join(mainpath, f"{final_object.name}.obj")
                                            
                                        bpy.ops.wm.obj_export(
                                            filepath = path_,
                                            path_mode = abp.ab_export_pathmode,
                                            
                                            global_scale = abp.ab_export_scale,
                                            forward_axis = abp.ab_obj_forward,
                                            up_axis = abp.ab_obj_up,
                                            apply_modifiers = abp.ab_export_applymodifiers,
                                            export_eval_mode = abp.ab_export_evalmode,
                                            export_colors = abp.ab_export_exportcolors,
                                            export_triangulated_mesh = abp.ab_export_triangulatedmesh,
                                            export_pbr_extensions = abp.ab_export_pbrextension,
                                            export_vertex_groups = abp.ab_export_vertexgroups,
                                            export_smooth_groups = abp.ab_export_smoothgroups,
                                            smooth_group_bitflags = abp.ab_export_groupbitflag,
                                            
                                            export_selected_objects = True,
                                            export_materials = True,
                                            export_uv = True,
                                            export_animation = False,
                                            export_normals = True,
                                            export_object_groups = False,
                                            export_material_groups = False)
                                            
                                   # Restore Selection
                                        final_object.select_set(False)
                                        for obj in stored_selection:
                                            obj.select_set(True)
                                                
                                # Export GLTF
                                    elif abp.ab_export_object_as == 'GLTF':
                                        stored_selection = list(context.selected_objects)
                                        for obj in reversed(context.selected_objects):
                                            obj.select_set(False)
                                        final_object.select_set(True)
                                        
                                        if abp.ab_gltf_format == 'GLB':
                                            path_ = os.path.join(mainpath, f"{final_object.name}.glb")
                                        else:
                                            path_ = os.path.join(mainpath, f"{final_object.name}")
                                    
                                        bpy.ops.export_scene.gltf(
                                            filepath = path_,
                                        
                                            export_format = abp.ab_gltf_format,
                                            export_copyright=abp.ab_gltf_copyright,
                                            export_import_convert_lighting_mode = abp.ab_gltf_lighting,
                                            export_original_specular = abp.ab_gltf_original_spelucar,
                                            export_yup = abp.ab_gltf_yup,
                                            
                                            export_apply = abp.ab_export_applymodifiers,
                                            export_tangents = abp.ab_gltf_tangents,
                                            export_colors = abp.ab_gltf_vertex_colors,
                                            export_attributes = abp.ab_gltf_attributes,
                                            use_mesh_edges = abp.ab_gltf_loose_edges,
                                            use_mesh_vertices = abp.ab_gltf_loose_points,

                                            export_image_format = abp.ab_gltf_images,
                                            export_texture_dir = abp.ab_gltf_texture_folder,
                                            export_keep_originals = abp.ab_gltf_keep_original,
                                            export_image_quality = abp.ab_gltf_image_quality,
                                            export_jpeg_quality = abp.ab_gltf_image_quality,
                                            export_image_add_webp = abp.ab_gltf_create_webp,
                                            export_image_webp_fallback = abp.ab_gltf_webp_fallback,
                 
                                            export_morph = abp.ab_gltf_shape_keys,
                                            export_morph_normal = abp.ab_gltf_shape_keys_normals,
                                            export_morph_tangent = abp.ab_gltf_shape_keys_tangents,
                                            export_try_sparse_sk = abp.ab_gltf_use_sparse,
                                            export_try_omit_sparse_sk = abp.ab_gltf_omitting_sparse,
                                            
                                            export_draco_mesh_compression_enable = abp.ab_gltf_compression,
                                            export_draco_mesh_compression_level = abp.ab_gltf_compression_level,
                                            export_draco_position_quantization = abp.ab_gltf_compression_position,
                                            export_draco_normal_quantization = abp.ab_gltf_compression_normal,
                                            export_draco_texcoord_quantization = abp.ab_gltf_compression_texcoord,
                                            export_draco_color_quantization = abp.ab_gltf_compression_color,
                                            export_draco_generic_quantization = abp.ab_gltf_compression_generic,
                                            
                                            use_selection = True,
                                            use_active_collection_with_nested = False,
                                            export_animations = False,
                                            export_nla_strips = False,
                                            export_skins = False,
                                            
                                            ui_tab = 'GENERAL', 
                                            gltf_export_id = "",
                                            will_save_settings = False,
                                            export_materials = 'EXPORT',
                                            use_visible = False,
                                            use_renderable = False,
                                            use_active_collection = False,
                                            use_active_scene = False,
                                            export_texcoords = True,
                                            export_normals = True,
                                            export_extras = False)
                                       
                                   # Restore Selection
                                        final_object.select_set(False)
                                        for obj in stored_selection:
                                            obj.select_set(True)
                                       
                                # Report Export
                                    if abp.ab_report_object_export:
                                        self.report({'INFO'}, f"Auto Bake: Object '{final_object.name}' has been exported.")
                                        
                                # Export Status
                                    item.Status = 'Exported'
                                    item.Icon = 'EXPORT'
                                    item.Error = ''
                                    item.name = f"{item.Object.name} {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
                                        
                                # Remove Final
                                    if abp.ab_export_object_remove:
                                        bpy.data.objects.remove(final_object, do_unlink=True)

                                # Restore Transform
                                    elif abp.ab_export_restore_transform:
                                        final_object.location = stored_loc
                                        final_object.rotation_euler = stored_rot
                                        final_object.scale = stored_scale
                                    
                        # Restore Names
                            if abp.ab_final_object and not self.selected_to_active:
                                if item.Status == 'Exported' and abp.ab_export_object_remove:
                                    item.Object.name = object_name
                                    item.Object.data.name = object_name
                                    
                                elif abp.ab_object_differentiator != '':
                                    diff_name = object_name + abp.ab_object_differentiator
                                    
                                    if abp.ab_object_keep_name == 'Original':
                                        final_object.name = diff_name
                                        final_object.data.name = diff_name
                                        item.Object.name = object_name
                                        item.Object.data.name = object_name
                                        
                                        if final_object.name != diff_name:
                                            bpy.data.objects[diff_name].data.name = final_object.name
                                            bpy.data.objects[diff_name].name = final_object.name
                                            final_object.name = diff_name
                                            final_object.data.name = diff_name
                                            
                                    elif abp.ab_object_keep_name == 'Final':
                                        item.Object.name = diff_name
                                        item.Object.data.name = diff_name
                                        final_object.name = object_name 
                                        final_object.data.name = object_name
                                        
                                        if item.Object.name != diff_name:
                                            bpy.data.objects[diff_name].data.name = item.Object.name
                                            bpy.data.objects[diff_name].name = item.Object.name
                                            item.Object.name = diff_name
                                            item.Object.data.name = diff_name
                                            
                        # Move Finished
                            if abp.ab_move_finished_bake:
                                scene.autobake_objectqueuelist.move(index, len(scene.autobake_objectqueuelist)-1)
                                last_item = scene.autobake_objectqueuelist[len(scene.autobake_objectqueuelist)-1]
                            else:
                                last_item = item
                                
                        # Store Bake Results
                            results = []
                            for item in scene.autobake_queuelist:
                                results.append({f"{item.Type} " + (f"{item.Multiplier:.2f}" if is_udim_bake else f"{item.Size}"): {'Status': item.Status, 'Icon': item.Icon, 'Error': item.Error,'Cancel': item.Cancel}})
                            bake_results[last_item.Object.name] = results

                            break
                 
                # Next Object
                    if any(item.Enabled for item in scene.autobake_objectqueuelist):
                        self.phase_bake_locked = False
     
                    # Prepare Next Object
                        if abp.ab_auto_next == 'Always' or (abp.ab_auto_next == 'On-Success' and not any(item.Status == 'Failed' for item in scene.autobake_queuelist)):

                        # Restore for Next Object
                            for item in scene.autobake_queuelist:
                                item.Enabled = True
                                if item.Status in ['Baked', 'Exported', 'Failed']:
                                    item.Status = 'Pending'
                                    item.Icon = 'PREVIEW_RANGE'
                                    item.name = f"{item.Type} " + (f"{item.Multiplier:.2f}" if scene.autobake_properties.ab_udim_bake else f"{item.Size}") + f" {item.Status}" + (' Enabled' if item.Enabled else ' Disabled')
                            
                        # Restore Bake Queue Order
                            global bake_order
                            for index, item in enumerate(bake_order):
                                for index_, item_ in enumerate(scene.autobake_queuelist):
                                    if (f"{item_.Type} " + (f"{item_.Multiplier:.2f}" if is_udim_bake else f"{item_.Size}")) == item:
                                        scene.autobake_queuelist.move(index_, index)
                                        break

                        # Next Object Now
                            next_object_bake = True
                            
                    # Next Object on Click
                        else:
                            next_object_bake = False

                # Bake Finish
                    else:
                        
                    # Reports
                        if len(scene.autobake_objectqueuelist):
                            
                        # Object Summary Report
                            if abp.ab_report_object_summary:
                                self.report({'INFO'},
                                    f"Auto Bake: Objects are finished baking. " +
                                    (f"Baked & Exported: {sum(1 for item in scene.autobake_objectqueuelist if item.Status in ['Baked', 'Exported'])}; " if (sum(1 for item in scene.autobake_objectqueuelist if item.Status in ["Baked", 'Exported']) == sum(1 for item in scene.autobake_objectqueuelist if item.Status == "Exported")) else f"Baked: {sum(1 for item in scene.autobake_objectqueuelist if item.Status == 'Baked')}; Exported: {sum(1 for item in scene.autobake_objectqueuelist if item.Status == 'Exported')}; ") +
                                    f"Canceled: {sum(1 for item in scene.autobake_objectqueuelist if item.Status == 'Canceled')}; Mixed: {sum(1 for item in scene.autobake_objectqueuelist if item.Status == 'Mixed')}; Failed: {sum(1 for item in scene.autobake_objectqueuelist if item.Status == 'Failed')}")

                        # Bake Summary
                            obj_baked_report = 0
                            obj_exported_report = 0
                            obj_canceled_report = 0
                            obj_failed_report = 0
                            
                            for obj in scene.autobake_objectqueuelist:
                                if obj.Object.name in bake_results:
                                    for obj_results in bake_results[obj.Object.name]:
                                        for bake in obj_results:
                                            if obj_results[bake]['Status'] == 'Baked':
                                                obj_baked_report += 1
                                            elif obj_results[bake]['Status'] == 'Exported':
                                                obj_baked_report += 1
                                                obj_exported_report += 1
                                            elif obj_results[bake]['Status'] == 'Canceled':
                                                obj_canceled_report += 1
                                            elif obj_results[bake]['Status'] == 'Failed':
                                                obj_failed_report += 1
          
                        # Bake Summary Report
                            if abp.ab_report_bake_summary:
                                self.report({'INFO'},
                                    f"Auto Bake: Bakes are finished for all ({len(scene.autobake_objectqueuelist)}) objects: " + 
                                    (f"Baked & Exported: {obj_baked_report}; " if (obj_baked_report == obj_exported_report) else f"Baked: {obj_baked_report}; Exported: {obj_exported_report}; ") +
                                    f"Canceled: {obj_canceled_report}; Failed: {obj_failed_report}")

                    # Confirm Results
                        if abp.ab_auto_confirm == 'Always' or (abp.ab_auto_confirm == 'On-Success' and not any(item.Status in ['Mixed', 'Failed'] for item in scene.autobake_objectqueuelist)):
                            scene.autobake_queuelist.clear()
                            scene.autobake_objectqueuelist.clear()
                            
                    # Close Session
                        context.window_manager.event_timer_remove(self._timer)
                        bake_status = 'IDLE'
                        
                        return {'FINISHED'}
                    
        return {'PASS_THROUGH'}
