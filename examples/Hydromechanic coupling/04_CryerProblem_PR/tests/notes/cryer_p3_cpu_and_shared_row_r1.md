# Cryer 三轮压力更新的 CPU 短测与共享算术

本次使用 ν=0.3 的三维球体，37,173 个土体粒子和 8 个远端固定粒子。私有 CPU 程序沿用既有 Cryer 的 XYZ 核梯度、压力残差、球面围压、固定格点排水和 HG0。压力每步做三轮缺陷修正，位移、应力、J 与压力历史每步只提交一次。

## CPU 运行

VS2022 的 DebugCPU 方案在独立目录编译 86 个源文件。C02 模板有三处 HG 历史计数按 HG 开启设置，移植到 Cryer 后改为要求 HG0 计数为零；原有的每端点、每土粒 7 项只读位检查保留。两次构建的日志及程序分别留存，物理短测只启动一次。

步长为 1.9073486328125 μs，旧有限 Kw 参考采用 0.95367431640625 μs。64 步实际到达 0.0001220703125 s，围压仍在爬升。真实 Popen 和 Win32 退出值均为 0。64 次提交、192 次压力写回及 49,960,512 次只读字段检查通过，五个限步阶段各执行 64 次。观察到的最紧约束为水力限步 2.97876943365607 μs；骨架波速与人工黏性约束最小值为 25.1356224978 μs，原有限 Kw 波速参考最小值为 1.59412571992 μs。CPU Debug 求解循环耗时 589.94 s。

| 末步端点 | 压力最小值 Pa | 压力最大值 Pa | 本轮压力修正 RMS Pa | 离散残差 RMS，Pa/(m·s) |
|---|---:|---:|---:|---:|
| 1 | 309.11545 | 328.41037 | 1.16313 | 3.68715 |
| 2 | 309.92520 | 330.55157 | 1.16078 | 3.69587 |
| 3 | 310.69739 | 332.69128 | 1.16223 | 3.70343 |

末步三轮都实际改变了压力，残差 RMS 小幅上升。本检查证明三轮实现执行了规定更新，压力方程迭代收敛、开排水后的峰值及相位仍需各自检验。两帧侧车中初态和末轮的 37,173 个材料 ID 对齐后，float 孔压和 double J 与各自 BI4 逐位相同。此项复核只访问原生 Idp、PorePress、PoroVolumeRatio 的粒子数据。

## 可复用的行算术

`tests/support/TpiPressureRow.h` 提供线性/当前压力预测和一次 beta=0 的端点更新。线性预测采用

\[
 q^{(0)}=\operatorname{float32}\bigl(p_n+\tfrac12(p_n-p_{n-1})\bigr).
\]

每轮使用带有上一轮真实边界处理的场重新求残差。对未排水接收粒子，

\[
 q^{(i+1)}=\operatorname{float32}\bigl(q^{(i)}+R_\gamma(q^{(i)})/S\bigr).
\]

算术在 double 中执行，写回使用 round-to-nearest 的 float。排水行优先返回正零，未排水行要求有限且正的 S。当前压力预测不读历史差。行函数无历史写入，校验完整个材料集合后，原驱动才做 `previous[id]=pn[id]` 并提交本步。

主机与 CUDA 各自用 226,038 条真实记录回放。样本含 C02 的 2 s 窗末态三轮，每轮 1,000 个土粒、10 个真实排水接收点，以及 Cryer CPU 和 GPU 的 64 步末态三轮、每轮 37,173 个土粒。存盘预测 double、力学半步 float、端点压力 float 均逐位复现；九项溢出、无效行、边界优先级和舍入等边界测试也在两个后端通过。所有真实样本的三轮共用同一组 pn、previous 和半步压力，后两轮均读取各自前一轮的真实边界写回值。

固定材料 ID 在粒子排序后保持历史归属。C02 的既有组件有周期副本、排序、重复 ID、ID 缺失和角色变化的独立样例，Cryer 采用固定集合；动态退役、粒子新增和任意 PART 的完整历史恢复仍待开发。共享头当前仅供测试；公开算法开关及整机采用须结合 benchmark 精度决定。

## 复现及归档

- `tests/support/upl_tpi_cryer_p3_cpu_r1.patch` 从 `tests/outputs/upl_tpi_cryer_cpu_overlay_r1_source/source` 重建实际使用的四个源文件。补丁已在独立副本上用 `git apply` 验证，四个文件的源文本逐行一致。
- `tests/support/upl_tpi_cryer_p3_cpu_r1.py` 记录独立构建、一次 B64 计算和检查的入口。原输入是共用的 `tests/outputs/cryer_p3_local_seed_r1/upl_cryer_freebody_short_r1`。
- `tests/support/upl_tpi_pressure_row_r1.py` 和同名 `.cu` 为共享算术组件的 `build` / `check` 入口。二者只编译和回放组件，不求解物理算例。
- 具体收据为 `tests/logs/upl_tpi_cryer_p3_cpu_B64_r1.run.json`、`.pressure_review.json`、`.native_pressure_binding.json`、`upl_tpi_cryer_p3_cpu_r1.source_patch.json` 和 `upl_tpi_cryer_pressure_row_r1.check.json`。原始三轮压力侧车、BI4、私有程序及构建目录按原路径保留。
