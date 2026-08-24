import bpy
from pathlib import Path
from bpy.app.handlers import persistent

ASSET_FILENAME = "smirk_assets.blend"

SMIRK_MODIFIER = "SMIRK"

PROXY_MATERIAL = ".PROXY-Material"

GP_CUTTER_MAT = "GP_Cutter"

OVERRIDE_LAYER_MATERIAL = "GP-Override Layer Material"

TRANSPARENCY_MASK = "Transparency Mask"

OBJECT_SOCKET = 'Socket_2'

CUTTER_MASK = 'Socket_4'

SHADER_MASK = 'Socket_3'

MODIFIER_MODE = 'Socket_62'

CUTTER_RIM_MAT = 'Socket_25'

MAIN_SEP_FACTOR = 0.2


def get_smirk_obj_and_modifier(context):
    wm = context.window_manager
    obj = get_smirk_object(context)
    gn_name = wm.smirk_mod_list[wm.smirk_mod_active].name
    gn_mod = obj.modifiers.get(gn_name)

    return obj, gn_mod

def resolve_asset_path(filename: str = ASSET_FILENAME) -> Path:
    folder_root = Path(__file__).resolve().parent
    return folder_root / filename


def get_asset_nodetree(tree_name: str, asset_filename: str = ASSET_FILENAME) -> bpy.types.NodeTree:
    
    # Check if the NodeTree already exists
    existing_nodetree = bpy.data.node_groups.get(tree_name)
    if existing_nodetree is not None:
        return existing_nodetree
    
    asset_path = resolve_asset_path(asset_filename)
    if not asset_path.exists():
        raise FileNotFoundError(f"Library file not found: {asset_path}")
    
    asset_path_str = str(asset_path)
    with bpy.data.libraries.load(asset_path_str, link=False) as (data_from, data_to):
        if tree_name not in data_from.node_groups:
            raise ValueError(
                f"Node tree '{tree_name}' not found in '{asset_filename}'.\n"
                f"Available: {list(data_from.node_groups)}"
            )
        data_to.node_groups = [tree_name]

    appended_nodetree = bpy.data.node_groups.get(tree_name)
    appended_nodetree.asset_clear()
    return appended_nodetree

def get_asset_material(mat_name: str, asset_filename: str = ASSET_FILENAME) -> bpy.types.Material:
    
    # Check if the Material already exists
    existing_material = bpy.data.materials.get(mat_name)
    if existing_material is not None:
        return existing_material
    
    asset_path = resolve_asset_path(asset_filename)
    if not asset_path.exists():
        raise FileNotFoundError(f"Library file not found: {asset_path}")
    
    asset_path_str = str(asset_path)
    with bpy.data.libraries.load(asset_path_str, link=False) as (data_from, data_to):
        if mat_name not in data_from.materials:
            raise ValueError(
                f"Material '{mat_name}' not found in '{asset_filename}'.\n"
                f"Available: {list(data_from.materials)}"
            )
        data_to.materials = [mat_name]

    appended_material = bpy.data.materials.get(mat_name)
    appended_material.asset_clear()
    return appended_material

# add no proxy prefix for modifier names to exclude them from copying

def _add_simple_driver(target_id, target_path, src_id, src_path, index=None):
    """Add a driver on target_id.target_path that reads src_id.src_path.

    If `index` is provided, it will call driver_add(data_path, index). This
    covers array properties like location/scale/rotation components.
    """
    try:
        # driver_add accepts either (data_path) or (data_path, index)
        if index is None:
            fcurve = target_id.driver_add(target_path)
        else:
            fcurve = target_id.driver_add(target_path, index)
    except Exception:
        return False

    # Normalize FCurve/list return and retrieve its driver (use helper)
    driver = _get_driver_from_fcurve(fcurve)
    if driver is None:
        return False

    try:
        # Clear any existing variables and set a single SIMPLE_PROP variable
        for v in list(driver.variables):
            driver.variables.remove(v)

        var = driver.variables.new()
        var.name = 'var'
        var.type = 'SINGLE_PROP'
        targ = var.targets[0]
        targ.id = src_id
        targ.data_path = src_path
        driver.expression = 'var'
        return True
    except Exception:
        return False

def ensure_edit_mode(self, context):
    editmode = getattr(context, "mode", None)

    if editmode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

def _get_driver_from_fcurve(fcurve):
    """Normalize possible list/FCurve return from driver_add and return its driver or None."""
    
    if isinstance(fcurve, (list, tuple)):
        if len(fcurve) == 0:
            return None
        fcurve = fcurve[0]
    return getattr(fcurve, 'driver', None)

def _switch_properties_to_modifier_tab() -> bool:
    """Set any Properties editor to the Modifier context. Returns True if changed."""
    try:
        # quick path: if current space is a Properties editor
        space = getattr(bpy.context, "space_data", None)
        if space is not None and getattr(space, "type", "") == "PROPERTIES":
            space.context = "MODIFIER"
            return True
    except Exception:
        pass

    # fallback: search all windows/screens for a Properties area
    for window in bpy.context.window_manager.windows:
        try:
            for area in window.screen.areas:
                if area.type == "PROPERTIES":
                    try:
                        # preferred: use active space
                        area.spaces.active.context = "MODIFIER"
                        return True
                    except Exception:
                        # fallback: iterate spaces in area
                        for space in area.spaces:
                            if getattr(space, "type", "") == "PROPERTIES":
                                space.context = "MODIFIER"
                                return True
        except Exception:
            continue
    return False



                

def collect_references_to_obj(obj: bpy.types.Object):
    refs = []
    if obj is None:
        return refs
    for owner in bpy.data.objects:
        # Modifiers and object constraints
        for mod in owner.modifiers:
            if mod.type == 'NODES':
                ng = getattr(mod, "node_group", None)
                if not ng:
                    continue
                interface = getattr(ng, "interface", None)
                if not interface:
                    continue
                for item in interface.items_tree:
                    if item.item_type != 'SOCKET':
                        continue
                    if item.in_out != 'INPUT':
                        continue
                    if item.bl_socket_idname != 'NodeSocketObject':
                        continue

                    try:
                        val = mod.get(item.identifier, None)
                    except Exception:
                        continue
                    if val is obj:
                        refs.append({
                            "kind": "gn_modifier",
                            "owner": owner.name,
                            "modifier": mod.name,
                            "prop": item.identifier,
                        })
                        print(val)

            for prop in mod.bl_rna.properties:
                if getattr(prop, "type", None) != 'POINTER' or getattr(prop, "is_readonly", False):
                    continue
                try:
                    val = getattr(mod, prop.identifier, None)
                except Exception:
                    continue
                if val is obj:
                    refs.append({
                        "kind": "modifier",
                        "owner": owner.name,
                        "modifier": mod.name,
                        "prop": prop.identifier,
                    })
        for con in owner.constraints:
            for prop in con.bl_rna.properties:
                if getattr(prop, "type", None) != 'POINTER' or getattr(prop, "is_readonly", False):
                    continue
                try:
                    val = getattr(con, prop.identifier, None)
                except Exception:
                    continue
                if val is obj:
                    refs.append({
                        "kind": "constraint",
                        "owner": owner.name,
                        "constraint": con.name,
                        "prop": prop.identifier,
                    })
        # Bone Constraints
        if owner.type == 'ARMATURE':
            pose = owner.pose
            if not pose:
                continue
            for pb in pose.bones:
                for con in pb.constraints:
                    for prop in con.bl_rna.properties:
                        if getattr(prop, "type", None) != 'POINTER' or getattr(prop, "is_readonly", False):
                            continue
                        try:
                            val = getattr(con, prop.identifier, None)
                        except Exception:
                            continue
                        if val is obj:
                            refs.append({
                                "kind": "bone_constraint",
                                "owner": owner.name,
                                "bone": pb.name,
                                "constraint": con.name,
                                "prop": prop.identifier,
                            })
    def _collect_drivers_from(owner_collection, owner_type_name):
        for owner in owner_collection:
            anim_data = getattr(owner, "animation_data", None)
            if not anim_data:
                continue
            for fcur in anim_data.drivers:
                driver = fcur.driver
                for var in driver.variables:
                    for tidx, targ in enumerate(var.targets):
                        if targ.id is obj:
                            refs.append({
                                "kind": "driver",
                                "owner_type": owner_type_name,
                                "owner": owner.name,
                                "data_path": fcur.data_path,
                                "array_index": getattr(fcur, "array_index", -1),
                                "var_name": var.name,
                                "target_index": tidx,
                            })                        
    _collect_drivers_from(bpy.data.objects, "object")
    _collect_drivers_from(bpy.data.materials, "material")
    _collect_drivers_from(bpy.data.node_groups, "node_tree")
    return refs

def restore_references_to_obj(refs: list, obj: bpy.types.Object):
    if obj is None:
        return
    for r in refs:
        try:
            kind = r.get("kind")
            if kind == 'gn_modifier':
                owner = bpy.data.objects.get(r['owner'])
                if not owner:
                    continue
                mod = owner.modifiers.get(r['modifier'])
                if not mod:
                    continue
                try:
                    prop = r.get('prop')
                    mod[prop] = obj
                except Exception:
                    continue
            kind = r.get("kind")
            if kind == 'modifier':
                owner = bpy.data.objects.get(r['owner'])
                if not owner:
                    continue
                mod = owner.modifiers.get(r['modifier'])
                if not mod:
                    continue
                try:
                    setattr(mod, r['prop'], obj)
                except Exception:
                    continue
            elif kind == 'constraint':
                owner = bpy.data.objects.get(r['owner'])
                if not owner:
                    continue
                con = owner.constraints.get(r['constraint'])
                if not con:
                    continue
                try:
                    setattr(con, r['prop'], obj)
                except Exception:
                    continue
            elif kind == 'bone_constraint':
                owner = bpy.data.objects.get(r['owner'])
                if not owner or owner.type != 'ARMATURE':
                    continue
                pb = owner.pose.bones.get(r['bone'])
                if not pb:
                    continue
                con = pb.constraints.get(r['constraint'])
                if not con:
                    continue
                try:
                    setattr(con, r['prop'], obj)
                except Exception:
                    continue
            elif kind == "driver":
                owner = None
                if r.get("owner_type") == "object":
                    owner = bpy.data.objects.get(r["owner"])
                elif r.get("owner_type") == "material":
                    owner = bpy.data.materials.get(r["owner"])
                elif r.get("owner_type") == "node_tree":
                    owner = bpy.data.node_groups.get(r["owner"])
                if not owner:
                    continue
                ad = getattr(owner, "animation_data", None)
                if not ad:
                    continue
                fmatch = None
                for fcur in getattr(ad, "drivers", []):
                    if fcur.data_path == r["data_path"] and getattr(fcur, "array_index", -1) == r.get("array_index", -1):
                        fmatch = fcur
                        break
                if not fmatch:
                    continue
                driver = fmatch.driver
                var = next((v for v in driver.variables if v.name == r["var_name"]), None)
                if var is None:
                    continue
                tidx = r.get("target_index", 0)
                if tidx < len(var.targets):
                    try:
                        var.targets[tidx].id = obj
                    except Exception:
                        var.targets[tidx].id = bpy.data.objects.get(obj.name, obj)


                
        except Exception:
            continue

class SMIRK_OT_setup_proxy_mesh(bpy.types.Operator):
    bl_idname = "smirk.setup_proxy_mesh"
    bl_label = "Setup Proxy"
    bl_description = "Create a linked duplicate of the selected Object that will be used as a target for certain modifiers" 
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty(name='Target Object', default='')

    def execute(self, context):  # type: ignore

        
        # Ensure Object Mode
        ensure_edit_mode(self, context)

        orig = bpy.data.objects.get(self.object_name) if self.object_name else context.active_object

        if orig is None:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}
        
        # Prevent running this operator on a proxy object (avoid nesting proxies)
        if orig.name.startswith('PROXY-'):
            self.report({'ERROR'}, "Operator cannot run on a PROXY Object")
            return {'CANCELLED'}
        
        # Determine proxy name and whether a proxy already exists
        base_name = f"PROXY-{orig.name}"
        existing_proxy = None
        proxy_collections = None
        


        for obj in bpy.data.objects:
            if obj.name == base_name or obj.name.startswith(base_name + '.'):
                existing_proxy = obj
                break
        
        refs = []

        if existing_proxy is not None:
            proxy = existing_proxy
            proxy_exists = True
            
            refs = collect_references_to_obj(proxy)

            # Fallback to using orig's collection otherwise use previous Proxy collections
            if proxy.users_collection:
                proxy_collections = list(proxy.users_collection)
            else:
                proxy_collections = list(orig.users_collection)

            bpy.data.objects.remove(proxy)


        # Only duplicate active Object
        bpy.ops.object.select_all(action='DESELECT')
        orig.select_set(True)
        context.view_layer.objects.active = orig
        bpy.ops.object.duplicate(linked=True)
        # Create a linked duplicate
        proxy = context.active_object

        # Ensure unique proxy name
        name = base_name
        i = 1
        while name in bpy.data.objects:
            name = f"{base_name}.{i:03d}"
            i += 1
        proxy.name = name
        proxy_exists = False

        # Reassign collections
        if proxy_collections is not None:
            for col in proxy.users_collection:
                col.objects.unlink(proxy)
            for col in proxy_collections:
                col.objects.link(proxy)

        # Drivers for transforms: location, scale, rotation (handle Euler/Quaternion/Axis-Angle)
        # Only create transform drivers if we are making a new proxy
        if not proxy_exists:
            # Location
            for i in range(3):
                _add_simple_driver(proxy, 'location', orig, f'location[{i}]', index=i)

            # Scale
            for i in range(3):
                _add_simple_driver(proxy, 'scale', orig, f'scale[{i}]', index=i)

            # Rotation Quaternion
            if orig.rotation_mode == 'QUATERNION':
                for i in range(4):
                    _add_simple_driver(proxy, 'rotation_quaternion', orig, f'rotation_quaternion[{i}]', index=i)
            # Rotation Axis Angle
            elif orig.rotation_mode == 'AXIS_ANGLE':
                for i in range(4):
                    _add_simple_driver(proxy, 'rotation_axis_angle', orig, f'rotation_axis_angle[{i}]', index=i)
            # Rotation Euler
            else:
                for i in range(3):
                    _add_simple_driver(proxy, 'rotation_euler', orig, f'rotation_euler[{i}]', index=i)

        # Get list of modifiers on the original object
        orig_mod_names = [m.name for m in orig.modifiers]
        
        # Remove Smirk Modifiers and modifiers that contain 'NO_PROXY'
        for mod in proxy.modifiers:
            if 'NO_PROXY' in mod.name:
                proxy.modifiers.remove(mod)
                continue
            if mod.name not in orig_mod_names:
                try:
                    proxy.modifiers.remove(mod)
                except Exception:
                    pass
                continue
            if mod.type == 'NODES' and mod.node_group and mod.node_group.name == SMIRK_MODIFIER:
                proxy.modifiers.remove(mod)
                continue


        for mod in orig.modifiers:

            # Remove Geometry Node modifiers using node group SMIRK_MODIFIER
            for m in list(proxy.modifiers):
                try:
                    if m.type == 'NODES' and getattr(m, 'node_group', None) is not None:
                        if getattr(m.node_group, 'name', '') == SMIRK_MODIFIER:
                            proxy.modifiers.remove(m)
                except Exception:
                    continue

            for prop in mod.bl_rna.properties:
                if getattr(prop, 'is_readonly', False):
                    continue

                # Skip internal/rna properties
                ident = prop.identifier
                if ident in {'rna_type', 'name', 'type'}:
                    continue
                prop_type = getattr(prop, 'type', None)
                if prop_type not in {'BOOLEAN', 'INT', 'FLOAT', 'ENUM'}:
                    continue

                src_path = f'modifiers["{mod.name}"].{ident}'
                target_path = src_path

                # Use helper which wraps driver_add and variable setup
                success = False

                base_path = f'modifiers["{mod.name}"].{ident}'
                array_len = getattr(prop, "array_length", 0) or 0


                try:
                    # Try with full path (no index)
                    success = _add_simple_driver(proxy, target_path, orig, src_path, index=None)
                except Exception:
                    success = False

                if array_len > 1:
                    for i in range(array_len):
                        src_path = f'{base_path}[{i}]'
                        target_path = base_path  # driver_add will use index argument
                        try:
                            _add_simple_driver(proxy, target_path, orig, src_path, index=i)
                        except Exception:
                            # best-effort: try without index (some APIs accept flattened path)
                            try:
                                _add_simple_driver(proxy, f'{base_path}[{i}]', orig, src_path, index=None)
                            except Exception:
                                pass

                

                # Fallback: try to add with explicit path string if needed by API
                if not success:
                    try:
                        success = _add_simple_driver(proxy, f'modifiers["{mod.name}"].{ident}', orig, src_path, index= None)
                    except Exception:
                        success = False

        

        # Adjust Proxy Selection and Visuals
        try:
            # Deselect all, select orig and make active
            for o in context.selected_objects:
                o.select_set(False)
        except Exception:
            pass
        try:
            orig.select_set(True)
            context.view_layer.objects.active = orig
        except Exception:
            pass
        proxy.hide_render = True
        proxy.display_type = 'BOUNDS'
        proxy.visible_camera = False
        proxy.visible_shadow = False
        proxy.visible_diffuse = False
        proxy.visible_glossy = False
        proxy.visible_transmission = False
        proxy.visible_volume_scatter = False
        proxy.visible_shadow = False



        try:
            proxy_mat = get_asset_material(PROXY_MATERIAL)
        except Exception as e:
            proxy_mat = None
            self.report({'WARNING'}, f"Could not append proxy material '{PROXY_MATERIAL}': {e}")

        if len(proxy.material_slots) == 0:
            # Create temp material to fill new slot then remove it again
            tmp = bpy.data.materials.new(name="__tmp_slot__")
            proxy.data.materials.append(tmp)  
            proxy.data.materials[-1] = None    
            bpy.data.materials.remove(tmp)     
        else:
            for slot in proxy.material_slots:
                try:
                    slot.link = 'OBJECT'
                    slot.material = proxy_mat
                except:
                    continue

        
        restore_references_to_obj(refs, proxy)

        self.report({'INFO'}, f"Proxy '{proxy.name}' created/updated for '{orig.name}'")
        return {'FINISHED'}


class SMIRK_OT_fix_dependency_loop(bpy.types.Operator):
    bl_idname = "smirk.fix_dependency_loop"
    bl_label = "Fix Dependency Loops"
    bl_description = "Replaces References to the Surface Object on the Cutter Object with the PROXY Object." 
    bl_options = {'UNDO'}
    cutter_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()
    proxy_name: bpy.props.StringProperty()


    def execute(self, context):
        cutter_obj = bpy.data.objects.get(self.cutter_name)
        context.view_layer.depsgraph.update()
        cutter_obj = bpy.data.objects.get(self.cutter_name)
        obj = bpy.data.objects.get(self.object_name)
        proxy = bpy.data.objects.get(self.proxy_name)
        
        if not proxy:
            self.report({'ERROR'}, f"Create PROXY Object first in order to replace references.'")
            return {'CANCELLED'}
        if not cutter_obj:
            return {'CANCELLED'}
        if not obj:
            return {'CANCELLED'}
        
        replaced = 0

        for mod in cutter_obj.modifiers:
            # Geometry Node Modifiers
            if mod.type == 'NODES':
                interface = interface = mod.node_group.interface
                for item in interface.items_tree:
                    if item.item_type == 'PANEL':
                        continue
                    if item.bl_socket_idname != 'NodeSocketObject':
                        continue
                    if mod[item.identifier] == obj:
                        mod[item.identifier] = proxy
                        replaced += 1
                
            # Regular Modifiers
            else:
                for prop in mod.bl_rna.properties:
                    if prop.is_readonly:
                        continue
                    if prop.type != 'POINTER':
                        continue
                    try:
                        pointer_name = prop.identifier
                        pointer = getattr(mod, pointer_name)
                        if pointer is obj:
                            setattr(mod, pointer_name, proxy)
                            replaced += 1
                    except:
                        continue
        if replaced > 0:
            self.report({'INFO'}, f"Replaced {replaced} references of '{obj.name}' with '{proxy.name}'")
        else:
            self.report({'INFO'}, "No Surface Object references were found")
        return {'FINISHED'}

class SMIRK_OT_edit_cutter_obj(bpy.types.Operator):
    bl_idname = 'smirk.edit_cutter_obj'
    bl_label = 'Edit Cutter Object'
    bl_description = 'Enter the edititng context for the active context cutter object'
    bl_options = {"UNDO"}

    cutter_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()
    proxy_name: bpy.props.StringProperty()

    def execute(self, context):
        context.view_layer.depsgraph.update()
        cutter_obj = bpy.data.objects.get(self.cutter_name)
        obj = bpy.data.objects.get(self.object_name)
        proxy = bpy.data.objects.get(self.proxy_name)

        if not cutter_obj:
            return {'CANCELLED'}
        if not obj:
            return {'CANCELLED'}
        

        # Make Cutter Object active, deselect everything else and select surface object
        context.view_layer.objects.active = cutter_obj
        for ob in bpy.data.objects:
            ob.select_set(False)
        #obj.select_set(True)

        if cutter_obj.type=='GREASEPENCIL':
            bpy.ops.object.mode_set(mode='PAINT_GREASE_PENCIL')
            #bpy.ops.wm.tool_set_by_id(name="builtin.brush")
            context.scene.tool_settings.gpencil_stroke_placement_view3d = 'SURFACE'
        else:
            bpy.ops.object.mode_set(mode='EDIT')

        if proxy:
            proxy.hide_viewport = False
            proxy.hide_set(False)
            proxy.display_type = 'SOLID'
            proxy.show_in_front = False



        return {'FINISHED'}
    
class SMIRK_OT_goto_surface_obj(bpy.types.Operator):
    bl_idname = 'smirk.goto_surface_object'
    bl_label = 'Go to Surface Object'
    bl_description = 'Enter the edititng context for the active context cutter object'
    bl_options = {"UNDO"}

    cutter_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()
    proxy_name: bpy.props.StringProperty()

    def execute(self, context):
        context.view_layer.depsgraph.update()
        cutter_obj = bpy.data.objects.get(self.cutter_name)
        obj = bpy.data.objects.get(self.object_name)
        proxy = bpy.data.objects.get(self.proxy_name)

        if not cutter_obj:
            return {'CANCELLED'}
        if not obj:
            return {'CANCELLED'}
        

        # Make Cutter Object active, deselect everything else and select surface object
        for ob in bpy.data.objects:
            ob.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        bpy.ops.object.mode_set(mode='OBJECT')

        if proxy:
            proxy.hide_viewport = False
            proxy.hide_set(False)
            proxy.display_type = 'BOUNDS'
            proxy.show_in_front = False



        return {'FINISHED'}

class SMIRK_OT_modifier_add(bpy.types.Operator):
    bl_idname = "smirk.modifier_add"
    bl_label = "Add Smirk Modifier"
    bl_description = "Create a linked duplicate of the selected Object that will be used as a target for certain modifiers"
    bl_options = {'UNDO'}
    object_name: bpy.props.StringProperty(name='Target Object', default='')

    modifier_name: bpy.props.StringProperty(
        name='Modifier Name',
        description='Name of the SMIRK Modifier',
        default=SMIRK_MODIFIER
    )

    mask_name: bpy.props.StringProperty(
        name='Mask Name',
        description='Name of the Vertex Group or GP Layer used to determine the Body opening',
        default='cutter'
    )

    shader_att: bpy.props.StringProperty(
        name='Shader Attribute',
        description='Attribute for the Mask used in the Shader to control Transparency',
        default='cutter_mask'
    )


    def invoke(self, context, event):
        wm = context.window_manager
        op_props = wm.smirk_op_props
        # Reset Operator Properties for a Clean Slate
        op_props.cutter_obj = None
        return context.window_manager.invoke_props_dialog(self)


    def draw(self, context):

        wm = context.window_manager
        op_props = wm.smirk_op_props

        split_factor = 0.4

        layout = self.layout
        row = layout.row()
        row.alignment = 'CENTER'
        row.label(text='Modifier Setup')

        box = layout.box()
        row = box.split(factor=split_factor)
        row.label(text='Modifier Name')
        row.prop(self, "modifier_name", text='')

        
        row = box.split(factor=split_factor)
        row.label(text='Mask')
        row.prop(self, "mask_name", text='')

        row = box.split(factor=split_factor)
        row.label(text='Shader Attribute')
        row.prop(self, "shader_att", text='')

        
        row = box.split(factor=split_factor)
        row.label(text='Cutter Object')
        row.prop(op_props, "cutter_obj", text='')

    def execute(self, context):
        wm = context.window_manager
        op_props = wm.smirk_op_props


        
        obj = bpy.data.objects.get(self.object_name) if self.object_name else context.active_object

        if obj.name.startswith('PROXY-'):
            self.report({'ERROR'}, f"Cannot add SMIRK Modifier to Proxy Object")
            return {"FINISHED"}


        smirk_mod = obj.modifiers.new(self.modifier_name, type='NODES')
        smirk_mod.node_group = get_asset_nodetree(SMIRK_MODIFIER)
        smirk_mod.show_group_selector = False
        
        interface = smirk_mod.node_group.interface

        # insert and change smirk_mod properties
        for item in interface.items_tree:
            if item.item_type == 'PANEL':
                continue
            # Mask
            if item.identifier == 'Socket_4':
                smirk_mod[f'{item.identifier}'] = self.mask_name
            # Object
            if item.identifier == OBJECT_SOCKET and item.bl_socket_idname == 'NodeSocketObject':
                smirk_mod[f'{item.identifier}'] = op_props.cutter_obj
            # Shader Attribute
            if item.identifier == 'Socket_3':
                smirk_mod[f'{item.identifier}'] = self.shader_att

        try:
            bpy.ops.smirk.sync_rim_mat(
            object_name = obj.name,
            modifier_name = smirk_mod.name
            )
        except Exception:
            pass

        bpy.ops.smirk.insert_nodetree(
        object_name = obj.name,
        shader_mask = smirk_mod[SHADER_MASK]
        )
            
            
        _switch_properties_to_modifier_tab()


        return {"FINISHED"}

class SMIRK_OT_modifier_remove(bpy.types.Operator):
    bl_idname = 'smirk.modifier_remove'
    bl_label = 'Remove Modifier from Object'
    bl_description = 'Remove modifier from a specified Object'

    object: bpy.props.StringProperty()
    modifier: bpy.props.StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        obj = bpy.data.objects.get(self.object)
        if obj == None:
            self.report({'WARNING'}, f"Object '{self.object}' not found")
            return {'CANCELLED'}
        mod = obj.modifiers.get(self.modifier)
        if mod is None:
            self.report({'WARNING'}, f"Modifier '{self.modifier}' not found")
            return {'CANCELLED'}
        obj.modifiers.remove(mod)
        return {'FINISHED'}
    
class SMIRK_OT_setup_remove(bpy.types.Operator):
    bl_idname = 'smirk.setup_remove'
    bl_label = 'Remove current SMIRK setup'
    bl_description = 'Remove modifier and all related data from this and related objects'

    object_name: bpy.props.StringProperty()
    modifier_name: bpy.props.StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):


        

        #obj
        obj = bpy.data.objects.get(self.object_name)
        if obj == None:
            self.report({'WARNING'}, f"Object '{self.object}' not found")
            return {'CANCELLED'}
        #gn_mod
        gn_mod = obj.modifiers.get(self.modifier_name)
        if gn_mod is None:
            self.report({'WARNING'}, f"Modifier '{self.modifier}' not found")
            return {'CANCELLED'}
        
        #cutter_obj
        cutter_obj = gn_mod[OBJECT_SOCKET] or None
        

        # Remove Cutter Mask
        def _remove_cutter_mask(mod, obj):
            if obj == None:
                return
            cutter_mask = mod[CUTTER_MASK] or None
            if cutter_mask == None:
                return
            if obj.type == 'MESH':
                vg = obj.vertex_groups.get(cutter_mask) or None
                if not vg:
                    return
                obj.vertex_groups.remove(vg)
            elif obj.type == 'GREASEPENCIL':
                layers = obj.data.layers
                layer = obj.data.layers.get(cutter_mask) or None
                if not layer:
                    return
                layers.remove(layer)

        _remove_cutter_mask(gn_mod, cutter_obj)


        # Remove Cutter Object Modifiers
        def _remove_cutter_mods(cutter_obj):
            mods = getattr(cutter_obj, "modifiers", None)
            if not mods:
                return
            for m in mods:
                if m.type == 'NODES':
                    if m.node_group.name != OVERRIDE_LAYER_MATERIAL:
                        return
                    cutter_obj.modifiers.remove(m)
        _remove_cutter_mods(cutter_obj)

        # Remove Transparency Mask Nodes on obj Material
        def _remove_shader_nodes(mat, shader_attr):
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            for node in nodes:
                if node.bl_idname != 'ShaderNodeGroup':
                    continue
                if node.node_tree.name != TRANSPARENCY_MASK:
                    continue
                

                mask = node.inputs.get("Mask")
                in_shader = node.inputs.get("Shader")
                out_shader = node.outputs.get("Shader")
                lnk = mask.links[0] if mask.is_linked else None
                attr_node = getattr(lnk, "from_node", None)
                if attr_node or getattr(attr_node, "bl_idname", "") == "ShaderNodeAttribute":
                    if attr_node.attribute_name == shader_attr:
                        is_linked = mask.is_linked
                        if is_linked == False:
                            nodes.remove(attr_node)
                            nodes.remove(node)
                            return
                        incoming_links = list(getattr(in_shader, "links", []))
                        outgoing_links = list(getattr(out_shader, "links", []))
                        from_socket = incoming_links[0].from_socket

                        nodes.remove(attr_node)
                        nodes.remove(node)
                        for link in outgoing_links:
                            try:
                                links.new(from_socket, link.to_socket)
                            except Exception:
                                pass


        mat = obj.active_material
        shader_attr = gn_mod.get(SHADER_MASK,"")
        if mat and shader_attr:
            _remove_shader_nodes(mat, shader_attr)

        # Remove Modifier
        obj.modifiers.remove(gn_mod)

        

        return {'FINISHED'}


class SMIRK_OT_switch_tab(bpy.types.Operator):
    bl_idname = "smirk.to_tab"
    bl_label = "Switch Properties to the Modifier tab"
    bl_description = "Switches the current Properties Panel to the Modifier Tab"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        _switch_properties_to_modifier_tab()

        return {"FINISHED"}

class SMIRK_OT_add_cutter_mask(bpy.types.Operator):
    bl_idname = "smirk.add_cutter_mask"
    bl_label = "Add Smirk Cutter Vertex Group or GP Layer"
    bl_description = "Automatically creates a Vertex Group or Grease Pencil Layer corresponding to the Mask attribute"
    bl_options = {'UNDO'}
    object_name: bpy.props.StringProperty(name='Target Object', default='')
    cutter_name: bpy.props.StringProperty(name='Target Object', default='')

    def execute(self, context):

        
        # Ensure Object Mode
        ensure_edit_mode(self, context)

        obj = bpy.data.objects.get(self.object_name) or context.active_object
        cutter = self.cutter_name or 'cutter'

        if obj is None or obj.type != 'MESH' and obj.type != 'GREASEPENCIL':
            return {"FINISHED"} 
        if obj.type == 'MESH' and obj.vertex_groups.get(cutter) is None:
            obj.vertex_groups.new(name=cutter)
        elif obj.type == 'MESH':
            self.report({'WARNING'}, f"'{cutter}' Vertex Group already exists on '{obj.name}'")

        if obj.type == 'GREASEPENCIL':
            layers = obj.data.layers
            layer = obj.data.layers.get(cutter)
            if layer is None:
                layer = obj.data.layers.new(name=cutter, set_active=True)
                layers.move_bottom(layer)

            else:
                self.report({'WARNING'}, f"'{cutter}' Layer already exists on '{obj.name}'")
            
            try:
                proxy_mat = get_asset_material(GP_CUTTER_MAT)
            except Exception as e:
                proxy_mat = None
                self.report({'WARNING'}, f"Could not append cutter material '{GP_CUTTER_MAT}': {e}")

            obj.data.materials.append(proxy_mat)


            ovrl_exists = False
            for m in obj.modifiers:
                if m.type == 'NODES' and m.node_group == get_asset_nodetree(OVERRIDE_LAYER_MATERIAL):
                    ovrl_exists = True
                    break
                
            if ovrl_exists == False:
                # Add Override Layer Material Node and populate it
                ovrl_mod = obj.modifiers.new(OVERRIDE_LAYER_MATERIAL, type='NODES')
                ovrl_mod.node_group = get_asset_nodetree(OVERRIDE_LAYER_MATERIAL)
                ovrl_mod.show_group_selector = False
                
                interface = ovrl_mod.node_group.interface

                for item in interface.items_tree:
                    if item.item_type == 'PANEL':
                        continue
                    # Layer
                    if item.identifier == 'Socket_2':
                        ovrl_mod[f'{item.identifier}'] = cutter
                    # Material
                    if item.identifier == 'Socket_3':
                        ovrl_mod[f'{item.identifier}'] = proxy_mat

        
        

        return {"FINISHED"}

class SMIRK_OT_sync_rim_mat(bpy.types.Operator):
    bl_idname = "smirk.sync_rim_mat"
    bl_label = "Sync Cutter Rim Material"
    bl_description = "Syncs the Cutter Rim Material with the active material of the Object"
    bl_options = {'UNDO'}
    object_name: bpy.props.StringProperty(name="Target Object", default="obj")
    modifier_name: bpy.props.StringProperty(name="Modifier Name", default="gn_mod")

    def execute(self, context):

        try:
            obj = bpy.data.objects.get(self.object_name)
            gn_mod = obj.modifiers.get(self.modifier_name)
            mat = obj.active_material
        except:
            return {"CANCELLED"}

        try:
            gn_mod[CUTTER_RIM_MAT] = mat
            self.report({'INFO'}, f"Cutter Rim now uses '{mat.name}' as Material.")
        except:
            self.report({'WARNING'}, f"Could not sync Material for Cutter Rim")
            return {'CANCELLED'}

        return {"FINISHED"}

class SMIRK_OT_toggle_gp_cutter_visibility(bpy.types.Operator):
    bl_idname = "smirk.toggle_gp_cutter_visibility"
    bl_label = "Toggle GP Cutter Invisibility"
    bl_description = "Toggles Invisibility of Cutter Grease Pencil Layer"
    bl_options = {'UNDO'}
    object_name: bpy.props.StringProperty(name="Target Object", default="obj")
    
    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        cutter_mod = obj.modifiers.get(OVERRIDE_LAYER_MATERIAL)

        if cutter_mod.show_viewport == False:
            cutter_mod.show_viewport = True
            cutter_mod.show_render = True
        else:
            cutter_mod.show_viewport = False
            cutter_mod.show_render = False
        return {'FINISHED'}

class SMIRK_OT_insert_nodetree(bpy.types.Operator):
    bl_idname = "smirk.insert_nodetree"
    bl_label = "Insert Node Group into active Material"
    bl_description = "Insert an appended node group between the material's incoming shader and the Material Output"
    object_name: bpy.props.StringProperty(name="Target Object", default="")
    node_tree_name: bpy.props.StringProperty(name="Node Tree", default=TRANSPARENCY_MASK)
    shader_mask: bpy.props.StringProperty(name="Shader Attribute", default="cutter_mask")

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name) if self.object_name else context.active_object
        if obj is None:
            self.report({'ERROR'}, "Target object not found")
            return {'CANCELLED'}
        
        mat = None
        if obj.active_material:
            mat = obj.active_material
        if mat is None:
            self.report({'ERROR'}, f"No active material on {obj.name}")
            return {'CANCELLED'}
        
        node_tree = mat.node_tree
        nodes = node_tree.nodes
        links = node_tree.links

        mat_out = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if mat_out is None:
            self.report({'ERROR'}, "Material Output node not found")
            return {'CANCELLED'}
        surface_input = mat_out.inputs.get('Surface')
        if surface_input is None:
            self.report({'ERROR'}, "Material Output has no Surface input")
            return {'CANCELLED'}
        
        # Append Node Group
        try:
            import_tree = get_asset_nodetree(self.node_tree_name)
        except:
            return
        if import_tree == None:
            self.report({'ERROR'}, "Node group not found")
            return {'CANCELLED'}

        prev_link = None
        for link in links:
            if link.to_node == mat_out and link.to_socket == surface_input:
                prev_link = link
                break
        

        # Return early if Setup already exists
        src_node = getattr(prev_link, "from_node", None)
        if getattr(src_node, "node_tree", None) is import_tree:
            mask = src_node.inputs.get("Mask")
            lnk = mask.links[0] if mask.is_linked else None
            src_att_node = getattr(lnk, "from_node", None)
            if src_att_node or getattr(src_att_node, "bl_idname", "") == "ShaderNodeAttribute":
                if src_att_node.attribute_name == self.shader_mask:
                    self.report({'WARNING'}, "Node Group with same Shader Attribute already attached")
                    return {'FINISHED'}
        
        node_group = nodes.new('ShaderNodeGroup')
        node_group.show_options = False
        node_group.name = import_tree.name
        node_group.node_tree = import_tree
        node_group.location = (mat_out.location.x - 240.0, mat_out.location.y)

        
        group_input = node_group.inputs[0] if node_group.inputs else None
        group_output = node_group.outputs[0] if node_group.outputs else None

        if prev_link and group_input is not None:
            from_socket = prev_link.from_socket
            try:
                links.remove(prev_link)
            except Exception:
                pass
            try:
                links.new(from_socket, group_input)
            except Exception:
                try:
                    links.new(prev_link.from_node.outputs[0], group_input)
                except Exception:
                    pass
        
        if group_output is not None:
            try:
                links.new(group_output, surface_input)
            except Exception as e:
                self.report({'WARNING'}, f"Could not link group output to Material Output: {e}")

        mask_in = node_group.inputs.get("Mask")
        if mask_in:
            attr_node = nodes.new("ShaderNodeAttribute")
            attr_node.label = "SMIRK Mask Attribute"
            attr_node.attribute_name = self.shader_mask
            try:
                attr_node.location = (node_group.location.x - 240.0, node_group.location.y - 120.0)
            except Exception:
                pass
            try:
                for l in list(mask_in.links):
                    links.remove(l)
            except Exception:
                pass
            fac_out = attr_node.outputs.get("Fac")
            if fac_out:
                links.new(fac_out, mask_in)


        return {'FINISHED'}


def get_smirk_object(context, wm=None):
    """ Returns the object used for the SMIRK menu. Can be the active object, pinned object or an adjacent object that links back to an object with the Smirk Modifier """
    obj = None
    if wm == None:
        wm = context.window_manager
    pin_props = getattr(wm, 'smirk_pin', None)
    if pin_props.pinned_obj and pin_props.is_pinned:
        obj = pin_props.pinned_obj
    else:
        obj = context.active_object
    if obj == None:
        return
    if obj and obj.type == 'ARMATURE' or obj.type == 'MESH' or obj.type == 'GREASEPENCIL':
            for meshobj in bpy.data.objects:
                if meshobj.type != 'MESH':
                    continue
                if not any(mod.type == 'NODES' and mod.node_group and mod.node_group.name == SMIRK_MODIFIER for mod in meshobj.modifiers):
                    continue
                if any(mod.type == 'ARMATURE' and mod.object == obj for mod in meshobj.modifiers):
                    obj = meshobj
                if any(mod.type == 'NODES' and mod.node_group and mod.node_group.name == SMIRK_MODIFIER and mod[OBJECT_SOCKET] == obj for mod in meshobj.modifiers):
                    obj = meshobj
    return obj 

@persistent
def smirk_prop_handler(scene, depsgraph):
    context = bpy.context
    wm = context.window_manager
    if context.active_object == None:
        return
    obj = get_smirk_object(context)
    if not obj:
        return
    
    try:
        gn_name = wm.smirk_mod_list[wm.smirk_mod_active].name
        gn_mod = obj.modifiers.get(gn_name)
    except:
        return
    
    try:
        current_mask = gn_mod.get(CUTTER_MASK)
        current_cutter = gn_mod.get(OBJECT_SOCKET)
        current_cutter_name = getattr(current_cutter, "name", "")

        last_mask = gn_mod.get("_smirk_last_mask")
        last_cutter_name = gn_mod.get("_smirk_last_cutter")
    except:
        return

    changed = (current_mask != last_mask) or (current_cutter_name != last_cutter_name)
    if not changed:
        return
    try:
        gn_mod["_smirk_last_mask"] = current_mask
        gn_mod["_smirk_last_cutter"] = current_cutter_name
    except Exception:
        pass

    if (not current_cutter) or (not current_mask):
        return
    
    if current_mask != last_mask:
        try:
            if current_cutter.type == 'MESH':
                vgs = current_cutter.vertex_groups
                old_vg = vgs.get(last_mask)
                old_vg.name = current_mask
            elif current_cutter.type == 'GREASEPENCIL':
                layer = current_cutter.data.layers.get(last_mask)
                layer.name = current_mask

                ovrl_mod = current_cutter.modifiers.get(OVERRIDE_LAYER_MATERIAL)
                interface = ovrl_mod.node_group.interface
                
                for item in interface.items_tree:
                    # Layer
                    if item.identifier == 'Socket_2':
                        ovrl_mod[f'{item.identifier}'] = current_mask

        except Exception:
            pass

class SMIRK_op_props(bpy.types.PropertyGroup):
    cutter_obj: bpy.props.PointerProperty(type=bpy.types.Object)

    
_classes = (
    SMIRK_OT_setup_proxy_mesh,
    SMIRK_OT_modifier_add,
    SMIRK_OT_switch_tab,
    SMIRK_OT_modifier_remove,
    SMIRK_op_props,
    SMIRK_OT_add_cutter_mask,
    SMIRK_OT_insert_nodetree,
    SMIRK_OT_sync_rim_mat,
    SMIRK_OT_edit_cutter_obj,
    SMIRK_OT_goto_surface_obj,
    SMIRK_OT_toggle_gp_cutter_visibility,
    SMIRK_OT_setup_remove,
    SMIRK_OT_fix_dependency_loop,
)


_register, _unregister = bpy.utils.register_classes_factory(_classes)

def register() -> None:
    _register()

    bpy.types.WindowManager.smirk_op_props = bpy.props.PointerProperty(type=SMIRK_op_props)
    if smirk_prop_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(smirk_prop_handler)

    
    
def unregister() -> None:
    _unregister()

    del bpy.types.WindowManager.smirk_op_props
    bpy.app.handlers.depsgraph_update_post.remove(smirk_prop_handler)
    
    