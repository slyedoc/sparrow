import bpy

from bpy.types import Menu
        
class SPARROW_MT_BakeList(Menu):
    bl_label = "List Settings"
    bl_idname = "SPARROW_MT_bakelist"
    
    def draw(self, context):
        abp = context.scene.autobake_properties
        layout = self.layout
        layout.operator("sparrow.bakelist_load_linked", text="Load by Linked", icon='IMPORT')
        layout.separator()
        layout.operator("sparrow.move_to_top", text="Selected to Top", icon='TRIA_UP_BAR')
        layout.operator("sparrow.move_to_bottom", text="Selected to Bottom", icon='TRIA_DOWN_BAR')
        layout.separator()
        layout.operator("sparrow.enable_all", text="Enable All", icon='CHECKBOX_HLT')
        layout.operator("sparrow.disable_all", text="Disable All", icon='CHECKBOX_DEHLT')
        layout.operator("sparrow.invert_all", text="Invert All", icon='BLANK1')
        layout.separator()
        layout.operator("sparrow.remove_all", text="Clear List", icon='REMOVE')
        layout.operator("sparrow.remove_duplicates", text="Remove Duplicated", icon='BLANK1')
        layout.operator("sparrow.remove_disabled", text="Remove Disabled", icon='BLANK1')
        layout.separator()
        layout.prop(abp, "ab_item_details", text="Item Details")
        layout.separator()
        layout.operator("sparrow.reorder", text="Sort Items", icon='SORTALPHA')
        layout.separator()
        layout.prop(abp, "ab_udim_bake", text="UDIM Bake")
        
        
class SPARROW_MT_UDIMList(Menu):
    bl_label = "List Settings"
    bl_idname = "SPARROW_MT_udimlist"
    
    def draw(self, context):
        layout = self.layout
        layout.operator('sparrow.udimlist_import', text='Load Tiles', icon='IMPORT')
        layout.separator()
        layout.operator('sparrow.move_to_top_udim', text="Selected to Top", icon='TRIA_UP_BAR')
        layout.operator('sparrow.move_to_bottom_udim', text="Selected to Bottom", icon='TRIA_DOWN_BAR')
        layout.separator()
        layout.operator('sparrow.udimlist_enable_all', icon='CHECKBOX_HLT')
        layout.operator('sparrow.udimlist_disable_all', icon='CHECKBOX_DEHLT')
        layout.operator('sparrow.udimlist_invert_all')
        layout.separator()
        layout.operator('sparrow.udimlist_remove_all', icon='REMOVE', text='Clear List')
        layout.operator('sparrow.udimlist_remove_duplicates')
        layout.operator('sparrow.udimlist_remove_disabled')
        layout.separator()
        layout.prop(context.scene.autobake_properties, 'ab_udim_label', text='Tile Label')
        layout.separator()
        layout.operator('sparrow.udimlist_sort', icon='SORTALPHA')
        

class SPARROW_MT_ItemEdit(Menu):
    bl_label = "Item Edit"
    bl_idname = "SPARROW_MT_itemedit"
    bl_description ='Set how the items in the bake list (non-udim) can be edited'
    
    def draw(self, context):
        abp = context.scene.autobake_properties
        layout = self.layout
        layout.label(text='In-line')
        layout.prop(abp, "ab_item_type", text='Type (In Line)')
        layout.prop(abp, "ab_item_scale", text='Scale (In Line)')
        layout.separator()
        layout.label(text='Default')
        layout.prop(abp, "ab_item_default", text='Type & Scale')
        

class SPARROW_MT_ItemEdit_UDIM(Menu):
    bl_label = "Item Edit"
    bl_idname = "SPARROW_MT_udimitem"
    bl_description ='Set how the items in both of the UDIM Lists can be edited'
    
    def draw(self, context):
        abp = context.scene.autobake_properties
        layout = self.layout
        layout.label(text='In-line')
        layout.prop(abp, "ab_udim_item_type", text='Type')
        layout.prop(abp, "ab_udim_item_multiplier", text='Multiplier')
        layout.prop(abp, "ab_udim_item_tile", text='Tile')
        layout.prop(abp, "ab_udim_item_scale", text='Scale')
        layout.separator()
        layout.label(text='Default')
        layout.prop(abp, "ab_udim_item_default", text='Type & Multiplier')
        layout.prop(abp, "ab_udim_item_tilescale_default", text='Tile & Scale')


class SPARROW_MT_ColorSpace(Menu):
    bl_label = "Color Space"
    bl_idname = "SPARROW_MT_colorspace"
    bl_description ="Set what color space different texture types should use when creating them"
    
    def draw(self, context):
        layout = self.layout
        abp = context.scene.autobake_properties
        layout.label(text='Color Textures', icon='SEQUENCE_COLOR_03')
        layout.prop(abp, "ab_color_space_color", text="")
        layout.separator()
        layout.label(text='Vector Textures', icon='SEQUENCE_COLOR_06')
        layout.prop(abp, "ab_color_space_vector", text="")
        layout.separator()
        layout.label(text='Float Textures', icon='SEQUENCE_COLOR_09')
        layout.prop(abp, "ab_color_space_float", text="")


class SPARROW_MT_StartPopupSettings(Menu):
    bl_label = "Start Settings"
    bl_idname = "SPARROW_MT_startpopupsettings"
    bl_description ="Control what settings are shows in the bake start popup window"
    
    def draw(self, context):
        layout = self.layout
        abp = context.scene.autobake_properties
        
        layout.prop(abp, "ab_start_popup_settings", text='Settings (All)')
        
        col = layout.column()
        col.active = abp.ab_start_popup_settings

        col.separator()
        col.prop(abp, "ab_start_popup_final_material")
        
        col_m = col.column()
        col_m.active = abp.ab_start_popup_final_material
        col_m.prop(abp, "ab_start_popup_final_shader", text='Material Shader')
        col_m.prop(abp, "ab_start_popup_texture_apply", text='Apply Textures')
        
        col.separator()
        col.prop(abp, "ab_start_popup_final_object")
        col_m = col.column()
        col_m.active = abp.ab_start_popup_final_object
        col_m.prop(abp, "ab_start_popup_object_offset", text='Object Offset')
        col_m.prop(abp, "ab_start_popup_export_objects", text='Export Object')
        col.prop(abp, "ab_start_popup_selected_to_active")
        
        col.separator()
        col.prop(abp, "ab_start_popup_export_textures")
        col.prop(abp, "ab_start_popup_keep_textures")


class SPARROW_MT_Confirms(Menu):
    bl_label = "Confirm Windows"
    bl_idname = "SPARROW_MT_confirms"
    bl_description ="Disable confirm windows for buttons. Confirm windows can also be skipped with using 'CTRL + Click'"
    
    def draw(self, context):
        layout = self.layout
        abp = context.scene.autobake_properties
        layout.prop(abp, "ab_confirm_start_bake", text='Start')
        layout.prop(abp, "ab_confirm_cancel_bake", text='Cancel')
        layout.prop(abp, "ab_confirm_bake_results", text='Results')
        layout.prop(abp, "ab_confirm_next_object", text='Next Object')
        layout.prop(abp, "ab_confirm_queue_item_gate", text='Queue Item')
        
       
class SPARROW_MT_Alerts(Menu):
    bl_label = "Alerts"
    bl_idname = "SPARROW_MT_alerts"
    bl_description ='Set the visibility of the addon tooltips'
    
    def draw(self, context):
        abp = context.scene.autobake_properties
        layout = self.layout
        layout.prop(abp, "ab_alert_texts", text='UI Elements')
        layout.prop(abp, "ab_nodealert", text='Shader Editor')
        layout.prop(abp, "ab_bake_error_msg", text='Bake Errors')
        
        
class SPARROW_MT_Reports(Menu):
    bl_label = "Reports"
    bl_idname = "SPARROW_MT_Reports"
    bl_description ="Set which actions Auto Bake should report during the baking process. Some error reports can't be disabled, since they provide valuable feedback when an issue occurs"
    
    def draw(self, context):
        abp = context.scene.autobake_properties
        layout = self.layout
        layout.prop(abp, "ab_report_requests", text="Requests")
        layout.separator()
        layout.prop(abp, "ab_report_bake_start", text="Bake Start")
        layout.prop(abp, "ab_report_bake_end", text="Bake End")
        layout.separator()
        layout.prop(abp, "ab_report_object_start", text="Object Start")
        layout.prop(abp, "ab_report_object_end", text="Object End")
        layout.separator()
        layout.prop(abp, "ab_report_texture_export", text="Texture Export")
        layout.prop(abp, "ab_report_object_export", text="Object Export")
        layout.separator()
        layout.prop(abp, "ab_report_bake_summary", text="Bake Summary")
        layout.prop(abp, "ab_report_object_summary", text="Object Summary")
        layout.separator()
        layout.prop(abp, "ab_report_bake_error", text="Bake Errors")


