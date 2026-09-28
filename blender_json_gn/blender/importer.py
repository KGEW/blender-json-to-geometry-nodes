"""Blender-side importer. Import is deliberately isolated from validation."""
from __future__ import annotations

try:
    import bpy
except ImportError:  # allows importing package outside Blender
    bpy = None

from ..core.validation import DocumentError, validate_document

class ImportErrorDetail(RuntimeError):
    pass

def _socket(collection, key):
    if isinstance(key, int):
        if key < 0 or key >= len(collection): raise ImportErrorDetail(f"socket index {key} out of range")
        return collection[key]
    if not isinstance(key, str): raise ImportErrorDetail("socket reference must be name or index")
    for sock in collection:
        if sock.name == key: return sock
    raise ImportErrorDetail(f"socket {key!r} not found")

def _set_default(node, key, value):
    sock = _socket(node.inputs, key)
    if not sock.is_linked:
        try: sock.default_value = value
        except (TypeError, ValueError, AttributeError) as exc: raise ImportErrorDetail(f"cannot set input {key!r}: {exc}") from exc

def import_document(document, *, dry_run=False, attach_object=None):
    if bpy is None: raise ImportErrorDetail("Blender bpy is not available")
    issues = validate_document(document)
    if issues: raise DocumentError(issues)
    name = document["name"]
    if dry_run: return {"name": name, "nodes": len(document["nodes"]), "links": len(document["links"]), "dry_run": True}
    tree = None
    created_modifier = None
    try:
        if attach_object is not None and not hasattr(attach_object, "modifiers"):
            raise ImportErrorDetail("attach target does not support modifiers")
        tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
        # Blender 4.x+ interface API; Blender 3.x is intentionally unsupported.
        iface = document.get("interface", {})
        for direction, in_out in (("inputs", "INPUT"), ("outputs", "OUTPUT")):
            for sock in iface.get(direction, []):
                socket = tree.interface.new_socket(name=sock["name"], in_out=in_out, socket_type=sock["socket_type"])
                if "default" in sock:
                    try: socket.default_value = sock["default"]
                    except (TypeError, ValueError, AttributeError) as exc: raise ImportErrorDetail(f"interface {sock['id']!r} default invalid: {exc}") from exc
        group_in = tree.nodes.new("NodeGroupInput"); group_in.name = "__json_gn_group_input"; group_in.label = "Group Input"; group_in.location = (-400, 0)
        group_out = tree.nodes.new("NodeGroupOutput"); group_out.name = "__json_gn_group_output"; group_out.label = "Group Output"; group_out.location = (400, 0)
        created = {"__group_input__": group_in, "__group_output__": group_out}
        for item in document["nodes"]:
            node = tree.nodes.new(item["type"])
            node.name = item["id"]
            if item.get("label") is not None: node.label = item["label"]
            if item.get("location") is not None: node.location = item["location"]
            created[item["id"]] = node
            # Properties such as data_type/input_type/operation can create dynamic sockets.
            for key, value in item.get("properties", {}).items():
                if key.startswith("_"): raise ImportErrorDetail(f"property {key!r} is reserved")
                if not hasattr(node, key): raise ImportErrorDetail(f"node {item['id']!r} has no property {key!r}")
                try: setattr(node, key, value)
                except (TypeError, ValueError, AttributeError) as exc: raise ImportErrorDetail(f"cannot set property {key!r}: {exc}") from exc
            for key, value in item.get("inputs", {}).items(): _set_default(node, int(key) if str(key).isdigit() else key, value)
        for link in document["links"]:
            src = created[link["from_node"]]; dst = created[link["to_node"]]
            tree.links.new(_socket(src.outputs, link["from_socket"]), _socket(dst.inputs, link["to_socket"]))
        if attach_object is not None:
            created_modifier = attach_object.modifiers.new(name=f"JSON GN: {name}", type="NODES")
            created_modifier.node_group = tree
        return {"name": name, "nodes": len(created), "links": len(document["links"]), "dry_run": False, "tree": tree, "modifier": created_modifier}
    except Exception:
        if created_modifier is not None and attach_object is not None:
            try: attach_object.modifiers.remove(created_modifier)
            except Exception: pass
        if tree is not None:
            bpy.data.node_groups.remove(tree)
        raise
