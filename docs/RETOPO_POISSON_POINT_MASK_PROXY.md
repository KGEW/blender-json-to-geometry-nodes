# 重拓扑表面采样点蒙版代理

JSON：`examples/retopo_poisson_point_mask_proxy.json`

本节点组只在重拓扑模型表面生成 Poisson Disk 点云，不修改工业模型，也不修改输入网格数据。节点组的几何输出是点云，因此建议应用在重拓扑模型的副本或专用分析对象上；作为 Modifier 使用时，评估后的几何将显示为采样点代理，而不是原重拓扑网格。

## 中文接口

- `几何体`：手工重拓扑模型；
- `锐边顶点组`、`锐边阈值`：只有两个端点都超过阈值的边会成为连续锐边；
- `采样点最小距离`：Poisson Disk 点间最小距离；
- `最大点密度`：候选点密度上限，必须足够高才能填满目标点距；
- `随机种子`；
- `扩散距离`；
- `蒙版属性名称`：默认 `sharp_edge_point_mask`；
- `法向属性名称`：默认 `proxy_sample_normal`；
- `点显示半径`；
- 输出 `采样点代理` 和 `蒙版`。

## 节点流程

1. Mesh Edge Vertices 与两个 Evaluate at Index 读取边两端的顶点组权重；
2. Separate Geometry 提取连续锐边；
3. Distribute Points on Faces 使用 POISSON 模式生成均匀点云；
4. Geometry Proximity 直接计算每个点到连续锐边段的欧氏距离；
5. Smootherstep 将距离转换为 1→0 蒙版；
6. Sample Nearest Surface 从重拓扑表面采样 Smooth Normal；
7. 在点云 POINT 域存储蒙版和参考法线属性。

真实 Blender 5.2.1 回归在 4×4 单位面积格组成的平面上，以最小点距 0.2 生成 256 个点；实测最小点距 0.200041，蒙版范围 0..1，点法线 Z 分量全部大于 0.99。

## 密度建议

为了让扩散蒙版看起来接近连续渐变，建议：

`采样点最小距离 ≤ 扩散距离 / 10`

如果准备使用最近点方式向工业模型传递，建议进一步提高到扩散距离的 1/15～1/20。`最大点密度`过低会阻止 Poisson 分布填满目标密度；大模型和很小点距会显著增加点数。

## 重要限制

- 这是到锐边的三维欧氏距离，不是表面测地距离，薄壳或邻近表面可能发生跨层影响；
- 点云没有边和面，不能执行 Shortest Edge Paths；
- 现有 `industrial_model_masked_normal_transfer.json` 使用 Sample Nearest Surface 读取网格，不能直接读取该点云；
- 工业模型若通过最近点索引读取点云属性，会产生微小 Voronoi 分区，点距越小越不明显；
- 若需要多邻点加权、体积插值或纹理烘焙，需要另建专门传递方案。
