# 有界公开 GPU 动态渗流接线计划 r1

状态：仅计划，不是执行、公开 GPU 验收或正式发行。先完成本轮私有墙证据的选择性本地/远端 checkpoint 核验，再冻结新基线并编辑源码。当前私有墙最终依据为 `tests/logs/upl_gpu_wall_stage_r1.check.json`；本计划不改写该收据或此前失败记录。

## 最小改动与开关语义

生产改动限定为 `src/source/JSph.h`、`JSph.cpp`、`JSphGpu.cpp`、`JSphGpuSingle.cpp`，同步 `doc/xml_format/_FmtXML_ElastoplasticSoil.xml` 与 `examples/Hydromechanic coupling/validation/upl_current_status.json`。不改 kernel、方程、粒子排序、积分、CPU 物理路径或正式 XML/BAT。

- 复用已有 `HydroMechDynamicSeepage`，缺省仍为 false；缺省或显式 false 均保持原 u-pw，不能默开 J/n、动态 Darcy 或变 k。
- 在 `JSphGpuSingle::LoadConfig` 共享配置加载后、内存与域初始化前，显式 true 原子开启已有 observer、J-feedback、完整动态压力率；有真实固定墙才开启对应墙分支。`HydroMechConductivityModel=0` 仍取常 k；model1 映射已有私有 law 和显式有限正 Ck，不增加第二套公开半物理开关。
- `JSph::LoadConfig` 仅扩展后端许可与准确日志，不删除其余受限条件。`InitPorosityObserverGpu` 保留全部材料、几何、物理与限步检查：私有 fixture 仍要求 XML model0；公开入口的 model0/1 必须与映射后的内部 law/Ck 一致，不能直接删掉 model0 检查而留下不一致状态。
- 仅开启已验的 fresh、2D、零重力、弹性 Wendland/Symplectic、正 constant DtFixed 范围：矩形 XZ 周期无墙，或两面静止、对向、平行轴向 FreeSlip mDBC 墙及切向周期。保留既有限步、正 k 连续域与梯度 k 必要界；这些不是充分稳定性定理。

## 原生输出契约

公共 ON 在 `JSphGpuSingle::SaveData` 保存实际已下载并按正常粒子同步压缩的 `AuxPosDiv`，不得填零或从旧导出猜测。沿用实际 J/n/last-stage theta；从同一份已保存 J 派生并保存当前 V/rho/k，不增持久 GPU 粒子数组。输出必须保留 double 类型、native ID 与实际时刻对齐，不能用压缩后索引回读未压缩工作数组。

固定墙的 n/V/rho/k 采用明确的零 marker，与 CPU 公开契约一致；它们不是土体物性或水量。墙 J/最后阶段状态仍如实记录，不将真实重构状态伪装成土体控制体。保留旧 Rhop 为被动 float 诊断；CPU rational 与 GPU additive 的旧 Rhop 积分差异不在此轮修改。

共享 `JSph::SaveData` 已有主开关/schema/model/Ck 类型化元数据，需核对 GPU ON 实际写出。OFF 不新增动态数组或元数据。新增元数据、实际 PosDiv、固定 marker 的输出差异逐项单列；不得 mask、伪造旧值，或由共有场精确相等升级为整个旧/新原始文件相等。

## 有界验证与准入

1. 修改前冻结源码、受保护 canonical GPU 六件及旧私有实际控制；修改后先默认 CPU Debug，再权威 solution 的隔离 GPU Debug/Release 全量 Rebuild。绑定工具、对象、库、runtime、源码与输入哈希；不安装或覆盖 canonical/server 程序。
2. 默认 OFF 复用真正 case02 mDBC 控制 `tests/outputs/symc_1d_short_r1_gpu_old`：40 fixed + 1000 soil，Boundary2/SlipMode1、SPR1、HG=.1，dt=1e-5，15000 步、151 帧，实际终点 .15000000000000924 s。其程序 SHA `260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c` 与受保护 canonical GPU Release 一致；completion/receipt 已封存且 owned exit0。只运行新候选，旧程序和旧结果不重跑。按真实1040 IDs 比较所有原 typed15 数组与实际 time/Step/signed dterror，严格0ULP；动态数组与元数据保持缺席。该带载荷/排水的旧 u-pw 控制不是动态 ON 准入。
3. 公开 ON 先 Debug 实际两步 memcheck 0 errors/0 leaks，再 Release 周期/墙、常 k/smooth-k 的已有粗半步窗口。每个新进程单独准入，使用封存输入/原始私有控制；同后端公开与对应私有 Run 的共有实际字段、IDs、时刻要求位级一致，新输出另验。CPU 控制从原生 BI4 读取；CPU/GPU 跨后端仍按原5Pa/.005mm门槛，不冒称位级一致或计时基准。
4. 全部保存点保留原 finite、弹性、无排除、J/n/V/rho/k 账本、实际时钟与 signed dterror<=1e-14 安全条件；独立半步保留5Pa压力RMS/.005mm最大XYZ材料位移及 normalized p/v/u RMS<=1e-4。不得因新增公开开关重新调材料或降低阈值。墙常 k 的全域/近墙/端点1%及实际法向通量、反力原预算不得回退；变 k 无常系数精确理论。公开映射不得改变已通过的墙物理轨迹。
5. 拒绝测试封存实际错误原因、owned exit 和输出：HydroMech关闭却开主开关、非法 model、model1在master OFF、Ck缺失/非正/非有限、非法步长/安全系数、非矩形周期、非允许墙/滑移、重力/载荷/排水/塑性等不支持组合。`JPartsLoad4` 继续拒绝动态数组或元数据 PART，含 master OFF 读取；不悄悄丢状态或降级 u-pw。已完成求解的分析失败只修离线分析，不重跑求解。

## 交付边界

文档和状态仅在实际证据通过后说明受限的新 GPU 入口，并标记程序哈希/版本；旧 GPU 程序会忽略新键的警告仍保留。保留早先 CPU 初始 PosDiv/有符号零导致的 full raw26=false 历史，不能用新 GPU 结果回写历史验收。

该阶段不解锁重力、自重/固结、载荷、排水、Cryer、一般或运动/曲面墙、混合滑移 Lian、塑性、非饱和、界面 k、TPI、精确 PART 重启、正式长程或服务器安装。后续物理案例仍按父计划 `validation/upl_development_r1.md` / `upl_current_status.json` 单独准入；当前只做公开接线和既有有界实现等价性，不扩物理范围。
