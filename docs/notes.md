# Notes
[VS Code Blender addon](https://github.com/JacquesLucke/blender_vscode)

[Blender 4.2 - Extensions Replace Addons](https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html#extensions-getting-started)

[Panel Types](https://b3d.interplanety.org/en/all-possible-values-for-the-bl_context-parameter-in-ui-panel-classes/): 

{'keymap', 'themes', 'mesh_edit', 'animation', '.paint_common', '.vertexpaint', 'objectmode', '.sculpt_mode', 'data', 'tools', 'view_layer', '.curves_sculpt', '.posemode', 'input', 'particle', 'render', 'navigation', '.armature_edit', 'constraint', 'interface', '.greasepencil_vertex', 'material', '.grease_pencil_paint', 'object', 'file_paths', '.greasepencil_weight', 'extensions', 'physics', '.particlemode', 'experimental', '.imagepaint', '.weightpaint', 'bone', 'lights', '.imagepaint_2d', 'save_load', '.greasepencil_sculpt', '.objectmode', 'modifier', 'output', 'editing', 'scene', 'bone_constraint', 'system', 'texture', 'addons', 'viewport', '.mesh_edit', 'world', '.uv_sculpt', '.greasepencil_paint', 'shaderfx', 'collection', '.paint_common_2d'}

## Setup

To make switching between branches easier, I've added a symlink to the `sparrow` addon in the Blender config directory. This way, I can just switch branches and the addon will always be up to date.

Could so set additional script directory to blender

```bash
cd ~/.config/blender/4.3/scripts/addons 
ln -s ~/code/p/sparrow/addons/sparrow/ sparrow
```
