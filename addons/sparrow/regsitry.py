import json
import bpy

from dataclasses import dataclass
from typing import Any, Dict, List
from bpy_types import PropertyGroup
from .utils import *

@dataclass
class TypeInfo:
    is_component: bool
    is_resource: bool
    items: Any #{ "type": { "$ref": "#/$defs/glam::Quat" } },
    long_name: str # "alloc::vec::Vec<glam::Quat>"
    short_name: str # "Vec<Quat>",
    type: str # "array",
    type_info: str | None# "List"
    one_of: List[Any]

# helper function that returns a lambda, used for the PropertyGroups update function below        
def update_calback_helper(definition: TypeInfo, update, component_name_override):
    return lambda self, context: update(self, context, definition, component_name_override)

# called on updated by generated property groups for component_meta, serializes component_meta then saves it to bevy_components
## main callback function, fired whenever any property changes, no matter the nesting level
def update_component(self, context, definition: TypeInfo, component_name):
    registry = bpy.context.window_manager.components_registry
    
    # get selected object or collection:
    item = None
    object = context.object
    collection = None #  context.collection

    if object is not None:
        item = object
    elif collection is not None:
        item = collection     

    #print("updating component", component_name, item.name)      
    
    # if we have an object or collection
    if item:
        update_disabled = item["__disable__update"] if "__disable__update" in item else False
        #update_disabled = bevy.disable_all_object_updates or update_disabled # global settings
        if update_disabled:
            return
        
        if item["components_meta"] is None:
            print("ERROR: object does not have components", item.name)
            return
        
        component_meta =  next(filter(lambda component: component["long_name"] == component_name, item.components_meta.components), None)

        if component_meta is None:
            print("ERROR: object does not have component", component_name, item.name)
            return

        property_group_name = registry.get_propertyGroupName_from_longName(component_name)
        property_group = getattr(component_meta, property_group_name)
        # we use our helper to set the values
        previous = json.loads(item['bevy_components'])
        previous[component_name] = registry.property_group_value_to_custom_property_value(property_group, definition, None)
        item['bevy_components'] = json.dumps(previous)

