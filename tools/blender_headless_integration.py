"""Run with Blender 5.2.x: blender -b --python this_file.py.
The caller must check exit status, absence of Traceback, and the success markers.
"""
from __future__ import annotations
import importlib
import importlib.util
import json
import math
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLED_NAME = "bl_ext.user_default.blender_json_geometry_nodes"


def load_package_from_zip():
    import bpy
    zip_path = ROOT / "dist" / "blender_json_geometry_nodes-0.6.0.zip"
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(zip_path) as z:
            names = set(z.namelist())
            assert "blender_manifest.toml" in names and "manifest.toml" not in names
            assert "LICENSE" in names
            assert "__init__.py" in names and "blender_ui.py" in names and "blender/importer.py" in names
            z.extractall(td)
        spec = importlib.util.spec_from_file_location("json_gn_zip_test", Path(td) / "__init__.py", submodule_search_locations=[td])
        module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        importlib.import_module(f"{spec.name}.blender_ui")
        if not hasattr(bpy.ops.json_gn, "import_document"):
            module.register(); module.unregister()
        return module


def select_runtime():
    """Prefer the installed extension namespace; source fallback is for standalone runs."""
    require_installed = os.environ.get("JSON_GN_REQUIRE_INSTALLED") == "1"
    try:
        package = importlib.import_module(INSTALLED_NAME)
    except ImportError:
        if require_installed: raise AssertionError(f"installed namespace not available: {INSTALLED_NAME}")
        sys.path.insert(0, str(ROOT))
        package_name = "blender_json_gn"
        package = importlib.import_module(package_name)
        print("RUNTIME_IMPORTER_NAMESPACE", package_name)
    else:
        package_name = INSTALLED_NAME
        print("RUNTIME_IMPORTER_NAMESPACE", package_name)
    validation = importlib.import_module(package_name + ".core.validation")
    importer = importlib.import_module(package_name + ".blender.importer")
    exporter = importlib.import_module(package_name + ".blender.exporter")
    return package, validation, importer, exporter, package_name == INSTALLED_NAME


def make_mesh_object(bpy, name, vertices, faces, smooth=False, custom_normals=None):
    mesh = bpy.data.meshes.new(name + " Mesh")
    mesh.from_pydata(vertices, [], faces); mesh.update()
    for polygon in mesh.polygons: polygon.use_smooth = smooth
    if custom_normals is not None:
        mesh.normals_split_custom_set_from_vertices(custom_normals)
    obj = bpy.data.objects.new(name, mesh); bpy.context.scene.collection.objects.link(obj)
    return obj


def make_ico_sphere(bpy, name, subdivisions):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.object; obj.name = name
    for polygon in obj.data.polygons: polygon.use_smooth = True
    return obj


def analytic_normal(co):
    length = math.sqrt(sum(float(x) * float(x) for x in co))
    return tuple(float(x) / length for x in co)


def make_custom_cube(bpy, name):
    vertices = [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    faces = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    return make_mesh_object(bpy, name, vertices, faces, smooth=True, custom_normals=[analytic_normal(v) for v in vertices])


def refine_same_surface(bpy, name, source_obj):
    """Four-way coplanar subdivision; original vertices remain at indices 0..7."""
    source = source_obj.data
    vertices = [tuple(v.co) for v in source.vertices]
    normals = [analytic_normal(v) for v in vertices]
    edge_midpoints = {}
    faces = []
    def midpoint(a, b):
        key = tuple(sorted((a, b)))
        if key not in edge_midpoints:
            pa, pb = vertices[key[0]], vertices[key[1]]
            co = tuple((pa[i] + pb[i]) * 0.5 for i in range(3))
            edge_midpoints[key] = len(vertices); vertices.append(co); normals.append(analytic_normal(co))
        return edge_midpoints[key]
    for polygon in source.polygons:
        a, b, c = polygon.vertices
        ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
        faces.extend([(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)])
    return make_mesh_object(bpy, name, vertices, faces, smooth=True, custom_normals=normals)


def set_modifier_inputs(modifier, tree, values):
    for item in tree.interface.items_tree:
        if getattr(item, "item_type", None) == 'SOCKET' and getattr(item, "in_out", None) == 'INPUT' and item.name in values:
            socket = getattr(modifier.properties.inputs, item.identifier)
            socket.value = values[item.name]


def evaluate_mask(bpy, obj, tree, modifier, expected_topology, params=None):
    set_modifier_inputs(modifier, tree, params or {"Voxel Size": 0.1, "Sample Radius": 0.05, "Low Variation": 0.01, "High Variation": 0.35})
    depsgraph = bpy.context.evaluated_depsgraph_get(); depsgraph.update()
    evaluated = obj.evaluated_get(depsgraph); output = evaluated.to_mesh()
    try:
        assert len(output.vertices) == expected_topology[0]
        assert len(output.polygons) == expected_topology[1]
        attribute = output.attributes.get("normal_turn_mask")
        assert attribute is not None and len(attribute.data) == len(output.vertices)
        values = [float(item.value) for item in attribute.data]
        assert values and all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in values)
        return (sum(values) / len(values), min(values), max(values)), values
    finally:
        evaluated.to_mesh_clear()


def main():
    import bpy
    zip_module = load_package_from_zip()
    runtime_package, validation, importer, exporter, installed = select_runtime()
    DocumentError, parse_and_validate = validation.DocumentError, validation.parse_and_validate
    import_document, ImportErrorDetail = importer.import_document, importer.ImportErrorDetail
    export_node_group = exporter.export_node_group
    minimal = json.loads((ROOT / "examples/minimal.json").read_text(encoding="utf8"))
    mesh = json.loads((ROOT / "examples/mesh_transform.json").read_text(encoding="utf8"))
    v2 = json.loads((ROOT / "examples/normal_field_uniform_surface_mask_v2.json").read_text(encoding="utf8"))
    retopo_smooth = json.loads((ROOT / "examples/retopo_surface_normal_smooth.json").read_text(encoding="utf8"))
    industrial_transfer = json.loads((ROOT / "examples/industrial_model_masked_normal_transfer.json").read_text(encoding="utf8"))
    trees = []; objects = []
    result = import_document(minimal, attach_object=None); trees.append(result["tree"])
    assert len(result["tree"].nodes) == 2 and len(result["tree"].links) == 1
    obj = bpy.data.objects.new("JSON GN Integration Object", None); bpy.context.scene.collection.objects.link(obj); objects.append(obj)
    result = import_document(mesh, attach_object=obj); trees.append(result["tree"])
    print("MESH_LINK_COUNT", len(result["tree"].links), "NODE_NAMES", [node.name for node in result["tree"].nodes])
    assert len(result["tree"].links) == 3 and any(node.label == "Group Output" for node in result["tree"].nodes)
    assert result["modifier"] is not None and result["modifier"].node_group == result["tree"]
    bad = dict(minimal); bad["links"] = [{"from_node":"__group_input__","from_socket":"NO_SUCH_SOCKET","to_node":"__group_output__","to_socket":"Geometry"}]
    before = set(bpy.data.node_groups.keys())
    try: import_document(bad)
    except ImportErrorDetail: pass
    else: raise AssertionError("bad socket unexpectedly imported")
    assert set(bpy.data.node_groups.keys()) == before
    for text in ('{"version":"1.0","name":"x","nodes":[],"links":[],"v":NaN}', '{"version":"1.0","name":"x","nodes":[{"id":"__group_input__","type":"X","location":[0,0]}],"links":[]}'):
        try: parse_and_validate(text)
        except DocumentError: pass
        else: raise AssertionError("invalid JSON unexpectedly accepted")
    zip_ui = sys.modules.get("json_gn_zip_test.blender_ui")
    if zip_ui is None or not hasattr(zip_module, "blender_ui"): raise AssertionError("ZIP UI module did not load")
    assert "UNDO" in zip_ui.JSONGN_OT_import.bl_options
    assert hasattr(zip_ui, "JSONGN_OT_export")
    assert zip_module.bl_info["name"] == "JSON 转几何节点"
    assert zip_ui.JSONGN_PT_panel.bl_label == "JSON 几何节点"
    assert zip_ui.JSONGN_PT_panel.bl_category == "JSON 几何节点"
    assert zip_ui.JSONGN_OT_validate.bl_label == "验证 JSON"
    assert zip_ui.JSONGN_OT_validate.bl_idname == "json_gn.validate_document"
    assert zip_ui.JSONGN_OT_import.bl_label == "导入 JSON 几何节点"
    assert zip_ui.JSONGN_OT_import.bl_idname == "json_gn.import_document"
    assert zip_ui.JSONGN_OT_export.bl_label == "导出活动几何节点 JSON"
    assert zip_ui.JSONGN_OT_export.bl_idname == "json_gn.export_document"
    assert zip_ui.format_import_success(2, 1, dry_run=False) == "导入完成：2 个节点、1 条连线"
    try:
        zip_ui.parse_and_validate('{"version":"1.0","name":"x","nodes":[],"links":[],"wat":1}')
    except zip_ui.DocumentError as exc:
        localized_error = zip_ui.format_document_error(exc)
    else:
        raise AssertionError("invalid document unexpectedly passed localized formatter test")
    assert "$.wat" in localized_error and "未知字段" in localized_error
    print("BLENDER_JSON_GN_CHINESE_UI_SUCCESS")

    # Group 1: smooth the manually retopologized guide normals without changing topology.
    guide = make_mesh_object(bpy, "手工重拓扑参考模型", [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)], [(0,1,2),(0,2,3)], smooth=True, custom_normals=[(-0.6,0,0.8),(0.6,0,0.8),(0.6,0,0.8),(-0.6,0,0.8)])
    objects.append(guide); guide_positions=[tuple(v.co) for v in guide.data.vertices]
    smooth_result=import_document(retopo_smooth, attach_object=guide); trees.append(smooth_result["tree"])
    set_modifier_inputs(smooth_result["modifier"], smooth_result["tree"], {"平滑遮罩":1.0,"平滑强度":1.0,"迭代次数":5})
    depsgraph=bpy.context.evaluated_depsgraph_get(); depsgraph.update(); evaluated=guide.evaluated_get(depsgraph); output=evaluated.to_mesh()
    try:
        assert len(output.vertices)==4 and len(output.polygons)==2
        assert [tuple(v.co) for v in output.vertices] == guide_positions
        assert output.attributes.get("custom_normal") is not None
        smooth_normals=[tuple(n.vector) for n in output.corner_normals]
        stored_normals=[tuple(item.vector) for item in output.attributes["custom_normal"].data]
        max_abs_x=max(abs(n[0]) for n in stored_normals)
        assert max_abs_x < 0.1
    finally:
        evaluated.to_mesh_clear()
    print("RETOPO_NORMAL_SMOOTH_SUCCESS",len(smooth_result["tree"].nodes),len(smooth_result["tree"].links),"MAX_ABS_X",max_abs_x)

    # Group 2: transfer the guide normals through a Chinese mask input while preserving target topology.
    target = make_mesh_object(bpy, "工业模型传递目标", [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)], [(0,1,2),(0,2,3)], smooth=True, custom_normals=[(0.0,0.8,0.2)]*4)
    objects.append(target); original_positions=[tuple(v.co) for v in target.data.vertices]
    transfer_result = import_document(industrial_transfer, attach_object=target); trees.append(transfer_result["tree"])
    set_modifier_inputs(transfer_result["modifier"], transfer_result["tree"], {"参考模型":guide,"顶点组或遮罩":1.0,"传递强度":1.0})
    depsgraph.update(); evaluated=target.evaluated_get(depsgraph); output=evaluated.to_mesh()
    try:
        assert len(output.vertices)==4 and len(output.polygons)==2
        assert [tuple(v.co) for v in output.vertices] == original_positions
        normals=[tuple(n.vector) for n in output.corner_normals]
        assert normals and min(n[2] for n in normals) > 0.75
        assert output.attributes.get("custom_normal") is not None
    finally:
        evaluated.to_mesh_clear()
    print("INDUSTRIAL_MASKED_NORMAL_TRANSFER_SUCCESS",len(transfer_result["tree"].nodes),len(transfer_result["tree"].links))
    if installed: print("BLENDER_JSON_GN_INSTALLED_DUAL_NORMAL_SUCCESS")

    plane = make_mesh_object(bpy, "V2 Nonuniform Triangulated Plane", [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),(0.1,0.2,0)], [(0,1,4),(1,2,4),(2,3,4),(3,0,4)], smooth=True)
    objects.append(plane); plane_topology = (len(plane.data.vertices), len(plane.data.polygons))
    plane_result = import_document(v2, attach_object=plane); trees.append(plane_result["tree"])
    print("V2_GRAPH_COUNTS", len(v2["nodes"]), len(v2["links"]), len(plane_result["tree"].nodes), len(plane_result["tree"].links))
    assert len(plane_result["tree"].nodes) == len(v2["nodes"]) + 2 and len(plane_result["tree"].links) == len(v2["links"])
    plane_stats, _ = evaluate_mask(bpy, plane, plane_result["tree"], plane_result["modifier"], plane_topology)
    print("V2_PLANE_STATS", plane_stats)
    with tempfile.TemporaryDirectory() as export_dir:
        exported = export_node_group(plane_result["tree"], str(Path(export_dir) / "normal_field_export.json"))
        roundtrip = parse_and_validate(Path(exported["path"]).read_text(encoding="utf8"))
        assert len(roundtrip["nodes"]) == len(v2["nodes"]) and len(roundtrip["links"]) == len(v2["links"])
        assert set(roundtrip) == {"version", "name", "interface", "nodes", "links"}
        assert roundtrip["version"] == "1.0"
        assert all("type" in node and node["type"] for node in roundtrip["nodes"])
        print("JSON_EXPORT_ROUNDTRIP_SUCCESS", len(roundtrip["nodes"]), len(roundtrip["links"]))

    # Secondary smoke only: different icosphere geometry is not the density proof.
    sphere_a = make_ico_sphere(bpy, "V2 Sphere Low Density", 2); objects.append(sphere_a)
    sphere_b = make_ico_sphere(bpy, "V2 Sphere High Density", 3); objects.append(sphere_b)
    result_a = import_document(v2, attach_object=sphere_a); trees.append(result_a["tree"])
    result_b = import_document(v2, attach_object=sphere_b); trees.append(result_b["tree"])
    stats_a, _ = evaluate_mask(bpy, sphere_a, result_a["tree"], result_a["modifier"], (len(sphere_a.data.vertices), len(sphere_a.data.polygons)))
    stats_b, _ = evaluate_mask(bpy, sphere_b, result_b["tree"], result_b["modifier"], (len(sphere_b.data.vertices), len(sphere_b.data.polygons)))
    print("V2_SPHERE_SMOKE_STATS", stats_a, stats_b)

    # Core density proof: identical closed cube triangle surface, coplanar four-way subdivision,
    # and the same analytic custom smooth normal at every common spatial vertex.
    cube_a = make_custom_cube(bpy, "V2 Same Surface Base Cube"); objects.append(cube_a)
    cube_b = refine_same_surface(bpy, "V2 Same Surface Coplanar Subdivision", cube_a); objects.append(cube_b)
    result_a = import_document(v2, attach_object=cube_a); trees.append(result_a["tree"])
    result_b = import_document(v2, attach_object=cube_b); trees.append(result_b["tree"])
    params = {"Voxel Size": 0.05, "Sample Radius": 0.10, "Low Variation": 0.02, "High Variation": 0.35}
    cube_stats_a, cube_values_a = evaluate_mask(bpy, cube_a, result_a["tree"], result_a["modifier"], (len(cube_a.data.vertices), len(cube_a.data.polygons)), params)
    cube_stats_b, cube_values_b = evaluate_mask(bpy, cube_b, result_b["tree"], result_b["modifier"], (len(cube_b.data.vertices), len(cube_b.data.polygons)), params)
    deltas = [abs(cube_values_a[i] - cube_values_b[i]) for i in range(8)]
    print("V2_SAME_SURFACE_STATS", cube_stats_a, cube_stats_b, "COMMON_MAX_ABS", max(deltas), "COMMON_MEAN_ABS", sum(deltas) / len(deltas))
    assert max(deltas) < 0.01

    for tree in trees:
        if tree and tree.name in bpy.data.node_groups: bpy.data.node_groups.remove(tree)
    for object_ in objects:
        if object_.name in bpy.data.objects: bpy.data.objects.remove(object_, do_unlink=True)
    print("BLENDER_JSON_GN_INTEGRATION_SUCCESS")
    if installed: print("BLENDER_JSON_GN_INSTALLED_V2_SUCCESS")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    raise SystemExit(1)
