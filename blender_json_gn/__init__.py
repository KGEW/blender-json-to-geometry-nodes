"""Blender JSON 转几何节点扩展。"""
bl_info = {"name": "JSON 转几何节点", "author": "KGEW", "version": (0, 6, 0), "blender": (5, 2, 0), "location": "3D 视图 > 侧栏 > JSON 几何节点", "description": "验证、导入和导出 Geometry Nodes JSON", "category": "Node"}
__version__ = "0.6.0"

def register():
    from .blender_ui import register as register_ui
    register_ui()

def unregister():
    from .blender_ui import unregister as unregister_ui
    unregister_ui()
