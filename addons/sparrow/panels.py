import bpy

from .menu import *

from .operators import *
from .properties import *

def draw_components(item, layout, settings: SPARROW_PG_Settings, registry: ComponentsRegistry):
    if item is None:
        layout.label(text ="Select an object to edit its components")
        return
    
    item_type = get_selection_type(item)
    item_name = item.name

    if registry.has_type_infos() is None:
        layout.label(text ="No registry loaded, please load a registry file")
        return
    
    components_meta: ComponentsMeta = item.components_meta
    if components_meta is None:
        layout.label(text ="No components found")
        return


    col = layout.column_flow(columns=2)      
    
    row = col.row(align=True)
    row.prop(settings.components_dropdown, "filter", text="Filter")
    
    row = col.row(align=True)
    op = row.operator(SPARROW_OT_PasteComponent.bl_idname, text="Paste: "+settings.copied_source_component_name+"", icon="PASTEDOWN")
    op.target_item_name = item_name
    op.target_item_type = item_type
    row.enabled = settings.copied_source_item_name != '' 

    op = row.operator(SPARROW_OT_components_refresh_custom_properties_all.bl_idname, text="Refresh", icon="SYNTAX_ON")

    col = layout.column()
    row = col.row(align=True)       
    row.prop(settings.components_dropdown, "list", text="")
    
    small_row = row.row(align=True)
    small_row.scale_x = 0.5  # Adjust this value to control the width
    op = small_row.operator(SPARROW_OT_AddComponent.bl_idname, text="Add", icon="ADD")

    op.component_type = settings.components_dropdown.list
    op.target_item_name = item_name
    op.target_item_type = item_type
    row.enabled = settings.components_dropdown.list != '' and registry.has_type_infos()
    
    layout.separator()

    bevy_components = get_bevy_components(item)



    for component_name in sorted(bevy_components): # sorted by component name, practical

        component_meta: ComponentMetadata | None = next(filter(lambda component: component["long_name"] == component_name, components_meta.components), None)
        if component_meta is None:
            print("ERROR: object does not have component", component_name)
            continue

        # our whole row 
        box = layout.box() 
        row = box.row(align=True)

        # "header"
        row.alert = component_meta.invalid
        row.prop(component_meta, "enabled", text="")
        row.label(text=component_name)

        # we fetch the matching ui property group
        
        root_propertyGroup_name = registry.get_propertyGroupName_from_longName(component_name)  
        if root_propertyGroup_name is None:
            print("ERROR: object does not have component", component_name)
            error_message = component_meta.invalid_details if component_meta.invalid else "Missing property group name"
            row.label(text=error_message)
            continue

        component_internal = component_name in INTERNAL_COMPONENTS        
        propertyGroup = getattr(component_meta, root_propertyGroup_name, None)
        
        if propertyGroup is None:
            error_message = component_meta.invalid_details if component_meta.invalid else "Missing component UI data, please reload registry !"
            row.label(text=error_message)
            continue

        # if the component has only 0 or 1 field names, display inline, otherwise change layout
        single_field = len(propertyGroup.field_names) < 2
        prop_group_location = box.row(align=True).column()
        """if single_field:
            prop_group_location = row.column(align=True)#.split(factor=0.9)#layout.row(align=False)"""
        
        if component_meta.visible:
            if component_meta.invalid:

                error_message = component_meta.invalid_details if component_meta.invalid else "Missing component UI data, please reload registry !"
                prop_group_location.label(text=error_message)
            else:
                draw_propertyGroup(propertyGroup, prop_group_location, [root_propertyGroup_name], component_name, item_type, item_name, enabled=not component_internal)
        else :
            row.label(text="details hidden, click on toggle to display")

        # "footer" with additional controls
        # if component_invalid:
        #     if root_propertyGroup_name:
        #         propertyGroup = getattr(component_meta, root_propertyGroup_name, None)
        #         if propertyGroup:
        #             unit_struct = len(propertyGroup.field_names) == 0
        #             if unit_struct: 
        #                 op = row.operator(Fix_Component_Operator.bl_idname, text="", icon="SHADERFX")
        #                 op.component_name = component_name
        #                 row.separator()

        op = row.operator(SPARROW_OT_RemoveComponent.bl_idname, text="", icon="X")
        op.component_name = component_name
        op.item_name = item_name
        op.item_type = item_type

        row.separator()
        
        op = row.operator(SPARROW_OT_CopyComponent.bl_idname, text="", icon="COPYDOWN")
        op.source_component_name = component_name
        op.source_item_name = item_name
        op.source_item_type = item_type
        row.separator()
        
        #if not single_field:
        toggle_icon = "TRIA_DOWN" if component_meta.visible else "TRIA_RIGHT"
        op = row.operator(SPARROW_OT_ToggleComponentVisibility.bl_idname, text="", icon=toggle_icon)
        op.component_name = component_name
        op.item_name = item_name
        op.item_type = item_type
        #row.separator()

def draw_propertyGroup( propertyGroup, layout, nesting =[], rootName=None, item_type="OBJECT", item_name="", enabled=True):
    is_enum = getattr(propertyGroup, "with_enum")
    is_list = getattr(propertyGroup, "with_list") 
    is_map = getattr(propertyGroup, "with_map")
    # item in our components hierarchy can get the correct propertyGroup by STRINGS because of course, we cannot pass objects to operators...sigh

    # if it is an enum, the first field name is always the list of enum variants, the others are the variants
    field_names = propertyGroup.field_names
    layout.enabled = enabled
    #print("")
    #print("drawing", propertyGroup, nesting, "component_name", rootName)
    if is_enum:
        subrow = layout.row()
        display_name = field_names[0] if propertyGroup.tupple_or_struct == "struct" else ""
        subrow.prop(propertyGroup, field_names[0], text=display_name)
        subrow.separator()
        selection = getattr(propertyGroup, "selection")

        for fname in field_names[1:]:
            if fname == "variant_" + selection:
                subrow = layout.row()
                display_name = fname if propertyGroup.tupple_or_struct == "struct" else ""

                nestedPropertyGroup = getattr(propertyGroup, fname)
                nested = getattr(nestedPropertyGroup, "nested", False)
                #print("nestedPropertyGroup", nestedPropertyGroup, fname, nested)
                if nested:
                    draw_propertyGroup(nestedPropertyGroup, subrow.column(), nesting + [fname], rootName, item_type, item_name, enabled=enabled )
                # if an enum variant is not a propertyGroup
                break
    elif is_list:
        item_list = getattr(propertyGroup, "list")
        list_index = getattr(propertyGroup, "list_index")
        box = layout.box()
        split = box.split(factor=0.9)
        box.enabled = enabled
        list_column, buttons_column = (split.column(),split.column())

        list_column = list_column.box()
        for index, item  in enumerate(item_list):
            row = list_column.row()
            draw_propertyGroup(item, row, nesting, rootName, item_type, enabled=enabled)
            icon = 'CHECKBOX_HLT' if list_index == index else 'CHECKBOX_DEHLT'
            op = row.operator('sparrow.component_list_actions', icon=icon, text="")
            op.action = 'SELECT'
            op.component_name = rootName
            op.property_group_path = json.dumps(nesting)
            op.selection_index = index
            op.item_type = item_type
            op.item_name = item_name

        #various control buttons
        buttons_column.separator()
        row = buttons_column.row()
        op = row.operator('sparrow.component_list_actions', icon='ADD', text="")
        op.action = 'ADD'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)
        op.item_type = item_type
        op.item_name = item_name

        row = buttons_column.row()
        op = row.operator('sparrow.component_list_actions', icon='REMOVE', text="")
        op.action = 'REMOVE'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)
        op.item_type = item_type
        op.item_name = item_name

        buttons_column.separator()
        row = buttons_column.row()
        op = row.operator('sparrow.component_list_actions', icon='TRIA_UP', text="")
        op.action = 'UP'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)
        op.item_type = item_type
        op.item_name = item_name


        row = buttons_column.row()
        op = row.operator('sparrow.component_list_actions', icon='TRIA_DOWN', text="")
        op.action = 'DOWN'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)
        op.item_type = item_type
        op.item_name = item_name


    elif is_map:
        root = layout.row().column()
        if hasattr(propertyGroup, "list"): # TODO: improve handling of non drawable UI
            keys_list = getattr(propertyGroup, "list")
            values_list = getattr(propertyGroup, "values_list")
            box = root.box()
            row = box.row()
            row.label(text="Add entry:")
            keys_setter = getattr(propertyGroup, "keys_setter")
            draw_propertyGroup(keys_setter, row, nesting, rootName, item_type, item_name, enabled=enabled)

            values_setter = getattr(propertyGroup, "values_setter")
            draw_propertyGroup(values_setter, row, nesting, rootName, item_type, item_name, enabled=enabled)

            op = row.operator('sparrow.component_map_actions', icon='ADD', text="")
            op.action = 'ADD'
            op.component_name = rootName
            op.property_group_path = json.dumps(nesting)
            op.item_type = item_type
            op.item_name = item_name

            box = root.box()
            split = box.split(factor=0.9)
            list_column, buttons_column = (split.column(),split.column())
            list_column = list_column.box()

            for index, item  in enumerate(keys_list):
                row = list_column.row()
                draw_propertyGroup(item, row, nesting, rootName, item_type, item_name, enabled=enabled)

                value = values_list[index]
                draw_propertyGroup(value, row, nesting, rootName, item_type, item_name, enabled=enabled)

                op = row.operator('sparrow.component_map_actions', icon='REMOVE', text="")
                op.action = 'REMOVE'
                op.component_name = rootName
                op.property_group_path = json.dumps(nesting)
                op.target_index = index
                op.item_type = item_type
                op.item_name = item_name

            #various control buttons
            buttons_column.separator()
            row = buttons_column.row()
        

    else: 
        for fname in field_names:
            #subrow = layout.row()
            nestedPropertyGroup = getattr(propertyGroup, fname)
            nested = getattr(nestedPropertyGroup, "nested", False)
            display_name = fname if propertyGroup.tupple_or_struct == "struct" else ""

            if nested:
                layout.separator()
                layout.separator()

                layout.label(text=display_name) #  this is the name of the field/sub field
                layout.separator()
                subrow = layout.row()
                draw_propertyGroup(nestedPropertyGroup, subrow, nesting + [fname], rootName, item_type, item_name, enabled )
            else:
                subrow = layout.row()
                subrow.prop(propertyGroup, fname, text=display_name)
                subrow.separator()


class SPARROW_PT_Object:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

class SPARROW_PT_ObjectPanel(SPARROW_PT_Object, bpy.types.Panel):
    bl_idname = "SPARROW_PT_object"
    bl_label = "Bevy Components"


    def draw(self, context):
        layout = self.layout 
        settings = bpy.context.window_manager.sparrow_settings # type: SPARROW_PG_Settings    
        registry = bpy.context.window_manager.components_registry # type: ComponentsRegistry
        item  =  context.object

        draw_components(item, layout, settings, registry)

class SPARROW_PT_Collection:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "collection"

class SPARROW_PT_CollectionPanel(SPARROW_PT_Collection, bpy.types.Panel):
    bl_idname = "SPARROW_PT_collection"
    bl_label = "Bevy Components"

    def draw(self, context):
        layout = self.layout 
        settings = bpy.context.window_manager.sparrow_settings # type: SPARROW_PG_Settings    
        registry = bpy.context.window_manager.components_registry # type: ComponentsRegistry
        item  =  context.collection        
        draw_components(item, layout, settings, registry)

      
class SPARROW_PT_Output:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"

class SPARROW_PT_OutputPanel(SPARROW_PT_Output, bpy.types.Panel):
    bl_idname = "SPARROW_PT_output"
    bl_label = "Bevy"

    def draw(self, context):
        layout = self.layout
        #scene = context.scene
        settings = bpy.context.window_manager.sparrow_settings # type: SPARROW_PG_Settings

        col = layout.column_flow(columns=1)
        col.operator(SPARROW_OT_ExportScenes.bl_idname, icon="RENDER_STILL", text="Export Scenes")
        
        col = layout.column_flow(columns=1)
        col.operator(SPARROW_OT_ExportBlueprints.bl_idname, icon="PARTICLEMODE", text="Export Blueprints")
        
        
        row = col.row()
        row.label(text="Scenes")
        row.label(text="Scene/Blueprint")        

        box = col.box() 

        col = box.column_flow(align=True)            
        for scene in bpy.data.scenes:       ## new 
            
            scene_props = scene.sparrow_scene_props
            row = col.row()            
            row.label(text=scene.name)
            row.prop(scene_props, "export", text="")   ## changed
            row.prop(scene_props, "export_blueprints", text="")   ## changed
            

        col.separator()
        
        col.label(text="Global Settings")
        box = layout.box() 

        row = box.row()
        row.label(text="Assets Folder")
        row.prop(settings, "assets_path", text="")
        folder_selector = row.operator(SPARROW_OT_OpenAssetsFolderBrowser.bl_idname, icon="FILE_FOLDER", text="")
        folder_selector.target_property = "assets_path"

        row = box.row()
        row.label(text="Registry File")
        row.prop(settings, "registry_file", text="")
        row.operator(SPARROW_OT_OpenRegistryFileBrowser.bl_idname, icon="FILE", text="")

        row = box.row()
        row.label(text="Format")
        row.prop(settings, "gltf_format", text="")        



        row = box.row()
        row.operator(SPARROW_OT_LoadRegistry.bl_idname, text="Reload Registry")
        
        #folder_selector = row.operator(ReloadRegistryOperator.bl_idname, icon="FILE_FOLDER", text="")
        #folder_selector.target_property = "assets_path"

class SPARROW_PT_Scene:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

class SPARROW_PT_ScenePanel(SPARROW_PT_Scene, bpy.types.Panel):
    bl_idname = "SPARROW_PT_scene"
    bl_label = "Bevy Components"

    def draw(self, context):       

        layout = self.layout 
        settings = bpy.context.window_manager.sparrow_settings # type: SPARROW_PG_Settings    
        registry = bpy.context.window_manager.components_registry # type: ComponentsRegistry
        item  =  context.scene

        draw_components(item, layout, settings, registry)

class SPARROW_PT_Main:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"

class SPARROW_PT_Bake(SPARROW_PT_Main, Panel):
    bl_idname = "SPARROW_PT_Bake"
    bl_label = "Sparrow - Auto Bake"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
     
        col = layout.column_flow(columns=1)
     
        if bake_status == 'IDLE':
            col.alert = (not bool(os.path.exists(abp.ab_filepath)) and abp.ab_texture_export) or (abp.ab_bake_list_item_count < 1 if not abp.ab_udim_bake else (abp.ab_udim_list_item_count < 1 or abp.ab_udimtype_list_item_count < 1))
            col.operator("sparrow.start_bake", icon="RENDER_STILL", text="Auto Bake       ")
            
            row = col.row(align=True)
            col1 = row.column()
            col1.enabled = len(scene.autobake_imageexport) > 0 and bool(os.path.exists(abp.ab_filepath))
            col1.alert = not bool(os.path.exists(abp.ab_filepath))
            col1.operator("sparrow.export_textures", icon="EXPORT", text="   Export")
            
            row.separator()
            col2 = row.column()
            col2.alert = not bool(os.path.exists(abp.ab_filepath)) and abp.ab_texture_export 
            col2.prop(scene.autobake_properties, "ab_texture_export", text="", toggle=False, emboss=True)
            
        elif bake_status in ['INPROGRESS', 'PAUSED']:
            col.enabled = any(item.Enabled for item in scene.autobake_queuelist) or any(item.Enabled for item in scene.autobake_objectqueuelist)
            
            if bake_status == 'PAUSED':
                if next_object_bake:
                    col.operator("sparrow.resume_bake", icon="PLAY", text="Resume        ")
                else:
                    col.operator("sparrow.next_object", icon="PLAY", text="Resume & Next Object        ")
            else:
                row_pause = col.row()
                row_pause.enabled = next_object_bake
                row_pause.operator("sparrow.pause_bake", icon="PAUSE", text="Pause        ")

            col.operator("sparrow.cancel_bake", icon="CANCEL", text="Cancel        ")
            
            row = layout.row(align=True)
            sub = row.row()
            sub.label(text="Bake Queue", icon="TEMP")
            sub = row.row(align=True)
            sub.alignment = "RIGHT"
            sub.label(text="Textures: "+str(finished_bake_count)+'/'+str(len(scene.autobake_queuelist)), icon="TEXTURE")
            
        if len(scene.autobake_queuelist) > 0:
            col = layout.column_flow(columns=1)
            col.template_list("SPARROW_UL_BakeQueue", "Bake_Queue_List", scene, "autobake_queuelist", scene, "autobake_queuelist_index", rows=1)

            if len(scene.autobake_objectqueuelist) > 1:
                col.template_list("SPARROW_UL_ObjectQueue", "Object_Queue_List", scene, "autobake_objectqueuelist", scene, "autobake_objectqueuelist_index", rows=1)
    
            if bake_status == 'IDLE' or abp.ab_auto_next == 'Always' or (abp.ab_auto_next == 'On-Success' and next_object_bake):
                confirm_row = col.row()
                confirm_row.enabled = bake_status == 'IDLE'
                confirm_row.operator('sparrow.confirm_bakes', text='Confirm        ', icon='CHECKMARK')
            else:
                confirm_row = col.row()
                confirm_row.enabled = not next_object_bake
                confirm_row.operator('sparrow.next_object', text=' Next Object        ', icon='FRAME_NEXT')
                

class SPARROW_PT_Lists(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Bake"
    bl_idname = "SPARROW_PT_Lists"
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        if abp.ab_udim_bake:
            layout.alert = abp.ab_udimtype_list_item_count < 1
            layout.label(text="Bake List" +(" (" + str(abp.ab_udimtype_list_item_count) +")" if abp.ab_udimtype_list_item_count > 0 else ""), icon="OPTIONS")
        else:
            layout.alert = abp.ab_bake_list_item_count < 1
            layout.label(text="Bake List" +(" (" + str(abp.ab_bake_list_item_count) +")" if abp.ab_bake_list_item_count > 0 else ""), icon="OPTIONS")

    def draw(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        list =  scene.autobake_udimlist if abp.ab_udim_bake else scene.autobake_bakelist
    
    # Layout
        layout = self.layout
        layout = layout.column_flow(columns=1)
        row = layout.row(align=True)

    # Lists
        if abp.ab_udim_bake:
            if abp.ab_list_padding in ['Compact', 'Moderate']:
                row.template_list("SPARROW_UL_UDIMType", "UDIM_Type_List", scene, "autobake_udimlist", scene, "autobake_udimlist_index", rows=4)
            else:
                row.template_list("SPARROW_UL_UDIMType", "UDIM_Type_List", scene, "autobake_udimlist", scene, "autobake_udimlist_index", rows=5)
        else:
            if abp.ab_list_padding in ['Compact', 'Moderate']:
                row.template_list("SPARROW_UL_Bake", "Bake_List", scene, "autobake_bakelist", scene, "autobake_bakelist_index", rows=4)
            else:
                row.template_list("SPARROW_UL_Bake", "Bake_List", scene, "autobake_bakelist", scene, "autobake_bakelist_index", rows=5)   
        
    # Buttons
        if abp.ab_list_padding == 'Compact':
            row = row.row()
            col = row.column(align=True)
            col.operator("sparrow.bakelist_add", icon='ADD', text="")
            if list:
                col.operator("sparrow.bakelist_remove", icon='REMOVE', text="")
                if len(list) > 1:
                    col_a = col.column(align=True)
                    col_a.operator("sparrow.bakelist_move_up", icon='TRIA_UP', text="")
                    col_a.operator("sparrow.bakelist_move_down", icon='TRIA_DOWN', text="")
            col.menu(SPARROW_MT_BakeList.bl_idname, text="", icon="DOWNARROW_HLT")
            
        elif abp.ab_list_padding == 'Moderate':
            row.separator()
            col = row.column(align=False)
            col_c = col.column(align=True)
            col_c.operator("sparrow.bakelist_add", icon='ADD', text="")
            if list:
                col_c.operator("sparrow.bakelist_remove", icon='REMOVE', text="")
                if len(list) > 1:
                    col_a = col.column(align=True)
                    col_a.operator("sparrow.bakelist_move_up", icon='TRIA_UP', text="")
                    col_a.operator("sparrow.bakelist_move_down", icon='TRIA_DOWN', text="")
            col.menu(SPARROW_MT_BakeList.bl_idname, text="", icon="DOWNARROW_HLT")
            
        elif abp.ab_list_padding == 'Spacious':
            row.separator()
            col = row.column(align=True)
            col.operator("sparrow.bakelist_add", icon='ADD', text="")
            if list:
                col.operator("sparrow.bakelist_remove", icon='REMOVE', text="")
                if len(list) > 1:
                    col.separator()
                    col.operator("sparrow.bakelist_move_up", icon='TRIA_UP', text="")
                    col.operator("sparrow.bakelist_move_down", icon='TRIA_DOWN', text="")
            col.separator()
            col.menu(SPARROW_MT_BakeList.bl_idname, text="", icon="DOWNARROW_HLT")
            col.separator()
            col.separator()

    # Type & Size
        if abp.ab_udim_bake and list and abp.ab_udim_item_default:
            item = list[scene.autobake_udimlist_index]
            
            if abp.ab_list_padding in ['Moderate', 'Compact']:
                row = layout.row(align=True)
                
            elif abp.ab_list_padding == 'Spacious':
                row = layout.row(align=False)
                row = row.row(align=False)

            row.scale_x = 1.3
            row.alert = item.IsDuplicate
            row.prop(item, "Type")
            row = row.row()
            row.prop(item, "Size")
    
        elif not abp.ab_udim_bake and list and abp.ab_item_default:
            item = scene.autobake_bakelist[scene.autobake_bakelist_index]
            
            if abp.ab_list_padding in ['Moderate', 'Compact']:
                row = layout.row(align=True)
                
            elif abp.ab_list_padding == 'Spacious':
                row = layout.row(align=False)

            row.alert = item.IsDuplicate
            col1 = row.column()
            col1.scale_x = 1.15
            col1.prop(item, "Type")
            row = row.row(align=True)
            col2 = row.column(align=True)
            col2.scale_x = 1.05
            col2.operator("sparrow.scale_down", text='', icon="TRIA_LEFT")
            row.prop(item, "Size")
            col4 = row.column(align=True)
            col4.scale_x = 1.05
            col4.operator("sparrow.scale_up", text="", icon="TRIA_RIGHT")
        
    # Alerts
        if abp.ab_alert_texts:
            if not len(list):
                row = layout.row()
                row.alert = True
                row.label(text="List can't be empty!")
            
            elif (abp.ab_udimtype_list_item_count if abp.ab_udim_bake else abp.ab_bake_list_item_count) < 1:
                row = layout.row()
                row.alert = True
                row.label(text="List must have an enabled item!")
            
    # Item Specific
        if abp.ab_item_details and list:
            rd = context.scene.render
            image_settings = rd.image_settings
            Type = list[scene.autobake_udimlist_index].Type if abp.ab_udim_bake else list[scene.autobake_bakelist_index].Type

            col = layout.column_flow(columns=1, align=True)
            box = col.box()
            
            row = box.grid_flow(columns = 1)
            split = row.split(factor=.4)
            split.label(text="Name")
            split.alert = len(abp.ab_baketype_name) < 1
            split.prop(abp, "ab_baketype_name", text='')

            cbk = context.scene.render.bake
            
            if Type == 'Combined':
                box = col.box()
                box.alert = not (cbk.use_pass_emit or ((cbk.use_pass_indirect or cbk.use_pass_direct) and (cbk.use_pass_diffuse or cbk.use_pass_glossy or cbk.use_pass_transmission)))
            
                split = box.split(factor=.4)
                
                col = split.column(align=True, heading="")
                col.label(text='Influence')
                col.prop(cbk, "use_pass_direct")
                col.prop(cbk, "use_pass_indirect")
                col.prop(cbk, "use_pass_emit")
                
                col = split.column(align=True, heading="")
                col.active = cbk.use_pass_direct or cbk.use_pass_indirect
                col.label(text='')
                col.prop(cbk, "use_pass_diffuse")
                col.prop(cbk, "use_pass_glossy")
                col.prop(cbk, "use_pass_transmission")
            
                if box.alert and abp.ab_alert_texts:
                    box.label(text="Must use Emit, or a light pass with Direct or Indirect influence!")

            if Type in ['Diffuse', 'Glossy', 'Transmission']:
                box = col.box()
                box.alert = not (cbk.use_pass_direct or cbk.use_pass_indirect or cbk.use_pass_color)
            
                split = box.split(factor=.4)
                
                split.label(text='Influence')
                col = split.column(align=True)
                col.prop(cbk, "use_pass_direct")
                col.prop(cbk, "use_pass_indirect")
                col.prop(cbk, "use_pass_color")
                
                if box.alert and abp.ab_alert_texts:
                    box.label(text="Must enable at least one influence setting!")
                
            if Type in ['Normal', 'Normal ', 'Tangent', 'Coat Normal', 'Clearcoat Normal', 'Subsurface Radius']:
                box = col.box()
                col = box.column()
                
                split = col.split(factor=.4)
                split.label(text="Space")
                split.prop(cbk, "normal_space", text='')
                
                split = col.split(factor=.4)
                split.label(text="Red")
                split.prop(cbk, "normal_r", text='')
                
                split = col.split(factor=.4)
                split.label(text="Green")
                split.prop(cbk, "normal_g", text='')
                
                split = col.split(factor=.4)
                split.label(text="Blue")
                split.prop(cbk, "normal_b", text='')

            if Type == 'Channel Packing': 
                box = col.box()
                box.alert = abp.ab_channel_pack_r == "None" and abp.ab_channel_pack_g == "None" and abp.ab_channel_pack_b == "None"
                
                col = box.column()
                
                split = col.split(factor=.4)
                split.label(text="Red")
                split.prop(abp, "ab_channel_pack_r", text='')
                
                split = col.split(factor=.4)
                split.label(text="Green")
                split.prop(abp, "ab_channel_pack_g", text='')
                
                split = col.split(factor=.4)
                split.label(text="Blue")
                split.prop(abp, "ab_channel_pack_b", text='')
                
                if box.alert and abp.ab_alert_texts:
                    box.label(text="Can't all be set to 'None'!")
                
            if Type == 'Displacement':
                box = col.box()
                col = box.column()

                split = col.split(factor=.4)
                split.label(text="Viewport Level")
                split.prop(abp, "ab_multires_level", text='')
                
                split = col.split(factor=.4)
                split.label(text="Mesh Resolution")
                rd = scene.render
                split.prop(rd, "use_bake_lores_mesh", invert_checkbox=True, text='High      ', toggle=True, icon='CHECKBOX_DEHLT' if rd.use_bake_lores_mesh else 'CHECKBOX_HLT')

            if Type == 'Normals':
                box = col.box()
                col = box.column()

                split = col.split(factor=.4)
                split.label(text="Viewport Level")
                split.prop(abp, "ab_multires_level", text='')
                
            if Type == 'Ambient Occlusion ':
                box = col.box()
                col = box.column()
                
                split = col.split(factor=.4)
                split.label(text="Local Only")
                split.alert = scene.render.bake.use_selected_to_active and abp.ab_ao_local_only == 'COLLECTION'
                split.prop(abp, "ab_ao_local_only", icon='RESTRICT_RENDER_OFF', text='')

                split = col.split(factor=.4)
                split.label(text="Normal")
                split.prop(abp, "ab_ao_use_normal", toggle=True, text="Use")

            if Type == 'Ambient Occlusion':
                box = col.box()
                col = box.column()

                split = col.split(factor=.4)
                split.label(text="Sample")
                row = split.row(align=True)
                row.prop(abp, "ab_ao_sample_use", text='')
                row = row.row()
                row.active = abp.ab_ao_sample_use
                row.prop(abp, "ab_ao_sample", text='')
                
                split = col.split(factor=.4)
                split.label(text="Inside")
                split.prop(abp, "ab_ao_inside", text='Enabled      ', toggle=True, icon='CHECKBOX_HLT' if abp.ab_ao_inside else 'CHECKBOX_DEHLT')
                
                split = col.split(factor=.4)
                split.label(text="Only Local")
                split.prop(abp, "ab_ao_only_local", text='Enabled      ', toggle=True, icon='CHECKBOX_HLT' if abp.ab_ao_only_local else 'CHECKBOX_DEHLT')
                
                split = col.split(factor=.4)
                split.label(text="Distance")
                split.prop(abp, "ab_ao_distance", text='')
                
            if Type == 'Pointiness':
                box = col.box()
                col = box.column()

                split = col.split(factor=.4)
                split.label(text="Contrast")
                split.prop(abp, "ab_pointiness_contrast", text='')
                
                split = col.split(factor=.4)
                split.label(text="Brightness")
                split.prop(abp, "ab_pointiness_brightness", text='')
                
            if Type == 'Displacement ':
                box = col.box()
                col = box.column(align=True)
                
                split = col.split(factor=.4)
                split.label(text="Source Only")
                split.prop(abp, "ab_displacement_source", text='Enabled      ', toggle=True, icon='CHECKBOX_HLT' if abp.ab_displacement_source else 'CHECKBOX_DEHLT')
                
            if Type == 'UV':
                box = col.box()
                col = box.column()
                
                split = col.split(factor=.4)
                split.label(text="UV Map")
                split.prop(abp, "ab_uv_target", text='')
                
            if Type == 'Color Attribute':
                box = col.box()
                col = box.column()
                
                split = col.split(factor=.4)
                split.label(text="Color Attribute")
                split.prop(abp, "ab_attribute_target", text='')
                

class SPARROW_PT_List_UDIM(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Lists"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_udim_bake == True
    
    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        layout.alert = abp.ab_udim_list_item_count < 1
        layout.label(text="UDIM Tiles" +(" (" + str(abp.ab_udim_list_item_count) +")" if abp.ab_udim_list_item_count > 0 else ""), icon="UV_FACESEL")
        
    def draw(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        list = scene.autobake_udimtilelist
        
        layout = self.layout
        layout = layout.column_flow(columns=1)

        row = layout.row(align=True)
        if abp.ab_list_padding in ['Compact', 'Moderate']:
            row.template_list("SPARROW_UL_UDIMTile", "UDIM_List", scene, "autobake_udimtilelist", scene, "autobake_udimtilelist_index", rows=4)
        else:
            row.template_list("SPARROW_UL_UDIMTile", "UDIM_List", scene, "autobake_udimtilelist", scene, "autobake_udimtilelist_index", rows=5)

    # Buttons
        if abp.ab_list_padding == 'Compact':
            row = row.row()
            col = row.column(align=True)
            col.operator(SPARROW_OT_Add_UDIM.bl_idname, icon='ADD', text="")
            if list:
                col.operator(SPARROW_OT_Remove_UDIM.bl_idname, icon='REMOVE', text="")
                if len(list) > 1:
                    col_a = col.column(align=True)
                    col_a.operator(SPARROW_OT_Up_UDIM.bl_idname, icon='TRIA_UP', text="")
                    col_a.operator(SPARROW_OT_Down_UDIM.bl_idname, icon='TRIA_DOWN', text="")
            col.menu(SPARROW_MT_UDIMList.bl_idname, text="", icon="DOWNARROW_HLT")
            
        elif abp.ab_list_padding == 'Moderate':
            row.separator()
            col = row.column(align=False)
            col_c = col.column(align=True)
            col_c.operator(SPARROW_OT_Add_UDIM.bl_idname, icon='ADD', text="")
            if list:
                col_c.operator(SPARROW_OT_Remove_UDIM.bl_idname, icon='REMOVE', text="")
                if len(list) > 1:
                    col_a = col.column(align=True)
                    col_a.operator(SPARROW_OT_Up_UDIM.bl_idname, icon='TRIA_UP', text="")
                    col_a.operator(SPARROW_OT_Down_UDIM.bl_idname, icon='TRIA_DOWN', text="")
            col.menu(SPARROW_MT_UDIMList.bl_idname, text="", icon="DOWNARROW_HLT")
            
        elif abp.ab_list_padding == 'Spacious':
            row.separator()
            col = row.column(align=True)
            col.operator(SPARROW_OT_Add_UDIM.bl_idname, icon='ADD', text="")
            if list:
                col.operator(SPARROW_OT_Remove_UDIM.bl_idname, icon='REMOVE', text="")
                if len(list) > 1:
                    col.separator()
                    col.operator(SPARROW_OT_Up_UDIM.bl_idname, icon='TRIA_UP', text="")
                    col.operator("sparrow.udimlist_down", icon='TRIA_DOWN', text="")
            col.separator()
            col.menu(SPARROW_MT_UDIMList.bl_idname, text="", icon="DOWNARROW_HLT")
            col.separator()
            col.separator()
        
        
        if len(list) > 0 and abp.ab_udim_item_tilescale_default:
            item = scene.autobake_udimtilelist[scene.autobake_udimtilelist_index]
            
            if abp.ab_list_padding in ['Moderate', 'Compact']:
                row = layout.row(align=True)
                
            elif abp.ab_list_padding == 'Spacious':
                row = layout.row(align=False)
            
            col1 = row.column()
            col1.alert = item.IsDuplicate
            col1.scale_x = 1.15
            col1.prop(item, "UDIM")
            row = row.row(align=True)
            col2 = row.column(align=True)
            col2.scale_x = 1.05
            col2.operator("sparrow.scale_down", text="", icon="TRIA_LEFT")
            row.prop(item, "Size")
            col4 = row.column(align=True)
            col4.scale_x = 1.05
            col4.operator("sparrow.scale_up", text="", icon="TRIA_RIGHT")
        
        if abp.ab_alert_texts:
            if not len(list):
                row = layout.row()
                row.alert = True
                row.label(text="List can't be empty!")
            
            elif abp.ab_udim_list_item_count < 1:
                row = layout.row()
                row.alert = True
                row.label(text="List must have an enabled item!")


class SPARROW_PT_Image(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Bake"
    bl_idname = "SPARROW_PT_Image"
    bl_label = ""

    def draw_header(self, context):
        self.layout.label(text="Image", icon="IMAGE")

    def draw(self, context):
        pass


class SPARROW_PT_Name(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Image"
    bl_label = ""
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(text='Name')
        row = layout.row()
        row.active=False
        row.operator('sparrow.edit_name_structure', text='', icon='GREASEPENCIL', emboss=False)
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
      
        col = layout.column()
      
        split = col.split(factor=.4)
        split.label(text="Prefix")
        split.prop(abp, "ab_prefix", text="")
        
        split = col.split(factor=.4)
        split.label(text="Bridge")
        split.prop(abp, "ab_bridge", text="")
        
        split = col.split(factor=.4)
        split.label(text="Suffix")
        split.prop(abp, "ab_suffix", text="")


class SPARROW_PT_Format(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Image"
    bl_label = "Format"
    
    def draw(self, context):
        layout = self.layout
        scene: Scene = context.scene
        abp = scene.autobake_properties
        image_settings = scene.render.image_settings
        file_format = image_settings.file_format

        col = layout.column()

        split = col.split(factor=.4)
        split.label(text="File Format")
        split.prop(abp, "ab_fileformat", text="", icon="IMAGE_DATA")
        
        split = col.split(factor=.4)
        split.label(text="Use Float")
        split.prop(abp, "ab_floatbuffer", text=str(abp.ab_floatbuffer), toggle=True, expand=True)           
            
        if abp.ab_fileformat in ["PNG", "OPEN_EXR_MULTILAYER", "OPEN_EXR", "TIFF", "JPEG2000", "DPX"]:
            split = col.split(factor=.4)
            split.label(text="Color Depth")
            split.row().prop(image_settings, "color_depth", text=' ', expand=True)
        
        if abp.ab_fileformat == "PNG":
            split = col.split(factor=.4)
            split.label(text="Compression")
            split.prop(image_settings, "compression", text="")

        if abp.ab_fileformat in ["JPEG", "JPEG2000", "WEBP"]:
            split = col.split(factor=.4)
            split.label(text="Quality")
            split.prop(image_settings, "quality", text="")
            
        if abp.ab_fileformat == "JPEG2000":
            split = col.split(factor=.4)
            split.label(text="Codec")
            split.prop(image_settings, "jpeg2k_codec", text="")

            split = col.split(factor=.4)
            split.label(text="Cinema")
            split.prop(image_settings, "use_jpeg2k_cinema_preset", text=str(image_settings.use_jpeg2k_cinema_preset), toggle=True, expand=True)
            
            split = col.split(factor=.4)
            split.label(text="Cinema (48)")
            split.prop(image_settings, "use_jpeg2k_cinema_48", text=str(image_settings.use_jpeg2k_cinema_48), toggle=True, expand=True)
            
            split = col.split(factor=.4)
            split.label(text="YCC")
            split.prop(image_settings, "use_jpeg2k_ycc", text=str(image_settings.use_jpeg2k_ycc), toggle=True, expand=True)
            
        if abp.ab_fileformat == "DPX":
            split = col.split(factor=.4)
            split.label(text="Log")
            split.prop(image_settings, "use_cineon_log", text=str(image_settings.use_cineon_log), toggle=True, expand=True)
        
        if abp.ab_fileformat in ["OPEN_EXR_MULTILAYER", "OPEN_EXR"]:
            split = col.split(factor=.4)
            split.label(text="Codec")
            split.prop(image_settings, "exr_codec", text="")

        if abp.ab_fileformat == "TIFF":
            split = col.split(factor=.4)
            split.label(text="Compression")
            split.prop(image_settings, "tiff_codec", text="")
            
            
class SPARROW_PT_Export(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Image"
    bl_idname = "SPARROW_PT_Export"
    bl_label = "Export"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        row = layout.row()
        row.label(text="File Path", icon="EXPORT")
        sub = row.row(align=True)
        sub.alignment = "RIGHT"
        sub.prop(abp, "ab_subfolders", text="Subfolders", toggle=False)

        column = layout.column(align=True)
        row = column.row(align=True)
        col = row.column(align=True)
        col.alert = not bool(os.path.exists(abp.ab_filepath))
        col.prop(abp, "ab_filepath", text="")
        row.operator("sparrow.file_explorer", text="", icon='FILEBROWSER')
        
        if abp.ab_alert_texts and col.alert:
            row = column.row()
            row.alert = True
            row.label(text="Filepath is Invalid!")
        
        
class SPARROW_PT_ColorOverride(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Export"
    bl_idname = 'SPARROW_PT_ColorOverride'
    bl_label = ""
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        self.layout.prop(abp, "ab_custom_color_management", text="Color Override")
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        image_settings = scene.render.image_settings
        abp = scene.autobake_properties
    
        layout.enabled = abp.ab_custom_color_management
 
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        layout.row().prop(image_settings, "color_management", text=" ", expand=True)
        
        flow = layout.grid_flow(row_major=True, columns=1, even_columns=False, even_rows=False, align=True)

        if image_settings.color_management == 'OVERRIDE':
            owner = image_settings
        else:
            owner = scene
            flow.enabled = False

        col = flow.column()

        if image_settings.has_linear_colorspace:
            if hasattr(owner, "linear_colorspace_settings"):
                col.prop(owner.linear_colorspace_settings, "name", text="Color Space")
        else:
            col.prop(owner.display_settings, "display_device")
            col.separator()         
            col.template_colormanaged_view_settings(owner, "view_settings")


class SPARROW_PT_Settings(SPARROW_PT_Main, Panel):
    bl_parent_id = 'SPARROW_PT_Bake'
    bl_idname = "SPARROW_PT_Settings"
    bl_label = ""

    def draw_header(self, context):
        self.layout.label(text="Settings", icon="TOOL_SETTINGS")
        
    def draw(self, context):
        pass

        
class SPARROW_PT_Margin(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Settings"
    bl_label = "Margin"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        cbk = scene.render.bake

        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text="Type")
        split.prop(cbk, "margin_type", text="")

        split = col.split(factor=.4)
        split.label(text="Size")
        split.prop(cbk, "margin", text="")
        
        split = col.split(factor=.4)
        split.label(text="")
        split.prop(abp, "ab_adaptive_margin", text="Auto Adjust")
        
        
class SPARROW_PT_SelectedToActive(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Settings"
    bl_idname = 'SPARROW_PT_SelectedToActive'
    bl_label = ""
    
    def draw_header(self, context):
        cbk = context.scene.render.bake
        self.layout.prop(cbk, "use_selected_to_active", text="Selected to Active")
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        cbk = scene.render.bake
        abp = scene.autobake_properties

        layout.active = cbk.use_selected_to_active

        col = layout.column()

        split = col.split(factor=.4)
        split.label(text="Cage")
        split.prop(cbk, "use_cage", text='Use       ', toggle=True,  icon='CHECKBOX_HLT' if cbk.use_cage else 'CHECKBOX_DEHLT')

        if cbk.use_cage:
            split = col.split(factor=.4)
            split.label(text="Cage Object")
            split.prop(cbk, "cage_object", text="")

        split = col.split(factor=.4)
        split.label(text="Cage Extrusion" if cbk.use_cage else "Extrusion")
        split.prop(cbk, "cage_extrusion", text="")
        
        split = col.split(factor=.4)
        split.label(text="Max Ray Distance")
        split.prop(cbk, "max_ray_distance", text="")
        
        split = col.split(factor=.4)
        split.label(text="")
        split.prop(abp, "ab_active_as_final")
        

class SPARROW_PT_SelectionHelp(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_SelectedToActive"
    bl_label = "Selection Helper"
    bl_options = {'DEFAULT_CLOSED'}
    
    target_error = StringProperty(options = set(), default='None')
    source_error = StringProperty(options = set(), default='None')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        self.target_error = "None"
        self.source_error = "None"
        if layout.enabled:
            if abp.ab_target_object == None:
                self.target_error = "Select an object!"
            elif abp.ab_target_object.name not in bpy.context.scene.objects:
                self.target_error = "Object is not from this scene!"
            elif abp.ab_target_object.type != 'MESH':
                self.target_error = "Object is not a 'Mesh'"

            if abp.ab_source_object_method == 'COLLECTION':
                if abp.ab_source_collection == None:
                    self.source_error = "Select a collection!"
                elif abp.ab_source_collection not in scene.collection.children_recursive:
                    self.source_error = "Collection is not from this scene!"
                elif not len(abp.ab_source_collection.objects):
                    self.source_error = "Collection is empty!"
                    
            elif len(scene.autobake_sourceobject) < 2:
                self.source_error = "List can't be empty!"
                
        layout.active = scene.render.bake.use_selected_to_active

        row = layout.row()
        row.enabled = self.target_error == "None" and self.source_error == "None" and layout.active
        row.operator('sparrow.select_from_list', text='Select Objects      ', icon='SELECT_SET')
        
        split = layout.split(factor=.4)
        split.label(text='Target Object')
        col = split.column(align=True)
        col.alert = layout.active and self.target_error != "None"
        col.prop(abp, 'ab_target_object', text='')

        if layout.active and abp.ab_alert_texts and self.target_error != "None":
            col.label(text=self.target_error)
                
        split = layout.split(factor=.4)
        split.label(text='Source Objects')
        
        if abp.ab_source_object_method == 'COLLECTION':
            col = split.column()
            col.alert = layout.active and self.source_error != "None"
            col.row().prop(abp, "ab_source_object_method", text=' ', expand=True)
            col.prop(abp, "ab_source_collection", text='')

            if layout.active and abp.ab_alert_texts and self.source_error != "None":
                col.label(text=self.source_error)
        else:
            split.row().prop(abp, "ab_source_object_method", text=' ', expand=True)

            col = layout.column(align=True)
            col.alert = layout.active and self.source_error != "None"
            col.template_list("SPARROW_UL_SourceObjects", "Source_Objects", scene, "autobake_sourceobject", scene, "autobake_sourceobject_index", rows=2)
            col.operator('sparrow.load_selected_objects', icon='IMPORT', text='Load from Selected      ')
            
            if layout.active and abp.ab_alert_texts and self.source_error != "None":
                row = layout.row()
                row.alert = True
                row.label(text=self.source_error)


class SPARROW_PT_Sampling(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Settings"
    bl_idname = "SPARROW_PT_Sampling"
    bl_label = "Sampling"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties        

        col = layout.column()
        
        split = col.split(factor=.4)
        split.alignment = 'RIGHT'
        split.label(text="Render Sampling")
        split.prop(abp, "ab_sampling_use_render", toggle=True, text='Use       ', icon='CHECKBOX_HLT' if abp.ab_sampling_use_render else 'CHECKBOX_DEHLT')
        
        if not abp.ab_sampling_use_render:
            split = col.split(factor=.4)
            split.active = not abp.ab_sampling_use_render
            split.label(text="")
            split.prop(abp, "ab_auto_pick_sampling")
        
        else:
            cscene = scene.cycles
            
            split = col.split(factor=.4)
            split.label(text="")
            split.prop(cscene, "use_adaptive_sampling", text='Adaptive Sampling')
            
            if cscene.use_adaptive_sampling:
                split = col.split(factor=.4)
                split.alignment = 'RIGHT'
                split.label(text="Noise Threshold")
                split.prop(cscene, "adaptive_threshold", text="")
            
            split = col.split(factor=.4)
            split.alignment = 'RIGHT'
            split.label(text="Max Samples" if cscene.use_adaptive_sampling else "Samples")
            split.prop(cscene, "samples", text="")
            
            if cscene.use_adaptive_sampling:
                split = col.split(factor=.4)
                split.alignment = 'RIGHT'
                split.label(text="Min Samples")
                split.prop(cscene, "adaptive_min_samples", text="")
                
            split = col.split(factor=.4)
            split.alignment = 'RIGHT'
            split.label(text="Time Limit")
            split.prop(cscene, "time_limit", text="")
        

class SPARROW_PT_Denoise(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Sampling"
    bl_label = ""
    bl_options = {'DEFAULT_CLOSED'}
        
    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_sampling_use_render
    
    def draw_header(self, context):
        scene = context.scene
        self.layout.prop(scene.cycles, "use_denoising", text="Denoise")                     
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        cscene = scene.cycles
        
        layout.active = cscene.use_denoising
        
        split = layout.split(factor=.4)
        split.label(text="Denoiser")
        split.prop(cscene, "denoiser", text="")

        split = layout.split(factor=.4)
        split.label(text="Passes")
        split.prop(cscene, "denoising_input_passes", text="") 
        
        if cscene.denoiser == 'OPENIMAGEDENOISE':
            row = layout.row()
            split = row.split(factor=.4)
            split.label(text="Prefilter")
            split.prop(cscene, "denoising_prefilter", text="")


class SPARROW_PT_Sampling_Low(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Sampling"
    bl_idname = "SPARROW_PT_Sampling_Low"
    bl_label = "Low"
        
    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_sampling_use_render == False
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
    
        layout.use_property_split = True
        layout.use_property_decorate = False
    
        col = layout.column()
        col.prop(abp, 'ab_sampling_low_adaptive')
        
        if abp.ab_sampling_low_adaptive:
            col.prop(abp, 'ab_sampling_low_noise_threshold')
            col.prop(abp, 'ab_sampling_low_max')
            col.prop(abp, 'ab_sampling_low_min')
        else:
            col.prop(abp, 'ab_sampling_low_max', text='Samples')
        
        col.prop(abp, 'ab_sampling_low_time_limit')
        

class SPARROW_PT_Denoise_Low(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Sampling_Low"
    bl_label = ""
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        scene = context.scene
        self.layout.prop(context.scene.autobake_properties, "ab_sampling_low_denoise")                     
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = abp.ab_sampling_low_denoise
        
        col = layout.column()
        col.prop(abp, 'ab_sampling_low_denoiser')
        col.prop(abp, 'ab_sampling_low_passes')
        col = col.column()
        col.active = abp.ab_sampling_low_denoiser == 'OPENIMAGEDENOISE'
        col.prop(abp, 'ab_sampling_low_prefilter')


class SPARROW_PT_Sampling_High(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Sampling"
    bl_idname = "SPARROW_PT_Sampling_High"
    bl_label = "High" 
        
    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_sampling_use_render == False
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
    
        layout.use_property_split = True
        layout.use_property_decorate = False
    
        col = layout.column()
        col.prop(abp, 'ab_sampling_high_adaptive')
        
        if abp.ab_sampling_high_adaptive:
            col.prop(abp, 'ab_sampling_high_noise_threshold')
            col.prop(abp, 'ab_sampling_high_max')
            col.prop(abp, 'ab_sampling_high_min')
        else:
            col.prop(abp, 'ab_sampling_high_max', text='Samples')
        
        col.prop(abp, 'ab_sampling_high_time_limit')


class SPARROW_PT_Denoise_High(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Sampling_High"
    bl_label = ""
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        scene = context.scene
        self.layout.prop(context.scene.autobake_properties, "ab_sampling_high_denoise")                     
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = abp.ab_sampling_high_denoise
        
        col = layout.column()
        col.prop(abp, 'ab_sampling_high_denoiser')
        col.prop(abp, 'ab_sampling_high_passes')
        col = col.column()
        col.active = abp.ab_sampling_high_denoiser == 'OPENIMAGEDENOISE'
        col.prop(abp, 'ab_sampling_high_prefilter')
            
                
class SPARROW_PT_Addon(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_Bake"
    bl_idname = "SPARROW_PT_addon_settings"
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text='Addon', icon='PLUGIN')
        
    def draw(self, context):
        pass   


class SPARROW_PT_ImageSettings(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_addon_settings"
    bl_label = "Textures"
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        col = layout.column()

        split = col.split(factor=.4)
        split.label(text="Pack Images")
        split.prop(abp, "ab_pack_texture", text='Pack      ', toggle=True, icon='PACKAGE' if abp.ab_pack_texture else 'UGLYPACKAGE')
        
        split = col.split(factor=.4)
        split.label(text="Fake User")
        split.prop(abp, "ab_textures_fakeuser", text='Use      ', toggle=True, icon='FAKE_USER_ON' if abp.ab_textures_fakeuser else 'FAKE_USER_OFF')

        split = col.split(factor=.4)
        split.label(text='Anti-aliasing')
        
        col2 = split.column(align=True, heading="")
        col2.prop(abp, "ab_scaled_antialiasing", text='')
        
        if abp.ab_scaled_antialiasing == 'UPSCALED':
            col2.prop(abp, "ab_antialiasing_upscaled", text='Upscale')
            
        elif abp.ab_scaled_antialiasing == 'DOWNSCALED':
            col2.prop(abp, "ab_antialiasing_downscaled", text='Downscale', slider=True)
            col2.prop(abp, "ab_antialiasing_repeat", text='Iteration ')
        
        split = col.split(factor=.4)
        split.label(text='Color Space')
        split.menu(SPARROW_MT_ColorSpace.bl_idname, text='Texture Type', icon='COLOR')
        
        split = col.split(factor=.4)
        split.label(text="Shared Textures")
        split.prop(abp, "ab_shared_textures", text='Enabled      ', toggle=True,  icon='CHECKBOX_HLT' if abp.ab_shared_textures else 'CHECKBOX_DEHLT')
    
        
class SPARROW_PT_Materials(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_addon_settings"
    bl_label = "Materials"
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text="Image Textures")
        split.prop(abp, "ab_remove_imagetextures", text=str('Remove      '), toggle=True, icon='TRASH')
        
        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text='Final Material')
        split.prop(abp, "ab_final_material", text='Create      ', icon='MATERIAL')
        
        split = col.split(factor=.4)
        split.active = abp.ab_final_material
        split.label(text='Material Shader')
        split.prop(abp, "ab_final_shader", text='', icon='MATSHADERBALL')
        
        split = col.split(factor=.4)
        split.active = abp.ab_final_material
        split.label(text='Apply Textures')
        split.prop(abp, "ab_apply_textures", text='', icon='NODE_TEXTURE')
        
        col = layout.column()
        col.active = not abp.ab_remove_imagetextures or abp.ab_final_material
        
        split = col.split(factor=.4)
        split.label(text="Node Tiling")
        split.prop(abp, "ab_node_tiling", text='', toggle=True, icon='NODE_CORNER')
        
        split = col.split(factor=.4)
        split.label(text="Node Labels")
        split.prop(abp, "ab_node_label", text='', toggle=True, icon='NODE')
        
        
class SPARROW_PT_Objects(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_addon_settings"
    bl_idname = "SPARROW_PT_objects"
    bl_label = "Objects"
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        layout.active = not scene.render.bake.use_selected_to_active or not abp.ab_active_as_final
        
        col = layout.column()

        split = col.split(factor=.4)
        split.label(text="Final Object")
        split.prop(abp, "ab_final_object", text='Create      ', icon='OBJECT_DATAMODE')
        
        col = col.column()
        col.active = abp.ab_final_object and (not abp.ab_export_object or (abp.ab_export_object and not abp.ab_export_object_remove))

        split = col.split(factor=.4)
        split.label(text="Collection")
        row = split.row(align=True)
        row_b = row.row(align=True)
        row_b.alignment = 'LEFT'
        row_b.prop(abp, 'ab_final_collection_color', text='', icon_only=True)
        row.prop(abp, 'ab_final_collection', text='')

        split = col.split(factor=.4)
        split.label(text="Keep Name")
        split.row().prop(abp, "ab_object_keep_name", text='', icon='OBJECT_DATAMODE')
        
        split = col.split(factor=.4)
        split.alert = abp.ab_object_differentiator == ''
        split.label(text="Differentiator")
        
        
        col_b = split.column(align=True)
        col_b.prop(abp, "ab_object_differentiator", text='')
        
        if split.alert:
            col_b.label(text="This shouldn't be none!")

        split = col.split(factor=.4)
        split.label(text="Location")
        split.row().prop(abp, "ab_object_location", text=' ', expand=True)
        
        split = col.split(factor=.4)
        split.active = abp.ab_object_location == 'Copy'
        split.label(text="Location Offset")
        row = split.row(align=True)
        row_b = row.row(align=True)
        row_b.alignment = 'LEFT'
        row_b.prop(abp, 'ab_offset_direction', text='')
        row.prop(abp, 'ab_object_offset', text='')
        
        
class SPARROW_PT_ObjectExport(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_objects"
    bl_idname = "SPARROW_PT_objectexport"
    bl_label = ""
    bl_options = {'DEFAULT_CLOSED'}
        
    def draw_header(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        self.layout.active = abp.ab_final_object or scene.render.bake.use_selected_to_active
        self.layout.prop(abp, "ab_export_object", text="Export Object")
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        layout.active = abp.ab_export_object and (abp.ab_final_object or scene.render.bake.use_selected_to_active)

        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text="Export When")
        split.prop(abp, "ab_export_always", text='')
        
        split = col.split(factor=.4)
        split.label(text="Final Object")
        split.prop(abp, "ab_export_object_remove", text='Delete       ', toggle=True, icon='TRASH')
        
        split = col.split(factor=.4)
        split.label(text="Clear Transform")
        row = split.row(align=True)
        row.prop(abp, 'ab_export_clear_location', toggle=True, text='Loc')
        row.prop(abp, 'ab_export_clear_rotation', toggle=True, text='Rot')
        row.prop(abp, 'ab_export_clear_scale', toggle=True, text='Scale')
        
        split = col.split(factor=.4)
        split.label(text="")
        split.active = not abp.ab_export_object_remove and (abp.ab_export_clear_location or abp.ab_export_clear_rotation or abp.ab_export_clear_scale)
        split.prop(abp, "ab_export_restore_transform")
        
        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text="Export As")
        split.prop(abp, "ab_export_object_as", text='')
        
        if abp.ab_export_object_as == 'GLTF':
            split = col.split(factor=.4)
            split.label(text="Format")
            split.prop(abp, "ab_gltf_format", text='')
            
            split = col.split(factor=.4)
            split.label(text="Copyright")
            split.prop(abp, "ab_gltf_copyright", text='')
            
            split = col.split(factor=.4)
            split.label(text="Lighting Mode")
            split.prop(abp, "ab_gltf_lighting", text='')
            
            split = col.split(factor=.4)
            split.label(text="")
            split.prop(abp, "ab_gltf_original_spelucar", text='Original Specular')

            split = col.split(factor=.4)
            split.label(text="")
            split.prop(abp, "ab_gltf_yup", text='+Y Up')
        
        else:
            split = col.split(factor=.4)
            split.label(text="Path Mode")
            row = split.row(align=True)
            row.prop(abp, "ab_export_pathmode", text='')
            
            if abp.ab_export_object_as == 'FBX':
                sub = row.row(align=True)
                sub.enabled = abp.ab_export_pathmode == 'COPY'
                sub.prop(abp, "ab_export_embedtextures", text='', icon='PACKAGE' if abp.ab_export_embedtextures else 'UGLYPACKAGE', icon_only=True)
        
        
class SPARROW_PT_Transform(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_objectexport"
    bl_label = ""
        
    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_export_object_as in ['FBX', 'OBJ']
    
    def draw_header(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        self.layout.active = abp.ab_final_object and abp.ab_export_object
        self.layout.label(text="Transform")
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = abp.ab_final_object and abp.ab_export_object

        col = layout.column()
        
        if abp.ab_export_object_as == 'FBX':
            col.prop(abp, "ab_export_scale", text='Scale')
            col.prop(abp, "ab_fbx_apply_scaling", text='Apply Scalings')
            col.prop(abp, "ab_fbx_forward")
            col.prop(abp, "ab_fbx_up")
            col.prop(abp, "ab_export_applyunit")
            col.prop(abp, "ab_export_usespacetransform")
        
        elif abp.ab_export_object_as == 'OBJ':
            col.prop(abp, "ab_export_scale", text='Scale')
            col.prop(abp, "ab_obj_forward")
            col.prop(abp, "ab_obj_up")
           

class SPARROW_PT_Geometry(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_objectexport"
    bl_label = ""
        
    def draw_header(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        self.layout.active = abp.ab_final_object and abp.ab_export_object
        self.layout.label(text="Mesh" if abp.ab_export_object_as != 'FBX' else 'Geometry')
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = abp.ab_final_object and abp.ab_export_object

        col = layout.column(align=True)
        
        if abp.ab_export_object_as == 'FBX':
            col.prop(abp, "ab_export_smoothing")
            col.prop(abp, "ab_export_subdivisionsurface")
            col.prop(abp, "ab_export_applymodifiers")
            col.prop(abp, "ab_export_looseedges")
            col.prop(abp, "ab_export_triangulatefaces")
            col.prop(abp, "ab_export_tangentspace")
            col.prop(abp, "ab_export_vertexcolors")
            col.prop(abp, "ab_export_prioritizeactivecolor")
            col.prop(abp, "ab_export_evalmode")
            col.prop(abp, "ab_export_customprops")

        elif abp.ab_export_object_as == 'OBJ':
            col.prop(abp, "ab_export_applymodifiers")
            col.prop(abp, "ab_export_evalmode")
            col.prop(abp, "ab_export_exportcolors")
            col.prop(abp, "ab_export_vertexgroups")
            col.prop(abp, "ab_export_triangulatedmesh")
            col.prop(abp, "ab_export_pbrextension")
            col.prop(abp, "ab_export_smoothgroups")
            col.prop(abp, "ab_export_groupbitflag")

        elif abp.ab_export_object_as == 'GLTF':
            col.prop(abp, "ab_export_applymodifiers")
            col.prop(abp, "ab_gltf_tangents")
            col.prop(abp, "ab_gltf_vertex_colors")
            col.prop(abp, "ab_gltf_attributes")
            col.prop(abp, "ab_gltf_loose_edges")
            col.prop(abp, "ab_gltf_loose_points")


class SPARROW_PT_Images_GLTF(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_objectexport"
    bl_label = ""
        
    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_export_object_as == 'GLTF'
        
    def draw_header(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        self.layout.active = abp.ab_final_object and abp.ab_export_object
        self.layout.label(text='Images')
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
        
        layout.active = abp.ab_final_object and abp.ab_export_object

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=False)
        col.prop(abp, "ab_gltf_images")
        
        col = layout.column(align=True)
        col.active = abp.ab_gltf_images != 'NONE'
        row = col.row()
        row.active = not abp.ab_gltf_keep_original
        row.prop(abp, "ab_gltf_texture_folder", icon='FILE_FOLDER')
        
        col.prop(abp, "ab_gltf_keep_original")
        col.prop(abp, "ab_gltf_image_quality")
        col.prop(abp, "ab_gltf_create_webp")
        col.prop(abp, "ab_gltf_webp_fallback")


class SPARROW_PT_ShapeKeys_GTLF(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_objectexport"
    bl_label = ""
        
    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_export_object_as == 'GLTF'
        
    def draw_header(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        self.layout.active = abp.ab_final_object and abp.ab_export_object
        self.layout.prop(abp, "ab_gltf_shape_keys")
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = abp.ab_final_object and abp.ab_export_object and abp.ab_gltf_shape_keys

        col = layout.column(align=True)
        col.prop(abp, "ab_gltf_shape_keys_normals")
        col.prop(abp, "ab_gltf_shape_keys_tangents")
        col.prop(abp, "ab_gltf_use_sparse")
        col.prop(abp, "ab_gltf_omitting_sparse")


class SPARROW_PT_Compression_GLTF(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_objectexport"
    bl_label = ""
        
    @classmethod
    def poll(cls, context):
        return context.scene.autobake_properties.ab_export_object_as == 'GLTF'
        
    def draw_header(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        self.layout.active = abp.ab_final_object and abp.ab_export_object
        self.layout.prop(abp, "ab_gltf_compression")
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = abp.ab_final_object and abp.ab_export_object and abp.ab_gltf_compression

        col = layout.column(align=True)
        col.prop(abp, "ab_gltf_compression_level")
        col = layout.column(align=True)
        col.prop(abp, "ab_gltf_compression_position")
        col.prop(abp, "ab_gltf_compression_normal")
        col.prop(abp, "ab_gltf_compression_texcoord")
        col.prop(abp, "ab_gltf_compression_color")
        col.prop(abp, "ab_gltf_compression_generic")


class SPARROW_PT_BakeList(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_addon_settings"
    bl_label = "Bake Items"
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
    
        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text="Add New")
        split.row().prop(abp, "ab_new_item_method", text=' ', expand=True)

        split = col.split(factor=.4)
        split.label(text="Dynamic Scale")
        split.prop(abp, "ab_dynamic_scale", text='')
        
        col = layout.column()

        split = col.split(factor=.4)
        split.label(text="Bake List")
        split.menu(SPARROW_MT_ItemEdit.bl_idname, icon='PRESET')
        
        split = col.split(factor=.4)
        split.label(text="UDIM List")
        split.menu(SPARROW_MT_ItemEdit_UDIM.bl_idname, icon="PRESET")
        

class SPARROW_PT_BakeQueue(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_addon_settings"
    bl_label = "Bake Queue"
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties
    
        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text="Finished Bake")
        split.prop(abp, "ab_move_finished_bake", text='Move Down'+'      ', toggle=True, icon='SORT_ASC')
        
        split = col.split(factor=.4)
        split.active = not abp.ab_move_finished_bake
        split.label(text="Active Bake")
        split.prop(abp, "ab_move_active_bake", text='Move Up'+'      ', toggle=True, icon='SORT_DESC')
        
        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text='Next Object')
        split.prop(abp, 'ab_auto_next', text='')
        
        split = col.split(factor=.4)
        split.label(text='Confirm Results')
        split.prop(abp, 'ab_auto_confirm', text='')
        
        
class SPARROW_PT_Miscellaneous(SPARROW_PT_Main, Panel):
    bl_parent_id = "SPARROW_PT_addon_settings"
    bl_label = "Miscellaneous"
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        abp = scene.autobake_properties

        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text='Confirm Popups')
        split.menu(SPARROW_MT_Confirms.bl_idname, icon="WINDOW", text='Bake')
        
        split = col.split(factor=.4)
        split.label(text='Start Popup')
        split.menu(SPARROW_MT_StartPopupSettings.bl_idname, text='Settings', icon='MOD_HUE_SATURATION')
        
        split = col.split(factor=.4)
        split.label(text="Export List")
        split.prop(abp, "ab_export_list", text='', icon='EXPORT')
        
        col = layout.column()

        split = col.split(factor=.4)
        split.label(text='List Layout')
        split.prop(abp, 'ab_list_padding', icon="SEQ_STRIP_DUPLICATE", text='')
        
        col = layout.column()
        
        split = col.split(factor=.4)
        split.label(text="Text Alerts")
        split.menu(SPARROW_MT_Alerts.bl_idname, icon="ERROR", text='Alert')
        
        split = col.split(factor=.4)
        split.label(text='Reports')
        split.menu(SPARROW_MT_Reports.bl_idname, text='Actions', icon='INFO')
        
        split = col.split(factor=.4)
        split.label(text='Subfolder Name')
        split.prop(abp, 'ab_subfolder_use_prefix', icon="NEWFOLDER", text='Add Prefix      ')
