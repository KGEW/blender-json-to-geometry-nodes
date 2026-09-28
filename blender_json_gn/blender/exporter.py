"""Conservative Geometry Nodes -> project JSON exporter."""
from __future__ import annotations
import json
import math
from pathlib import Path

try:
    import bpy
except ImportError:
    bpy = None

class ExportError(RuntimeError):
    pass

_PROPERTY_ALLOWLIST = {"operation", "data_type", "domain", "mode", "transform_space", "input_type", "interpolation_type", "clamp"}

def _json_value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value): raise ExportError("cannot export non-finite float")
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    try:
        return [_json_value(item) for item in value]
    except (TypeError, ValueError):
        raise ExportError(f"unsupported Blender value type: {type(value).__name__}")

def _socket_default(socket):
    try:
        return _json_value(socket.default_value)
    except (AttributeError, TypeError, ValueError, ExportError):
        return None

def _socket_ref(collection, socket):
    same_name = [item for item in collection if item.name == socket.name]
    return socket.name if len(same_name) == 1 else list(collection).index(socket)

def _node_ids(tree):
    ids = {}
    group_input = [node for node in tree.nodes if node.bl_idname == "NodeGroupInput"]
    group_output = [node for node in tree.nodes if node.bl_idname == "NodeGroupOutput"]
    if len(group_input) > 1 or len(group_output) > 1:
        raise ExportError("export requires at most one Group Input and Group Output")
    if group_input: ids[group_input[0].as_pointer()] = "__group_input__"
    if group_output: ids[group_output[0].as_pointer()] = "__group_output__"
    nodes = []
    for node in tree.nodes:
        pointer = node.as_pointer()
        if pointer in ids: continue
        node_id = node.name
        if not node_id or node_id in {"__group_input__", "__group_output__"}:
            raise ExportError(f"node has invalid export id: {node_id!r}")
        if node_id in ids.values(): raise ExportError(f"duplicate export node id: {node_id!r}")
        ids[pointer] = node_id
        item = {"id": node_id, "type": node.bl_idname, "location": [float(node.location.x), float(node.location.y)]}
        if node.label: item["label"] = node.label
        properties = {}
        for name in _PROPERTY_ALLOWLIST:
            if hasattr(node, name):
                try: properties[name] = _json_value(getattr(node, name))
                except (AttributeError, TypeError, ValueError, ExportError): pass
        if properties: item["properties"] = properties
        inputs = {}
        for socket in node.inputs:
            if socket.is_linked: continue
            value = _socket_default(socket)
            if value is not None:
                duplicate_name = sum(1 for item in node.inputs if item.name == socket.name) > 1
                inputs[str(_socket_ref(node.inputs, socket)) if duplicate_name else socket.name] = value
        if inputs: item["inputs"] = inputs
        nodes.append(item)
    return ids, nodes

def export_node_group(tree, filepath):
    if bpy is None: raise ExportError("Blender bpy is not available")
    if tree is None or getattr(tree, "bl_idname", None) != "GeometryNodeTree":
        raise ExportError("active node group is not a GeometryNodeTree")
    ids, nodes = _node_ids(tree)
    document = {"version": "1.0", "name": tree.name, "interface": {"inputs": [], "outputs": []}, "nodes": nodes, "links": []}
    for item in tree.interface.items_tree:
        if getattr(item, "item_type", None) != 'SOCKET': continue
        socket = {"id": item.identifier, "name": item.name, "socket_type": item.socket_type}
        default = _socket_default(item)
        if default is not None: socket["default"] = default
        direction = "inputs" if item.in_out == 'INPUT' else "outputs"
        document["interface"][direction].append(socket)
    for link in tree.links:
        source_id = ids.get(link.from_node.as_pointer()); target_id = ids.get(link.to_node.as_pointer())
        if source_id is None or target_id is None: raise ExportError("link references an unsupported node")
        document["links"].append({"from_node": source_id, "from_socket": _socket_ref(link.from_node.outputs, link.from_socket), "to_node": target_id, "to_socket": _socket_ref(link.to_node.inputs, link.to_socket)})
    path = Path(filepath)
    if path.suffix.lower() != ".json": path = path.with_suffix(".json")
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "nodes": len(nodes), "links": len(document["links"]), "document": document}

def export_active_node_group(obj, filepath):
    if obj is None: raise ExportError("no active object")
    for modifier in obj.modifiers:
        if modifier.type == 'NODES' and modifier.node_group is not None:
            return export_node_group(modifier.node_group, filepath)
    raise ExportError("active object has no Geometry Nodes modifier")
