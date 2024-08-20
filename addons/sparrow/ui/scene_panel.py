import bpy

class SPARROW_PT_Scene:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

class SPARROW_PT_ScenePanel(SPARROW_PT_Scene, bpy.types.Panel):
    bl_idname = "SPARROW_PT_scene"
    bl_label = "Bevy Components"
    #bl_options = {'DEFAULT_CLOSED'}
    
    #@classmethod
    #def poll(cls, context):
    #    return (context.object is not None)
    
    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(text="")

    def draw(self, context):
        layout = self.layout
        #scene = context.scene
        #abp = scene.autobake_properties
     
        col = layout.column_flow(columns=1)
        row = col.row(align=True)
        row.label(text="Testing")
