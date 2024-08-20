import bpy
from bpy_extras.io_utils import ImportHelper

from ..properties import SPARROW_PG_Global

class OT_OpenAssetsFolderBrowser(bpy.types.Operator, ImportHelper):
    """Assets folder's browser"""
    bl_idname = "bevy.open_folderbrowser" 
    bl_label = "Select folder" 

    # Define this to tell 'fileselect_add' that we want a directoy
    directory: bpy.props.StringProperty(
        name="Outdir Path",
        description="selected folder"
        # subtype='DIR_PATH' is not needed to specify the selection mode.
        # But this will be anyway a directory path.
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
        settings = bpy.context.window_manager.sparrow # type: SPARROW_PG_Global
        setattr(settings, self.target_property, self.directory)
        return {'FINISHED'}