
import bpy
import os
import platform
import re

from .utils import *

from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty)
from bpy.types import (Material, Scene, Panel, Operator, PropertyGroup, UIList, Menu)


#------------------------------------------------------------------------------------
#   UI Lists

class SPARROW_UL_Bake(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        abp = scene.autobake_properties
        layout.alert = item.IsDuplicate

        if abp.ab_item_type:
            row = layout.row()
            row.alignment = "LEFT"
            row.scale_x=.71
            row.label(text='', icon="TEXTURE_DATA")
            row_input=row.row()
            row_input.scale_x=1.3
            row_input.prop(item, "Type", emboss=False)     
        else:
            row = layout.row()
            row.alignment = "EXPAND"
            row.label(text=str(item.Type), icon="TEXTURE_DATA")
            
        if abp.ab_item_scale:
            row = layout.row()
            row.alignment = "RIGHT"
            row_size = row.row()
            row_size.scale_x = .75
            row_size.prop(item, "Size", text=' ', emboss=False, slider=True)
        else:
            row = layout.row()
            row.alignment = "RIGHT"
            row.label(text=str(item.Size)+' ')
            
        row = layout.row()
        row.scale_x=.9
        row.prop(item, "Gate")

        
class SPARROW_UL_BakeQueue(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        layout.enabled = item.Enabled
        
        layout.alert = item.Status == 'Failed'
        col = layout.column(align=True)
        row_main = col.row()
        
        row = row_main.row()
        row.operator("sparrow.toggle_queued", text="", icon= 'CHECKBOX_DEHLT' if item.Cancel else 'CHECKBOX_HLT', emboss=False).index = index
        row.label(text= f"{item.Type}  -  " + (f"{item.Multiplier:.2f}" if is_udim_bake else f"{item.Size}"))

        row_status = row_main.row()
        row_status.alignment = "RIGHT"
        row_status.label(text=item.Status)
        row_status.label(text="", icon=item.Icon)

        if scene.autobake_properties.ab_bake_error_msg and item.Status == 'Failed': 
            row_alert = col.row()
            row_alert.alert = True
            row_alert.label(text=f"{item.Error}")
    
    
class SPARROW_UL_UDIMType(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        abp = scene.autobake_properties

        layout.alert = item.IsDuplicate
        row = layout.row()
        row.alignment = "LEFT"
        row.scale_x=.71
        row.label(text='', icon="TEXTURE_DATA")
        split = layout.split(factor=.7, align=True)
        row = split.row(align=True)
        row.alignment = "LEFT"
        row.scale_x=.975
        if abp.ab_udim_item_type:
            row.prop(item, "Type", emboss=False)     
        else:
            row.label(text='  '+str(item.Type))
        row = split.row(align=True)
        row.alignment = "RIGHT"
        if abp.ab_udim_item_multiplier:
            row.prop(item, "Size", text=' ', emboss=False, slider=True)
        else:
            row.label(text=f"{item.Size:.2f}"+' ')
        row = layout.row()
        row.scale_x=.9
        row.prop(item, "Gate")
        
        
class SPARROW_UL_UDIMTile(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        abp = scene.autobake_properties
        
        layout.alert = item.IsDuplicate

        row = layout.row()
        row.alignment = "LEFT"
        row.scale_x=.71
        row.label(text='', icon="TEXTURE_DATA")
        
        split = layout.split(factor=.65 if abp.ab_udim_label else .55, align=True)

        row = split.row(align=True)
        row.alignment = 'LEFT'
        
        if abp.ab_udim_label:
            row.prop(item, 'Label', text='', emboss=False)
            
        if abp.ab_udim_item_tile:
            row.prop(item, "UDIM", slider=True, emboss=False)
        else:
            if not abp.ab_udim_label:
                row.label(text='      ')
            row.label(text=f'{item.UDIM}')
            
        row = split.row(align=True)
        row.alignment = "RIGHT"
        row.alert = False
        if abp.ab_udim_item_scale:
            row.prop(item, "Size", text=' ', slider=True, emboss=False)
        else:
            row.label(text=str(item.Size)+' ')
            
        row = layout.row(align=True)
        row.scale_x=.9
        row.prop(item, "Gate")

        
class SPARROW_UL_SourceObjects(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        abp = scene.autobake_properties
        
        layout.prop(item, 'Object', text='')


class SPARROW_UL_ImageExport(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        abp = scene.autobake_properties
        
        layout.enabled = item.Image.is_dirty
        
        split = layout.split(factor=.333, align=True)
        split.prop(item, 'Prefix', text='', icon='FILE_FOLDER', emboss=False)
        
        row = split.row(align=True)
        row.prop(item, 'Name', text='', icon='TEXTURE', emboss=False)
        
        row2 = row.row()
        if layout.active:
            row2.prop(item, 'Gate', text='')
        else:
            row2.label(text='', icon='ERROR')
        

class SPARROW_UL_ObjectQueue(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        layout.enabled = item.Enabled
        
        layout.alert = item.Status in ['Failed', 'Mixed']
        col = layout.column(align=True)
        row_main = col.row()
        
        row = row_main.row()
        row.operator("sparrow.toggle_queued_object", text="", icon= 'CHECKBOX_DEHLT' if item.Cancel else 'CHECKBOX_HLT', emboss=False).index = index
        row.label(text= f"{item.Object.name}", icon='OBJECT_DATAMODE')

        row_status = row_main.row()
        row_status.alignment = "RIGHT"
        row_status.label(text=item.Status)
        row_status.label(text="", icon=item.Icon)

        if scene.autobake_properties.ab_bake_error_msg and item.Status in ['Failed', 'Mixed']: 
            row_alert = col.row()
            row_alert.alert = True
            row_alert.label(text=f"{item.Error}")