from dataclasses import dataclass
from types import SimpleNamespace
from typing import List
import bpy

from .utils import *


@dataclass
class BlueprintInstance:    
    object: bpy.types.Object
    collection: bpy.types.Collection

