"""Chinese user-facing text without changing the JSON machine contract."""
from __future__ import annotations

import re

UI_TEXT = {
    "addon_name": "JSON 转几何节点",
    "panel_label": "JSON 几何节点",
    "panel_category": "JSON 几何节点",
    "validate_label": "验证 JSON",
    "validate_description": "检查 JSON 是否符合当前 1.0 协议，不创建节点",
    "import_label": "导入 JSON 几何节点",
    "import_description": "验证 JSON 并创建新的 Geometry Nodes 节点组",
    "export_label": "导出活动几何节点 JSON",
    "export_description": "将活动对象的第一个 Geometry Nodes 节点组导出为 JSON",
    "dry_run_name": "仅验证（不创建节点）",
    "dry_run_description": "只验证并显示节点与连线统计，不创建节点组或修改器",
    "attach_name": "附加到活动对象",
    "attach_description": "导入后在活动对象上创建 Geometry Nodes 修改器",
    "filepath_name": "JSON 文件",
    "validation_success": "JSON 验证通过：协议版本 1.0",
}

_EXACT_ISSUE_MESSAGES = {
    "required": "缺少必填字段",
    "unknown field": "未知字段",
    "document must be an object": "JSON 顶层必须是对象",
    "must be a string": "必须是字符串",
    "must be an array": "必须是数组",
    "must be an object": "必须是对象",
    "must be a non-empty node id string": "必须是非空节点 ID 字符串",
    "must be a non-empty string or non-negative integer": "必须是非空字符串或非负整数",
    "socket index must be non-negative": "socket 索引不能为负数",
    "reserved node id": "节点 ID 为保留值",
    "duplicate node id": "节点 ID 重复",
    "unknown node id": "未知节点 ID",
    "objects are not allowed as values": "值不能是对象",
    "must be a JSON scalar or array": "必须是 JSON 标量或数组",
    "must be [finite number, finite number]": "必须是两个有限数字组成的数组",
    "keys must be non-empty short strings": "键必须是非空短字符串",
    "JSON text too large": "JSON 文本过大",
}

_RUNTIME_MESSAGES = {
    "Blender bpy is not available": "当前环境无法使用 Blender bpy",
    "attach target does not support modifiers": "附加目标不支持修改器",
    "no active object": "没有活动对象",
    "active object has no Geometry Nodes modifier": "活动对象没有 Geometry Nodes 修改器",
    "active node group is not a GeometryNodeTree": "活动节点组不是 GeometryNodeTree",
    "link references an unsupported node": "连线引用了不支持的节点",
    "socket reference must be name or index": "socket 引用必须使用名称或索引",
    "export requires at most one Group Input and Group Output": "导出要求最多各有一个 Group Input 和 Group Output",
}


def translate_issue_message(message: str) -> str:
    """Translate validator prose while preserving paths and protocol literals."""
    if message in _EXACT_ISSUE_MESSAGES:
        return _EXACT_ISSUE_MESSAGES[message]
    patterns = (
        (r"maximum is (\d+)", r"最多允许 \1 项"),
        (r"maximum (\d+) entries", r"最多允许 \1 项"),
        (r"maximum array length is (\d+)", r"数组长度最多为 \1"),
        (r"maximum nesting depth is (\d+)", r"最大嵌套深度为 \1"),
        (r"must be 1\.\.(\d+) characters", r"长度必须为 1～\1 个字符"),
        (r"string must be at most (\d+) characters", r"字符串最多为 \1 个字符"),
        (r"socket name must be 1\.\.(\d+) characters", r"socket 名称长度必须为 1～\1 个字符"),
        (r"must be supported version '([^']+)'", r"必须使用受支持的协议版本 '\1'"),
        (r"must be finite; NaN and Infinity are not allowed", r"必须是有限数值；不允许 NaN 或 Infinity"),
        (r"non-standard JSON constant (.+) is not allowed", r"不允许非标准 JSON 常量 \1"),
        (r"invalid JSON: (.+)", r"JSON 语法无效：\1"),
    )
    for pattern, replacement in patterns:
        if re.fullmatch(pattern, message):
            return re.sub(pattern, replacement, message)
    return message


def format_document_error(error) -> str:
    """Format DocumentError for Blender reports without altering issue paths."""
    issues = getattr(error, "issues", None)
    if not issues:
        return f"JSON 验证失败：{error}"
    return "JSON 验证失败：" + "；".join(
        f"{issue.path}：{translate_issue_message(issue.message)}" for issue in issues
    )


def _translate_runtime_message(message: str) -> str:
    if message in _RUNTIME_MESSAGES:
        return _RUNTIME_MESSAGES[message]
    patterns = (
        (r"socket index (\d+) out of range", r"socket 索引 \1 超出范围"),
        (r"socket (.+) not found", r"找不到 socket \1"),
        (r"cannot set input (.+): (.+)", r"无法设置输入 \1：\2"),
        (r"interface (.+) default invalid: (.+)", r"接口 \1 的默认值无效：\2"),
        (r"property (.+) is reserved", r"属性 \1 为保留属性"),
        (r"node (.+) has no property (.+)", r"节点 \1 没有属性 \2"),
        (r"cannot set property (.+): (.+)", r"无法设置属性 \1：\2"),
        (r"node has invalid export id: (.+)", r"节点的导出 ID 无效：\1"),
        (r"duplicate export node id: (.+)", r"导出节点 ID 重复：\1"),
        (r"unsupported Blender value type: (.+)", r"不支持的 Blender 值类型：\1"),
        (r"cannot export non-finite float", r"无法导出非有限浮点数"),
        (r"(?:Error: )?[Nn]ode type (.+) undefined", r"节点类型 \1 未定义"),
    )
    for pattern, replacement in patterns:
        if re.fullmatch(pattern, message):
            return re.sub(pattern, replacement, message)
    return message


def format_runtime_error(error: Exception, action: str) -> str:
    """Add a Chinese action prefix and translate stable runtime errors."""
    if isinstance(error, FileNotFoundError):
        detail = f"找不到文件或目录：{error.filename}" if error.filename else "找不到文件或目录"
    elif isinstance(error, PermissionError):
        detail = f"没有文件访问权限：{error.filename}" if error.filename else "没有文件访问权限"
    elif isinstance(error, IsADirectoryError):
        detail = f"所选路径是目录：{error.filename}" if error.filename else "所选路径是目录"
    elif isinstance(error, OSError):
        detail = f"文件系统错误（错误码 {error.errno}）" if error.errno is not None else "文件系统错误"
    else:
        message = str(error) or error.__class__.__name__
        detail = _translate_runtime_message(message)
    return f"{action}失败：{detail}"


def format_import_success(nodes: int, links: int, *, dry_run: bool) -> str:
    if dry_run:
        return f"仅验证完成：计划导入 {nodes} 个节点、{links} 条连线"
    return f"导入完成：{nodes} 个节点、{links} 条连线"


def format_export_success(nodes: int, links: int, path: str) -> str:
    return f"导出完成：{nodes} 个节点、{links} 条连线；文件：{path}"
