# CPU 正式 Vel0：double 孔压状态迁移复核

日期：2026-09-09。完成本轮第 1、2 项：正式边界四组短测、区分迁移差与步长敏感性。因原始采样在刚排水窗口无共同时间帧，另完成四组 30 ms 的输出采样诊断。

## 结论

当前 double 孔压状态与保留高低位补丁的差异明显小于减半时间步造成的差异，孔压、沉降总体历史基本重合。证据支持“状态替换造成的短程数值影响很小”，不支持“完整固结精度已经提高”或“所有迁移验收已通过”。

- 原 0.2 s 比较仍未通过此前 RMS 0.01 Pa / 最大 0.1 Pa 的严格压力审查线，不能因为相对步长差较小就悄悄放宽标准。
- 0--30 ms 事件补测中，减半步长最大孔压差约 49.6 Pa，而状态迁移最大差约 0.0028 Pa；初始加载/刚排水阶段的步长敏感性远大于状态表示差异。
- 本轮未修改求解器、物理方程、积分或边界；未扩大 double 孔压率/空间算子范围；未运行完整 2Tv，未做有效效率验收，未提交或推送 Git。

建议先冻结当前 double 状态版本、确认可接受的迁移容差，再进入同参数完整 2Tv 回归。不建议为追求浮点逐位重现重新引入生产高低位兼容分支；进一步扩大 double 范围仍应单独分阶段。

## 输入、版本和完整性

算例为 `02_TerzaghiConsolidation_q0_PR` 的正式 full_k1em4：k=1e-4 m/s，q0=10000 Pa，Kw=2e8 Pa，n=0.3，dp=0.01 m，H=1 m；CPU 4 线程、Stable、Symplectic、正式 `-mdbc`=Vel0，周期 X，Shepard 关闭，PairDivergence / KernelGradient，mDBC 孔压 ZeroOrder。加载至 0.01 s，FreeSurface 排水起始参数为 0.01 s。

新旧同 dt 使用同一个派生 XML。物理内容与正式 precision Def 核对一致；只更改 DtIni、DtFixed、TimeMax、TimeOut，移除旧 timeout 覆盖块（如有）。没有在正式 XML 的 special 中重复添加 timeout。

| 组别 | 每个版本的 dt | 每个版本步数 | 每组输出帧 | 结果 |
|---|---|---|---|---|
| 原四组，0--0.2 s | 10 / 5 us | 20000 / 40000 | 201 | 全部正常结束 |
| 事件四组，0--0.03 s | 10 / 5 us | 3000 / 6000 | 61 | 全部正常结束 |

八组均 0 粒子排除、0 DtMin 调整。参考孔压/FSType 的同 dt 迁移比较均一致。原生字段类型、ID、有限值、初始顶部粒子集合均经过检查。

版本来源：

- 基线不是 Git HEAD，而是此前归档的高低位补丁 CPU Release；SHA256 `A2CD2B1023F6487EAC3F7D7185F02175494FE680B238C558C478B71E29B6EFF6`。
- 当前 Stage 1 double 状态 CPU Release；SHA256 `95683EA87702A50CC8246B7C32C7DE9C2B203435985A373378A6FCDDA7347DBD`。
- 本轮前后检查上一阶段 manifest 的 23 项源文件记录，全部一致；原输入与两份 Release 程序哈希未变。
- 默认 CPU Debug 增量构建通过，日志 `tests/logs/pore_double_vel0/cpu_debug_check.log`。Debug 可执行文件 SHA256 仍为 `41EAC47CA6427D27999F0CDA1D4D88E72A9B6251E572A40C7231C662F770E233`，未重写生产程序内容。

## 比较口径

土体指标使用 ID 40--1039 的 1000 个土粒子；40 个底部边界不计入土孔压 RMS。旧孔压按 double(high)+double(residual) 重构，新状态直接读取 double，不能拿旧输出高位当完整基线。

沉降使用初始顶部固定 10 个 ID：139、239、339、439、539、639、739、839、939、1039，计算 mean(z0-z)。Part0 保存位置为 float，后续帧因统一的 `-svextraparts:1` 保存 Posd double。初始输出原点误差是共同项，在版本/步长沉降差中抵消；绝对沉降仍以该保存原点定义。不以 VTK float 位置比较微小沉降差。

按 BI4 实际时间匹配，容差 1e-11 s，不插值、不直接将不同实际时刻的同 PART 相减。时间窗口以实测时间和该舍入容差分组；0.01 s 图示为参数规定时刻，不保证该帧已执行排水。

## 0--0.2 s：迁移差和步长差

下表前两行使用完整 201 帧；后两行只使用四组共有的 85 帧，不能直接将这两种时间集合的 RMS 比值当成公平比值。

| 比较 | 时刻数 | 土孔压 RMS 差 Pa | 土孔压最大绝对差 Pa | 固定顶部沉降最大绝对差 mm |
|---|---:|---:|---:|---:|
| double−高低位，10 us | 201 | 0.0426605 | 0.196328 | 3.50075e-7 |
| double−高低位，5 us | 201 | 0.0210963 | 0.169042 | 7.51358e-7 |
| 高低位，5−10 us | 85 | 2.621662 | 11.578987 | 1.35052e-4 |
| double，5−10 us | 85 | 2.620177 | 11.559130 | 1.35754e-4 |

将迁移差也限制到相同 85 帧后，10 / 5 us 的 RMS 分别为 0.05934594 / 0.03062161 Pa，约为对应步长差的 2.26% / 1.17%。这说明量级较小，不是相对真实解的误差百分比。

10 us 的最大迁移孔压差位于 t≈0.146 s、ID241；5 us 位于 t≈0.196 s、ID138。最大沉降迁移差分别约 0.350 / 0.751 nm。新旧同 dt 的参考孔压位差和 FSType 差均为 0。

终点平均孔压 / 固定顶部沉降：

| 版本与 dt | 孔压 Pa | 沉降 mm |
|---|---:|---:|
| 高低位 10 us | 9186.064533 | 0.405795915 |
| double 10 us | 9186.116860 | 0.405796048 |
| 高低位 5 us | 9184.690075 | 0.405660863 |
| double 5 us | 9184.705229 | 0.405660294 |

原始跨步长采样排除了 116 个不匹配时刻；尤其 (0.01,0.03] s 没有共同帧。原图已在缺口处断线，不能凭连接缺口的曲线判断刚排水阶段。

## 0--30 ms：补齐事件窗口

补测独立保存为 `_event`，TimeOut=0.00049999 s，使输出截止阈值略早于共同 500 us 步点。只改测试采样，没有调整求解器积分或排水生效逻辑。实际得到 61 个共同时间帧，最大时间差 4.91e-15 s，0 帧排除；加载窗口 21 帧、10--30 ms 窗口 40 帧。

| 比较，61 个共同帧 | 土孔压 RMS 差 Pa | 最大绝对差 Pa | 固定顶部沉降最大绝对差 mm |
|---|---:|---:|---:|
| 迁移，10 us | 1.88962e-10 | 1.08230e-9 | 0 |
| 迁移，5 us | 2.75464e-4 | 0.00278785 | 6.33819e-9 |
| 高低位步长减半 | 5.802743 | 49.616072 | 6.12412e-4 |
| double 步长减半 | 5.802706 | 49.616072 | 6.12412e-4 |

步长差峰值在 t≈0.0115 s、ID438。加载窗口步长 RMS 约 2.754 Pa，刚排水窗口约 6.883 Pa，两版本几乎相同。该差包括积分和事件离散等步长敏感性，尚未将二者分离，不能当成绝对精度误差或全部归咎于排水阈值。

补测与原运行的同版本、同 dt 在共有时刻的全部物理字段逐位一致。覆盖限制必须保留：10 us 各只有 5 个共同帧，覆盖到 0.004 s；5 us 各有 16 个共同帧，覆盖到 0.03 s。因此不能声称 coarse 组排水后所有时刻的轨迹已逐位验证。

## 对差异来源能说明什么

- 10 us 的完整输出中，重构压力从首个非零输出已有极微小差；float 压力投影与位置/速度/应力首次同时出现输出可见差异是在 0.06 s，而非 0.01 s 刚开启排水时。
- 已存 201 帧的 1000 个土粒子中，基线 `stored_high` 与 `float(high+low)` 没有出现不一致。此前理论中点例子不能直接当成本算例根因；保存帧未出现，也不能排除步内发生。
- 同 dt 使用同一 XML、相同边界、程序来源可追溯，因此这些量级是状态迁移相关的数值差；还没有定位到具体一次舍入/写回/力计算，不能声称精确根因已经证明。
- 从本轮量级看，时间步敏感性比状态表示变化更值得优先关注。没有证据要求立刻将整个 u-pw 体系扩大为 double，也没有证据表明长期孔压平台已改善。

## 验证与图片

独立脚本未调用主分析函数，使用另一套 CSV 读取、时间交集、求和实现：原四组 5471 项检查、事件补测 2139 项检查全部通过。BI4 读取器另外完成旧 float / 高低位 / 新 double / 分片格式 20 行逐位测试，真实前两帧 2080 行验证，拒绝覆盖测试通过。

三个 PNG 均已在实际输出中检查：单位、图例、坐标及注释可读，无裁切；对数差值图明确省略精确零，原共同时间缺口断线。使用 visualize-data 规范固定对比口径和双色/线型，按 validate-data 要求独立核算，不将步长差写成真值误差。

- [压力与沉降历史](../../figures/pore_double_vel0_history.png)
- [迁移与步长差](../../figures/pore_double_vel0_differences.png)
- [事件窗口](../../figures/pore_double_vel0_event.png)

每幅同时保留同名 PDF。静态图片仅用于比较，不替代原生数组和计算表。

## 本轮全部新增位置与用途

正式 `src/source`、VS 工程、根目录正式 XML/BAT：本轮零修改。以下脚本/记录都是本轮新建（脚本内部为本轮迭代完善），没有改旧测试脚本。

| 位置（相对算例根目录） | 具体入口与目的 |
|---|---|
| `tests/support/pore_double_vel0/run_vel0.py` | `prepare` 第62行：校验正式物理段并按原排版生成共享时间配置；`run_one` 第109行：串行求解、校验哈希/Vel0/步数/帧数；`main` 第176行：原四组与 event 模式 |
| `tests/support/pore_double_vel0/export_state.cpp` | `Scalar` 第28行、`Triple` 第40行：原生 float/double 读取；`Export` 第86行：按 ID 导出整段历史、重构旧余量、保留 double 坐标与类型；`main` 第152行：批量入口和覆盖保护 |
| `tests/support/pore_double_vel0/build_export.ps1` | 第1行起：隔离编译 BI4 读取器，保存源码/程序来源，不写入正式 bin |
| `tests/support/pore_double_vel0/analyze_vel0.py` | `read_run` 第41行：数组/ID/schema 检查；`align` 第77行：实际时刻交集；`compare` 第95行：分时窗土压和沉降统计；`main` 第142行：普通/event 结果及来源校验 |
| `tests/support/pore_double_vel0/verify_vel0.py` | `read_one` / `intersection` / `compare_primary`：独立复算；`diagnose_10us`：保存帧投影与机械量首差；`--event`：另存事件复核及原轨迹共有样本检查 |
| `tests/support/pore_double_vel0/plot_vel0.py` | `frame` 第29行：统一版式；`plot_event` 第53行：事件图；`main` 第96行：原历史/差值图、共同时间缺口断线、受限图片替换 |
| `tests/support/pore_double_vel0/README.md` | 分类位置、复现命令、指标含义及覆盖保护 |
| `tests/notes/pore_double_vel0_chart_contract.md` | 预先统计/配色/输出/QA 规则及追加事件补测的原因 |
| `tests/notes/pore_double_vel0_acceptance.md` | 本记录：结论、限制和全部修改位置 |

生成的输入（四个浅层配置目录，每目录一个 XML 和原 `.bi4` / `_Normals.nbi4` 副本）：`tests/configs/pore_double_vel0/{dt1em5,dt5em6,dt1em5_event,dt5em6_event}/`。XML 文件统一保留原正式生成名 `CaseTerzaghiConsolidation_q0_PR_full_k1em4.xml`。

原生输出：`tests/outputs/pore_double_vel0/q0_vel0_{baseline,current}_dt{1em5,5em6}` 及相应 `_event`，共八组；各组 `data` 为原生 PART，`particles` 为 VTK，`native` 为读取器 CSV。独立读取器及 QA 在同分组 `reader`。

证据集中在 `tests/logs/pore_double_vel0/`：八份运行 JSON 及 solver/VTK 日志；`analysis.json`、`history.csv`、`differences.csv`、`time_alignment.csv`；相应 `event_` 四份；`independent_validation.json`、`event_independent_validation.json`；`reader.build/qa` 记录、输出精度说明和 CPU Debug 构建日志。没有覆盖原全 2Tv 结果、旧高低位基线或上阶段记录。

所有“检查通过”仅指已描述的读取/统计/构建或运行完整性。整体判断为：证据可带上述限制使用；严格 0.2 s 压力迁移审查仍未通过，完整 2Tv 与效率验收仍未进行。
