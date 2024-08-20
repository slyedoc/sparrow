import bpy

from ..operators.select_asset_folder import OT_OpenAssetsFolderBrowser

from ..properties import SPARROW_PG_Scene

class SPARROW_PT_Output:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"

class SPARROW_PT_OutputPanel(SPARROW_PT_Output, bpy.types.Panel):
    bl_idname = "SPARROW_PT_output"
    bl_label = "Bevy"

    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(text="")

    def draw(self, context):
        layout = self.layout
        #scene = context.scene
        settings = bpy.context.window_manager.sparrow # type: SPARROW_PG_Scene

        col = layout.column_flow(columns=1)
        col.operator("sparrow.export_scenes", icon="RENDER_STILL", text="Export Scenes")

        col.label(text= "Scenes" )
        for scene in bpy.data.scenes:       ## new 
            row = col.row(align=True)            
            scene_settings = scene.sparrow
            row.prop(scene_settings, "export", text=scene.name)   ## changed

        col.separator()

        row = col.row()
        row.label(text="Assets Folder")
        row.prop(settings, "assets_path", text="")

        folder_selector = row.operator(OT_OpenAssetsFolderBrowser.bl_idname, icon="FILE_FOLDER", text="")
        folder_selector.target_property = "assets_path"

