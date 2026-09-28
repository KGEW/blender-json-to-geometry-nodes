import json
import math
from pathlib import Path
import pytest
from blender_json_gn.core.validation import DocumentError, parse_and_validate, validate_document

BASE={"version":"1.0","name":"x","nodes":[],"links":[]}

def test_chinese_dual_normal_workflow_examples_parse():
    root=Path(__file__).parents[1]/"examples"
    smooth=parse_and_validate((root/"retopo_surface_normal_smooth.json").read_text(encoding="utf8"))
    transfer=parse_and_validate((root/"industrial_model_masked_normal_transfer.json").read_text(encoding="utf8"))
    assert smooth["name"] == "重拓扑表面法向平滑"
    assert [item["name"] for item in smooth["interface"]["inputs"]] == ["几何体", "平滑遮罩", "平滑强度", "迭代次数"]
    smooth_properties={node["id"]: node.get("properties", {}) for node in smooth["nodes"]}
    assert smooth_properties["set_mesh_normal"] == {"mode": "FREE", "domain": "POINT"}
    assert transfer["name"] == "工业模型局部法向传递"
    assert [item["name"] for item in transfer["interface"]["inputs"]] == ["几何体", "参考模型", "顶点组或遮罩", "传递强度"]
    properties={node["id"]: node.get("properties", {}) for node in transfer["nodes"]}
    assert properties["set_mesh_normal"] == {"mode": "FREE", "domain": "CORNER"}
    assert properties["guide_info"]["transform_space"] == "RELATIVE"

def test_v2_formal_example_parses():
    path=Path(__file__).parents[1]/"examples/normal_field_uniform_surface_mask_v2.json"
    document=parse_and_validate(path.read_text(encoding="utf8"))
    assert document["name"] == "Normal Field Uniform Surface Mask v2"
    assert len(document["nodes"]) <= 100 and len(document["links"]) <= 200
    assert all(node.get("properties", {}).get("operation") != "MAXIMUM" for node in document["nodes"])
    labels={node.get("label") for node in document["nodes"]}
    assert {"Sample +T", "Sample -T", "Sample +B", "Sample -B"} <= labels
def test_minimal_valid(): assert parse_and_validate(json.dumps(BASE))["version"] == "1.0"
def test_duplicate_id_path():
    d={**BASE,"nodes":[{"id":"a","type":"GeometryNodeMeshCube","location":[0,0]},{"id":"a","type":"GeometryNodeMeshCube","location":[1,1]}]}
    issues=validate_document(d); assert any(i.path == "$.nodes[1].id" for i in issues)
def test_reserved_node_ids_rejected():
    d={**BASE,"nodes":[{"id":"__group_input__","type":"GeometryNodeMeshCube","location":[0,0]}]}
    assert any("reserved" in i.message for i in validate_document(d))
def test_bad_link_reference():
    issues=validate_document({**BASE,"links":[{"from_node":"no","from_socket":"Mesh","to_node":"no2","to_socket":"Geometry"}]})
    assert {i.path for i in issues} >= {"$.links[0].from_node","$.links[0].to_node"}
def test_link_node_refs_must_be_non_empty_strings():
    d={**BASE,"links":[{"from_node":1,"from_socket":"x","to_node":True,"to_socket":"y"}]}
    assert any(i.path == "$.links[0].from_node" for i in validate_document(d))
    assert any(i.path == "$.links[0].to_node" for i in validate_document(d))
def test_socket_refs_reject_negative_and_bool():
    d={**BASE,"links":[{"from_node":"__group_input__","from_socket":-1,"to_node":"__group_output__","to_socket":True}]}
    paths={i.path for i in validate_document(d)}
    assert "$.links[0].from_socket" in paths and "$.links[0].to_socket" in paths
def test_socket_refs_allow_nonnegative_integer():
    d={**BASE,"interface":{"inputs":[{"id":"i","name":"Geometry","socket_type":"NodeSocketGeometry"}],"outputs":[{"id":"o","name":"Geometry","socket_type":"NodeSocketGeometry"}]},"links":[{"from_node":"__group_input__","from_socket":0,"to_node":"__group_output__","to_socket":0}]}
    assert validate_document(d) == []
def test_unknown_field_rejected_and_modifier_removed():
    assert any(i.path == "$.wat" for i in validate_document({**BASE,"wat":1}))
    assert any(i.path == "$.modifier" for i in validate_document({**BASE,"modifier":{}}))
def test_bad_json_has_structured_error():
    with pytest.raises(DocumentError) as err: parse_and_validate("{")
    assert err.value.issues[0].path == "$"
def test_nonfinite_json_constants_rejected():
    for text in ('{"version":"1.0","name":"x","nodes":[],"links":[],"x":NaN}', '{"version":"1.0","name":"x","nodes":[],"links":[],"interface":{"inputs":[],"outputs":[]},"links":[],"v":Infinity}'):
        with pytest.raises(DocumentError): parse_and_validate(text)
def test_nonfinite_runtime_values_rejected():
    d={**BASE,"nodes":[{"id":"x","type":"X","location":[math.nan,0],"inputs":{"x":[1,math.inf]},"properties":{"p":-math.inf}}],"interface":{"inputs":[{"id":"i","name":"I","socket_type":"NodeSocketFloat","default":math.nan}],"outputs":[]}}
    paths={i.path for i in validate_document(d)}
    assert "$.nodes[0].location" in paths
    assert "$.nodes[0].inputs.x[1]" in paths
    assert "$.nodes[0].properties.p" in paths
    assert "$.interface.inputs[0].default" in paths
def test_top_level_nodes_and_links_have_independent_limits():
    nodes=[{"id":str(i),"type":"X","location":[0,0]} for i in range(33)]
    assert not any("$.nodes" == i.path for i in validate_document({**BASE,"nodes":nodes}))
    links=[{"from_node":"__group_input__","from_socket":"x","to_node":"__group_output__","to_socket":"y"} for _ in range(33)]
    assert not any("$.links" == i.path for i in validate_document({**BASE,"links":links}))
    too_many_nodes=[{"id":str(i),"type":"X","location":[0,0]} for i in range(101)]
    assert any("maximum" in i.message for i in validate_document({**BASE,"nodes":too_many_nodes}))
def test_value_and_interface_arrays_stay_limited():
    many=[0]*33
    d={**BASE,"nodes":[{"id":"x","type":"X","location":[0,0],"inputs":{"v":many}}],"interface":{"inputs":[{"id":str(i),"name":str(i),"socket_type":"NodeSocketFloat"} for i in range(33)]}}
    issues=validate_document(d)
    assert any(i.path == "$.nodes[0].inputs.v" for i in issues)
    assert any(i.path == "$.interface.inputs" for i in issues)
def test_no_python_execution_surface():
    d={**BASE,"nodes":[{"id":"x","type":"X","location":[0,0],"inputs":{"x":{"__import__":"os"}}}]}
    assert any("objects are not allowed" in i.message for i in validate_document(d))
