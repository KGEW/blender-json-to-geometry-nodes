from pathlib import Path
import hashlib, zipfile
root=Path(__file__).resolve().parents[1]; out=root/'dist'/'blender_json_geometry_nodes-0.6.0.zip'
include=[(root/'blender_manifest.toml', 'blender_manifest.toml'), (root/'LICENSE', 'LICENSE')]
for p in (root/'blender_json_gn').rglob('*.py'):
    include.append((p, str(p.relative_to(root/'blender_json_gn'))))
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for source, arcname in include: z.write(source, arcname)
print(out); print(hashlib.sha256(out.read_bytes()).hexdigest())
