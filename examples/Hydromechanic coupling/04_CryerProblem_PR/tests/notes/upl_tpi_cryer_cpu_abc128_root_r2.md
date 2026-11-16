# Cryer CPU A/B/C 128-update 启动实施审查（完整三组根审查）

本记录补齐 C 的完成事实，已由根线程结合三组实际 run/native 审查复核；不修改原 `upl_tpi_cryer_cpu_startup_root_r1` 的 A/B 结论和当时 C pending 记录。结论范围是三维 CPU 时间积分实施资格，不是 Cryer 峰值、耗散曲线或物理精度验收。

A 是原有限 Kw 显式压力路径，默认不进入新分支。B 使用 α=.5、β=0，C 使用 α=0、β=0；B/C 采用真实材料 ID 所有的历史，整套 half/guess 压力为 `q=pn+α(pn−pprev)`，endpoint 做一次 `pnew=q+Rγ(q)/S` 缺陷修正。`S=−kΣw` 是 leading-LP 正预条件，不是完整耦合算子的真实对角，不宣称完成迭代收敛、二阶时间精度或有限 Kw 与 M0 等价。完整三维 Rγ/S 含原 XYZ、自由表面 Taylor 与加速度反馈项；不改变空间核、η、荷载/梯度、力学更新和唯一 J/material 推进。HG=0、SPR=0；公共源码、正式 XML/BAT 与暂停 C08 不变。

实际程序来自新的全 86-TU CPU Debug 构建。原 MSBuild 两种真实出口均为 0；旧构建 wrapper 的 tlog 路径解析假拒保留为 failed，由独立 `build_review_r2` 核完整对象/依赖/flags 后逐字节复制程序和五项 runtime 到新目录，不重编、不重链接。该闭包不是事后追认旧 86 对象的完整历史源码捕获。

三组各独立运行一次 CPU8/Stable，冷启动复用原 seed，无 PART restart、GenCase、half 或自动后续链。dt=2^-20 s，128 更新；实际两个保存态为 t=0/Step0 和 t=2^-13=.0001220703125 s/Step127（completed128）。原 ramp=2^-8=.00390625 s、drain=2^-7=.0078125 s，当前尚未完成 ramp、没有开排水状态；末帧为原普通输出目标，不把计划中的其它时刻虚构为已保存。

| 方案 | solver/native Popen、Win32 出口 | 孔压 RMS 差，末态相对新 A（Pa） | 材料 XYZ 最大差，末态相对新 A（mm） | 实测 loop（s） |
|---|---|---:|---:|---:|
| A 有限 Kw | 均 0 | — | — | 255.026810 |
| B α=.5 β=0 | 均 0 | 58.096954429291145 | 7.892377009948237e-6 | 396.533112 |
| C α=0 β=0 | 均 0 | 43.86977948207901 | 7.057713577584699e-6 | 376.894226 |

上述差值是不同时间算子在启动窗口中的描述性差异，不是理论误差、半步误差或 5 Pa 跨模型等价门。loop 来自实际 Run.csv，含 Debug/输出与同期其它工作影响，不是受控效率基准。

每组唯一原生读取均通过：37181 个全部 IDs（37173 soil+8 fixed）、22 typed 数组、原 finite/elastic/no-out/geometry/P0/float excess、真实保存时钟/Step/dt、J/n/V/rho/恒 k ledger、fixed markers 与原必要 signed-dterror 门。每组 ledger 74346 次、fixed marker 16 次，最大相对 ledger 误差 0，最大半径 .05000000000000002 m。初始 signed 诊断按实际 0 保留；唯一非初始 signed 值分别为 A −6.404499390307806e−7、B −6.40451377662893e−7、C −6.40451209856834e−7 s，均保留原符号且满足 <=1e−14 s。post-open=0、FS2/3 排水零压检查=0 是明确未覆盖，不用空掩码宣称 drainage 已验收。saved-J 质量乘荷载是 proxy，不是原力阶段 .001 荷载预算证据。

A 未创建私有 TPI policy/csv/summary。其全部 common26、native IDs、含初始和非初始 signed 诊断的实际 clock 与保留旧 CPU128 比较逐字节相同。该旧控制只有真实 call/native call 等既有证据，没有独立旧 run/start，不伪造。common26 导出不包含全部 22 原始数组，因此不将此比较扩大成 raw22 全数组位证明；22 数组读取/安全检查与跨运行全部数组位相等是两件事。

B/C 各有两帧 74346 条材料侧车行；实际 α/β、历史预测、double Rγ/S 修正、float 写回、末态 native p/J 对照均通过。全部 128 次 commit/endpoint、33307008 项 committed-field bit 检查、HG snapshot=0 符合；没有声称输出了 128 步逐 ID 侧车。B/C 的末态最小 S 为 3.0566670714718183/3.0566671396531886，末态最大 |Rγ| 为 4.25745936322748/19.400109457199967。native PorePressRate 保留旧 Kw/n 缩放 residual 诊断，不是 B/C 实际 dp/dt，不用于 dp/dt 精度验收。

| 末态直接原生量 | A | B | C |
|---|---:|---:|---:|
| 固定 18 材料点平均孔压（Pa，初始 r/a=.05，非精确原点） | 382.64535692003034 | 297.71321614583331 | 321.25034417046436 |
| 全 soil 算术平均孔压（Pa） | 345.4812315203352 | 302.33946217888479 | 314.88742057137983 |
| 最大材料位移（mm） | 8.675024636249088e-6 | 7.826476270258405e-7 | 1.617311059423062e-6 |

A 第一次 native 准入漏列 run.root_admission，在 reader 启动前安全终止；旧 r1 失败和准入保留，r2 核不存在旧目录/call/log 后执行首次实际读取。B/C 直接使用 r2。三组 run/start/call 的 child PID/creation/exe/argv 一致，owner 是真实 parent，solver 和 reader 的实际 Popen/Win32 出口均为 0；不是只凭完成文字作判断。本次摘要只读取既有证据，核对 126 个去重路径的 size/mtime 身份未变，没有重跑 reader、solver、构建、hash 或 Git。

选择性 Git 建议（具体相对路径列于配套 JSON `selective_git_candidates`）：保存已完成 CPU source/overlay/build-review/run/native 的作者脚本和说明、三组小 run/start/call/clock/admission/native/review JSON、原两项审计失败及新的完整摘要；可保存 native completion/summary/center18/columns 小表及 B/C policy/summary。Git 状态和忽略规则由根线程另核，本审查未执行 Git；选择性备份由根线程随后单独执行。排除 EXE/DLL/LIB/OBJ/PDB/ILK、BI4/NBI4/重启数据、VTK、common26.bin/clock.bin、完整 native_ids.csv 和大型逐材料侧车；这些证据本地原位保留，Git 不是原始数据备份。

下一物理资格仍需真实 GPU 三维实现、独立 CPU/GPU 同算法对照和到达开排水/Mandel 峰/消散的窗口，使用正确有限 Kw/M0/固定材料半径参考。当前 128 步结果不自动准入任何新 solver、不验收 1% 峰值精度，不接公共 XML、不宣称完整状态重启或完整 TPI 发布。
