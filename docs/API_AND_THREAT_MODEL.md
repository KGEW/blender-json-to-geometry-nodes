# API 调研与威胁模型

## 结论（Blender 5.2 优先）

Blender 4.0 起节点组接口从旧式 `tree.inputs/outputs` 迁移到 `tree.interface`；创建接口 socket 使用 `tree.interface.new_socket(name, in_out='INPUT'|'OUTPUT', socket_type='NodeSocketGeometry')`。节点使用 `tree.nodes.new(type)`；`Node.bl_idname` 是稳定的 Blender 类型标识，socket 的 `.name` 可用于人类可读引用但可能随版本/本地化变化，所以协议同时允许索引，节点连接身份始终使用 JSON node `id`。连接是 `tree.links.new(output_socket, input_socket)`。Geometry Nodes modifier 使用对象 `obj.modifiers.new(name, 'NODES')` 并设置 `node_group`。

4.x/5.2 的接口 API 是本 MVP 的边界；3.x 旧接口不支持。具体 node type 和 socket 由目标 Blender 注册表决定，导入时创建/查找失败即报错并回滚，不静默降级。

## 安全边界

不执行 JSON 中的代码；拒绝未知字段；限制 100 节点、200 links、2 MB 文本、256 字符文本、8 层嵌套和数组/属性数量。仅允许标量/短数组默认值。失败时先创建临时新树，异常路径删除该树；不更新已有树。

## Extension 打包规范

Blender Extension 的根清单固定命名为 `blender_manifest.toml`；打包脚本会把该文件放在 ZIP 根目录，且不会放入旧名 `manifest.toml`。发布前先运行官方 `blender --command extension validate`，再在隔离用户配置中运行 `extension install-file`。

## 已知限制

外部 Blender 5.2.1 已 headless 验证 `minimal.json`、`mesh_transform.json`、ZIP 代码注册、节点/link/Group Output、Modifier 和坏 socket 回滚。MVP 不做任意 RNA 反射、远程服务、AI API、复杂 merge/update。0.1.1 删除顶层 `modifier` JSON 字段；Modifier 只由 UI Attach 选项控制。Blender 3.x 和跨大版本兼容仍不支持。

## JSON 导出

UI 的 Export 只处理当前活动对象第一个 Geometry Nodes modifier 的 GeometryNodeTree，写出当前 1.0 JSON 协议。为避免把 Blender RNA 反射变成隐式协议，导出属性仅限 `operation`、`data_type`、`domain`、`mode`、`transform_space`、`input_type`、`interpolation_type`、`clamp`；无法安全表达的资源引用、复杂 RNA 值和不支持的数据块不会被猜测导出。导出的 Group Input/Output 使用协议保留 ID，重复 socket 名使用非负索引。

## 0.4.0 中文双节点组法线工作流

`examples/retopo_surface_normal_smooth.json` 用 Blur Attribute（FLOAT_VECTOR）平滑手工重拓扑参考模型法线，并通过中文“平滑遮罩/平滑强度/迭代次数”接口控制；Set Mesh Normal 以 FREE/POINT 写入点域自定义法线。`examples/industrial_model_masked_normal_transfer.json` 在相对对象空间采样“参考模型”的 Smooth Normal，通过中文“顶点组或遮罩/传递强度”接口局部混合并写入工业模型。真实 Blender 回归分别确认两组可导入执行、输出位置和拓扑不变、自定义法线存在。自动边界桥接、SDF 融合与局部 G1/G2 补片仅记录在 `SEAM_NORMAL_WORKFLOW.md`，未在主线实现。

## 0.2.0 均匀表面采样遮罩

`examples/normal_field_uniform_surface_mask_v2.json` 使用 `GeometryNodeMeshToSDFGrid` 和 `GeometryNodeGridToMesh` 构建仅用于分析的均匀代理表面，Grid to Mesh 的 Adaptivity 固定为 0。代理上的采样位置通过稳定参考轴选择构建 T/B 基，在 `Sample Nearest Surface` 中以原始 Geometry 为 Mesh、原始 `GeometryNodeInputNormal` 为 Value，执行 +T、-T、+B、-B 四个固定半径采样；四个法线距离取平均后经 Map Range 得到 0..1 mask。

mask 先存储在代理点域，再通过另一枚 `Sample Nearest Surface` 投射回原始 Geometry；`Store Named Attribute` 在原始 Geometry 的 POINT 域写入 `normal_turn_mask`，所以输出拓扑来自原始输入而不是代理。开放面、薄壳、窄缝、过细特征受 SDF 体素化/边界影响；该示例不实现 Poisson fallback，也不声称适合所有 CAD。集成测试使用同一闭合立方体三角表面及其共面四分细分版本，并为共同顶点设置相同解析式自定义平滑法线，要求共同顶点 mask 最大绝对差 < 0.01。对于硬边/不连续法线，均匀代理不能消除法线跳变；`SampleNearestSurface` 在等距最近面或顶点处有选择歧义，本功能依赖可靠的平滑法线。
