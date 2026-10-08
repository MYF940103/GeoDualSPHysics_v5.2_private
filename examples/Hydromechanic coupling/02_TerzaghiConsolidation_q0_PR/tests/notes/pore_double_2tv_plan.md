# double 孔压状态：正式 k=1e-4 完整 2Tv 回归

> 状态更新：2026-09-09 15:26:27 已按用户要求停止，最后完整输出 t=15.303610 s、1,530,361 步。此运行未完成，不能作为完整 2Tv 验收；输出原样保留。当前正式求解器正在恢复无补丁 float，后续状态见同目录 `upw_float_restore.md`，下文保留当时计划与启动记录。

日期：2026-09-09。本轮任务是上一阶段之后的完整过程验证，不是继续升级孔压率或空间算子的 double 改造。

## 范围和路径

- 冻结当前 CPU Release double 孔压状态版本，SHA256 `95683EA87702A50CC8246B7C32C7DE9C2B203435985A373378A6FCDDA7347DBD`；求解器源码与上一阶段 23 项记录核对一致。本轮不修改正式求解器、VS 工程或原结果，不提交或推送 Git。
- 正式入口在算例根：`xCaseTerzaghiConsolidation_q0_PR_full_k1em4_double_win64_CPU.bat`，配套 `CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_Def.xml`。可以双击完成 GenCase、CPU 求解、VTK 转换、原生比较及出图。
- 新结果：根目录 `CaseTerzaghiConsolidation_q0_PR_full_k1em4_double_out`。已有同名输出时立即拒绝，不删除、不覆盖。`-postprocess` 只允许已完成、来源核验通过的运行进入后处理，既有最终图仍拒绝覆盖。
- 旧基线：根目录 `CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out`，保持只读；旧原生数据导出另存 `tests/outputs/pore_double_2tv/baseline_native`。
- 后处理/来源防护：`support/compare_double_q0.py`、`support/run_double_q0.py`。原生读取复用已经验收的 `tests/outputs/pore_double_vel0/reader/export_state.exe`；正式 BAT 会先核验该依赖，无需重新构建求解器。
- 新运行记录在 `tests/logs/pore_double_2tv`；正式图与表在根 `figures/pore_double_q0_k1em4_*`。自测只在 `tests/figures/pore_double_2tv/selfcheck`，不能混作新模型完整结果。

## 配置

严格沿用原 precision 正式 XML/BAT：CPU 4 线程、Vel0 (`-mdbc`)、k=1e-4 m/s、n=0.3、Kw=2e8 Pa、q0=10000 Pa、0.01 s 外载爬升后开启顶部排水，Symplectic、Shepard 关闭。DtIni 保持正式配置 1e-6 s，DtFixed=1e-5 s；固定步长初始化实际使用 DtFixed，不能将 DtIni 解释成实际首步必为 1e-6。

TimeMax=72.8842857142858 s，TimeOut=0.182185714285714 s，预计 7,288,429 步、402 帧。保留原 precision 的两段 timeout：第一段是常规间隔，第二段在 TimeMax 请求额外终点输出。它用于与旧基线匹配全部 402 帧，并非新增物理配置；只在新 XML 里补充说明，未再引入其他时序或模型开关。旧最后保存时刻约为 72.884290 s，分析使用原生实际时间而非虚构精确 Tv=2 的帧。

旧运行 Simulation Runtime=20426.009766 s，约 5 小时 40 分，仅用于安排等待，不能当成受控性能基准。

## 基线来源限制

旧完整 precision 运行记录的 9 个源码 SHA 与 Stage 1 高低位基线清单及 ZIP 内容全部匹配：JSph、JSphCpu、JSphCpuSingle、JPartsLoad4 各 .h/.cpp，以及 FunPorePressure.h。没有发现这些 CPU 力、积分、边界核心文件的额外变化。

旧完整运行 CPU 二进制 SHA 为 `0E6DE119F8A4AAF8219FBCD46FA174FF2C8F0602F1B682C3E0439343527F3D3A`，后来归档的短测基线为 `A2CD2B1023F6487EAC3F7D7185F02175494FE680B238C558C478B71E29B6EFF6`。构建日志链接命令和对象列表一致、后者仅重链，但历史 obj/lib/DLL 及其他头文件未完整保存，不能保证两份二进制语义完全相同，更不能据此宣称性能加速。

## 检查口径与图表合同

问题：从高低位补丁替换为 double 状态后，完整固结曲线、Tv>=1 的孔压平台、孔压剖面和沉降是否改变？不预设改善，不沿用“精度补丁已解决平台”的说法。

采用原生 BI4：旧压力 double(high)+double(residual)，新压力 double；按 1040 个唯一 ID 核验，土指标仅使用 ID 40--1039 的 1000 个土粒子，沉降用初始固定顶部 10 个 ID。原生实际时刻容差 1e-9 s，不做隐式插值或错帧相减。旧和新均要求完整运行、零排除、期望步数/帧数、有限数值和参考孔压一致。Part0 初始保存位置的 float 共同原点误差与后续 double 位置精度需显式记录。

静态图（遵循用户要求放正式 figures，Matplotlib）：

1. history：全程平均超孔压、Tv>=1 放大、固结度 U、固定顶部沉降，多面板时间曲线，预期 402 个采样点。
2. profiles：Tv≈0.5、1、2 的同初始层孔压剖面，以实际时间和初始层坐标说明比较口径。

配色 hard two-root cap：旧蓝 #3274A1、新橙 #E1812C，经典 Terzaghi 灰色虚线；版本辅以线型/空心标记区分。白底、安静灰网格、明确单位、中性标题。经典解析解只是小应变、不可压缩水等假设下的物理参考，不能当成有限 Kw、外载爬升、移动粒子离散方程的精确真值。

先使用旧完整结果对自身进行后处理自测，验证重构压力、时间/ID、剖面/沉降及零迁移差，并目视检查自测图片。该自测不是新 double 的完整结果。运行结束后自动生成的是待最终图像复审的比较产物，不能仅凭启动记录认定完成。

## 尚未消除的限制

- 上一轮严格短程压力审查线 RMS 0.01 Pa / 最大 0.1 Pa 未通过，此事实不会被进入长程测试抹去；本轮是进一步收集长程影响证据。
- 不在本轮更改物理方程、边界、时间推进或误差容差，不扩大 double 孔压率/空间算子范围。
- 计算尚未完成时，只报告实际已写出的进度，不提供最终改善或效率结论。

## 新增位置清单

正式根 XML/BAT 各一个；`support/run_double_q0.py`（preflight、generated_check、validate_manifest 来源和不覆盖保护）；`support/compare_double_q0.py`（完整状态对照、原生导出、图表、自测）；本计划记录。其余为以上脚本自动生成的分类日志、自测/正式输出。旧根 XML/BAT、旧 figures 及旧完整计算数据不改动。

## 启动与工具验证记录（不是完整计算验收）

2026-09-09 本机时间 14:11:20 启动正式 BAT，批处理 PID 37460；CPU Release 求解器 PID 22108，14:11:24 开始推进。命令为正式 BAT 的 `-cpu -ompthreads:4 -mdbc ... -dirdataout data -svres -svextraparts:1`，未额外放大步长或更换算法。

- `tests/logs/pore_double_2tv/run_manifest.json` 保存启动前源码、执行程序、输入、依赖及旧原生数据的 SHA；`generated_manifest.json` 确认五个生成配置部分与旧结果一致，并保存生成输入和启动记录的 SHA。
- `tests/logs/pore_double_2tv/full_run.log` / `full_run.err.log` 保存后台正式 BAT 的输出；求解器实时进度在新输出目录 `Run.out`。BAT 在求解成功后自动继续 VTK 转换、原生数据对比及正式出图，任何校验失败会保留结果并停止。
- 求解器初始化确认 40 个固定边界粒子、1000 个土粒子，CPU 4 线程、固定步长 1e-5 s、TimeMax 72.8842857142858 s。14:13:51 核查时 Part_0000、Part_0001 已保存；后者时间 0.182190 s、18,219 步，约完成 0.25%，当前无报错。首段日志 Time/Sec=708.13，初始预测约需 14 小时（日志预计本机时间 09-10 04:31:35 完成），明显慢于历史记录，不能把它直接归因于本次 double 改造或作为效率验收结论。
- 启动后再次核验 425 个受保护文件及生成输入指纹一致，旧基线未改动，CPU Release SHA 与冻结版本一致，尚无新正式比较图，避免把工具自测图片误称为本次长程结果。
- 本轮 CPU Debug 构建成功；没有修改生产 C++/CUDA 求解器源码或 VS 工程，也没有提交/推送 Git。

后处理工具自测 r2 使用同一旧基线两次：402 帧、每份 418080 行，全部孔压/沉降自比差为零；6 个错误输入测试均被拒绝；重复输出被拒绝。独立只读测试还在内存中注入末帧 0.001 Pa 土粒子压力差和 2e-7 m 顶部位移差，工具正确检出均压差约 0.001 Pa 和沉降差约 0.0002 mm。注入没有写入任何实际数据。

`tests/logs/pore_double_2tv/selfcheck/comparison_qa_r2.json` 及 `tests/figures/pore_double_2tv/selfcheck/pore_double_q0_k1em4_selfcheck_r2_*` 是本轮最终工具自测记录。两张 r2 PNG 已目视检查；早先不带 r2 的自测保留为过程记录，其 history 页脚存在已修正的 double 措辞，不能用作新模型结果。正式脚本冻结 SHA256 为 `2CB0C2726366842F30DCD2B74A276BEBEA8F554E05702EBA8ED32CCE4778A396`。

主要新增功能位置：正式 XML 第 100 行为沿用输出时序，第 111 行起为原物理配置，第 150 行起为时间设置；正式 BAT 第 43 行起校验/生成/求解、第 63 行起核验/后处理；`run_double_q0.py` 第 111 行 `preflight`、第 159 行 `validate_manifest`、第 170 行 `generated_check`；`compare_double_q0.py` 第 105 行原生读取来源、第 157 行完整性检查、第 260 行同粒子配对、第 281 行指标、第 356 行图表、第 516 行后处理入口。

在完整求解、原生比较和正式图片复查结束前，状态保持“运行中、整体验收未完成”，不能据此宣称双精度解决了 Tv>=1 的平台。
