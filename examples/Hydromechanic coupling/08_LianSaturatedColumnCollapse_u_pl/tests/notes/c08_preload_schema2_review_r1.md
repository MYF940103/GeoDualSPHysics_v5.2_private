# C08 预载 schema2 阶段记录

本记录只汇总已封口证据，截点见白名单的 `snapshot_utc`。本次编写只读取明确标签的文本、收据和既有 CSV，没有执行 Git、构建、GenCase、求解、BI4 解码、VTK 或 SHA 扫描；没有修改已冻结代码、输入和历史结果。待 Git 路径白名单见 `tests/logs/c08_preload_schema2_checkpoint_r1.files.json`，它是备份建议，不是已提交或已推送的证明。

## 床角角色修正的实际结果

`logs/c08_h18_bedroles_geometry_r1.check.json` 通过。GenCase 的 float32 VTK 坐标集合保持 7060 点、5000 土点 ID 顺序坐标相同，仅五个浅床角重叠点从右墙角色改为床；这不是原生 double 坐标逐位证明。新的固定注册为左墙255、床1550、右墙255，撤墙后固定1805/土5000；`keep_bed_overlap=false`，普通连续255点撤墙，不再依靠旧 keep5 修补。

原角色 H1.8 源最后保存 Part0062，真实时刻 `0.62000499999982805 s`、completed124001，实际 solver/tool Win32 退出1。床角修正后源同样退出1，最后保存 Part0207、`2.0700000000062184 s`、completed414000；两者原始 Run.out 均在 GPU predictor 报 `status bits 4`。冻结材料状态枚举的 Smooth=2，所以这个错误位是成功 Smooth 返回被 strict elastic-source 资格拒绝，不是状态值4的 TensionRepair，也不是 NonConverged。拒绝的未保存阶段不能由最后保存帧反推停止时刻或塑性乘子。

在真实相同时钟 `0.62000499999982805 s`（不是插值）对比：

| 量 | 原角色 | 床角修正 |
|---|---:|---:|
| 最大速度 m/s | 0.00900376299020 | 0.000226805967560 |
| 速度 RMS m/s | 0.000290811726308 | 0.000166186702354 |
| 保存态最大屈服函数 f / Pa | -151.848921867 | -4237.17311513 |
| 最小 J | 0.999575405670 | 0.999746925362 |

最大速度降低 `97.4810%`，约97.5%；这说明该边界角色修正影响了早期局部运动，不能据此宣布平衡或解决预载屈服。修正源2.07s末态仍有最大速度 `0.0243473381779 m/s`、速度RMS `0.00185790612771 m/s`，保存态 f_max `-120.090826881 Pa`（ID2260），κ仍为0。208帧原生只读检查通过，原22/ledger/P0/clock/signed等门保留；其 `partial=true`、`uncertified=true`、`certified_PRE=false`、`runtime_success_claimed=false`。分析 `c08_h18_bedroles208_review_r1.check.json` 已通过、生成三张PNG和配套CSV；其历史 `visual_QA_pending=true` 字段没有被本记录改写。另存的 `c08_h18_bedroles208_review_r1.visual.json` 已通过，明确物理接受和源平衡接受仍为false。

## schema2 的实际改动边界

本轮生产改动仅四文件：`src/source/JGravityPreloadState.h`、`src/source/JSph.cpp`、`src/source/JSph.h`、`doc/xml_format/_FmtXML_ElastoplasticSoil.xml`。它扩展真实演化塑性 PRE 的完整状态继承，不赋初始应力、不重置κ/J/p，不改变物理方程、材料返回、时间积分、孔压/力学稳定限制、边界或核函数。

schema1 弹性合同原字符串和分支资格保持；旧 source cohesion<=target 和全κ0规则保留。独立 schema2 要求 unified law2、`elastic_source=false`、土κ有限且>=0、固定κ0，以及源/目标完整材料合同严格相同，包含 cp/cr/软化/摩擦角/ψ/sf/DP/trigger/tension 政策。未知schema、非完整事件、PartBegin和legacyMR1源不取得schema2资格。普通默认false的连续 warmup 不新增全局拒绝门：仅完整PRE事件具备原稳定、双精度位置、Model1、阻尼/Shepard和新鲜完整注册等条件时才写schema2证书，否则沿用旧连续路径、不伪造证书。

ψ0、ψ+2.5、ψ-5 的材料/塑性演化历史不同，不能共享塑性PRE。新源必须各自从零真实演化；同材料σ/p/J/κ继续，不用κ0弹性源冒充塑性历史。增加 State.Schema 涉及主机类布局，所以实际配置重编而非把旧物理对象与新布局混合。

## 已有真实验证

下列结果均来自现有封口收据，不是计划：

| 项目 | 实际结果 | 收据 |
|---|---|---|
| 默认 CPU Debug 权威任务 | passed，Popen/Win32=0 | `c08_preload_schema2_DebugCPU_default_r1.check.json` |
| 私有 CPU Release | passed，Popen/Win32=0，consumed未变 | `c08_preload_schema2_ReleaseCPU_r1.build.json` |
| 私有 GPU Debug | passed，Popen/Win32=0，consumed未变 | `c08_preload_schema2_Debug_r1.build.json` |
| 私有 GPU Release | passed，Popen/Win32=0，consumed未变 | `c08_preload_schema2_Release_r1.build.json` |
| 合成 loader 测试 | 24项：5接受、19拒绝，实际测试退出0 | `c08_preload_schema2_loader_r1.check.json` |
| 新塑性原生工具构建 | passed，6封口BI4 utility+main共7对象，无JSph | `c08_h18_plastic_native_r1.build.json` |

24项是私有合成BI4测试，覆盖schema1兼容、schema2正κ继承和不兼容材料/非法κ等拒绝；不替代真实长预载、JSph完整合同生成的物理验证。新原生工具明确读取schema2，源f用实际κ调用 UpdateDPvars；源逐IDκ不减、固定κ0，旧全部数值预算保留。它传入实际源contract2而不独立重建完整目标合同；完整同材料目标校验仍由实际 receiving solver 承担。

真实旧路径回归现已封口：原程序/新程序各一次 source 8000更新、3帧，均solver/native通过；原程序/新程序各一次旧schema1 handoff 10更新、1帧，均通过。`c08_preload_schema2_regression_r1_source.compare.json` 与 `_handoff.compare.json` 均通过，原22载荷、布局、实际时钟和signed dterror逐字节相同，原始头未重写。额外新GPU Debug handoff10更新+memcheck及原生检查也通过，收据 `..._handoff_debug.run.json` 明确零errors/leaks。这是旧短路径兼容证据，不是新H1.8塑性PRE或最终三组结果验收。

## 尚未由本阶段证明的内容与备份口径

新共用塑性源owner `c08_h18_plastic_pre_r1.py` 与原生适配稿已准备/冻结。主线程已启动第一组 `c08_h18_plastic_psi0_pre_r1`，owner19272/GPU43000，固定5us、计划2M更新/1001帧。已核其静态 prepare/admission/owner_admission/start 记录：材料cp5000/ψ0/sf0，`elastic_source=false`，仅ψ0源获准；其他材料源和receiver尚未准入，原生检查及真实schema2 handoff仍待审。本记录不读取活动source的状态/求解log/粒子数据，不宣称任何新的schema2完整10s源或后续三ψ接收轨迹已成功，也不选AS参数、不宣布平衡或物理接受。

后续应分别核真实源事件证书/κ历史、同材料加载连续性及实际接收输出。白名单只纳入当前明确标签的轻量源码/输入/说明/收据/原始文本log/PNG/CSV和必要diff；活动源只纳静态输入和上述四份启动绑定JSON，不纳活动status/call/log。BI4、typed22载荷、exe/DLL/object/PDB/ZIP/VTK及无关旧改动均排除。已有旧H1.8原角色63帧证据仅作为保留引用，不重复打包其原始数据。

本记录与白名单只新增，不改旧收据和图；白名单是截点清单，后来产生或仍活动文件须终态封口后由主线程另行审查追加，不能通过全目录add带入。
