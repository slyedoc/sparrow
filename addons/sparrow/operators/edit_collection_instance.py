import bpy

from ..properties import SPARROW_PG_Global


def edit_collection_menu(self, context):
    self.layout.operator(EditCollectionInstance.bl_idname)

def exit_collection_instance(self, context):
    self.layout.operator(ExitCollectionInstance.bl_idname)


class EditCollectionInstance(bpy.types.Operator):
    """Goto Collection Instance Scene and isolate it"""
    bl_idname = "object.edit_collection_instance"
    bl_label = "Edit Instanced Collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):  
        sparrow = context.window_manager.sparrow #type: SPARROW_PG_Global
        coll = bpy.context.active_object.instance_collection #type: bpy.types.Collection

        if not coll:    
            self.report({"WARNING"}, "Active item is not a collection instance")
            return {"CANCELLED"}
        
        # Save the current scene so we can return to it later
        sparrow.last_scene = bpy.context.scene

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
        setting
        bpy.context.window.scene = target_scene

        # Deselect all objects, then select the root object in the collection
        bpy.ops.object.select_all(action='DESELECT')
        root_obj = next((obj for obj in coll.objects if obj.parent is None), None)
        if root_obj:
            root_obj.select_set(True)
            bpy.context.view_layer.objects.active = root_obj

            # Trigger Local View (isolation mode) to isolate the selected object
            bpy.ops.view3d.localview()
            # Zoom to the selected object
            bpy.ops.view3d.view_selected()
        else:
            self.report({"WARNING"}, "No root object found in the collection")
            return {"CANCELLED"}

        return {"FINISHED"}


    
class ExitCollectionInstance(bpy.types.Operator):    
     """Exit current scene and return to the previous scene"""
     bl_idname = "object.exit_collection_instance"
     bl_label = "Exit Collection Instance"
     bl_options = {"UNDO"}
   
     def execute(self, context):
        sparrow = context.window_manager.sparrow
       
        if not sparrow.last_scene:
            self.report({"WARNING"}, "No scene to return to")
            return {"CANCELLED"}
        
        if bpy.context.space_data.local_view: 
            bpy.ops.view3d.localview()

        bpy.context.window.scene = sparrow.last_scene
        sparrow.last_scene = None

        return {'FINISHED'}

# def traverse_tree(t):
#     yield t
#     for child in t.children:
#         yield from traverse_tree(child)
