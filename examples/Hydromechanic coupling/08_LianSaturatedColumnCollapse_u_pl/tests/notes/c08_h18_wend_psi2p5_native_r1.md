# Wendland ψ=+2.5° 预载唯一原生审查作者稿

仅作者稿，未执行；不编译新读取器，不启动求解器、VTK、通知或其他组。对象是已完成的 `c08_h18_wend_branches_psi2p5_pre_r1`，原 generic schema2/law2 GPU 程序、H/dp=1.8、5 μs、10 s/2M 更新、1001 帧、bed-last 7060=5000 soil+2060 fixed。源端 `elastic_source=false`、keep=false，材料 coh=5000 Pa、ψ=+2.5°、DilationDecay=0.2；κ/J/p/应力历史保持原值。正常退出与 native 认证均不等于平衡验收。

现有工具已支持精确三组 source，故不需新增 native build：

- 构建收据：`tests/logs/c08_h18_wend_native_r1.build.json`。
- 程序：`tests/outputs/c08_h18_wend_native_r1_build/C08H18WendNative_win64.exe`。
- 最外入口：`tests/support/c08_h18_wend_native_r1.cpp`，包含 frozen `h18_wend_entry_r1.cpp`。
- 实际 source body、pure22 loader：同一 build 目录的 `h18_source_core_r1.cpp`、`public22_core_r1.h`。
- 原 builder：`tests/support/c08_h18_wend_native_r1_build.py`；本轮只读，不调用。
- 实际 source runner：`tests/support/c08_h18_wend_branches_pre_r1.py`，本 wrapper 只复用 stat/owned invoke/已定义的 clock/material helpers，绝不调用 prepare/run。

精确 CLI 为 `C08H18WendNative_win64.exe --source full DATA MATERIAL_CSV PLAN FRESHOUT`。group 不在 CLI 中，由实际生成 XML 导出的精确 15-key CSV 识别；native 内已有 `psi2p5` 分支，按原 `float(TORAD*XML-float)` 转换校核 signed dilation。CSV 包含 Kernel/group/E/nu/DPCtes/phi/phi_r/n_phi/coh/coh_r/n_coh/dlt/DilationDecay/SoilTriggerFos/fresh_trigger_active。本稿锁定 XML 实值且不复用旧 ψ0 profile。只在明确执行后新建 `configs/c08_h18_wend_psi2p5_native_r1.material.csv`。

执行前根线程须全读，并准备 `logs/c08_h18_wend_psi2p5_native_r1.root_admission.json`，绑定 script/note/source_run/terminal_review/native_build 的 stat、当前根线程ID，`authorized=true`、`allowed_stage=c08_h18_wend_psi2p5_native_r1`、group=psi2p5、`reader_once_only=true`、`automatic_solver=false`、`automatic_VTK=false`。wrapper同时绑定原 start/call/run/solver_completed seal、实际 program/XML/plan/必要源归档收据，以及当前 `terminal_review_r1.json`；不重复审扫旧全部源码，不计算SHA。

当前 root terminal seal 已核过原 run 绑定的1001个 PART stat；wrapper继承这份身份，并在读完后做一次必要 stat 对照，任何前后改变均保留失败。不再次复制/重写 BI4，也不把旧 wrapper `reader_invocations=0` 当永久无读取器证据：执行时仍检查实际 active reader、已有 native 输出/profile/call。任何完整或部分产物均禁止覆盖。原 native 输出唯一为该 source 下新的 `native_r1/`；异常后仅写 fresh failure receipt，不自动重解码。

现有 native 原门原样：7060全部ID无重漏、22个原始类型/数量/finite，P0位继承、float excess、固定2060标记、5000 soil单J的n/V/rho/k ledger与float rho缓存、κ非负单调、真实 scalar +=5us 时钟、原1000个非初始 signed dterror<=1e-14、initial区间标记、law2/sf/schema2最终证书。FS2/3保存帧符号全史是观测，因为Shepard和保存重分类之后可能存在正值；原最终认证要求FS2/3非空且无正压，本稿不增加或放宽任何符号门。

能力边界保留：工具独立读取最终 kernel/geometry/cohesion 证书和原生字段，但不独立重建整段材料合同；非event kernel也需actual generated XML/Run.out/程序绑定。κ参与的yield为保存态诊断，不是试算返回重建。旧 `c08_h18_wend_review_r1.py` 硬编码 ψ0/source，不能用它直接分析本组或改标签伪装；后续根独立审查新组压力/速度/能量/应力/κ收敛后才决定接收 collapse。
