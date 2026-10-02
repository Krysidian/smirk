import bpy
from bpy.props import *
from collections import defaultdict
from .operators import *
from .custom_icons import *

from bpy.types import Context
from bpy.types import ID, Bone, BoneColor, Context, Object, PoseBone, PropertyGroup


class Properties_Smirk(PropertyGroup):

    
    smirk_version: FloatProperty(
        name="SMIRK Version",
        description="For internal use only",
        default=0.0
    )
    


_classes = (
    Properties_Smirk,
)

_register, _unregister = bpy.utils.register_classes_factory(_classes)

def register() -> None:
    _register()
    Object.smirk = PointerProperty(type=Properties_Smirk)
    
    
def unregister() -> None:
    _unregister()

    del Object.smirk