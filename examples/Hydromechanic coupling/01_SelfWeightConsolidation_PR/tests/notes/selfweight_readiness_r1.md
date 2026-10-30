# Case01 自重固结重新验证前的检查

日期：2026-10-30。范围：在 case02 已验收一维固结上先检查 symC 影响，然后准备 case01。此次只新增本记录，不修改正式输入、后处理、源码或历史结果，不运行求解器，不建立新的 TPI/u-pl 工作项。

检查时源码 HEAD 为 `be006f1dd6cf80e74238d86dae4564d91cd0b755`。这里引用的是当时工作区内容，HEAD 不表示全部工作区变更已经提交；本记录不是当前程序的运行或精度验收。以下路径除特别注明外，相对本 case 根目录。

## 1. 当前入口与历史结果不是同一版本证据

三个正式 XML 的共同设置为：柱高 `H=1 m`、宽 `.1 m`、`dp=.01 m`、`rho=2100 kg/m3`、`rho_w=1000 kg/m3`、`E=2e6 Pa`、`nu=.3`、`Kw=2e8 Pa`、`n=.3`、Wendland、Symplectic、固定 `dt=1e-6 s`。正式孔压边界为 `PoreMdbcInterpolationMode=0`，速度边界为 `SlipMode=1`，未显式启用新的 SPR/HG。

| 工况 | 当前输入要点 | 已保留根目录 Run.out 的实际状态 |
| --- | --- | --- |
| `CaseSelfWeightConsolidation_Stage1_Def.xml` | 重力保留，FreeSurface 初始化，`k=0`，Shepard40，阻尼 `.02`，至 `.30 s` | 2026-07-03 GPU；`Part_0060`、`.300001 s`、300001 步，正常结束、零排除 |
| `CaseSelfWeightConsolidation_Scenario2_Def.xml` | 从 Stage1 继承状态，`k=1e-3`，关闭 Shepard，阻尼 `.02`，目标 `7.2874285714 s` | 2026-07-03 GPU；最后 `Part_0005`、`.091093 s`、91093 步，无正常结束标志 |
| `CaseSelfWeightConsolidation_Scenario1_Def.xml` | Mode3 解析初始化，演化重力为零，阻尼 `4e-5`，至 `.4 s` | 2026-06-04 CPU；400000 步，正常结束、零排除 |

完整历史 MLS 对照位于 `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/Run.out`：2026-07-05 GPU、`SlipMode="No-slip"`、7.287429 s、7287429 步、正常结束、零排除。它不是根目录 Vel0/零阶孔压边界的同配置结果，也不是当前 double 应力与 symC 的验收结果。

## 2. 旧误差需要按来源拆开

- `support/SCENARIO2_FULL_RUN_SUMMARY.md`：早期 Mode3 直接初始化的末期底部超孔压约 `-5.90 kPa`；不能把它归给现在的 Stage1 重启方案。其报告输出路径曾被后续运行复用，报告与当前同名目录不应直接配对。
- `tests/notes/self_weight_final_validation_conclusion_20260702.md`：零阶边界两阶段历史参考在 `Tv=1` 给出底部超孔压 `.84620 kPa`、理论 `.73877 kPa`、剖面 RMS `73.623 Pa`；这是当时配置的结果。
- `tests/notes/self_weight_mls_direct_boundary_selection_20260705.md`：修正命令行覆盖后的 MLS p56 完整2Tv仍有晚期平台；汇总最大底部误差约 `.499 kPa`，没有证明 MLS 在该整段算例中降低误差。该记录也说明曾有 `-mdbc` 将 XML NoSlip 覆盖成 Vel0 的旧运行。
- `tests/notes/hydromech_late_platform_root_cause_20260731.md`：记录当时压缩源与 Darcy 消散大项相消及边界影响的诊断。它是后续检验的线索，不证明当前程序仍有同一误差或同一主导原因。

历史笔记、对应原生输出及图表保持原位，不根据新程序重命名或改写旧结论。

## 3. 参考解和观测口径先核对

### 论文的两种自重验证与初始场

`src/papers/u-pw/u-pw supporting material.md` Section II（检查时76–153行）明确给出两种验证：初始不排水自重响应后关闭重力，孔压按一维固结解消散；或保持重力，孔压趋于静水分布。两种都是论文中的验证对象，不能仅因 Scenario1 关闭重力便将其排除。

令 `M=E(1-nu)/((1+nu)(1-2nu))`、`B=(Kw/n)/(M+Kw/n)`，以柱底为 `z=0`。论文 Eq.4 的初始总孔压为 `pw0=B*rho*g*(H-z)`；Eq.5–8 对关闭重力分支给出：

```text
pw(z,t) = sum_n A_n*cos(lambda_n*z)*exp(-lambda_n^2*Cv*t)
lambda_n = (2*n+1)*pi/(2*H)
A_n = (2/H)*integral_0^H pw0(z)*cos(lambda_n*z) dz
Tv = Cv*t/H^2
```

该初始总孔压形式对应未先叠加静水孔压的自重不排水响应。当前 Stage1 则采用 `FreeSurface`，先建立并保存静水参考孔压。在线弹性、小应变、一维约束且相应平衡成立时，这种先有静水场的理想参考为：

```text
p_h(z) = rho_w*g*(H-z)
q_0(z) = B*(rho-rho_w)*g*(H-z)
p(z)   = p_h(z) + q_0(z)
sigma'_zz(z) = -(1-B)*(rho-rho_w)*g*(H-z)
```

这个总孔压比论文 Eq.4 多 `(1-B)*rho_w*g*(H-z)`；有限 Kw 下两个初始场并不严格相同，不能默认为同一初态。以上也不意味着真实 Stage1 输出恰好满足理想场。Stage1 检查必须同时看总孔压、超孔压、有效应力、总应力和剩余速度；下一阶段要记录从实际交接状态开始的初值差异。

旧图的时间因子采用 `Cv=k*M/(rho_w*g)`。对同样的线弹性准静态约化，保留有限水储量得到 `Cv=k/[rho_w*g*(1/M+n/Kw)]`，本组比前者小约 0.40%。新分析应区分旧 Tv 标尺与有限储量参考，不能将这点差异宣称为旧平台的解释。

### Scenario1 的初始化和重力切换需要核对

`src/source/JSphCpu.cpp` 的 `InitHydroMechState`（检查时约1305–1360行）中，Mode3 在演化重力为零时仍用 `analyticg=9.80665` 构造 `p=B*rho*g_ref*(H-z)`、`sigma'_zz=-(1-B)*rho*g_ref*(H-z)`，并令 `p0=0`。这保留了自重初态随后关闭重力的含义，不能要求切换瞬间仍满足原重力平衡。需要核对的是：当前直接赋值的应力/压力/速度、重力切换后的动量演化及实际边界，是否等价于论文的准备和切换过程；同时区分瞬态卸载响应与所用准静态标量参考。

`support/postprocess_self_weight_scenario1.py:45` 从实测初始孔压作余弦展开，再按旧 `Cv` 推进标量扩散。应同时保留论文 Eq.4 初态与实测初态展开两种比较，分别判断初始化差异和后续消散差异；不能用实测初态重新拟合后就宣称已经复现论文全部初始化过程。

### 旧后处理不宜直接用于新验收

| 位置 | 已核实行为 | 新分析要求 |
| --- | --- | --- |
| `support/postprocess_self_weight_consolidation.py:18–36` | 几何、材料及 Cv 写死在脚本内 | 从该次生成输入读取，并明确参考假设 |
| 同脚本 `load_series`，约217行 | 使用当前根 XML 的 TimeOut × Part 序号推算历史时间 | 使用实际保存时间，保留重启局部时间与全局阶段时间的区别 |
| 同脚本 `read_part_vtk` / `layer_average`，约97/234行 | 未保留原生 Idp，按当前 z 重新分层 | 用初始材料点 ID 跟踪沉降；固定初始分层与当前剖面分开报告 |
| `support/postprocess_stage1_history.py:18` | 以 `B*rho*g*(H-z)` 对照 `ExcessPorePress` | 与主脚本 `undrained_excess` 的浮重口径核对，不混用总孔压/超孔压 |

新脚本应独立放入 `tests/support`，不重写旧脚本来改变历史证据。对比至少包括底部/各层孔压、材料点沉降、静水/有效/总应力平衡、最大速度、塑性指标及排除粒子数；半步长一致性不替代物理参考验收。

## 4. 重启和新功能限制

- 根目录 Scenario2 的 CPU/GPU BAT 默认依赖 `CaseSelfWeightConsolidation_Stage1_out/data/Part_0060.bi4`、`PartExtra_0060.bi4` 及头文件。不能删除或覆盖这些文件。
- 旧测试 `tests/outputs/CaseSWSt1_MLSDirect_GPU_out/data` 的 Part56，以及 `tests/outputs/CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/data` 的 Part300，存在既有测试/跨 case 依赖；本轮不动。
- 正式 BAT 有删除同名输出的 `rd` 和 `-force` 分支；新实验不能直接调用这些入口覆盖已有结果。`xCaseSelfWeightConsolidation_Scenario2_win64_CPU.bat:55` 还显式传入 `-mdbc`，边界验收应核对 Run.out 的实际 SlipMode。
- `doc/xml_format/_FmtXML_ElastoplasticSoil.xml` 检查时约174/187行分别明确 SPR、HG 不支持历史重启。不能将 case02 的 SPR/HG 组合直接复制进现有 Stage1→Scenario2 链，也不能删除限制或把历史状态冒充 fresh 启动。
- 当前 double 应力应通过原生 `SigmaState_kk/ij` 交接检查，而非仅凭显示用旧 float 应力字段。旧 float checkpoint 续算只能作为迁移/对照，不能证明整段 double 应力演化的效果。
- symC 对应 `PoreDarcySymmetricCorr`。`src/source/JSphCpu.cpp` 检查时约2480行的 Darcy 计算受 `if(khyd>0)` 控制；正式 Stage1 的 `k=0` 不进入此分支，不需要为 symC 单因素复制一套 Stage1。有效的开关比较应放在 `k>0` 的 Scenario1/Scenario2 消散阶段。

## 5. 推荐分步验证

1. 先完成 case02 的 symC 单因素与半步长比较，保存程序来源、实际时间和同物理差异；不同时更改 Darcy、孔压精度或其他方法。
2. Case01先统一参考与观测口径，准备独立浅层测试输入及分析。保留现有 Vel0/零阶边界作为可辨认的起点，不把 MLS/SPR/HG 全部同时启用。
3. 新鲜 Stage1 在当前 double 应力下先短窗，再至 `.30 s`，必要时检查半步长；`k=0` 不做无效的 symC 开关重复组。Stage1通过的依据是状态和平衡，不是固定 Part60 编号本身。Scenario1另按论文初始场与重力切换含义核对后，开展 `k>0` 的有界消散对照。
4. 对新 Stage1→新 Scenario2 做交接检查：ID、p/p0、原生应力、速度和 mDBC额外状态；从同一已核验交接状态比较 `k>0` 下 symC 开关，先短窗及半步长，再评审是否启动完整2Tv。全部使用新输出名。
5. 如要加入 SPR/HG，先独立设计有明确物理参考的 fresh 自重加载—排水流程，或另行实现并验收所需重启状态；这不是本次检查已经完成的功能。

推荐标签保持简短，例如公共初始化 `sw_stage1_current`、消散比较 `sw_stage2_symc`，配置、结果、日志、图和结论使用同一标签，分别进入现有 `tests/configs`、`outputs`、`logs`、`figures`、`notes`。正式 README/XML/BAT 和根目录结果暂不变；达到明确验收后再单独更新。

## 6. 原生参考孔压与当前静水压必须分开

CPU Mode1初始化约1313–1367行按最近自由表面粒子中心构造`PorePress0`；Mode3约1305–1309行使用`max(soil z)+dp/2`。若平顶粒子中心为`.995m`而几何顶面为`1m`，两种静水面约定的压力差量级为`rho_w*g*dp/2=49.05Pa`。这只是条件计算；Mode1实际候选自由表面和原生p0仍须检查。

已追踪正常封闭粒子路径：p0初始化后仅按材料ID排序、周期复制或重启继承，没有随沉降重算。CPU重启见`src/source/JSphCpuSingle.cpp:167–177`；GPU见`JSphGpuSingle.cpp:203–216`。排水改当前p，不重置p0。CPU/GPU输出分别约1456/1240行明确`ExcessPorePress=p-p0`；mDBC/Shepard也使用固定p0，因此不只是绘图标签。

新分析对同一材料ID同时记录：

```text
q_native  = p_i - p0_i
p_h_now   = rho_w*g*(H_d(t)-z_i(t))
q_current = p_i - p_h_now
delta_ref = p_h_now - p0_i
q_native  = q_current + delta_ref
```

其中`H_d(t)`为明确选定的实际排水粒子层位置；同时保留论文固定`H=1m`的比较，几何边缘/粒子中心两种约定另列，不暗中换H或平移数据。对平整一维、初始p0来自同一排水层的情形，以向下沉降`s`为正，`delta_ref=rho_w*g*(s_i-s_top)`。即使当前p达到静水状态，原生`p-p0`也不必为零。

半粒距约定和材料差动沉降只是可量化的参考偏差，不能据此宣称解释或消除了历史约`.5kPa`平台。
