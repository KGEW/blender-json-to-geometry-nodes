"""Blender 中文界面：验证、导入与导出 Geometry Nodes JSON。"""
try:
    import bpy
    from bpy.props import BoolProperty, StringProperty
    from bpy.types import Operator, Panel
except ImportError:
    bpy = None

from .core.validation import DocumentError, parse_and_validate
from .blender.importer import import_document
from .blender.exporter import export_active_node_group, ExportError
from .localization import (
    UI_TEXT,
    format_document_error,
    format_export_success,
    format_import_success,
    format_runtime_error,
)


if bpy:
    class JSONGN_OT_import(Operator):
        bl_idname = "json_gn.import_document"
        bl_label = UI_TEXT["import_label"]
        bl_description = UI_TEXT["import_description"]
        bl_options = {'REGISTER', 'UNDO'}

        filepath: StringProperty(name=UI_TEXT["filepath_name"], subtype="FILE_PATH")
        filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

        def execute(self, context):
            try:
                with open(self.filepath, "r", encoding="utf-8") as handle:
                    document = parse_and_validate(handle.read())
                attach = context.object if context.scene.json_gn_attach else None
                if context.scene.json_gn_attach and attach is None:
                    self.report({'ERROR'}, "导入失败：已启用附加，但当前没有活动对象")
                    return {'CANCELLED'}
                if context.scene.json_gn_attach and not hasattr(attach, "modifiers"):
                    self.report({'ERROR'}, "导入失败：活动对象不支持修改器")
                    return {'CANCELLED'}
                result = import_document(
                    document,
                    dry_run=context.scene.json_gn_dry_run,
                    attach_object=attach,
                )
                self.report(
                    {'INFO'},
                    format_import_success(result["nodes"], result["links"], dry_run=result["dry_run"]),
                )
                return {'FINISHED'}
            except DocumentError as exc:
                self.report({'ERROR'}, format_document_error(exc))
                return {'CANCELLED'}
            except OSError as exc:
                self.report({'ERROR'}, format_runtime_error(exc, "读取 JSON 文件"))
                return {'CANCELLED'}
            except Exception as exc:
                self.report({'ERROR'}, format_runtime_error(exc, "导入"))
                return {'CANCELLED'}

        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}


    class JSONGN_OT_validate(Operator):
        bl_idname = "json_gn.validate_document"
        bl_label = UI_TEXT["validate_label"]
        bl_description = UI_TEXT["validate_description"]

        filepath: StringProperty(name=UI_TEXT["filepath_name"], subtype="FILE_PATH")
        filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

        def execute(self, context):
            try:
                with open(self.filepath, "r", encoding="utf-8") as handle:
                    parse_and_validate(handle.read())
                self.report({'INFO'}, UI_TEXT["validation_success"])
                return {'FINISHED'}
            except DocumentError as exc:
                self.report({'ERROR'}, format_document_error(exc))
                return {'CANCELLED'}
            except OSError as exc:
                self.report({'ERROR'}, format_runtime_error(exc, "读取 JSON 文件"))
                return {'CANCELLED'}
            except Exception as exc:
                self.report({'ERROR'}, format_runtime_error(exc, "验证"))
                return {'CANCELLED'}

        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}


    class JSONGN_OT_export(Operator):
        bl_idname = "json_gn.export_document"
        bl_label = UI_TEXT["export_label"]
        bl_description = UI_TEXT["export_description"]

        filepath: StringProperty(name=UI_TEXT["filepath_name"], subtype="FILE_PATH")
        filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

        def execute(self, context):
            try:
                result = export_active_node_group(context.object, self.filepath)
                self.report(
                    {'INFO'},
                    format_export_success(result["nodes"], result["links"], result["path"]),
                )
                return {'FINISHED'}
            except OSError as exc:
                self.report({'ERROR'}, format_runtime_error(exc, "写入 JSON 文件"))
                return {'CANCELLED'}
            except ExportError as exc:
                self.report({'ERROR'}, format_runtime_error(exc, "导出"))
                return {'CANCELLED'}
            except Exception as exc:
                self.report({'ERROR'}, format_runtime_error(exc, "导出"))
                return {'CANCELLED'}

        def invoke(self, context, event):
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}


    class JSONGN_PT_panel(Panel):
        bl_label = UI_TEXT["panel_label"]
        bl_idname = "JSONGN_PT_panel"
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = UI_TEXT["panel_category"]

        def draw(self, context):
            layout = self.layout
            layout.prop(context.scene, "json_gn_dry_run")
            layout.prop(context.scene, "json_gn_attach")
            layout.operator("json_gn.validate_document")
            layout.operator("json_gn.import_document")
            layout.operator("json_gn.export_document")


    _CLASSES = (JSONGN_OT_import, JSONGN_OT_validate, JSONGN_OT_export, JSONGN_PT_panel)


def register():
    if not bpy:
        return
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.json_gn_dry_run = BoolProperty(
        name=UI_TEXT["dry_run_name"],
        description=UI_TEXT["dry_run_description"],
        default=False,
    )
    bpy.types.Scene.json_gn_attach = BoolProperty(
        name=UI_TEXT["attach_name"],
        description=UI_TEXT["attach_description"],
        default=False,
    )


def unregister():
    if not bpy:
        return
    del bpy.types.Scene.json_gn_dry_run
    del bpy.types.Scene.json_gn_attach
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
