import bpy
import cProfile
with cProfile.Profile() as pr:
    bpy.ops.export_scene.gltf(filepath=r'4000cubes-b3d_3.2.glb', use_visible=True, use_active_scene=True, export_materials='PLACEHOLDER', export_animations=False, export_morph=False, export_skins=False)

import pstats
from pstats import SortKey
p = pstats.Stats(pr)
p.sort_stats(SortKey.CUMULATIVE).print_stats(30)