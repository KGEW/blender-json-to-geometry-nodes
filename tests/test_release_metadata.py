import importlib
import tomllib
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_0bsd_license_and_manifest_are_release_ready():
    manifest = tomllib.loads((ROOT / "blender_manifest.toml").read_text(encoding="utf-8"))
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert manifest["version"] == "0.6.0"
    assert manifest["license"] == ["SPDX:0BSD"]
    assert manifest["maintainer"] == "KGEW"
    assert license_text.startswith("BSD Zero Clause License\n")
    assert "Permission to use, copy, modify, and/or distribute this software" in license_text
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in license_text
    assert "YEAR" not in license_text and "AUTHOR EMAIL" not in license_text


def test_source_version_matches_manifest():
    package = importlib.import_module("blender_json_gn")
    manifest = tomllib.loads((ROOT / "blender_manifest.toml").read_text(encoding="utf-8"))
    assert package.__version__ == manifest["version"] == "0.6.0"
    assert package.bl_info["version"] == (0, 6, 0)
    assert package.bl_info["author"] == "KGEW"


def test_packager_includes_root_license_in_new_version_zip():
    package_script = (ROOT / "tools" / "package.py").read_text(encoding="utf-8")
    assert "blender_json_geometry_nodes-0.6.0.zip" in package_script
    assert "(root/'LICENSE', 'LICENSE')" in package_script
