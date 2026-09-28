#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BLENDER=${BLENDER_BIN:-blender}
ZIP="$ROOT/dist/blender_json_geometry_nodes-0.6.0.zip"
TMP_HOME=$(mktemp -d)
trap 'rm -rf "$TMP_HOME"' EXIT
export HOME="$TMP_HOME"
export XDG_CONFIG_HOME="$TMP_HOME/config"

run_checked() {
    label=$1
    marker=$2
    shift 2
    log="$TMP_HOME/$label.log"
    set +e
    "$@" >"$log" 2>&1
    status=$?
    set -e
    cat "$log"
    if [ "$status" -ne 0 ]; then
        echo "${label}: non-zero exit $status" >&2
        exit "$status"
    fi
    if grep -Fq "Traceback" "$log"; then
        echo "${label}: Traceback found" >&2
        exit 1
    fi
    if ! grep -Fq "$marker" "$log"; then
        echo "${label}: missing marker $marker" >&2
        exit 1
    fi
}

# Official validation is deliberately the first acceptance action.
run_checked validate "Success parsing TOML" "$BLENDER" --command extension validate "$ZIP"
run_checked install "STATUS Installed \"blender_json_geometry_nodes\"" "$BLENDER" --command extension install-file -r user_default -e "$ZIP"
run_checked enable "BLENDER_EXTENSION_ENABLE_SUCCESS" "$BLENDER" -b --python-expr "import importlib,bpy; m=importlib.import_module('bl_ext.user_default.blender_json_geometry_nodes'); ui=importlib.import_module('bl_ext.user_default.blender_json_geometry_nodes.blender_ui'); assert hasattr(bpy.ops.json_gn,'import_document'); assert hasattr(bpy.ops.json_gn,'export_document'); assert 'bl_ext.user_default.blender_json_geometry_nodes' in bpy.context.preferences.addons; assert m.__version__=='0.6.0'; assert ui.JSONGN_PT_panel.bl_label=='JSON 几何节点'; assert ui.JSONGN_OT_validate.bl_label=='验证 JSON'; assert bpy.types.Scene.bl_rna.properties['json_gn_dry_run'].name=='仅验证（不创建节点）'; assert bpy.types.Scene.bl_rna.properties['json_gn_attach'].name=='附加到活动对象'; print('BLENDER_EXTENSION_ENABLE_SUCCESS')"
run_checked integration "BLENDER_JSON_GN_INSTALLED_V2_SUCCESS" env JSON_GN_REQUIRE_INSTALLED=1 "$BLENDER" -b --python "$ROOT/tools/blender_headless_integration.py"
for marker in BLENDER_JSON_GN_INTEGRATION_SUCCESS BLENDER_JSON_GN_INSTALLED_DUAL_NORMAL_SUCCESS BLENDER_JSON_GN_CHINESE_UI_SUCCESS; do
    if ! grep -Fq "$marker" "$TMP_HOME/integration.log"; then
        echo "integration: missing marker $marker" >&2
        exit 1
    fi
done
