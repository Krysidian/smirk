import bpy
from bpy.props import *
from collections import defaultdict
from .operators import *
from .custom_icons import *

from bpy.types import Context

def draw_menu(self, context) -> None:
    layout = self.layout
    layout.operator("smirk.setup_proxy_mesh", icon="DUPLICATE")



class SMIRK_sync_props(bpy.types.PropertyGroup):

    # --- Cutter Object ---

    def _get_cutter_mask(self) -> None:
        obj, gn_mod = get_smirk_obj_and_modifier(bpy.context)

        return getattr(gn_mod.properties.inputs, CUTTER_MASK).value
    
    def _set_cutter_mask(self, value: str) -> None:
        obj, gn_mod = get_smirk_obj_and_modifier(bpy.context)
        old = getattr(gn_mod.properties.inputs, CUTTER_MASK).value
        new = value
        getattr(gn_mod.properties.inputs, CUTTER_MASK).value = new
        cutter_obj = getattr(gn_mod.properties.inputs, OBJECT_SOCKET).value

        if cutter_obj is None or cutter_obj.type != 'MESH' and cutter_obj.type != 'GREASEPENCIL':
            return 
        if cutter_obj.type == 'MESH':
            vgroup = cutter_obj.vertex_groups.get(old)
            if vgroup:
                vgroup.name = new
        elif cutter_obj.type == 'GREASEPENCIL':
            layers = cutter_obj.data.layers
            layer = cutter_obj.data.layers.get(old)
            if layer:
                layer.name = new
        
        for mod in cutter_obj.modifiers:
            # Geometry Node Modifiers
            if mod.type == 'NODES':
                interface = interface = mod.node_group.interface
                for item in interface.items_tree:
                    if item.item_type == 'PANEL':
                        continue
                    if item.bl_socket_idname not in {'NodeSocketString', 'NodeSocketBool'}:
                        continue
                    if getattr(mod.properties.inputs, item.identifier).value == old:
                        getattr(mod.properties.inputs, item.identifier).value = new
                
            # Regular Modifiers
            else:
                for prop in mod.bl_rna.properties:
                    if prop.is_readonly:
                        continue
                    if prop.type != 'STRING':
                        continue
                    try:
                        prop_name = prop.identifier
                        prop = getattr(mod, prop_name)
                        if prop == old:
                            setattr(mod, prop_name, new)
                    except:
                        continue
        obj.update_tag()
        cutter_obj.update_tag()
        return
    
    # PROP
    cutter_mask: bpy.props.StringProperty(
        name="Cutter Mask",
        description="Name of the Vertex Group or GP Layer used to determine the Body opening",
        get=_get_cutter_mask,
        set=_set_cutter_mask,
    )

    # --- Shader Attribute ---

    def _get_shader_attr(self) -> None:
        obj, gn_mod = get_smirk_obj_and_modifier(bpy.context)

        return getattr(gn_mod.properties.inputs, SHADER_MASK).value
    
    def _set_shader_attr(self, value: str) -> None:
        obj, gn_mod = get_smirk_obj_and_modifier(bpy.context)
        old = getattr(gn_mod.properties.inputs, SHADER_MASK).value
        new = value
        getattr(gn_mod.properties.inputs, SHADER_MASK).value = new
        cutter_obj = getattr(gn_mod.properties.inputs, OBJECT_SOCKET).value

        mat = obj.active_material

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        for node in nodes:
            if node.bl_idname != 'ShaderNodeAttribute':
                continue
            if node.attribute_name == old:
                node.attribute_name = new

        
        obj.update_tag()
        cutter_obj.update_tag()
        return
    
    # PROP
    shader_attr: bpy.props.StringProperty(
        name="Shader Attribute",
        description="Attribute for the Mask used in the Shader to control Transparency",
        get=_get_shader_attr,
        set=_set_shader_attr,
    )






class SMIRK_panels(bpy.types.PropertyGroup):
    persistent_uid: bpy.props.IntProperty()
    expanded: bpy.props.BoolProperty(default=False)

class SMIRK_pin(bpy.types.PropertyGroup):
    pinned_obj: bpy.props.PointerProperty(type=bpy.types.Object)
    is_pinned: bpy.props.BoolProperty(default=False)

class SMIRK_MT_modifiers(bpy.types.Menu):
    bl_label = "Modifier Menu"
    bl_idname = "SMIRK_MT_modifiers"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        obj = get_smirk_object(context)

        gn_name = wm.smirk_mod_list[wm.smirk_mod_active].name
        gn_mod = obj.modifiers.get(gn_name)

        
        op = layout.operator("smirk.insert_nodetree", icon='NODE_INSERT_OFF')
        shader_mask = getattr(gn_mod.properties.inputs, SHADER_MASK).value
        op.object_name = obj.name
        op.shader_mask = shader_mask
        op = layout.operator("smirk.sync_rim_mat", icon='MATERIAL')
        op.object_name = obj.name
        op.modifier_name = gn_mod.name



class SMIRK_UL_modifiers(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        # data is the Scene, item is a string = modifier name
        depsgraph = context.view_layer.depsgraph
        mod_name = item.name
        obj = get_smirk_object(context)
        gn_mod = obj.modifiers[mod_name]
        obj_eval = obj.evaluated_get(depsgraph)
        execution_time = obj_eval.modifiers[mod_name].execution_time * 1000


        row = layout.row(align=True)
        row.use_property_decorate = False
        row.prop(gn_mod, 'name', text='', emboss=False, icon='GEOMETRY_NODES')
        row.label(text=f"{execution_time:.2f} ms")
        row.prop(gn_mod, 'show_viewport', icon_only=True, emboss=False)
        row.prop(gn_mod, 'show_render', icon_only=True, emboss=False)


        op = row.operator('smirk.modifier_remove', text ='', icon='X', emboss=False)
        op.object = obj.name
        op.modifier = item.name


        mod = obj.modifiers.get(item.name)
        if mod is None:
            # Try to find modifier with previous name
            for m in obj.modifiers:
                if m.name != item.name and item.name in m.name:
                    # User changed the name — rename real modifier
                    m.name = item.name
                    break

class SMIRK_OT_pin_object(bpy.types.Operator):
    bl_idname = 'smirk.pin_object'
    bl_label = "Toggle SMIRK pin"
    bl_description = "Pin active Object or unpin currently pinned object"

    def execute(self, context):
        wm = context.window_manager
        pin_props = getattr(wm, 'smirk_pin', None)
        if pin_props.pinned_obj is None:
            pin_props.pinned_obj = context.active_object
            pin_props.is_pinned = True
            self.report({'INFO'}, f"Pinned '{pin_props.pinned_obj.name}'")
        else:
            self.report({'INFO'}, f"Unpinned '{pin_props.pinned_obj.name}'")
            pin_props.pinned_obj = None
            pin_props.is_pinned = False

        return {"FINISHED"}





class SMIRK_PT_menu(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Freeform Facial Features"
    bl_idname = "SMIRK_PT_menu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SMIRK'
    bl_icon = 'NONE'


    def draw(self, context):
        scene = context.scene
        wm = context.window_manager
        obj = get_smirk_object(context)
        pin_props = getattr(wm, 'smirk_pin', None)
        layout = self.layout
        layout.use_property_split = True

        panel_icons = {
            "Cutter": 'scissors',
            "Extractor": "EYEDROPPER",
            "Shader Mask": 'MOD_MASK',
            "Adaptive Subdivision": 'MOD_MULTIRES',
            "Cutout Mesh": 'SELECT_SUBTRACT',
            "Cutter Rim": 'circle',
            "Inner Area": 'circle-dot-dashed',
            "Viewport": 'RESTRICT_VIEW_OFF',
            "Isolate View": 'SOLO_ON',
            "Manifold Boolean": 'MOD_BOOLEAN'
        }
        socket_icons = {
            "Isolate View": 'SOLO_ON'
        }

        
        #"Inner Area": 'OUTLINER_DATA_META',
        #"Cutter Rim": 'ANTIALIASED',


        # Object Header
        row = layout.row()
        if obj:
            row.label(text=f"Surface Object: {obj.name}" if obj else 'No Object selected', icon='OUTLINER_OB_SURFACE')
            pin_icon = 'PINNED' if pin_props.is_pinned == True else 'UNPINNED'
            row.operator('smirk.pin_object', text='', icon=pin_icon, emboss=False)
            layout.separator(type='LINE',factor=MAIN_SEP_FACTOR)

        if not obj:
            row.alert = True
            row.label(text='No Object selected', icon='OBJECT_DATA')
            return
        if obj.type != 'MESH':
            row = layout.row()
            row.alert = True
            row.label(text='Selected Object is not a Mesh')
            return


        panel_header, panel_body = layout.panel(idname='smirk_setup', default_closed=False)
        panel_header.label(text = 'Setup', icon='FILE_NEW')
        if panel_body and obj:
            row = panel_body.row().split(factor=0.4)
            row.scale_y = 2
            if f'PROXY-{obj.name}' in bpy.data.objects:
                op = row.operator("smirk.setup_proxy_mesh", icon='UV_SYNC_SELECT', text='Update Proxy')
            else:
                op = row.operator("smirk.setup_proxy_mesh", icon='DUPLICATE', text='Setup Proxy')
            op.object_name = obj.name
            

            op = row.operator("smirk.modifier_add", icon='MODIFIER')
            op.object_name = obj.name
            
        layout.separator(type='SPACE',factor=MAIN_SEP_FACTOR)
        panel_header, panel_body = layout.panel(idname='smirk_modifiers', default_closed=False)
        panel_header.label(text = 'Modifiers', icon='MODIFIER')

        wm.smirk_mod_list.clear()
        try:
            for m in obj.modifiers:
                if m.type == 'NODES' and m.node_group and m.node_group.name == SMIRK_MODIFIER:
                    item = wm.smirk_mod_list.add()
                    item.name = m.name
        except Exception:
            return
        
        # Making sure the List index doesn't go out of range
        if len(wm.smirk_mod_list) == 0:
            wm.smirk_mod_active = 0
        else:
            wm.smirk_mod_active = max(0, min(wm.smirk_mod_active, len(wm.smirk_mod_list) - 1))
        

        # Building the List
        if panel_body:

            if len(wm.smirk_mod_list) == 0:
                row = panel_body.row()
                row.alert = True
                row.label(text='No SMIRK modifier on Object')
            
            try:
                gn_name = wm.smirk_mod_list[wm.smirk_mod_active].name
                gn_mod = obj.modifiers.get(gn_name)
            except:
                return

            


            # Show UIList
            row = panel_body.box().row()
            row.template_list(listtype_name="SMIRK_UL_modifiers", list_id="", dataptr=wm, propname="smirk_mod_list", active_dataptr=wm, active_propname="smirk_mod_active", rows=6)
            col = row.column(align=True)
            col.scale_x = 1.15
            col.scale_y = 1.3
            col.operator("smirk.to_tab", icon='DECORATE_OVERRIDE', text='')

            
            op = col.menu("SMIRK_MT_modifiers", icon='COLLAPSEMENU', text="")
            col.separator(type = 'LINE')

            
            op = col.operator('smirk.modifier_add', text ='', icon='ADD', emboss=True)
            
            op = col.operator('smirk.modifier_remove', text ='', icon='REMOVE', emboss=True)
            op.object = obj.name
            op.modifier = wm.smirk_mod_list[wm.smirk_mod_active].name

            op = col.operator('smirk.setup_remove', text='', icon='TRASH', emboss=True)
            op.object_name = obj.name
            op.modifier_name = wm.smirk_mod_list[wm.smirk_mod_active].name

            panel_body.separator(type='LINE')
            panel_body = panel_body.box()
            row = panel_body.row()
            row.alignment = 'CENTER'
            row.label(text=gn_mod.name)

            # Smirk Property Setter

            prop_panel_header, prop_panel_body = panel_body.panel(idname='smirk_props', default_closed=False)
            prop_panel_header.label(text = 'Properties', icon='PROPERTIES')
            if prop_panel_body:
                row = prop_panel_body.row()
                row.prop(getattr(gn_mod.properties.inputs, OBJECT_SOCKET), 'value', text='Cutter Object', emboss=True, icon='GEOMETRY_NODES', placeholder="Cutter Object")
                row = prop_panel_body.row()
                row.prop(context.scene.smirk_sync_props, 'cutter_mask', text='Cutter Mask', emboss=True, icon='GEOMETRY_NODES', placeholder="Cutter Mask")
                row = prop_panel_body.row()
                row.prop(context.scene.smirk_sync_props, 'shader_attr', text='Shader Attribute', emboss=True, icon='GEOMETRY_NODES', placeholder="Shader Attribute")
            

            # Draw Modifier Panel and get its sockets and panels
            draw_modifier_panel(obj, gn_mod, wm, panel_body, panel_icons, socket_icons)

        try:
            gn_name = wm.smirk_mod_list[wm.smirk_mod_active].name    
            gn_mod = obj.modifiers.get(gn_name)
            interface = gn_mod.node_group.interface
        except:
            return
        


        # Cutter Object Settings

        if getattr(gn_mod.properties.inputs, OBJECT_SOCKET).value == None:
            row = layout.row()
            row.alert = True
            row.label(text='No Cutter Object selected yet')
            
        try:
            cutter_obj = getattr(gn_mod.properties.inputs, OBJECT_SOCKET).value
        except:
            cutter_obj = None


        

        if cutter_obj:
            # Dependency Loop Check
            dep_cycle = False
            for mod in cutter_obj.modifiers:
                
                if mod.type == 'NODES':
                    try:
                        interface = mod.node_group.interface
                    except:
                        interface = None
                    if not interface:
                        continue
                    for item in interface.items_tree:
                        if item.item_type != 'SOCKET':
                            continue
                        if item.bl_socket_idname != 'NodeSocketObject':
                            continue
                        key = item.identifier
                        if getattr(mod.properties.inputs, key).value == obj:
                            dep_cycle = True
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
                                dep_cycle = True
                        except:
                            continue

            # Add Mask Prop
            layout.separator(type='SPACE',factor=MAIN_SEP_FACTOR)
            if cutter_obj.type == 'MESH':
                op_icon = 'GROUP_VERTEX'
                op_text= 'Add SMIRK Cutter Vertex Group'
                obj_icon = 'OBJECT_DATA'
            elif cutter_obj.type == 'GREASEPENCIL':
                op_icon = 'GREASEPENCIL_LAYER_GROUP'
                op_text= 'Add SMIRK Cutter GP Layer'
                obj_icon = 'OUTLINER_OB_GREASEPENCIL'
            else:
                op_icon = 'ERROR'
                obj_icon = 'ERROR'
            if dep_cycle == True:
                obj_icon = 'ERROR'
            header, body = layout.panel(idname=cutter_obj.name, default_closed=True)
            header.alert = True if dep_cycle == True else False
            header.label(text="Cutter Object", icon=obj_icon)
            
            if body:
                row = body.row()
                row.alignment = 'CENTER'
                row.label(text=f'{cutter_obj.name}')
                body.separator(type='LINE')
                
                
                
                # Dependendcy Loop Warning + Fix
                if dep_cycle == True:
                    box = body.box()
                    row = box.row()
                    row.alert = True
                    row.label(text=f"'{obj.name}' referenced on '{cutter_obj.name}'. Causes Dependency Cycles")

                    row = box.row()
                    row.scale_y = 2
                    op = row.operator("smirk.fix_dependency_loop", icon_value=get_icon('replace-all'), text='Fix Dependency Cycles')
                    op.cutter_name = cutter_obj.name
                    op.proxy_name = f'PROXY-{obj.name}'
                    op.object_name = obj.name

                    body.separator(factor=1.0)

                cutter_name = getattr(gn_mod.properties.inputs, CUTTER_MASK).value

                # Show add Cutter Mask button if it hasn't been added yet
                cutter_mask_exists = False
                if cutter_obj.type == 'GREASEPENCIL':
                    cutter_mask_exists = bool(cutter_obj.data.layers.get(cutter_name))
                elif cutter_obj.type == 'MESH':
                    cutter_mask_exists = bool(cutter_obj.vertex_groups.get(cutter_name))

                if not cutter_mask_exists:
                    op = body.operator("smirk.add_cutter_mask", icon=op_icon, text=op_text)
                    op.object_name = cutter_obj.name
                    op.cutter_name = cutter_name

                # Show Shrinkwrap Add button if it doesn't exist yet
                shrink_mod = cutter_obj.modifiers.get(SHRINKWRAP_NAME)
                if not shrink_mod:
                    row = body.row()
                    row.enabled = not bool(cutter_obj.modifiers.get(SHRINKWRAP_NAME))
                    op = row.operator("smirk.add_shrinkwrap", icon='MOD_SHRINKWRAP')
                    op.proxy_name = f'PROXY-{obj.name}'
                    op.cutter_name = cutter_obj.name
                elif shrink_mod:
                    old_body = body # cache body
                    header, body = body.panel(idname='smirk_shrinkwrap', default_closed=True)
                    header.label(text='Shrinkwrap', icon='MOD_SHRINKWRAP')
                    op = header.operator('smirk.modifier_remove', text ='', icon='X', emboss=False)
                    op.object = cutter_obj.name
                    op.modifier = SHRINKWRAP_NAME
                    if body:
                        row = body.row()
                        op = row.prop(shrink_mod, "wrap_method")
                        row = body.row()
                        op = row.prop(shrink_mod, "wrap_mode")
                        row = body.row()
                        op = row.prop(shrink_mod, "offset")
                    body = old_body # reinstate previous body

                # Show Make Cutter Invisible option if cutter object is Grease Pencil
                if cutter_obj.type == 'GREASEPENCIL' and cutter_obj.modifiers.get(OVERRIDE_LAYER_MATERIAL):
                    cutter_mod = cutter_obj.modifiers.get(OVERRIDE_LAYER_MATERIAL)
                    row = body.row(align=True)
                    row.use_property_decorate = False
                    op = row.operator('smirk.toggle_gp_cutter_visibility', text='Make Cutter Invisible', depress = True if cutter_mod.show_viewport == True else False, icon='HIDE_ON' if cutter_mod.show_viewport == True else 'HIDE_OFF')
                    op.object_name = cutter_obj.name

                body.separator(type='LINE')
                row = body.row()
                op = row.operator("smirk.edit_cutter_obj", icon=obj_icon)
                op.object_name = obj.name
                op.cutter_name = cutter_obj.name
                op.proxy_name = f'PROXY-{obj.name}'


                op = row.operator("smirk.goto_surface_object", icon='OUTLINER_OB_SURFACE')
                op.object_name = obj.name
                op.cutter_name = cutter_obj.name
                op.proxy_name = f'PROXY-{obj.name}'
        
        # Info Panel
        warnings = list(getattr(gn_mod, "node_warnings"))

        info_text = 'Info'

        if warnings:
            info_text = f'Info ({len(warnings)})'

            error_count = sum(w.type == 'ERROR' for w in warnings)
            warning_count = sum(w.type == 'WARNING' for w in warnings)
            info_count = sum(w.type == 'INFO' for w in warnings)
                
        layout.separator(type='LINE',factor=MAIN_SEP_FACTOR)
        header, body = layout.panel(idname='smirk_info', default_closed=True)
        header.label(text=info_text, icon='STATUS_WARNING_FILLED' if warnings else 'INFO')
        
        header.alert = bool(warnings)
        
        if body:
            row = body.column_flow(columns=2)
            row.column().label(text= 'Surface Object:')
            row.column().label(text= obj.name)

            row = body.column_flow(columns=2)
            row.column().label(text= 'Cutter Object:')
            
            try:
                cutter_name = getattr(gn_mod.properties.inputs, OBJECT_SOCKET).value.name
                row.column().label(text= cutter_name)
            except:
                row.alert = True
                row.column().label(text= "No Object")

            row = body.column_flow(columns=2)
            row.column().label(text= 'Mask:')

            if getattr(gn_mod.properties.inputs, CUTTER_MASK).value != "":
                att_name = getattr(gn_mod.properties.inputs, CUTTER_MASK).value
                row.column().label(text= att_name)
            else:
                row.alert = True
                row.column().label(text= "No Attribute")

            row = body.column_flow(columns=2)
            row.column().label(text= 'Shader Attribute:')

            if getattr(gn_mod.properties.inputs, SHADER_MASK).value != "":
                att_name = getattr(gn_mod.properties.inputs, SHADER_MASK).value
                row.column().label(text= att_name)
            else:
                row.alert = True
                row.column().label(text= "No Attribute")

            # Show Warnings
            if not warnings:
                return

            label_parts = []

            if error_count:
                label_parts.append(f"Errors ({error_count})")
            if warning_count:
                label_parts.append(f"Warnings ({warning_count})")
            if info_count:
                label_parts.append(f"Info ({info_count})")

            label_text = ", ".join(label_parts)
            
            body.separator(type='LINE',factor=MAIN_SEP_FACTOR)
            row = body.row()
            row.label(text=label_text)
            for w in warnings:
                message = w.message
                icon = 'INFO'
                match w.type:
                    case 'ERROR':
                        icon = 'CANCEL'
                    case 'WARNING':
                        icon = 'STATUS_WARNING_FILLED'
                    case 'INFO':
                        icon = 'INFO'
                row = body.row()
                if w.type == 'ERROR':
                    row.alert = True
                row.label(text=message, icon=icon)

            
        
        
        

                    


                    
                    






def draw_modifier_panel(obj, gn_mod, wm, layout, panel_icons, socket_icons):
    
    complex_only_panels = {'Cutter Rim', 'Inner Area'}


    current_mode = None
    try:
        current_mode = getattr(gn_mod.properties.inputs, MODIFIER_MODE).value
    except Exception:
        current_mode = None

    if gn_mod.type == 'NODES':
        
        def _builtin_icon_names_for_label() -> set[str]:
            """Return the enum identifiers accepted by row.label(icon=...)."""
            try:
                fn = bpy.types.UILayout.bl_rna.functions["label"]
                enum_items = fn.parameters["icon"].enum_items
                return {e.identifier for e in enum_items}
            except Exception:
                return set()

        _BUILTIN_LABEL_ICONS = _builtin_icon_names_for_label()
        

        layout_header, body = layout.panel(idname=gn_mod.name, default_closed=True)
        layout_header.label(text = f'Modifier', icon='GEOMETRY_NODES')


        # Get Node Interface
        try:
            interface = gn_mod.node_group.interface
        except:
            return

        

        if body: 

            state_map = {panel_state.persistent_uid: panel_state for panel_state in wm.smirk_panels}
            panel_box_map = {}
            
            complex_separator_drawn = False
            visibility_row = None
            for item in interface.items_tree:

                

                if item.item_type == 'PANEL' and item.persistent_uid not in state_map:
                        new = wm.smirk_panels.add()
                        new.persistent_uid = item.persistent_uid
                        state_map[item.persistent_uid] = new

                panel_state = state_map[item.persistent_uid] if item.item_type == 'PANEL' else 0

                parent_panel_open = state_map[item.parent.persistent_uid].expanded if item.parent.persistent_uid !=0 else True


                # Complex Only Panels
                if item.item_type == 'PANEL' and item.name in complex_only_panels:
                    if current_mode == 'Simple':
                        panel_state.expanded = False
                        continue
                    elif complex_separator_drawn == False:
                        complex_separator_drawn = True
                        body.separator(type='LINE')
                        row = body.row(align=True)
                        row.alignment = 'CENTER'
                        row.label(text='', icon='SHADERFX')
                        row.label(text='Complex')
               
                    
                # Modifier Panels
                if item.item_type == 'PANEL' and parent_panel_open:

                    visibility_row = None

                    # Skip invisible panels
                    panel_sockets = [
                        socket for socket in interface.items_tree
                            if socket.item_type == 'SOCKET' 
                            and socket.in_out == 'INPUT'
                            and socket.parent == item
                    ]
                    has_visible_sockets = any(
                        gn_mod.is_input_visible(socket.identifier) for socket in panel_sockets
                    )
                    if not has_visible_sockets:
                        continue
                    
                    parent = item.parent.name
                    # Nested if parent exists, else new box
                    if parent and parent in panel_box_map:
                        current_box = panel_box_map[parent].box()
                    else:
                        current_box = body.box()
                    
                    row = current_box.row(align=False)
                    row.use_property_decorate = False
                    row.prop(panel_state, "expanded", text='', emboss=False, icon='DOWNARROW_HLT' if panel_state.expanded else 'RIGHTARROW')


                    # Optional Icons
                    if item.name in panel_icons:
                        if panel_icons[item.name] in _BUILTIN_LABEL_ICONS:
                            row.label(text= '', icon=panel_icons[item.name])
                        else:
                            row.label(text= '', icon_value=get_icon(panel_icons[item.name]))


                    # Panel Toggles
                    for socket in interface.items_tree:
                        if socket.item_type != 'SOCKET':
                            continue
                        if socket.is_panel_toggle == False:
                            continue
                        if socket.parent == item:
                            socket_prop = getattr(gn_mod.properties.inputs, socket.identifier, None)
                            row.prop(socket_prop, "value", emboss=False, icon_only=True, icon='CHECKBOX_HLT' if getattr(gn_mod.properties.inputs, socket.identifier).value == True else 'CHECKBOX_DEHLT')
                    row.label(text=item.name)
                    panel_box_map[item.name] = current_box

                # Close all subpanels when parent panel is closed  
                elif item.item_type == 'PANEL' and not parent_panel_open:
                    panel_state.expanded = False

                # Modifier Sockets
                elif item.item_type == 'SOCKET' and item.in_out == 'INPUT' and parent_panel_open:
                    socket_id = item.identifier

                    #remove panel prefix the way Blender does it for Socket names natively
                    socket_name= item.name.removeprefix(item.parent.name).strip()

                    # Make sure the socket_id can be drawn
                    socket_prop = getattr(gn_mod.properties.inputs, socket_id, None)
                    if socket_prop is not None:
                        # Use the panel box if exists, else top-level
                        parent_box = panel_box_map.get(item.parent.name, body)

                        # Viewport/Render column
                        if socket_name == 'Viewport':

                            visiblity_icon = 'RESTRICT_VIEW_OFF' if getattr(gn_mod.properties.inputs, socket_id).value else 'RESTRICT_VIEW_ON'

                            visibility_row = parent_box.row(align=True)
                            visibility_row.alignment = 'RIGHT'
                            target = visibility_row
                        elif socket_name == 'Render':

                            visiblity_icon = 'RESTRICT_RENDER_OFF' if getattr(gn_mod.properties.inputs, socket_id).value else 'RESTRICT_RENDER_ON'

                            # Reuse row created for Viewport
                            target = visibility_row
                        else:
                            target = parent_box.row()


    
                        if item.is_panel_toggle:
                            
                            continue

                        # Expanded Menu Sockets
                        if item.menu_expanded:
                            expand = True
                        else:
                            expand = False


                        try:
                            socket_prop = getattr(gn_mod.properties.inputs, item.identifier, None)

                            # skip Socket_0
                            if item.identifier == 'Socket_0':
                                continue

                            # Hide invisible sockets
                            if gn_mod.is_input_visible(item.identifier) == False:
                                continue

                            
                            # Create Socket Prop
                            if socket_name in {'Viewport', 'Render'}:
                                target.use_property_decorate = False
                                prop = target.prop(socket_prop, 'value', text='', icon=visiblity_icon, icon_only=True, toggle=True)
                            elif socket_name == 'Exclusion Mask':
                                target.use_property_decorate = True
                                prop = target.prop(socket_prop, 'attribute_name', text=socket_name, expand=expand)
                            else:
                                target.use_property_decorate = True
                                prop = target.prop(socket_prop, 'value', text=socket_name, expand=expand)

                            # grey out unused sockets
                            if gn_mod.is_input_used(item.identifier):
                                target.enabled = True
                            else:
                                target.enabled = False
                            # Optional Icons
                            

                            if socket_name in socket_icons:
                                if socket_icons[item.name] in _BUILTIN_LABEL_ICONS:
                                    target.label(text='', icon=socket_icons[socket_name])
                                else:
                                    target.label(text='', icon_value=get_icon(socket_icons[socket_name]))
                        except: 
                            continue
                    


_classes = (
    SMIRK_PT_menu,
    SMIRK_panels,
    SMIRK_UL_modifiers,
    SMIRK_pin,
    SMIRK_OT_pin_object,
    SMIRK_MT_modifiers,
    SMIRK_sync_props,
)

_register, _unregister = bpy.utils.register_classes_factory(_classes)

def register() -> None:
    _register()
    bpy.types.VIEW3D_MT_object.append(draw_menu)

    bpy.types.WindowManager.smirk_panels = bpy.props.CollectionProperty(type=SMIRK_panels)
    bpy.types.WindowManager.smirk_mod_list = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.WindowManager.smirk_mod_active = bpy.props.IntProperty()
    bpy.types.WindowManager.smirk_pin = bpy.props.PointerProperty(type=SMIRK_pin)

    bpy.types.Scene.smirk_sync_props = bpy.props.PointerProperty(type=SMIRK_sync_props,options={'SKIP_SAVE'})
    
    
def unregister() -> None:
    _unregister()
    bpy.types.VIEW3D_MT_object.remove(draw_menu)

    del bpy.types.WindowManager.smirk_panels
    del bpy.types.WindowManager.smirk_mod_list
    del bpy.types.WindowManager.smirk_mod_active
    del bpy.types.WindowManager.smirk_pin

    del bpy.types.Scene.smirk_sync_props
    