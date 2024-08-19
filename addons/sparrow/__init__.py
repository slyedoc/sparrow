bl_info = {
    "name": "Sparrow",
    "description": "Tooling for Bevy",
    "author": "slyedoc",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "warning": "",
    "wiki_url": "https://github.com/slyedoc/sparrow",
    "tracker_url": "https://github.com/slyedoc/sparrow",
    "category": "Import-Export"
}

import bpy

addon_keymaps = []

class ObjectMoveX(bpy.types.Operator):
    """My Object Moving Script"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.move_x"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Move X by One"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.

        # The original script
        scene = context.scene
        for obj in scene.objects:
            obj.location.x += 1.0

        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

def menu_func(self, context):
    self.layout.operator(ObjectMoveX.bl_idname)

def register():
    bpy.utils.register_class(ObjectMoveX)
    bpy.types.VIEW3D_MT_object.append(menu_func)  # Adds the new operator to an existing menu.

def unregister():
    bpy.utils.unregister_class(ObjectMoveX)

if __name__ == "__main__":
    register()
  