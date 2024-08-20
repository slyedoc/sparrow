import bpy
import os
import json

from ..properties import SPARROW_PG_Global

class LoadRegistry(bpy.types.Operator):
    """Load the registry file"""
    bl_idname = "sparrow.load_registry"
    bl_label = "Load Registry"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = bpy.context.window_manager.sparrow # type: SPARROW_PG_Global
        
        info = None
        # load registry file if it exists
        if os.path.exists(self.registry_file):            
            try:
                with open(self.registry_file) as f:
                    data = json.load(f)
                    defs = data.get("$defs", {})
                    info = defs                                        
            except (IOError, json.JSONDecodeError) as e:
                print(f"ERROR: An error occurred while reading the file: {e}")
                return
        else:
            print(f"WARN: registy file does not exist: {self.registry_file}")
            return
        
        if not info:
            print(f"WARN: registry file is empty: {self.registry_file}")
            return