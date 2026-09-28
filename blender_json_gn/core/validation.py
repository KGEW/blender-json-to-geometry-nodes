"""Pure-Python validation for the small JSON Geometry Nodes MVP."""
from __future__ import annotations
import json
import math
from dataclasses import dataclass
from typing import Any

MAX_TEXT = 256
MAX_NODES = 100
MAX_LINKS = 200
MAX_DEPTH = 8
MAX_VALUE_ITEMS = 32
MAX_INTERFACE_ITEMS = 32
RESERVED_NODE_IDS = {"__group_input__", "__group_output__"}

@dataclass(frozen=True)
class Issue:
    path: str
    message: str
    def as_dict(self): return {"path": self.path, "message": self.message}

class DocumentError(ValueError):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("; ".join(f"{i.path}: {i.message}" for i in issues))

def _path(base: str, key: str) -> str:
    return f"{base}.{key}" if base else key

def _check_depth(value: Any, path: str, depth: int, issues: list[Issue]) -> None:
    if depth > MAX_DEPTH:
        issues.append(Issue(path, f"maximum nesting depth is {MAX_DEPTH}")); return
    if isinstance(value, dict):
        for k, v in value.items(): _check_depth(v, _path(path, str(k)), depth + 1, issues)
    elif isinstance(value, list):
        for i, v in enumerate(value): _check_depth(v, f"{path}[{i}]", depth + 1, issues)
    elif isinstance(value, float) and not math.isfinite(value):
        issues.append(Issue(path, "must be finite; NaN and Infinity are not allowed"))

def _required(obj: dict, fields: set[str], path: str, issues: list[Issue]) -> None:
    for field in fields:
        if field not in obj: issues.append(Issue(_path(path, field), "required"))

def _strict(obj: dict, allowed: set[str], path: str, issues: list[Issue]) -> None:
    for key in obj:
        if key not in allowed: issues.append(Issue(_path(path, str(key)), "unknown field"))

def _text(value: Any, path: str, issues: list[Issue], *, max_len=MAX_TEXT) -> None:
    if not isinstance(value, str): issues.append(Issue(path, "must be a string"))
    elif not value or len(value) > max_len: issues.append(Issue(path, f"must be 1..{max_len} characters"))

def _value(value: Any, path: str, issues: list[Issue]) -> None:
    """Allow JSON scalar/array defaults, but never object-shaped values."""
    if isinstance(value, dict):
        issues.append(Issue(path, "objects are not allowed as values"))
    elif isinstance(value, list):
        if len(value) > MAX_VALUE_ITEMS: issues.append(Issue(path, f"maximum array length is {MAX_VALUE_ITEMS}"))
        for i, item in enumerate(value): _value(item, f"{path}[{i}]", issues)
    elif isinstance(value, float) and not math.isfinite(value):
        issues.append(Issue(path, "must be finite; NaN and Infinity are not allowed"))
    elif not (value is None or isinstance(value, (str, int, float, bool))):
        issues.append(Issue(path, "must be a JSON scalar or array"))
    if isinstance(value, str) and len(value) > MAX_TEXT:
        issues.append(Issue(path, f"string must be at most {MAX_TEXT} characters"))

def _socket_ref(value: Any, path: str, issues: list[Issue]) -> None:
    if isinstance(value, bool):
        issues.append(Issue(path, "must be a non-empty string or non-negative integer"))
    elif isinstance(value, int):
        if value < 0: issues.append(Issue(path, "socket index must be non-negative"))
    elif isinstance(value, str):
        if not value or len(value) > 128: issues.append(Issue(path, "socket name must be 1..128 characters"))
    else:
        issues.append(Issue(path, "must be a non-empty string or non-negative integer"))

def validate_document(document: Any) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(document, dict): return [Issue("$", "document must be an object")]
    _check_depth(document, "$", 0, issues)
    _strict(document, {"version", "name", "nodes", "links", "interface"}, "$", issues)
    _required(document, {"version", "name", "nodes", "links"}, "$", issues)
    if document.get("version") != "1.0": issues.append(Issue("$.version", "must be supported version '1.0'"))
    if "name" in document: _text(document["name"], "$.name", issues)
    nodes = document.get("nodes")
    ids: set[str] = set()
    if not isinstance(nodes, list): issues.append(Issue("$.nodes", "must be an array")); nodes = []
    elif len(nodes) > MAX_NODES: issues.append(Issue("$.nodes", f"maximum is {MAX_NODES}"))
    for i, node in enumerate(nodes):
        p = f"$.nodes[{i}]"
        if not isinstance(node, dict): issues.append(Issue(p, "must be an object")); continue
        _strict(node, {"id", "type", "label", "name", "location", "inputs", "properties"}, p, issues)
        _required(node, {"id", "type", "location"}, p, issues)
        if isinstance(node.get("id"), str):
            node_id = node["id"]
            if node_id in RESERVED_NODE_IDS: issues.append(Issue(f"{p}.id", "reserved node id"))
            if node_id in ids: issues.append(Issue(f"{p}.id", "duplicate node id"))
            ids.add(node_id); _text(node_id, f"{p}.id", issues, max_len=64)
        elif "id" in node: issues.append(Issue(f"{p}.id", "must be a string"))
        if "type" in node: _text(node["type"], f"{p}.type", issues)
        if "label" in node and node["label"] is not None: _text(node["label"], f"{p}.label", issues)
        if "name" in node and node["name"] is not None: _text(node["name"], f"{p}.name", issues)
        loc = node.get("location")
        if not isinstance(loc, list) or len(loc) != 2 or not all(isinstance(x, (int, float)) and not isinstance(x, bool) and (not isinstance(x, float) or math.isfinite(x)) for x in loc):
            issues.append(Issue(f"{p}.location", "must be [finite number, finite number]"))
        for key in ("inputs", "properties"):
            if key in node:
                val = node[key]
                if not isinstance(val, dict): issues.append(Issue(f"{p}.{key}", "must be an object"))
                elif len(val) > 64: issues.append(Issue(f"{p}.{key}", "maximum 64 entries"))
                for sk, sv in (val.items() if isinstance(val, dict) else []):
                    if not isinstance(sk, str) or not sk or len(sk) > 128: issues.append(Issue(f"{p}.{key}", "keys must be non-empty short strings"))
                    _value(sv, f"{p}.{key}.{sk}", issues)
    links = document.get("links")
    if not isinstance(links, list): issues.append(Issue("$.links", "must be an array")); links = []
    elif len(links) > MAX_LINKS: issues.append(Issue("$.links", f"maximum is {MAX_LINKS}"))
    allowed_refs = ids | {"__group_input__", "__group_output__"}
    for i, link in enumerate(links):
        p = f"$.links[{i}]"
        if not isinstance(link, dict): issues.append(Issue(p, "must be an object")); continue
        _strict(link, {"from_node", "from_socket", "to_node", "to_socket"}, p, issues); _required(link, {"from_node", "from_socket", "to_node", "to_socket"}, p, issues)
        for key in ("from_node", "to_node"):
            value = link.get(key)
            if not isinstance(value, str) or not value or len(value) > 64: issues.append(Issue(f"{p}.{key}", "must be a non-empty node id string"))
            elif value not in allowed_refs: issues.append(Issue(f"{p}.{key}", "unknown node id"))
        for key in ("from_socket", "to_socket"): _socket_ref(link.get(key), f"{p}.{key}", issues)
    if "interface" in document:
        iface = document["interface"]
        if not isinstance(iface, dict): issues.append(Issue("$.interface", "must be an object"))
        else:
            _strict(iface, {"inputs", "outputs"}, "$.interface", issues)
            for direction in ("inputs", "outputs"):
                vals = iface.get(direction, [])
                if not isinstance(vals, list): issues.append(Issue(f"$.interface.{direction}", "must be an array")); continue
                if len(vals) > MAX_INTERFACE_ITEMS: issues.append(Issue(f"$.interface.{direction}", f"maximum is {MAX_INTERFACE_ITEMS}"))
                for j, sock in enumerate(vals):
                    p=f"$.interface.{direction}[{j}]"
                    if not isinstance(sock, dict): issues.append(Issue(p,"must be an object")); continue
                    _strict(sock,{"id","name","socket_type","default"},p,issues); _required(sock,{"id","name","socket_type"},p,issues)
                    for k in ("id","name","socket_type"):
                        if k in sock: _text(sock[k],f"{p}.{k}",issues)
                    if "default" in sock: _value(sock["default"], f"{p}.default", issues)
    return issues

def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-standard JSON constant {value!r} is not allowed")

def parse_and_validate(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text) > 2_000_000: raise DocumentError([Issue("$", "JSON text too large")])
    try: value = json.loads(text, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError) as exc: raise DocumentError([Issue("$", f"invalid JSON: {exc}")]) from exc
    issues = validate_document(value)
    if issues: raise DocumentError(issues)
    return value
