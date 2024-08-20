import bpy
import os
import platform
import re
from .utils import *

from typing import Annotated, Optional
from bpy.props import (StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty, PointerProperty, CollectionProperty)
from bpy.types import (Material, Scene, Panel, Operator, PropertyGroup, UIList, Menu)

class SPARROW_PG_Global(PropertyGroup):
    last_scene:  PointerProperty(name="last scene", type=Scene, options= set())
    asset_path: StringProperty(
        name='Export folder',
        description='The root folder for all exports(relative to the root folder/path) Defaults to "assets" ',
        default='./assets',
        options={'HIDDEN'},
    ) # type: ignore
    registry_file: StringProperty(
        name='Registry File',
        description='The registry.json file',
        default='./assets/registry.json',
        options={'HIDDEN'},
    )
        
class SPARROW_PG_Scene(PropertyGroup):
    export: Annotated[bool, BoolProperty(name="Export", description="Automatically export scene as level", default = False, options = set())] # type: ignore


class SPARROW_PG_Collection(PropertyGroup):
    export: BoolProperty(name="Export", description="Automatically export scene as level", default = False, options = set()) # type: ignore

    
#------------------------------------------------------------------------------------
#   Properties

class SPARROW_PG_Collection(PropertyGroup):
    def update_file_format(self, context):
        context.scene.render.image_settings.file_format = self.ab_fileformat
    
    def reserved_char_check(self, context):
        if platform.system() == 'Windows' and self.ab_prefix != (re.sub('[{}]'.format(re.escape('<>:/\|?*')), '', self.ab_prefix)):
            self.ab_prefix = re.sub('[{}]'.format(re.escape('<>:/\|?*')), '', self.ab_prefix)
            
        if platform.system() == 'Windows' and self.ab_bridge != (re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', self.ab_bridge)):
            self.ab_bridge = re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', self.ab_bridge)
            
        if platform.system() == 'Windows' and self.ab_suffix != (re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', self.ab_suffix)):
            self.ab_suffix = re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', self.ab_suffix)
        
    def update_item_name(self, context):
        scene = context.scene
        abp = scene.autobake_properties
        
        list = scene.autobake_udimlist if self.ab_udim_bake else scene.autobake_bakelist
        if len(list) > 0:
            type_names = {}
            for item in abp.ab_baketype_name_all.split(', '):
                type_names[item.split(':')[0]] = item.split(':')[1]
                
            active_type = scene.autobake_udimlist[scene.autobake_udimlist_index].Type if self.ab_udim_bake else scene.autobake_bakelist[scene.autobake_bakelist_index].Type
            if active_type not in type_names:
                type_names[active_type] = active_type.strip()
            abp.ab_baketype_name = type_names[active_type]
            
    def update_custom_type_name(self, context):
        scene = context.scene
        abp = scene.autobake_properties
                
        if platform.system() == 'Windows' and self.ab_baketype_name != (re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', self.ab_baketype_name)):
            self.ab_baketype_name = re.sub('[{}]'.format(re.escape('<>:"/\|?*')), '', self.ab_baketype_name)

        type_names = {}
        for item in abp.ab_baketype_name_all.split(', '):
            type_names[item.split(':')[0]] = item.split(':')[1]

        active_type = scene.autobake_udimlist[scene.autobake_udimlist_index].Type if self.ab_udim_bake else scene.autobake_bakelist[scene.autobake_bakelist_index].Type

        if len(self.ab_baketype_name.strip()) == 0:
            type_names[active_type] = active_type.strip()
            abp.ab_baketype_name = active_type.strip()
        else:
            type_names[active_type] = abp.ab_baketype_name

        abp.ab_baketype_name_all = ", ".join([f"{key}:{value}" for key, value in type_names.items()])

    def update_object_selection(self, context):
        scene = context.scene
        if self.ab_source_object_method == 'LIST' and not scene.autobake_sourceobject:
            scene.autobake_sourceobject.add()
        

# # # # # # # # # # # # # #
# Main

    ab_texture_export : BoolProperty(name="Export", description="Automatically export the baked texture(s) to the given file path", default = False, options = set()) # type: ignore
    
    ab_bake_list_item_count : IntProperty(name='List Length', default=0, options = set()) # type: ignore
    ab_udim_list_item_count : IntProperty(name='UDIM List Length', default=0, options = set())  # type: ignore
    ab_udimtype_list_item_count : IntProperty(name='TIle list Length', default=0, options = set())  # type: ignore

    ab_load_method : EnumProperty(default='Material', description='', options = set(), items=[
        ("Material", "Material", "Load items from the selected material") ,
        ("Object", "Object", "Load items from all the materials of the selected object")]) # type: ignore
    ab_load_linked_material : PointerProperty(name='Source Material', type=Material, options = set())  # type: ignore
    ab_load_linked_object : PointerProperty(name='Source Object', type=bpy.types.Object, options = set())  # type: ignore
    ab_import_tiles : PointerProperty(name='Import Tiles', type=bpy.types.Image, options = set())  # type: ignore

    ab_udim_bake : BoolProperty(name="UDIM Bake", description="Switch between UDIM and default single texture bake", default = False, update=update_item_name, options = set())  # type: ignore
    ab_udim_label : BoolProperty(default=False, description='Visibility of the UDIM Tile labels', options = set())  # type: ignore


# # # # # # # # # # # # # #
# Bake List

# Item Details

    ab_multires_level : IntProperty(name='Level Viewport', default=0, min=-1, soft_max=10, options=set(), description="Level to set the Multires modifier's 'Level Viewport' value. Set -1 to leave it as it is. NOTE: Make sure the 'Level Viewport' and the 'Render' level is not the same, as this would result in an empty bake, since multires data is baked based on the difference between the two subdivision levels")  # type: ignore

    ab_ao_use_normal : BoolProperty(name="Use Normal", description="Use shader normal data when baking Ambient Occlusion", default = False, options = set())  # type: ignore
    ab_ao_local_only : EnumProperty(name="Local Only", default='FALSE', description="Disable objects for the texture bake. Could result a faster bake when there are a lot of objects in the scene", options = set(), items=[
        ('SELECTED', 'Selected', "Disable all the objects except the active and selected objects when 'Selected to Active' is enabled. If it's not enabled, only the active object will be the exception"),
        ('COLLECTION', 'Collection', "Disable all except those in the Active Object's collection"),
        ('FALSE', 'False', "Use all the enabled objects")])  # type: ignore

    ab_ao_sample : IntProperty(name='Sample', default=16, min=1, max=128, description='Number of rays to trace per shader evaluation', options = set())  # type: ignore
    ab_ao_sample_use : BoolProperty(name='Use Sample', default=True, description="Use the node's sample rate instead of the set sampling from the settings. If false, the bake type will use the 'High' sampling settings instead of the 'Low'", options = set())  # type: ignore
    ab_ao_inside : BoolProperty(name='Inside', default=False, description='Trace rays towards the inside of the object', options = set())  # type: ignore
    ab_ao_only_local : BoolProperty(name='Only Local', default=True, description='Only consider the object itself when computing ambient occlusion', options = set())  # type: ignore
    ab_ao_distance : FloatProperty(name='Distance', default=1, min=0, max=1000, step=10, precision=3, description="Limit the ray's distance. Zero for no limit", options = set())  # type: ignore
    
    ab_pointiness_contrast : FloatProperty(name='Contrast', default=5, min=-100, max=100, precision=3, step=10, description='Changes the contrast between the darkest and lightest parts of the pointiness map', options = set())  # type: ignore
    ab_pointiness_brightness : FloatProperty(name='Brightness', default=0, min=-100, max=100, precision=3, step=10, description='Changes the overall brightness', options = set())  # type: ignore
    
    ab_channel_pack_r : EnumProperty(name="Channel Packing R", items = channel_packing_items, description = "Select the bake type to use on the red channel for the 'Channel Packing' bake", default = "Metallic", options = set())  # type: ignore
    ab_channel_pack_g : EnumProperty(name="Channel Packing G", items = channel_packing_items, description = "Select the bake type to use on the green channel for the 'Channel Packing' bake", default = "Roughness", options = set())  # type: ignore
    ab_channel_pack_b : EnumProperty(name="Channel Packing B", items = channel_packing_items, description = "Select the bake type to use on the blue channel for the 'Channel Packing' bake", default = "Alpha", options = set())  # type: ignore

    ab_uv_target : StringProperty(name='UV Map', default='UVMap', description='Preferred UV map coordinate to bake, useful for objects with multiple UV maps. When unspecified or the specified uv map is not found, the active (render) UV map will be used', options = set())  # type: ignore
    ab_attribute_target : StringProperty(name='Color Attribute', default='Attribute', description='Preferred color attribute channel to bake, useful for objects with multiple color attributes. When unspecified or the specified color attribute is not found, the active (render) color attribute will be used', options = set())  # type: ignore
    ab_displacement_source : BoolProperty(name='Source Only', default=False, description="Bake the source of the displacement/vector displacement node. This will be either the 'Height' or the 'Color' input socket value", options = set())  # type: ignore


# # # # # # # # # # # # # #
# Image

# Name

    ab_prefix : StringProperty(name= "Prefix", description = "Custom prefix before the texture (type) name. Leave it empty to use the target object's name. For none use double apostrophes ('') or double quotation marks (\"\"). The prefix cannot contain reserved characters as defined by the operating system. The prefix will be ignored and the objects' names will be used when multiple objects are baked at once", update=reserved_char_check, options = set())  # type: ignore
    ab_bridge : StringProperty(name= "Bridge", description = "Custom text between the texture type and scale. Leave it empty for none. The bridge cannot contain reserved characters as defined by the operating system", default=" - ", update=reserved_char_check, options = set())  # type: ignore
    ab_suffix : StringProperty(name= "Suffix", description = "Custom suffix after the texture (scale) name. Leave it empty for none. The suffix cannot contain reserved characters as defined by the operating system", default="px", update=reserved_char_check, options = set())  # type: ignore

    ab_baketype_name : StringProperty(name='Type Name', description="Customize the name of this bake type. Clear to reset its value", update=update_custom_type_name, options = set())  # type: ignore
    ab_baketype_name_all : StringProperty(name='Type Name (All)', description="", default="x:x", options = set())  # type: ignore

    ab_name_structure : StringProperty(name='Name Structure', description='Fully custumize your texture names', default="{prefix}{type}{bridge}{size}{suffix}", options = set())  # type: ignore
    ab_name_structure_udim : StringProperty(name='Name Structure UDIM', description='Fully custumize your UDIM texture names', default="{prefix}{type}{bridge}{size}x", options = set())  # type: ignore
    ab_name_structure_udim_export : StringProperty(name='Name Structure UDIM Export', description='Fully custumize your UDIM export texture names', default="{prefix}{type}{bridge}{size}x.{udim}", options = set())  # type: ignore

# Format

    ab_floatbuffer: BoolProperty(name="Use Float", description="Create image with 32-bit floating-point bit depth", default = False, options = set())  # type: ignore
    
# Export

    ab_subfolders : BoolProperty(name="Subfolders", description="Separate exported textures into different subolders based on bake type", default = False, options = set())  # type: ignore
    ab_filepath : StringProperty(name= "Filepath", description = "File path to use when exporting the textures", options = set(), default = os.path.join(os.environ['USERPROFILE'], 'Desktop') if platform.system() == 'Windows' else os.path.join(os.environ['HOME'], 'Desktop') if platform.system() == 'Linux' else "")  # type: ignore
    ab_fileformat :  EnumProperty(name="File Format", description="File format to use when saving the image", default="PNG", update=update_file_format, options = set(), items=[
        ('', "Image File Formats", "", ),
        ('BMP', "BMP", "", ),
        ('IRIS', "Iris", "", ),
        ('PNG', "PNG", "", ),
        ('JPEG', "JPEG", "", ),
        ('JPEG2000', "JPEG 2000", "", ),
        ('TARGA', "Targa", "", ),
        ('TARGA_RAW', "Targa Raw", "", ),
        ('', "", "", ),
        ('CINEON', "Cineon", "", ),
        ('DPX', "DPX", "", ),
        ('OPEN_EXR_MULTILAYER', "OpenEXR MultiLayer", "", ),
        ('OPEN_EXR', "OpenEXR", "", ),
        ('HDR', "Radiance HDR", "", ),
        ('TIFF', "TIFF", "", ),
        ('WEBP', "WebP", "", )])

# Color Management
    ab_custom_color_management : BoolProperty(name='Custom Color Management', description="Use custom color management settings when exporting textures. Recommended to keep this option off for raw image exports. When it's off the following color management settings will be used:\n\u2022 Display Device: sRGB\n\u2022 View: Raw\n\u2022 Look: None\n\u2022 Exposure: 0\n\u2022 Gamma: 1\n\u2022 Use Curves: False", options = set())  # type: ignore

# # # # # # # # # # # # # #
# Settings

# Margin
    
    ab_adaptive_margin : BoolProperty(name='Adaptive Margin', default=False, description="Automatically adjust the margin size based on the baked texture's scale. The currently set margin size will be used for textures with a resolution of 1024px, and will be correspondingly adjusted for different texture sizes", options = set())  # type: ignore

# Selected to Active

    ab_active_as_final : BoolProperty(name='Active as Final', default=False, description='Use the active object as the final object', options = set())  # type: ignore

# Selection Helper

    ab_target_object : PointerProperty(name='Target Object', type=bpy.types.Object, description = 'Low Poly Object', options = set())  # type: ignore
    ab_source_object_method : EnumProperty(name='Source Object Method', default='COLLECTION', description='Choose your source object selection method', update=update_object_selection, options = set(), items=[
        ('COLLECTION', 'Collection', 'The collection containing your source objects'),
        ('LIST', 'List', 'Set up a list with your source objects')])  # type: ignore
    ab_source_collection : PointerProperty(name='Source Collection', type=bpy.types.Collection, description='Collection that contains your high poly objects', options = set())  # type: ignore

# Sampling

    ab_sampling_use_render : BoolProperty(name='Use Render Settings', default=False, description='Use the same sampling settings as for rendering images', options = set())  # type: ignore
    ab_auto_pick_sampling : BoolProperty(name='Auto Select', default=True, options = set(), description="Automatically choose which sampling settings to use, with this you can optimize to only bake textures with high sampling settings that needs to be baked with. High sampling settings will be picked for: \n\u2022 Combined \n\u2022 Ambient Occlusion (Standard) \n\u2022 Glossy \n\u2022 Diffuse \n\u2022 Transmission \n\u2022 Shadow \n\u2022 Environment")  # type: ignore

    ab_sampling_low_adaptive : BoolProperty(name='Adaptive Sampling', default=False, description='Automatically reduce the number of samples per pixel based on estimated noise level', options = set())  # type: ignore
    ab_sampling_low_noise_threshold : FloatProperty(name='Noise Threshold', default=0.01, precision=4, min=0, max=1, description='Noise level step to stop sampling at, lower values reduce noise at the cost of render time. Zero for automatic setting based on number of AA sample', options = set())  # type: ignore
    ab_sampling_low_max : IntProperty(name='Max Samples', default=1, min=1, max=16777216, description='Number of samples to render for each pixel', options = set())  # type: ignore
    ab_sampling_low_min : IntProperty(name='Min Samples', default=0, min=0, max=4096, description='Minimum AA samples for adaptive sampling, to discover noisy features before stopping sampling. Zero for automatic setting based on noise threshold', options = set())  # type: ignore
    ab_sampling_low_time_limit : FloatProperty(name='Time Limit', default=0, min=0, subtype='TIME_ABSOLUTE', description='Limit the render time (exclude synchronization time). Zero disables the limit', options = set())  # type: ignore
    ab_sampling_low_denoise : BoolProperty(name='Denoise', default=False, description='Denoise the rendered image', options = set())  # type: ignore
    ab_sampling_low_denoiser : EnumProperty(name='Denoiser', default='OPENIMAGEDENOISE', description='Denoise the image with the selected denoiser. For denoising the image after rendering:', options = set(), items=[
        ('OPENIMAGEDENOISE', 'OpenImageDenoise', 'Use Intel OpenImageDenoise AI denoiser running on the CPU'),
        ('OPTIX', 'OptiX', 'Use the OptiX AI denoiser with GPU acceleration, only available on NVIDIA GPUs')])  # type: ignore
    ab_sampling_low_passes : EnumProperty(name='Passes', default='RGB_ALBEDO_NORMAL', description='Passes used by the denoiser to distinguish noise from shader and geometry detail', options = set(), items=[
        ('RGB', 'None', "Don't use utility passes for denoising",),
        ('RGB_ALBEDO', 'Albedo', 'Use albedo pass for denoising',),
        ('RGB_ALBEDO_NORMAL', 'Albedo and Normal', 'Use albedo and normal passes for denoising',)])  # type: ignore
    ab_sampling_low_prefilter : EnumProperty(name='Prefilter', default='ACCURATE', description='Prefilter noise guiding (albedo and normal) passes to improve denoising quality when using OpenImageDenoiser', options = set(), items=[
        ('NONE', 'None', 'Noe prefiltering, use when guiding passes are noise-free'),
        ('FAST', 'Fast', 'Denoise color and guiding passes together. Improves quality when guiding passes are noisy using least amount of extra processing time'),
        ('ACCURATE', 'Accurate', 'Prefilter noise guaiding passes before denoising color. Improves quality when guiding passes are noisy using least amount of extra processing time')])  # type: ignore
    
    ab_sampling_high_adaptive : BoolProperty(name='Adaptive Sampling', default=True, description='Automatically reduce the number of samples per pixel based on estimated noise level', options = set())  # type: ignore
    ab_sampling_high_noise_threshold : FloatProperty(name='Noise Threshold', default=0.01, precision=4, min=0, max=1, description='Noise level step to stop sampling at, lower values reduce noise at the cost of render time. Zero for automatic setting based on number of AA sample', options = set())  # type: ignore
    ab_sampling_high_max : IntProperty(name='Max Samples', default=4096, min=1, max=16777216, description='Number of samples to render for each pixel', options = set())  # type: ignore
    ab_sampling_high_min : IntProperty(name='Min Samples', default=0, min=0, max=4096, description='Minimum AA samples for adaptive sampling, to discover noisy features before stopping sampling. Zero for automatic setting based on noise threshold', options = set())  # type: ignore
    ab_sampling_high_time_limit : FloatProperty(name='Time Limit', default=0, min=0, subtype='TIME_ABSOLUTE', description='Limit the render time (exclude synchronization time). Zero disables the limit', options = set())  # type: ignore
    ab_sampling_high_denoise : BoolProperty(name='Denoise', default=True, description='Denoise the rendered image', options = set())  # type: ignore
    ab_sampling_high_denoiser : EnumProperty(name='Denoiser', default='OPENIMAGEDENOISE', description='Denoise the image with the selected denoiser. For denoising the image after rendering:', options = set(), items=[
        ('OPENIMAGEDENOISE', 'OpenImageDenoise', 'Use Intel OpenImageDenoise AI denoiser running on the CPU'),
        ('OPTIX', 'OptiX', 'Use the OptiX AI denoiser with GPU acceleration, only available on NVIDIA GPUs')])  # type: ignore
    ab_sampling_high_passes : EnumProperty(name='Passes', default='RGB_ALBEDO_NORMAL', description='Passes used by the denoiser to distinguish noise from shader and geometry detail', options = set(), items=[
        ('RGB', 'None', "Don't use utility passes for denoising",),
        ('RGB_ALBEDO', 'Albedo', 'Use albedo pass for denoising',),
        ('RGB_ALBEDO_NORMAL', 'Albedo and Normal', 'Use albedo and normal passes for denoising',)])  # type: ignore
    ab_sampling_high_prefilter : EnumProperty(name='Prefilter', default='ACCURATE', description='Prefilter noise guiding (albedo and normal) passes to improve denoising quality when using OpenImageDenoiser', options = set(), items=[
        ('NONE', 'None', 'Noe prefiltering, use when guiding passes are noise-free'),
        ('FAST', 'Fast', 'Denoise color and guiding passes together. Improves quality when guiding passes are noisy using least amount of extra processing time'),
        ('ACCURATE', 'Accurate', 'Prefilter noise guaiding passes before denoising color. Improves quality when guiding passes are noisy using least amount of extra processing time')])  # type: ignore

# # # # # # # # # # # # # #
# Addon 

# Textures

    ab_textures_fakeuser : BoolProperty(name="Fake User", description="Save the image data-block even if it has no user", default=False, options = set())  # type: ignore
    ab_pack_texture : BoolProperty(name='Pack Images', default=False, description='Pack the baked textures into the .blend file', options = set())  # type: ignore
    ab_scaled_antialiasing : EnumProperty(name='Anti-aliasing', default='FALSE', description='Anti-aliasing method to use', options = set(), items=[
        ('FALSE', 'Off', 'No scaling will be applied for anti-alising', 'ALIASED', 0),
        ('UPSCALED', 'Upscaled', 'Textures will be created and baked at a higher resolution (original texture size * specified value), and then scaled back to the original texture size after the bake', 'ANTIALIASED', 1),
        ('DOWNSCALED', 'Downscaled', "After the baking process, textures are scaled to the specified percentage and then rescaled back to the original size. This operation can be repeated the set amount of times", 'ANTIALIASED', 2),])  # type: ignore
    ab_antialiasing_downscaled : FloatProperty(name='Downscaled', default=75, precision=2, soft_min=25, soft_max=95, min=1, max=99.99, subtype='PERCENTAGE', description="Set the downscale percetange for the 'Downscaled' anti-aliasing", options = set())  # type: ignore
    ab_antialiasing_repeat : IntProperty(name='Downscale Iteration', min=1, max=100, default=1, description='Repeat the rescale operation the set amount of time', options = set())  # type: ignore
    ab_antialiasing_upscaled : FloatProperty(name='Upscaled', default=150, precision=2, min=100.1, soft_min=105, soft_max=800, max=10000, options = set(), description="Set the upscale percentage for the 'Upscaled' anti-aliasing. This value will be used to bake the texture at a higher resolution, resulting in longer bakes. 200% will result double the bake size and approximately double the bake time. After the bake the texture will be scaled back to its original size", subtype='PERCENTAGE')  # type: ignore
    ab_color_space_float: EnumProperty(name='Float Image Color Space', default='Non-Color', items=color_space, options = set(), description='Set the default color space for the float image textures.\n'
                                                                                                                        "Affected Items: Metallic, Roughness, IOR, Alpha, Subsurface Weight, Subsurface Scale, Subsurface IOR, Subsurface Anisotropy, Specular IOR Level, Anisotropic, Anisotropic Rotation, Transmission Weight, Coat Weight, Coat Roughness, Coat IOR, Sheen Weight, Sheen Roughness, Emission Strength, Displacement (Multires), Roughness (Standard), Glossy, Shadow, Ambient Occlusion, Subsurface, Specular, Sheen, Clearcoat, Clearcoat Roughness, Transmission Roughness, Channel Packing")  # type: ignore
    ab_color_space_color: EnumProperty(name='Color Image Color Space', default='sRGB', items=color_space, options = set(), description='Set the default color space for the color image textures.\n'
                                                                                                                        "Affected Items: Base Color, Specular Tint, Coat Tint, Sheen Tint, Emission Color, Color Attribute, Combined, Diffuse, Transmission, Environment, Emit, Subsurface Color, Emission")  # type: ignore
    ab_color_space_vector: EnumProperty(name='Vector Image Color Space', default='Non-Color', items=color_space, options = set(), description='Set the default color space for the vector image textures.\n'
                                                                                                                        "Affected Items: Normal, Subsurface Radius, Tangent, Coat Normal, Normals, Normal (Standard), Position, UV, Displacement (Miscellaneous), Clearcoat Normal")  # type: ignore
    ab_shared_textures : BoolProperty(name='Shared Textures', default=False, options = set(), description="Use this option when you want to bake each selected object onto the same textures. When shared texture is used with the final material option, only one final material will be created (and applied), and it will be named as the set prefix if set, or as the first object. Anti-aliasing will only be applied with the last baking object, likewise the textures exported. Please note that UV islands are not respected, so make sure you use a lower margin size to avoid texture bleeding. If this option is used with anti-aliasing, it will always be applied to the last object in the queue")  # type: ignore

# Materials

    ab_final_material : BoolProperty(name='Final Material', description="Create a final material where the baked textures will be placed and kept regardless of what the 'Image Textures' property set to", default=False, options = set())  # type: ignore
    ab_final_shader : EnumProperty(name='Final Shader', default='ShaderNodeBsdfPrincipled', description='Set what shader to use for the final material', options = set(), items=[
        ('', 'Shaders', ''),
        ('ShaderNodeBsdfPrincipled', 'Principled BSDF', ''),
        ('ShaderNodeBsdfDiffuse', 'Diffuse BSDF', ''),
        ('ShaderNodeEmission', 'Emission', ''),
        ('ShaderNodeBsdfTranslucent', 'Translucent BSDF', ''),
        ('ShaderNodeBsdfTransparent', 'Transparent BSDF', ''),
        ('ShaderNodeBsdfRefraction', 'Refraction BSDF', ''),
        ('ShaderNodeBsdfGlass', 'Glass BSDF', ''),
        ('ShaderNodeBsdfSheen', 'Sheen BSDF', ''),
        ('', '', ''),
        ('ShaderNodeBsdfToon', 'Toon BSDF', ''),
        ('ShaderNodeBsdfAnisotropic', 'Glossy BSDF', ''),
        ('ShaderNodeBsdfHair', 'Hair BSDF', ''),
        ('ShaderNodeBsdfHairPrincipled', 'Principled Hair BSDF', ''),
        ('ShaderNodeVolumeAbsorption', 'Volume Absorption', ''),
        ('ShaderNodeVolumeScatter', 'Volume Scatter', ''),
        ('ShaderNodeVolumePrincipled', 'Principled Volume', ''),
        ('ShaderNodeSubsurfaceScattering', 'Subsurface Scattering', '')
            ] if bpy.app.version >= (4, 0, 0) else [
        ('', 'Shaders', ''),
        ('ShaderNodeBsdfPrincipled', 'Principled BSDF', ''),
        ('ShaderNodeBsdfDiffuse', 'Diffuse BSDF', ''),
        ('ShaderNodeEmission', 'Emission', ''),
        ('ShaderNodeBsdfTranslucent', 'Translucent BSDF', ''),
        ('ShaderNodeBsdfTransparent', 'Transparent BSDF', ''),
        ('ShaderNodeBsdfRefraction', 'Refraction BSDF', ''),
        ('ShaderNodeBsdfGlass', 'Glass BSDF', ''),
        ('ShaderNodeBsdfVelvet', 'Velvet BSDF', ''),
        ('', '', ''),
        ('ShaderNodeBsdfToon', 'Toon BSDF', ''),
        ('ShaderNodeBsdfAnisotropic', 'Anisotropic BSDF', ''),
        ('ShaderNodeBsdfHair', 'Hair BSDF', ''),
        ('ShaderNodeBsdfHairPrincipled', 'Principled Hair BSDF', ''),
        ('ShaderNodeVolumeAbsorption', 'Volume Absorption', ''),
        ('ShaderNodeVolumeScatter', 'Volume Scatter', ''),
        ('ShaderNodeVolumePrincipled', 'Principled Volume', ''),
        ('ShaderNodeSubsurfaceScattering', 'Subsurface Scattering', '')
            ] if bpy.app.version >= (3, 6, 0) else [
        ('', 'Shaders', ''),
        ('ShaderNodeBsdfPrincipled', 'Principled BSDF', ''),
        ('ShaderNodeBsdfDiffuse', 'Diffuse BSDF', ''),
        ('ShaderNodeEmission', 'Emission', ''),
        ('ShaderNodeBsdfTranslucent', 'Translucent BSDF', ''),
        ('ShaderNodeBsdfTransparent', 'Transparent BSDF', ''),
        ('ShaderNodeBsdfRefraction', 'Refraction BSDF', ''),
        ('', '', ''),
        ('ShaderNodeBsdfGlass', 'Glass BSDF', ''),
        ('ShaderNodeBsdfAnisotropic', 'Glossy BSDF', ''),
        ('ShaderNodeVolumeAbsorption', 'Volume Absorption', ''),
        ('ShaderNodeVolumeScatter', 'Volume Scatter', ''),
        ('ShaderNodeVolumePrincipled', 'Principled Volume', ''),
        ('ShaderNodeSubsurfaceScattering', 'Subsurface Scattering', '')])  # type: ignore
    
    ab_apply_textures : EnumProperty(name="Apply Textures", description="Select which baked textures should be connected (from each bake type) to the final material's shader. *Only works for bake types from the Shader and its sub-categories", default='Highest', options = set(), items=[
        ('False', 'False', "Don't connect the textures", 'X', 0),
        ('First', 'First', "Connect the first baked texture from the type", 'EVENT_A', 1),
        ('Last', 'Last', "Connect the last baked texture from the type", 'EVENT_Z', 2),
        ('Highest', 'Highest', "Connect the texture with the highest resolution from the type", 'SORT_DESC', 3),
        ('Lowest', 'Lowest', "Connect the texture with the lowest resolution from the type", 'SORT_ASC', 4)])  # type: ignore
    ab_remove_imagetextures : BoolProperty(name="Keep Texture Nodes", description="Remove the 'Image Texture' nodes from the materials used in the bake process", default = False, options = set())  # type: ignore
    ab_node_tiling : EnumProperty(name="Node Tiling", description="Choose how the 'Image Texture' nodes will be placed", default='GRID', options = set(), items=[
        ('OFF', 'Off', "All the 'Image Texture' nodes will be placed at the same location", 'X', 0),
        ('GRID', 'Grid', "The 'Image Texture' nodes will be placed in a grid-tile system", 'SNAP_VERTEX', 1),
        ('SINGLEROW', 'Single Row', "The 'Image Texture' nodes will be places into a single vertical row", 'DOT', 2),
        ('ROWBYTYPE', 'Row By Type', "Place every 'Image Texture' node into different rows by texture type", 'SNAP_EDGE', 3),
        ('ROWBYTYPECOMBINED', 'Row By Type +', "Place every 'Image Texture' node into different rows by texture type; single types are put into a combined row", 'SNAP_EDGE', 4)])  # type: ignore
    ab_node_label : EnumProperty(name="Use Node Labels", default="Off", description="Add labels to the image texture nodes. This will not effect the texture's name", options = set(), items=[
        ('Off', 'Off', 'No label will be applied'),
        ('Name', 'Name', 'Use the custom type name as labels'),
        ('Type', 'Type', 'Use the type name as labels')])  # type: ignore

# Objects
    
    ab_final_object : BoolProperty(name='Final Object', default=False, description='Duplicate the baked object and assign the final material to it (final material can only be assigned to the object if it is set to be created)', options = set())  # type: ignore
    ab_final_collection : StringProperty(name='Collection', default='', description="Create a new collection with the set name for the final object(s). If left empty, no new collection will be created, and each final object will be located in the same collection as its original object", options = set())  # type: ignore
    ab_final_collection_color : EnumProperty(name='Collection Color', default='NONE', description='Final object collection color', options = set(), items=[
        ('NONE', 'Collection', '', 'OUTLINER_COLLECTION', 0),
        ('COLOR_01', 'Collection', '', 'COLLECTION_COLOR_01', 1),
        ('COLOR_02', 'Collection', '', 'COLLECTION_COLOR_02', 2),
        ('COLOR_03', 'Collection', '', 'COLLECTION_COLOR_03', 3),
        ('COLOR_04', 'Collection', '', 'COLLECTION_COLOR_04', 4),
        ('COLOR_05', 'Collection', '', 'COLLECTION_COLOR_05', 5),
        ('COLOR_06', 'Collection', '', 'COLLECTION_COLOR_06', 6),
        ('COLOR_07', 'Collection', '', 'COLLECTION_COLOR_07', 7),
        ('COLOR_08', 'Collection', '', 'COLLECTION_COLOR_08', 8)])  # type: ignore
    ab_object_location : EnumProperty(name='Object Location', default='Copy', items=[('Copy', 'Copy', 'Copy the location of the baked object', 'COPYDOWN', 0), ('Clear', 'Clear', 'Object will be placed to the world origin', 'LOOP_BACK', 1)], description='Location of the final object', options = set())  # type: ignore
    ab_offset_direction : EnumProperty(options = set(), name='Offset Direction', default='Y', items=[("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")], description='Direction to offset the final object')  # type: ignore
    ab_object_offset : FloatProperty(options = set(), name='Offset', default=0.0, subtype='DISTANCE', description='Distance to offset the final object')  # type: ignore
    ab_object_keep_name : EnumProperty(name='Keep Namme', description="Set which object should have the original name and which should have it with the differentiator. If the object is set to be exported, it will always be without the differentiator, regardless of this setting", default='Final', options = set(), items=[
        ('Final', 'Final', "The final object will take the name of the original object, and the differentiator will be added to the original object's name"),
        ('Original', 'Original', "Keep the name for the original object, and add the differentiator to the final object")])  # type: ignore
    ab_object_differentiator : StringProperty(name='Differentiator', default='_', description="Differentiator for the selected object. This text will be added to the end of the object's name, this will help Auto Bake to avoid name conflicts for objects and materials", options = set())  # type: ignore
    
# Export Object

    ab_export_object : BoolProperty(name='Export Object', default=False, description="Export the final object to the texture's location. (NOTE: OBJ and GLTF object export method uses viewport object selection)", options = set())  # type: ignore
    ab_export_always : EnumProperty(name='Export When', default='Success', description='', options = set(), items=[
        ('Always', 'Always', 'Always export the object even if it has failed bake items'),
        ('Success', 'On-Success', "Only export when none of the object's bakes have failed (canceled items are not counted as failed items)")]) # type: ignore
    ab_export_object_remove : BoolProperty(name='Remove Object', default=False, description='Remove the final object after export', options = set()) # type: ignore
    ab_export_clear_location : BoolProperty(name='Clear Location', default=True, description='Export object with its location set to the world origin. After export the location will be set back to the original', options = set()) # type: ignore
    ab_export_clear_rotation : BoolProperty(name='Clear Rotation', default=True, description='Export object with cleared rotation. After export the rotation will be set back to the original', options = set()) # type: ignore
    ab_export_clear_scale : BoolProperty(name='Clear Scale', default=True, description='Export object with cleared scaling. After export the scale will be set back to the original', options = set()) # type: ignore
    ab_export_restore_transform : BoolProperty(name='Restore Transform', default=True, description='Restore object transform after the export', options = set()) # type: ignore
    
# Export Settings
    
    ab_export_object_as : EnumProperty(name="Export As", default="OBJ", description="Export objects with the selected file format. (When exporting, the exported objects will be selected in the 3D viewport, except during FBX export)", options = set(), items=[
        ('FBX', 'FBX (.fbx)', 'Write a FBX file'),
        ('GLTF', 'glTF 2.0 (.glb/.gltf)', 'Export the object as glTF 2.0 file'),
        ('OBJ', 'Wavefront (.obj)', 'Save the object to a Wavefront OBJ file.')]) # type: ignore
    ab_export_pathmode : EnumProperty(name='Path Mode', default='AUTO', description='Method used to reference paths', options = set(), items=[
        ('AUTO', 'Auto', 'Use relative paths with subdirectories only'),
        ('ABSOLUTE', 'Absolute', 'Always write absolute paths'),
        ('RELATIVE', 'Relative', 'Always write relative paths (where possible)'),
        ('MATCH', 'Match', 'Match absolute/relative setting with input path'),
        ('STRIP', 'Strip Path', 'Filename only'),
        ('COPY', 'Copy', 'Copy the file to the destionation path (or subdirectory)')]) # type: ignore
    ab_export_embedtextures : BoolProperty(name='Embed Textures', default=False, description='Embed textures in FBX binary file (only for "Copy" path mode)', options = set()) # type: ignore
    ab_export_scale : FloatProperty(default=1, min=0.001, max=1000.0, description='Scale all data', name='', options = set()) # type: ignore
    ab_export_applyunit : BoolProperty(name='Apply Unit', default=True, description='Take into account current Blender units settings (if unset, raw Blender Units values are used as-is)', options = set()) # type: ignore
    ab_export_usespacetransform : BoolProperty(name='Use Space Transform', default=True, description='Apply global space transform to the object rotations. When disabled only the axis space is written to the file and all object transform are left as-is', options = set()) # type: ignore
    ab_export_smoothing : EnumProperty(name='Smoothing', default='OFF', description="Export smoothing information (prefer 'Normals Only' option if your target importer understand split normals)", options = set(), items=[
        ('OFF', 'Normals Only', 'Export only normals instead of writing edge or face smoothing data'),
        ('FACE', 'Face', 'Write face smoothing'),
        ('EDGE', 'Edge', 'Write edge smoothing')]) # type: ignore
    ab_export_subdivisionsurface : BoolProperty(name='Export Subdivision Surface', default=False, description="Export the last Catmull-Rom subdivision modifier as FBX subdivision (does not apply the modifier even if 'Apply Modifiers' is enabled)", options = set()) # type: ignore
    ab_export_applymodifiers : BoolProperty(name='Apply Modifiers', default=True, description='Apply modifiers to mesh objects (except Armature ones) - WARNING: prevents exporting shape keys', options = set()) # type: ignore
    ab_export_looseedges : BoolProperty(name='Loose Edges', default=False, description='Export loose edges (as two-vertices polygons)', options = set()) # type: ignore
    ab_export_triangulatefaces : BoolProperty(name='Triangulate Faces', default=False, description='Convert all faces to triangles', options = set()) # type: ignore
    ab_export_tangentspace : BoolProperty(name='Tangent Space', default=False, description='Add binormal and tangent vectors, together with normal they form the tangent space (will only work correctly with tris/quads only meshes)', options = set()) # type: ignore
    ab_export_vertexcolors : EnumProperty(name='Vertex Colors', default='SRGB', description="Export vertex color attribute", options = set(), items=[
        ('NONE', 'None', 'Do not export colot attributes'),
        ('SRGB', 'sRGB', 'Export colors in sRGB color space'),
        ('LINEAR', 'Linear', 'Export colors in linear color space')]) # type: ignore
    ab_export_prioritizeactivecolor : BoolProperty(name='Prioritize Active Color', default=False, description='Make sure active color will be exported first. Could be important since some other software can discard other color attributes besides the first one', options = set()) # type: ignore
    ab_export_customprops : BoolProperty(name='Custom Properties', default=False, description='Export custom properties', options = set()) # type: ignore
    ab_export_evalmode : EnumProperty(name='Properties', default='DAG_EVAL_VIEWPORT', description="Determines properties like object visibility, modifiers etc., where they differ for Render and Viewport", options = set(), items=[
        ('DAG_EVAL_RENDER', 'Render', 'Export objects as they appear in render'),
        ('DAG_EVAL_VIEWPORT', 'Viewport', 'Export objects as they appear in the viewport')]) # type: ignore
    ab_export_triangulatedmesh : BoolProperty(name='Triangulated Mesh', default=False, description='All ngons with four or more vertices will be triangulated. Meshes in the scene will not be affected. Behaves like Triangulate Modifier with ngon-method: "Beauty", squad-method: "Shortest Diagonal", min vertices: 4', options = set()) # type: ignore
    ab_export_exportcolors : BoolProperty(name='Vertex Colors', default=False, description='Export per-vertex colors', options = set()) # type: ignore
    ab_export_vertexgroups : BoolProperty(name='Vertex Groups', default=False, description='Export the name of the vertex group of a face. It is approximated by choosing the vertex group with the most members among the vertices of a face', options = set()) # type: ignore
    ab_export_smoothgroups : BoolProperty(name='Smooth Groups', default=False, description='Every smooth shaded-face is assigned group "1" and every flat-shaded face "off"', options = set()) # type: ignore
    ab_export_groupbitflag : BoolProperty(name='Smooth Group Bitflags', default=False, description='Generate Bitflags for Smooth Groups', options = set()) # type: ignore
    ab_export_pbrextension : BoolProperty(name='PBR Extensions', default=False, description='Export MTL library using PBR extensions (roughness, metallic, sheen, coat, anisotropy, transmission)', options = set()) # type: ignore

# FBX Export

    ab_fbx_forward : EnumProperty(name='Forward', default='-Z', description='', options = set(), items=[
        ('X', 'X', ''),
        ('Y', 'Y', ''),
        ('Z', 'Z', ''),
        ('-X', '-X', ''),
        ('-Y', '-Y', ''),
        ('-Z', '-Z', '')]) # type: ignore
    ab_fbx_up : EnumProperty(name='Up', default='Y', description='', options = set(), items=[
        ('X', 'X', ''),
        ('Y', 'Y', ''),
        ('Z', 'Z', ''),
        ('-X', '-X', ''),
        ('-Y', '-Y', ''),
        ('-Z', '-Z', '')]) # type: ignore
    ab_fbx_apply_scaling : EnumProperty(name='', default='FBX_SCALE_NONE', description='How to apply custom and units scalings in generated FBX file (Blender uses FBX scale to detect units on import, but many other applications do not handle the same way)', options = set(), items=[
        ('FBX_SCALE_NONE', 'All Local', 'Apply custom scaling and units scaling to each object transormation, FBX scale remains at 1.0'),
        ('FBX_SCALE_UNITS', 'FBX Units Scale', 'Apply custom scaling to each object transformation, and units scaling to FBX scale'),
        ('FBX_SCALE_CUSTOM', 'FBX Custom Scale', 'Apply custom scaling to FBX scale, and units scaling to each object transformation'),
        ('FBX_SCALE_ALL', 'FBX All', 'Apply custom scaling and units scaling to FBX scale')]) # type: ignore

# OBJ Export

    ab_obj_forward : EnumProperty(name='Forward Axis', default='NEGATIVE_Z', description='', options = set(), items=[
        ('X', 'X', ''),
        ('Y', 'Y', ''),
        ('Z', 'Z', ''),
        ('NEGATIVE_X', '-X', ''),
        ('NEGATIVE_Y', '-Y', ''),
        ('NEGATIVE_Z', '-Z', '')]) # type: ignore
    ab_obj_up : EnumProperty(name='Up Axis', default='Y', description='', options = set(), items=[
        ('X', 'X', ''),
        ('Y', 'Y', ''),
        ('Z', 'Z', ''),
        ('NEGATIVE_X', '-X', ''),
        ('NEGATIVE_Y', '-Y', ''),
        ('NEGATIVE_Z', '-Z', '')]) # type: ignore

# GLTF Export

    ab_gltf_format : EnumProperty(options = set(), name='Format', default='GLB', description='Output format', items=[
        ('GLB', 'glTF Binary (.glb)', 'Exports single file, with all data packed in binary form. Most efficient and protable, but more difficult to edit later'),
        ('GLTF_SEPARATE', 'glTF Separate (.gltf + .bin + textures)', 'Exports multiple files, with separate JSON, binary and texture data. Easiest to edit later')]) # type: ignore
    ab_gltf_lighting : EnumProperty(options = set(), name='Lighting Mode', default='SPEC', description='Optional backwards compatibility for non-standard render engines. Applies to light', items=[
        ('SPEC', 'Standard', 'Physically-based glTF lighting units (cd, lx, nt)'),
        ('COMPAT', 'Unitless', 'Non-physical, unitless lighting. Useful when exposure controls are not available'),
        ('RAW', 'Raw (Deprecated)', 'Blender lighting strengths with no conversion')]) # type: ignore
    ab_gltf_shape_keys : BoolProperty(options = set(), name='Shape Keys', default=False, description='Export shape keys (morph targets)') # type: ignore
    ab_gltf_shape_keys_normals : BoolProperty(options = set(), name='Shape Key Normals', default=True, description='Export vertex normals with shape keys (morph targets)') # type: ignore
    ab_gltf_shape_keys_tangents : BoolProperty(options = set(), name='Shape Key Tangents', default=False, description='Export vertex tangents with shape keys (morph targets)') # type: ignore
    ab_gltf_use_sparse : BoolProperty(options = set(), name='Use Sparse Accessor', default=True, description='Try using Sparse Accessor if it saves space') # type: ignore
    ab_gltf_omitting_sparse : BoolProperty(options = set(), name='Omitting Sparse Accessor', default=False, description='Omitting Sparse Accessor if data is empty') # type: ignore
    ab_gltf_compression : BoolProperty(options = set(), name='Compression', default=False, description='Compress mesh using Draco') # type: ignore
    ab_gltf_compression_level : IntProperty(options = set(), name='Compression Level', default=6, min=0, max=10,  description='') # type: ignore
    ab_gltf_compression_position : IntProperty(options = set(), name='Quantize Position', default=14, min=0, max=30,  description='Quantization bits for position values (0 = no quantization)') # type: ignore
    ab_gltf_compression_normal : IntProperty(options = set(), name='Normal', default=10, min=0, max=30,  description='Quantization bits for normal values (0 = no quantization)') # type: ignore
    ab_gltf_compression_texcoord : IntProperty(options = set(), name='Tex Coord', default=12, min=0, max=30,  description='Quantization bits for texture coordinate values (0 = no quantization)') # type: ignore
    ab_gltf_compression_color : IntProperty(options = set(), name='Color', default=10, min=0, max=30,  description='Quantization bits for color values (0 = no quantization)') # type: ignore
    ab_gltf_compression_generic : IntProperty(options = set(), name='Generic', default=12, min=0, max=30,  description='Quantization bits for generic values like weights or joints (0 = no quantization)') # type: ignore
    ab_gltf_yup : BoolProperty(options = set(), name='+Y Up', default=True, description='Export using glTF convention, +Y Up') # type: ignore
    ab_gltf_tangents : BoolProperty(options = set(), name='Tangents', default=False, description='Export vertex tangents with meshes') # type: ignore
    ab_gltf_vertex_colors : BoolProperty(options = set(), name='Vertex Colors', default=True, description='Export vertex colors with meshes') # type: ignore
    ab_gltf_attributes : BoolProperty(options = set(), name='Attributes', default=False, description='Export Attributes (when starting with underscore)') # type: ignore
    ab_gltf_loose_edges : BoolProperty(options = set(), name='Loose Edges', default=False, description='Export loose edges as lines, using the material from first material slot') # type: ignore
    ab_gltf_loose_points : BoolProperty(options = set(), name='Loose Points', default=False, description='Expaort loose points as glTF points, using the material from the first material slot') # type: ignore
    ab_gltf_keep_original : BoolProperty(options = set(), name='Same Location', default=False, description='Keep original textures files if possible. WARNING: if you use more than one texture, where pbr standard requires only one, only one texture will be used, This can lead to unexpected results') # type: ignore
    ab_gltf_texture_folder : StringProperty(options = set(), name='Image Folder', default='', description='Folder to place textures files in. Relative to the gltf. file') # type: ignore
    ab_gltf_copyright : StringProperty(options = set(), name='Copyright', default='', description='Legal rights and conditions for the model') # type: ignore
    ab_gltf_images : EnumProperty(options = set(), name='Images', default='AUTO', description='Output format for images', items=[
        ('AUTO', 'Automatic', ''),
        ('JPEG', 'JPEG Format (.jpg)', 'Save images as JPEGs'),
        ('WEBP', 'WebP Format', 'Save images as WebPs as main image (no fallback)'),
        ('NONE', 'None', "Don't export images")]) # type: ignore
    ab_gltf_image_quality : IntProperty(options = set(), name='Image Quality', default=75, description='Quality of image export', min=0, max=100) # type: ignore
    ab_gltf_create_webp : BoolProperty(options = set(), name='Create WebP', default=False, description='Create WebP textures for every for every texture. For already WebP textures nothing happens') # type: ignore
    ab_gltf_webp_fallback : BoolProperty(options = set(), name='WebP fallback', default=False, description='For all WebP textures, create a PNG fallback texture') # type: ignore
    ab_gltf_original_spelucar : BoolProperty(options = set(), name='Original Specular', default=False, description='Export original glTF PBR Specular, instead of Blender Principled Shader Specular') # type: ignore

# Bake Items

    ab_new_item_method : EnumProperty(options = set(), name='New Item Method', default='Simple', description='Choose how the new items are added to the list', items=[
        ("Simple", "Single ", "Add a single new item to the list", 'ADD', 0),
        ("Advanced", "Multiple", "Use a panel where the new item(s) can be set. This panel can also be opened with 'CTRL + Click' on the 'Add New' button", 'ADD', 1)]) # type: ignore
    
    ab_dynamic_scale: EnumProperty(options = set(), name="Dynamic Scale", description="Dynamically set the texture size for the new item based on the previous ones.", default='ENABLED', items=[
        ('FALSE', 'Disabled', "Scale by the active item", 'CHECKBOX_DEHLT', 0),
        ('ENABLED', 'Enabled', ("Scale by the previous two items.\n"
                                "\u2022 The size is doubled when the previous two are also doubled and the type is the same\n"
                                "\u2022 The size is divided when the previous two are also divided and the type is the same"), 'CHECKBOX_HLT', 1),
        ('ENABLED+', 'Enabled+', ("Scale by the previous two or three items.\n"
                                "\u2022 The size is doubled when the previous two are also doubled and the type is the same\n"
                                "\u2022 The size is divided when the previous two are also divided and the type is the same\n"
                                "\u2022 The size is doubled when the previous two items have the same size but different types and the third item's size is double of the second\n"
                                "\u2022 The size is divided when the previous two items have the same size but different types and the third item's size is half of the second"), 'CHECKBOX_HLT', 2)]) # type: ignore

    ab_udim_item_tilescale_default : BoolProperty(options = set(), name="Tile Scale Default", description="Disable the default tile & scale item editor", default = True) # type: ignore
    ab_udim_item_default : BoolProperty(options = set(), name="UDIM Default", description="Disable the default type & multiplier editor", default = True) # type: ignore
    ab_udim_item_tile : BoolProperty(options = set(), name="UDIM Tile", description="Enable in-line tile edit", default = False) # type: ignore
    ab_udim_item_scale : BoolProperty(options = set(), name="UDIM Scale", description="Enable in-line tile scale edit", default = False) # type: ignore
    ab_udim_item_type : BoolProperty(options = set(), name="UDIM Type", description="Enable in-line type edit", default = True) # type: ignore
    ab_udim_item_multiplier : BoolProperty(options = set(), name="UDIM Multiplier", description="Enable in-line scale-multiplier edit", default = True) # type: ignore

    ab_item_details : BoolProperty(options = set(), name="Item Details", description="Enable/Disable the visibility of the item specific details", default=True) # type: ignore
    ab_item_type : BoolProperty(options = set(), name="Item Type", description="Enable in-line type edit", default = False) # type: ignore
    ab_item_scale : BoolProperty(options = set(), name="Item Scale", description="Enable in-line scale edit", default = False) # type: ignore
    ab_item_default : BoolProperty(options = set(), name="Item Default", description="Disable default item editor", default = True) # type: ignore

# Bake Queue

    ab_move_finished_bake : BoolProperty(options = set(), name="Finished Bake", description="Move the finished bake item to the bottom of the bake queue list", default = False) # type: ignore
    ab_move_active_bake : BoolProperty(options = set(), name="Active Bake", description="Move the active bake item to the top of the bake queue list", default = True) # type: ignore
    ab_auto_next : EnumProperty(options = set(), name='Auto Next Object', default='On-Success', description='Clear images from the export list', items=[
        ("On-Success", "On-Success", "Continue the bakes with the next object but only if no bakes failed", 'CHECKMARK', 0),
        ("On-Click", "On-Click", "Never continue with the next object, always wait for manual input", 'RESTRICT_SELECT_OFF', 1),
        ("Always", "Always", "Always continue with the next object, even ignoring failed bakes", 'PLAY', 2)]) # type: ignore
    ab_auto_confirm : EnumProperty(options = set(), name='Auto Confirm Results', default='On-Click', description='Auto confirm bake results', items=[
        ("On-Success", "On-Success", "Auto-confirm bake results only if no bakes failed", 'CHECKMARK', 0),
        ("On-Click", "On-Click", "Never auto-confirm bake results, always wait for manual input", 'RESTRICT_SELECT_OFF', 1),
        ("Always", "Always", "Always auto-confirm bake results, even ignoring failed bakes", 'PLAY', 2)]) # type: ignore

# Miscellaneous

    ab_confirm_start_bake : BoolProperty(options = set(), name='', default=True, description='Confirm window for bake start') # type: ignore
    ab_confirm_cancel_bake : BoolProperty(options = set(), name='', default=True, description='Confirm window for bake cancel') # type: ignore
    ab_confirm_bake_results : BoolProperty(options = set(), name='', default=True, description='Confirm window for bake results') # type: ignore
    ab_confirm_next_object : BoolProperty(options = set(), name='', default=True, description='Confirm window for next object bake') # type: ignore
    ab_confirm_queue_item_gate : BoolProperty(options = set(), name='', default=True, description='Confirm window for disabling and enabling items in the bake queue list') # type: ignore
    
    ab_start_popup_settings : BoolProperty(options = set(), name="Settings", default=True, description="Disable all the settings with this option") # type: ignore
    ab_start_popup_final_object : BoolProperty(options = set(), name="Final Object", default=True, description="") # type: ignore
    ab_start_popup_object_offset : BoolProperty(options = set(), name="Final Object Offset", default=True, description="") # type: ignore
    ab_start_popup_final_material : BoolProperty(options = set(), name="Final Material", default=True, description="") # type: ignore
    ab_start_popup_final_shader : BoolProperty(options = set(), name="Final Shader", default=True, description="") # type: ignore
    ab_start_popup_texture_apply : BoolProperty(options = set(), name="Texture Apply", default=True, description="") # type: ignore
    ab_start_popup_export_textures : BoolProperty(options = set(), name="Export Textures", default=True, description="") # type: ignore
    ab_start_popup_export_objects : BoolProperty(options = set(), name="Export Objects", default=True, description="") # type: ignore
    ab_start_popup_selected_to_active : BoolProperty(options = set(), name="Selected to Active", default=True, description="") # type: ignore
    ab_start_popup_keep_textures : BoolProperty(options = set(), name="Keep Textures", default=True, description="") # type: ignore
    
    ab_export_list : EnumProperty(options = set(), name='Clear Exports', default='Ask', description='Clear images from the export list', items=[
        ("Ask", "Ask", "Ask before bake starts", 'QUESTION', 0),
        ("Clear", "Clear", "Always remove the images from the list", 'TRASH', 1),
        ("Keep", "Keep", "Keep the images in the export list", 'GROUP', 2)]) # type: ignore
        
    ab_list_padding : EnumProperty(options=set(), name='List Layout', default='Moderate', description='Choose the padding for the lists and their buttons', items=[
        ('Compact', 'Compact', 'No padding', 'SEQ_STRIP_DUPLICATE', 0),
        ('Moderate', 'Moderate', 'Moderate padding', 'SEQ_STRIP_DUPLICATE', 1),
        ('Spacious', 'Spacious', 'Maximum padding', 'SEQ_STRIP_DUPLICATE', 2)]) # type: ignore
        
    ab_alert_texts : BoolProperty(options = set(), name='Show Alerts', default=True, description='Show text alerts below the alerted UI elements') # type: ignore
    ab_nodealert : BoolProperty(options = set(), name="Node Alert", description="Create a 'frame node' in the shader editor as a reminder not to delete, move, or modify nodes until the bake is completed", default = True) # type: ignore
    ab_bake_error_msg : BoolProperty(options = set(), name='Show Bake Failures', default=False, description='Show the error message in the list below the failed bake item') # type: ignore
    
    ab_report_requests : BoolProperty(options = set(), name="Start Requests", default=True, description="Report the collection of bake requests. \n\u2022 Auto Bake: Collecting objects to bake... \n\u2022 Auto Bake: ...2 objects are added to the object queue list.\n\u2022 Auto Bake: Collecting objects to bake... \n\u2022 Auto Bake: ...3 bake requests are added to the queue") # type: ignore
    ab_report_bake_start : BoolProperty(options = set(), name="Bake Start", default=True, description="Report when a texture's baking process is started. \n\u2022 Auto Bake: Texture 'Base Color - 512' is started baking") # type: ignore
    ab_report_bake_end : BoolProperty(options = set(), name="Bake End", default=True, description="Report when a texture's baking process is ended. \n\u2022 Auto Bake: Texture 'Base Color - 512' is finished baking") # type: ignore
    ab_report_object_start : BoolProperty(options = set(), name="Object Start", default=True, description="Report when an object starts its baking process. \n\u2022 Auto Bake: Object 'Cube' has been started baking") # type: ignore
    ab_report_object_end : BoolProperty(options = set(), name="Object End", default=True, description="Report when an object has completed all its baking items. \n\u2022 Auto Bake: Object 'Cube' is finished. Baked & Exported: 3; Canceled: 0; Failed: 0") # type: ignore
    ab_report_texture_export : BoolProperty(options = set(), name="Texture Export", default=True, description="Report when a texture is exported. \n\u2022 Auto Bake: 'Base Color - 512' successfully exported to: C:\Cube") # type: ignore
    ab_report_object_export : BoolProperty(options = set(), name="Object Export", default=True, description="Report when an object is exported. \n\u2022 Auto Bake: Object 'Cube' has been exported") # type: ignore
    ab_report_bake_summary : BoolProperty(options = set(), name="Bake Summary", default=True, description="Report a summary of bakes for the object. \n\u2022 Auto Bake: Bakes are finished for all (2) objects: Baked & Exported: 6; Canceled: 0; Failed: 0") # type: ignore
    ab_report_object_summary : BoolProperty(options = set(), name="Object Summary", default=True, description="Report a summary of the baked objects. \n\u2022 Auto Bake: Objects are finished baking. Baked & Exported: 2; Canceled: 0; Mixed: 0; Failed: 0") # type: ignore
    ab_report_bake_error : BoolProperty(options = set(), name="Bake Errors", default=True, description="Report when there is an issue with the bake. \n\u2022 Auto Bake: Target object 'Cube' has no active UV layer") # type: ignore

    ab_subfolder_use_prefix : BoolProperty(options = set(), default=False, description="Use prefix with bake type in subfolder names, otherwise only the bake type will be used", name='Use Prefix') # type: ignore

#------------------------------------------------------------------------------------
#   List Properties

class SPARROW_PG_BakeQueue(PropertyGroup):
    Type : StringProperty(options = set(), name="", default="Unknown")
    Size : IntProperty(options = set(), name="", default=0)
    Multiplier : FloatProperty(options = set(), name='', default=1)
    Status : StringProperty(options = set(), name="", default="Pending")
    Cancel : BoolProperty(options = set(), name='', default=False)
    Enabled : BoolProperty(options = set(), name='', default=True)
    Icon : StringProperty(options = set(), name="", default="PREVIEW_RANGE")
    Error : StringProperty(options = set(), name='', default='')
    
    Image : PointerProperty(options = set(), type=bpy.types.Image)
    Prefix : StringProperty(options = set(), default='')
    Type_Name : StringProperty(options = set(), default='')
    

class SPARROW_PG_Bake(PropertyGroup):
    def update_duplicates(self, context):
        for item in context.scene.autobake_bakelist:
            item.IsDuplicate = sum(1 for item2 in context.scene.autobake_bakelist if item.Type == item2.Type and item.Size == item2.Size) > 1
            item.name = f"{item.Type} {item.Size}" + (' Enabled' if item.Gate else ' Disabled') + (' Duplicate' if item.IsDuplicate else '')
                
    def update_gate(self, context):
        self.name = self.Type + " " + str(self.Size) + (' Enabled' if self.Gate else ' Disabled') + (' Duplicate' if self.IsDuplicate else '')
        context.scene.autobake_properties.ab_bake_list_item_count = sum(1 for item in context.scene.autobake_bakelist if item.Gate)
        
    def update_type(self, context):
        self.update_duplicates(context)
        
        scene: Scene = context.scene
        abp = scene.autobake_properties
        
        type_names = {}
        for item in abp.ab_baketype_name_all.split(', '):
            type_names[item.split(':')[0]] = item.split(':')[1]
            
        active_type = scene.autobake_bakelist[scene.autobake_bakelist_index].Type
        if active_type not in type_names:
            type_names[active_type] = active_type.strip()
            
        abp.ab_baketype_name = type_names[active_type]


    Type: EnumProperty(options = set(), name="", items=bake_items, default="Base Color", description="Texture Type", update=update_type)
    Size: IntProperty(options = set(), min=1, max=65536, default=512, name="", description="Texture scale", update=update_duplicates)
    Gate: BoolProperty(options = set(), name="", default=True, description="Enable item to Bake", update=update_gate)
    IsDuplicate: BoolProperty(options = set(), name="", default=False)


class SPARROW_PG_UDIMType(PropertyGroup):
    def update_duplicates(self, context):
        for item in context.scene.autobake_udimlist:
            item.IsDuplicate = sum(1 for item2 in context.scene.autobake_udimlist if (item.Type == item2.Type and item.Size == item2.Size)) > 1
            item.name = f"{item.Type} {item.Size:.2f}" + (' Enabled' if item.Gate else ' Disabled') + (' Duplicated' if item.IsDuplicate else '')
            
    def update_gate(self, context):
        self.update_duplicates(context)
        context.scene.autobake_properties.ab_udimtype_list_item_count = sum(1 for item in context.scene.autobake_udimlist if item.Gate)

    def update_type(self, context):
        self.update_duplicates(context)
        
        scene = context.scene
        abp = scene.autobake_properties

        type_names = {}
        for item in abp.ab_baketype_name_all.split(', '):
            type_names[item.split(':')[0]] = item.split(':')[1]
            
        active_type = scene.autobake_udimlist[scene.autobake_udimlist_index].Type
        if active_type not in type_names:
            type_names[active_type] = active_type.strip()
            
        abp.ab_baketype_name = type_names[active_type]

        
    Type : EnumProperty(options = set(), name="", description="Bake Type", items=bake_items, default='Base Color', update=update_type)
    Size : FloatProperty(options = set(), name="", default=1, min=.01, soft_min=.1, max=100, soft_max=10, precision=2, step=10, description='UDIM Tile Size Multiplier', update=update_duplicates)
    Gate: BoolProperty(options = set(), name="", default=True, description="Enable item to Bake", update=update_gate)
    IsDuplicate: BoolProperty(options = set(), name="", default=False)


class SPARROW_PG_UDIMTile(PropertyGroup):
    def update_name(self, context):
        self.name = str(self.UDIM)+' '+str(self.Size)+(' Enabled' if self.Gate else ' Disabled')+(' Duplicated' if self.IsDuplicate else '')
        
    def update_gate(self, context):
        self.update_name(context)
        context.scene.autobake_properties.ab_udim_list_item_count = sum(1 for item in context.scene.autobake_udimtilelist if item.Gate)
        
    def update_duplicates(self, context):
        self.update_name(context)
        scene = context.scene
        
        for item in scene.autobake_udimtilelist:
            item.IsDuplicate = sum(1 for item2 in scene.autobake_udimtilelist if item.UDIM == item2.UDIM) > 1
            item.name = str(item.UDIM)+' '+str(item.Size)+(' Enabled' if item.Gate else ' Disabled')+(' Duplicated' if item.IsDuplicate else '')
    
    def update_label(self, context):
        if self.Label == "":
            self.Label = "#Unknown"
            
    UDIM : IntProperty(options = set(), name="", default=1001, min=1001, max=2000, description="UDIM Tile Number", update=update_duplicates)
    Label : StringProperty(options = set(), name="UDIM Tile Label", default='#Unknown', update=update_label)
    Size : IntProperty(options = set(), name="", default=512, min=1, max=65536, description="UDIM Tile Size", update=update_name)
    Gate: BoolProperty(options = set(), name="", default=True, description="Enable UDIM Tile", update=update_gate)
    IsDuplicate: BoolProperty(options = set(), name="", default=False)
    
    
class SPARROW_PG_SourceObjects(PropertyGroup):
    def object_update(self, context):
        scene = context.scene
        list = scene.autobake_sourceobject
        
        for index in range(len(list)-1, -1, -1):
            if list[index].Object == None or list[index].Object.type not in ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT']:
                list.remove(index)
            elif sum(1 for item in list if (item.Object == list[index].Object)) > 1:
                list.remove(index)
        list.add()
   
    Object: PointerProperty(options = set(), type=bpy.types.Object, update=object_update)


class SPARROW_PG_ImageExport(PropertyGroup):
    
    def update_name(self, context):
        if self.Image and self.Name != self.Image.name:
            if self.Name not in bpy.data.images:
                if self.Name == '':
                    self.Image.name = 'Auto Bake Image'
                else:
                    self.Image.name = self.Name
            
            self.Name = self.Image.name
            self.name = self.Name
            
    Name : StringProperty(options = set(), name="Export Name", update=update_name)
    Gate : BoolProperty(options = set(), default=True, description="Disable/Enable export for this image. If it's disabled at the export it will be removed from the list without exporting it", name='Toggle Export')
    Image : PointerProperty(options = set(), type=bpy.types.Image)
    Prefix : StringProperty(options = set(), )
    Type : StringProperty(options = set(), )
    Label : StringProperty(options = set(), )
        

class SPARROW_PG_ObjectQueue(PropertyGroup):
    Object : PointerProperty(options = set(), name="Object", type=bpy.types.Object)
    Gate: BoolProperty(options = set(), name="", default=True, description="Enable object to bake")
    Status : StringProperty(options = set(), name="", default="Pending")
    Enabled : BoolProperty(options = set(), name='', default=True)
    Icon : StringProperty(options = set(), name="", default="PREVIEW_RANGE")
    Error : StringProperty(options = set(), name='', default='')
    Cancel : BoolProperty(options = set(), name='', default=False)
