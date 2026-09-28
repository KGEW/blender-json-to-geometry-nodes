import json

import pytest

from blender_json_gn.core.validation import DocumentError, parse_and_validate
from blender_json_gn.localization import (
    UI_TEXT,
    format_document_error,
    format_export_success,
    format_import_success,
    format_runtime_error,
)


def test_default_user_interface_is_chinese():
    assert UI_TEXT["panel_label"] == "JSON 几何节点"
    assert UI_TEXT["panel_category"] == "JSON 几何节点"
    assert UI_TEXT["validate_label"] == "验证 JSON"
    assert UI_TEXT["import_label"] == "导入 JSON 几何节点"
    assert UI_TEXT["export_label"] == "导出活动几何节点 JSON"
    assert UI_TEXT["dry_run_name"] == "仅验证（不创建节点）"
    assert UI_TEXT["attach_name"] == "附加到活动对象"


def test_document_error_is_chinese_and_keeps_structured_path():
    with pytest.raises(DocumentError) as captured:
        parse_and_validate('{"version":"1.0","name":"x","nodes":[],"links":[],"wat":1}')
    message = format_document_error(captured.value)
    assert message.startswith("JSON 验证失败：")
    assert "$.wat" in message
    assert "未知字段" in message


def test_invalid_json_user_message_keeps_root_path():
    with pytest.raises(DocumentError) as captured:
        parse_and_validate("{")
    message = format_document_error(captured.value)
    assert "$：JSON 语法无效" in message


def test_non_object_document_error_is_chinese():
    with pytest.raises(DocumentError) as captured:
        parse_and_validate("[]")
    assert format_document_error(captured.value) == "JSON 验证失败：$：JSON 顶层必须是对象"


def test_runtime_error_has_chinese_action_prefix():
    assert format_runtime_error(RuntimeError("no active object"), "导出") == "导出失败：没有活动对象"
    assert format_runtime_error(RuntimeError("socket 'Bad' not found"), "导入") == "导入失败：找不到 socket 'Bad'"
    assert format_runtime_error(RuntimeError("node type GeometryNodeMissing undefined"), "导入") == "导入失败：节点类型 GeometryNodeMissing 未定义"
    assert format_runtime_error(FileNotFoundError(2, "No such file or directory", "/tmp/missing.json"), "读取 JSON 文件") == "读取 JSON 文件失败：找不到文件或目录：/tmp/missing.json"


def test_success_notifications_are_chinese():
    assert UI_TEXT["validation_success"] == "JSON 验证通过：协议版本 1.0"
    assert format_import_success(4, 3, dry_run=False) == "导入完成：4 个节点、3 条连线"
    assert format_import_success(2, 1, dry_run=True) == "仅验证完成：计划导入 2 个节点、1 条连线"
    assert format_export_success(5, 4, "/tmp/a.json") == "导出完成：5 个节点、4 条连线；文件：/tmp/a.json"


def test_localization_does_not_change_machine_json_contract():
    source = {
        "version": "1.0",
        "name": "契约兼容",
        "interface": {
            "inputs": [{"id": "geometry_in", "name": "Geometry", "socket_type": "NodeSocketGeometry"}],
            "outputs": [{"id": "geometry_out", "name": "Geometry", "socket_type": "NodeSocketGeometry"}],
        },
        "nodes": [{"id": "cube", "type": "GeometryNodeMeshCube", "location": [0, 0]}],
        "links": [],
    }
    document = parse_and_validate(json.dumps(source, ensure_ascii=False))
    assert set(document) == {"version", "name", "interface", "nodes", "links"}
    assert document["version"] == "1.0"
    assert document["nodes"][0]["type"] == "GeometryNodeMeshCube"
    assert document["interface"]["inputs"][0]["socket_type"] == "NodeSocketGeometry"
