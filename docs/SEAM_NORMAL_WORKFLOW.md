# 合模线中文双节点组工作流

## 节点组一：重拓扑表面法向平滑

文件：`examples/retopo_surface_normal_smooth.json`

用途是先改善手工重拓扑参考模型的法向连续性，不移动顶点、不改变拓扑。中文接口：

- `几何体`：手工重拓扑参考模型；
- `平滑遮罩`：0..1，可使用常量、命名属性或顶点组；
- `平滑强度`：原法向和平滑法向的混合强度；
- `迭代次数`：Blur Attribute 的迭代次数；
- 输出 `几何体`。

节点组以 Blur Attribute（FLOAT_VECTOR）在网格邻域平滑 Normal，再按“平滑遮罩 × 平滑强度”与原 Normal 混合、归一化，并通过 Set Mesh Normal（FREE、POINT）写入点域自定义法向。POINT 域确保 Blur Attribute 在相邻顶点之间执行；工业模型传递组仍使用 CORNER 域。它只平滑法向，不执行位置 fairing，因此不会让几何曲面获得真正的 G1/G2 连续。

## 节点组二：工业模型局部法向传递

文件：`examples/industrial_model_masked_normal_transfer.json`

中文接口：

- `几何体`：最终保留的工业模型；
- `参考模型`：完成重拓扑并经过节点组一处理的对象；
- `顶点组或遮罩`：0..1 的局部影响场；
- `传递强度`：整体传递比例；
- 输出 `几何体`。

节点组使用 Relative Object Info 取得参考模型，在工业模型 Position 上由 Sample Nearest Surface 采样参考模型 Smooth Normal。`顶点组或遮罩 × 传递强度 × Is Valid` 作为混合因子，将工业模型原法线与参考法线混合、归一化，再以 Set Mesh Normal（FREE、CORNER）写入面角自定义法线。工业模型顶点位置、面数量和拓扑保持不变。

## 推荐使用顺序

1. 在重拓扑参考模型上导入 `retopo_surface_normal_smooth.json` 并勾选 Attach；
2. 用“平滑遮罩”限定需要处理的区域，调整“平滑强度”和“迭代次数”；
3. 选中工业模型，导入 `industrial_model_masked_normal_transfer.json` 并勾选 Attach；
4. 在 Modifier 中将“参考模型”指定为步骤 1 的对象；
5. 将“顶点组或遮罩”切换为工业模型上的顶点组/命名属性，合模线中心建议为 1，向外围平滑衰减到 0；
6. 调整“传递强度”。

该方案改善法线和高光连续性，不会修复真实间隙、轮廓断裂，也不是数学意义上的 G2 几何连续。硬边、不连续法线以及等距最近面选择仍可能产生跳变。

## 后续实验分支（暂不实现）

### A. 边界环自动桥接

提取两侧开放边界，统一重采样点数、匹配方向和起点，生成桥接带并局部 fairing。适合规则且一一对应的边界；难点是自动配对、扭转和严格连续性。

### B. SDF 自动融合参考面

Join Geometry → Mesh to SDF Grid → Grid to Mesh → 局部平滑。适合拓扑完全不同、小间隙或轻微相交的部件，可自动产生连续参考面；但开放面、薄壳、窄缝、小倒角会受体素化影响。

### C. 局部 G1/G2 过渡补片

只在合模线两侧生成带状补片，使用边界位置、切向与曲率条件构造过渡。它最接近工业曲面目标，但需要稳定的边界对应和约束求解，Geometry Nodes 不适合承诺严格 CAD/NURBS G2。

当前主线继续使用手工重拓扑参考面；上述分支在独立验证后再考虑合入。
