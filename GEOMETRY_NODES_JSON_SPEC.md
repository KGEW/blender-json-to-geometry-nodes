# Blender JSON Geometry Nodes 生成规范

**规范版本：1.0（对应插件 0.6.0）**
**目标 Blender：5.2.1 LTS**  
**用途：约束 AI 生成可由本项目插件安全校验并导入的 Geometry Nodes JSON。**

> 本文是后续 AI 生成 JSON 时必须遵守的项目契约。它不是 Blender 官方交换格式。
>
> 0.5.0 仅汉化插件用户界面和通知；`version`、所有 schema key、节点 `bl_idname`、socket 名、操作符 ID、类名、结构化错误路径及文件格式均保持原机器契约，不得翻译序列化值。

## 1. 权威来源与优先级

生成或审查 JSON 时，按以下顺序判断：

1. 插件运行时实现：`blender_json_gn/core/validation.py` 与 `blender_json_gn/blender/importer.py`；
2. 本文定义的保守、已验证子集；
3. 机器可读 Schema：`blender_json_gn/schema/geometry_nodes_v1.json`；
4. 目标 Blender **同版本源码和运行时 RNA**。

若文档、Schema、AI 记忆与实际代码冲突，必须停止生成并核对实现；不得猜测。顶层 `nodes` 最多 100 项、`links` 最多 200 项；接口 socket 数组和普通值数组最多 32 项。嵌套深度仍最多 8 层。

核对时应使用目标 Blender 5.2.1 的官方源码 checkout 或同版本运行时 RNA。源码 checkout 中的关键位置：

```text
source/blender/nodes/geometry/nodes/
source/blender/makesrna/intern/rna_nodetree.cc
source/blender/makesdna/DNA_node_types.h
```

节点注册名必须在源码的 `geo_node_type_base(...)` 或 Blender 5.2.1 运行时 RNA 中确认；socket 必须在节点声明的 `add_input<...>()` / `add_output<...>()` 中确认。不得把中文界面名、搜索菜单名称或其他 Blender 版本的名称当成依据。

## 2. AI 输出硬性要求

AI 必须：

- 只输出一个严格 JSON 对象；
- 不输出 Markdown 代码围栏、解释、注释或 JSON5；
- 使用 UTF-8；
- 使用 `version: "1.0"`；
- 使用 Blender 5.2.1 的真实节点 `bl_idname`；
- 使用唯一、稳定、非空的节点 `id` 建立连线；
- 使用源码确认过的英文 socket 名称，或确认过的非负整数索引；
- 确保连线方向为 output → input，且 socket 数据类型兼容；
- 确保最终几何链连接到 `__group_output__`；
- 只设置经 Blender 5.2.1 RNA/源码确认可写且 JSON 值可表达的属性；
- 在提交前按本文检查清单自检。

AI 禁止：

- 输出 `NaN`、`Infinity`、`-Infinity`；
- 输出 Python、表达式、驱动、`eval`/`exec` 或导入指令；
- 猜测节点类型、socket、枚举值或属性；
- 使用 `__group_input__`、`__group_output__` 作为普通节点 ID；
- 使用负数或布尔值作为 socket 索引；
- 添加本规范未定义的字段；
- 假设复杂 Blender 数据块引用可直接用字符串赋值；
- 生成当前规范没有表达能力的模拟区域、重复区域、嵌套节点组、动态 socket 拓扑或资源解析逻辑。

## 3. 顶层对象

```json
{
  "version": "1.0",
  "name": "AI Generated Geometry",
  "interface": {"inputs": [], "outputs": []},
  "nodes": [],
  "links": []
}
```

必填字段：

| 字段 | 类型 | 规则 |
|---|---|---|
| `version` | string | 必须是 `"1.0"` |
| `name` | string | 1–256 字符，作为新建节点组名称 |
| `nodes` | array | 最多 100 项 |
| `links` | array | 最多 200 项 |

可选字段 `interface` 仅允许 `inputs`、`outputs`。顶层 `additionalProperties=false`。插件 0.6.0 不接受顶层 `modifier`；Modifier 只能通过 UI 的 **附加到活动对象** 选项创建。

## 4. 节点定义

```json
{
  "id": "transform",
  "type": "GeometryNodeTransform",
  "label": "Transform",
  "location": [-200, 0],
  "inputs": {"Translation": [0.0, 0.0, 1.0]},
  "properties": {}
}
```

| 字段 | 必填 | 规则 |
|---|---:|---|
| `id` | 是 | 1–64 字符；文档内唯一；不能是保留 ID |
| `type` | 是 | 1–256 字符；必须是 Blender 5.2.1 可用于 GeometryNodeTree 的真实 `bl_idname` |
| `location` | 是 | 两个有限数字 `[x, y]`；布尔值不算数字 |
| `label` | 否 | 非空，最多 256 字符 |
| `name` | 否 | 当前导入器最终以 `id` 设置 Blender node name；不得依赖该字段改变节点身份 |
| `inputs` | 否 | 最多 64 个键；设置输入 socket 默认值 |
| `properties` | 否 | 最多 64 个键；设置经源码/RNA 确认的节点属性 |

普通节点不得使用 `__group_input__` 或 `__group_output__`。

`inputs` 推荐以源码中的英文 socket 名为键：

```json
"inputs": {"Size": [2.0, 2.0, 2.0], "Vertices X": 2}
```

普通值仅允许 JSON 标量或数组，不允许对象。数组不超过 32 项，嵌套深度不超过运行时限制 8；字符串不超过 256 字符；浮点数必须有限。

若 socket 名重复或随模式动态变化，必须改用 Blender 5.2.1 中确认过的索引，或者判定当前规范无法稳定表达，不得猜测。

## 5. 节点组接口

```json
"interface": {
  "inputs": [{"id": "geometry_in", "name": "Geometry", "socket_type": "NodeSocketGeometry"}],
  "outputs": [{"id": "geometry_out", "name": "Geometry", "socket_type": "NodeSocketGeometry"}]
}
```

每个接口 socket 必须包含：

- `id`：非空标识；当前 1.0 导入器不使用它解析 links，仅用于文档身份；
- `name`：Blender 中显示并用于名称连线的 socket 名；
- `socket_type`：Blender 的真实 socket 类型；
- `default`：可选，必须能赋给该接口 socket。

常见类型：`NodeSocketGeometry`、`NodeSocketFloat`、`NodeSocketInt`、`NodeSocketBool`、`NodeSocketVector`、`NodeSocketColor`、`NodeSocketString`、`NodeSocketObject`、`NodeSocketMaterial`。类型和默认值必须以 Blender 5.2.1 为准。

## 6. 连线定义

```json
{
  "from_node": "cube",
  "from_socket": "Mesh",
  "to_node": "transform",
  "to_socket": "Geometry"
}
```

四个字段全部必填且不允许额外字段：

- `from_node`、`to_node`：非空节点 ID 字符串；
- `from_socket`、`to_socket`：非空英文 socket 名称，或从 0 开始的非负整数索引；
- `from_socket` 必须属于输出集合，`to_socket` 必须属于输入集合；
- 两端必须能由 Blender `tree.links.new(output, input)` 连接。

优先使用源码确认过的名称。只有名称重复、动态变化或明确需要时才使用索引。

## 7. Group Input / Group Output

插件自动创建两个节点，不得放进 `nodes`：

```text
__group_input__
__group_output__
```

它们只能在 links 中引用：

```json
{
  "from_node": "__group_input__",
  "from_socket": "Geometry",
  "to_node": "__group_output__",
  "to_socket": "Geometry"
}
```

期望产生几何结果时，最终链路必须到达 `__group_output__` 的 Geometry 输入；仅创建未接到输出的节点不算完成。

## 8. Blender 5.2.1 源码核对示例

### Mesh Cube

```text
source/blender/nodes/geometry/nodes/node_geo_mesh_primitive_cube.cc
bl_idname: GeometryNodeMeshCube
inputs: Size, Vertices X, Vertices Y, Vertices Z
outputs: Mesh, UV Map
```

`Size` 是 Vector，必须写 `[2.0, 2.0, 2.0]`，不能写标量 `2.0`。

### Transform Geometry

```text
source/blender/nodes/geometry/nodes/node_geo_transform_geometry.cc
bl_idname: GeometryNodeTransform
inputs: Geometry, Mode, Translation, Rotation, Scale, Transform
output: Geometry
```

### Set Material

```text
source/blender/nodes/geometry/nodes/node_geo_set_material.cc
bl_idname: GeometryNodeSetMaterial
inputs: Geometry, Selection, Material
output: Geometry
```

注册名还可在 `source/blender/makesrna/intern/rna_nodetree.cc` 交叉确认。

## 9. 已验证完整示例

```json
{
  "version": "1.0",
  "name": "Anonymous Mesh Transform",
  "interface": {
    "inputs": [{"id": "geometry_in", "name": "Geometry", "socket_type": "NodeSocketGeometry"}],
    "outputs": [{"id": "geometry_out", "name": "Geometry", "socket_type": "NodeSocketGeometry"}]
  },
  "nodes": [
    {"id": "cube", "type": "GeometryNodeMeshCube", "label": "Cube", "location": [-500, 0], "inputs": {"Size": [2.0, 2.0, 2.0]}},
    {"id": "transform", "type": "GeometryNodeTransform", "location": [-200, 0], "inputs": {"Translation": [0.0, 0.0, 1.0]}},
    {"id": "set_material", "type": "GeometryNodeSetMaterial", "location": [100, 0]}
  ],
  "links": [
    {"from_node": "cube", "from_socket": "Mesh", "to_node": "transform", "to_socket": "Geometry"},
    {"from_node": "transform", "from_socket": "Geometry", "to_node": "set_material", "to_socket": "Geometry"},
    {"from_node": "set_material", "from_socket": "Geometry", "to_node": "__group_output__", "to_socket": "Geometry"}
  ]
}
```

对应项目文件 `examples/mesh_transform.json` 已在 Blender 5.2.1 中验证为 5 个节点（含自动 Group Input/Output）、3 条连线，并连接到 Group Output。

## 10. 0.2.0 正式示例：均匀表面采样法线变化遮罩

`examples/normal_field_uniform_surface_mask_v2.json` 是本项目 0.2.0 的正式可导入示例。它使用 `GeometryNodeMeshToSDFGrid` → `GeometryNodeGridToMesh` 创建只用于分析的均匀代理表面，Voxel Size 为组输入，Grid to Mesh 的 Adaptivity 为 0；原始网格通过 `GeometryNodeInputNormal` 提供 Smooth Normal，并由 `GeometryNodeSampleNearestSurface` 在代理位置采样。代理上使用稳定参考轴构建 T/B，按 +T、-T、+B、-B 四个方向采样，四个法线距离取平均而非 Maximum。mask 先存储在代理点域，再用 `SampleNearestSurface` 投射回原始网格；最终 `StoreNamedAttribute` 在原始点域写入 `normal_turn_mask`，Group Output 的 Geometry 保持原始拓扑。

该纯 Geometry Nodes/SDF 方法对开放面、薄壳、窄缝和过细 CAD 特征存在体素边界限制；示例不实现 Poisson fallback 或 Poisson 多邻点插值，也不保证适合所有 CAD 模型。集成回归使用同一闭合立方体三角表面的共面四分细分版本和相同解析式自定义平滑法线，比较共同空间顶点并要求 mask 最大绝对差 < 0.01。对于硬边或不连续法线，均匀代理不能消除法线跳变；`SampleNearestSurface` 在等距最近面/顶点处存在选择歧义，因此本示例前提是可靠的平滑法线。

## 11. 0.4.0 正式示例：中文双节点组法线工作流

`examples/retopo_surface_normal_smooth.json` 用 `GeometryNodeBlurAttribute` 的 FLOAT_VECTOR 模式平滑手工重拓扑参考模型的 Normal，并通过中文接口“平滑遮罩”“平滑强度”“迭代次数”限制效果，最后由 `GeometryNodeSetMeshNormal` 的 FREE/POINT 模式写入点域自定义法线；POINT 域也确保 Blur Attribute 在网格顶点邻域实际执行。

`examples/industrial_model_masked_normal_transfer.json` 以中文接口“参考模型”“顶点组或遮罩”“传递强度”控制工业模型局部法线传递。Object Info 使用 RELATIVE 空间；Sample Nearest Surface 在工业模型 Position 上采样参考模型 Smooth Normal，遮罩、强度与 Is Valid 共同控制混合，输出保留工业模型位置和拓扑。参考对象必须由用户在 Modifier 中设置；JSON 不保存对象数据块引用。

这两个节点组只改善法线和高光连续性，不会修复真实间隙或获得数学意义上的 G2 几何连续。自动边界桥接、SDF 融合参考面和局部 G1/G2 补片仅作为 `docs/SEAM_NORMAL_WORKFLOW.md` 中记录的后续实验分支。

## 12. 当前 1.0 不支持或不保证

- Blender 3.x及跨 Blender 大版本自动兼容；
- 修改、合并或覆盖已有节点组；
- 按名称解析 Material/Object/Collection/Image 等复杂数据块引用；
- 嵌套节点组的创建与引用；
- Simulation、Repeat、Foreach 等成对 Zone 节点拓扑；
- 动态 socket、菜单驱动 socket 和依赖模式切换的完整表达；
- 节点 UI 展开状态、颜色、父 Frame、宽度等布局细节；
- 自动判断几何语义是否符合创作意图。

遇到上述需求时必须先扩展 Schema、验证器、导入器和测试，再生成 JSON；不得私自编码。

## 13. AI 生成前检查清单

1. 目标是否明确为 Blender 5.2.1？
2. 每个 `type` 是否在同版本源码/RNA 中确认？
3. 每个 socket 的英文名、方向、类型是否确认？
4. Vector/Rotation/Color 等值是否使用正确长度和类型？
5. 节点 ID 是否唯一且未占用保留 ID？
6. 所有 link 是否 output → input，且端点存在、类型兼容？
7. 结果链是否到达 `__group_output__`？
8. 是否仅使用允许字段和严格 JSON 数值？
9. `nodes`/`links` 是否分别不超过 100/200 项？
10. 接口 socket 数组和普通值数组是否不超过 32 项？
11. 是否避免当前规范不支持的 Zone、嵌套组和资源引用？
12. 是否先通过插件 Validate，再在目标 Blender 中实测 Import？

## 14. 可直接提供给 AI 的约束提示词

```text
请严格按照项目 GEOMETRY_NODES_JSON_SPEC.md 生成 Blender Geometry Nodes JSON 1.0，并同时核对目标 Blender 5.2.1 源码/RNA。节点 type 必须是真实 bl_idname；socket 名称、方向、类型和节点属性不得猜测。只输出一个严格 JSON 对象，不要 Markdown、解释或注释。使用唯一节点 id，Group Input/Output 仅通过 __group_input__ / __group_output__ 引用，最终几何链必须连接到 Group Output。不得输出 NaN/Infinity、额外字段、Python、动态代码或当前规范不支持的结构。生成后逐项执行规范中的检查清单。
```
