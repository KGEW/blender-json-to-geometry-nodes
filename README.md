# Blender JSON 转几何节点

一个面向 Blender 5.2+ 的中文 Extension：严格校验项目定义的 JSON 1.0 协议，并将其导入为 Geometry Nodes 节点组；也可将受支持的节点组子集导出为 JSON。

> 本项目是社区项目，与 Blender Foundation 无隶属或官方认可关系。Blender 和 Geometry Nodes 名称归其各自权利人所有。

## 功能

- 默认中文 N 侧栏、按钮、选项和通知；
- 严格 JSON 校验，错误包含稳定的 `$...` 路径；
- 导入时创建新的 `GeometryNodeTree`，可选附加到活动对象；
- 保守导出当前活动对象第一个 Geometry Nodes 修改器的节点组；
- 导入失败时清理本次创建的数据，并支持 Blender 撤销；
- 无 `eval`/`exec`、动态 Python 导入或 JSON 指定的任意文件写入。

文件选择器和 Blender 自带节点名称由 Blender/操作系统管理，可能显示当前系统语言。

## 安装

manifest 最低版本为 Blender **5.2.0**；自动化验收目标是 Blender **5.2.1 LTS**。项目面向 5.2+，但不声称已逐一验证所有后续 Blender 版本；不支持 Blender 3.x。

1. 公开发布后从 [GitHub Releases](https://github.com/KGEW/blender-json-to-geometry-nodes/releases) 获取 `blender_json_geometry_nodes-0.6.0.zip`；尚无 Release 时可在本地运行 `python3 tools/package.py` 构建；
2. 在 Blender 扩展设置中选择从磁盘安装；
3. 安装并启用该 ZIP；
4. 打开 **3D 视图 → N 侧栏 → JSON 几何节点**。

ZIP 根目录包含 `blender_manifest.toml`、`LICENSE` 和插件 Python 包内容，符合 Blender Extension 布局。

## 使用

- **验证 JSON**：检查文件是否符合 JSON 1.0 协议，不创建节点；
- **导入 JSON 几何节点**：验证并创建新的 Geometry Nodes 节点组；
- **导出活动几何节点 JSON**：导出活动对象第一个 Geometry Nodes 修改器的节点组；
- **仅验证（不创建节点）**：显示计划导入的节点和连线统计；
- **附加到活动对象**：导入后创建并绑定新的 Geometry Nodes 修改器。

导出仅覆盖协议允许的节点、接口、可表达默认值、白名单属性和连线，不是 Blender 任意节点树的无损交换格式。

## JSON 协议

权威规范见 [`GEOMETRY_NODES_JSON_SPEC.md`](GEOMETRY_NODES_JSON_SPEC.md)。协议版本仍为 `"1.0"`，本次许可证与版本变更不改变机器契约。

顶层必需字段：

```json
{
  "version": "1.0",
  "name": "Example",
  "nodes": [],
  "links": []
}
```

可选顶层字段为 `interface`。节点 `type`、socket 名及属性值必须使用目标 Blender 版本的真实 RNA/`bl_idname`，不能翻译成中文显示名。

## 示例

- `examples/minimal.json`：最小 Group Input → Group Output；
- `examples/mesh_transform.json`：Cube、Transform、Set Material；
- `examples/retopo_surface_normal_smooth.json`：重拓扑表面法向平滑；
- `examples/industrial_model_masked_normal_transfer.json`：工业模型局部法向传递；
- `examples/normal_field_uniform_surface_mask_v2.json`：均匀代理法向场分析；
- `examples/retopo_poisson_point_mask_proxy.json`：重拓扑表面 Poisson 点云代理。

更多工作流说明位于 [`docs/`](docs/)。

## 开发与验证

```bash
pytest -q
python3 tools/package.py
BLENDER_BIN=/path/to/blender sh tools/extension_acceptance.sh
```

`tools/extension_acceptance.sh` 会依次执行官方 `extension validate`、隔离的 `extension install-file -e`、扩展启用检查，以及真实 headless 导入/导出和几何回归；脚本同时要求成功 marker 且拒绝 `Traceback`。

生成缓存、本机配置、`.blend` 文件和 `dist/` 构建产物由 `.gitignore` 排除。

## 安全边界

解析层只使用 `json.loads`。未知字段、未知节点、socket 和属性会被拒绝；节点数、连线数、文本长度、数组长度和嵌套深度均有限制。JSON 文件选择由 Blender UI 完成，导入器本身不接受 JSON 指定的输出路径。

完整威胁模型见 [`docs/API_AND_THREAT_MODEL.md`](docs/API_AND_THREAT_MODEL.md)。

## 许可证

本项目按 [0BSD](LICENSE) 授权。自 0.6.0 起，仓库当前发布内容使用 0BSD；项目权利人已确认其拥有重授权权利，并确认此前版本中的本项目源码一并按 0BSD 重新授权。

旧的本地构建 ZIP 可能仍保留生成时的历史许可证元数据，不应作为当前 0BSD 发布包；请使用 0.6.0 或更高版本的新包。
