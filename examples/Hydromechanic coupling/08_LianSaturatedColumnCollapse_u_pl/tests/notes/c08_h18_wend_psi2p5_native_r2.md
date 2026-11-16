# Wendland ψ=+2.5° 预载唯一原生审查 r2 作者稿

仅作者稿，未执行。本稿替代的是 r1 wrapper 的失败进程参数预检，不替代或重跑物理 source，也不编译新读取器。原 r1 脚本、说明、准入和失败收据原位保留。

已只读核对 `logs/c08_h18_wend_psi2p5_native_r1.check.json`：`passed=false`、`reader_invocations=0`、`calls=[]`，首因为 `WinError 231`，在解析 Chrome native messaging 命名管道 argv 时发生。r1 call、material.csv 和 source/native_r1 目录均不存在。这不是 native 读失败，原1001个 BI4未改变。r1 脚本当时为11718 B，mtime_ns=1794799744471117300；失败收据为290877 B，mtime_ns=1794799811958993600。

唯一逻辑修复：活动进程 argv 与目标 native 目录比较改为 `os.path.normcase(os.path.abspath(q))` 的纯词法路径比较，绝不对任意进程参数调用 `Path.resolve()`、stat 或打开命名管道。进程 exe 的 basename 比较保留。其余变更仅新 r2 tag/输出路径和 r1失败证据绑定；原数值、物理输入、材料、C++读取器及全部既有门未改。

新文件为 `tests/support/c08_h18_wend_psi2p5_native_r2.py` 与本说明。执行需根线程完整阅读并另建 `logs/c08_h18_wend_psi2p5_native_r2.root_admission.json`，包含 r1说明列出的原准入键，改为r2 script/note/allowed_stage，另绑定 `prior_failed_check` 和 `prior_script` 的实际stat。运行前再次要求 r1读器计数仍为0，r1 call/profile/native_r1仍不存在；新 r2 call/profile/native_r2也必须fresh。已有任何完整或部分产物都不得覆盖。失败保留partial和新收据，无自动重试。

本次若准入，将是第一次实际 native read：现有 `tests/outputs/c08_h18_wend_native_r1_build/C08H18WendNative_win64.exe --source full DATA MATERIAL_CSV PLAN FRESHOUT`。原 entry/source body/pure22 loader分别为同build目录的 `h18_wend_entry_r1.cpp`、`h18_source_core_r1.cpp`、`public22_core_r1.h`；outer入口为 `tests/support/c08_h18_wend_native_r1.cpp`。本稿不调用builder。

目标source仍为 `c08_h18_wend_branches_psi2p5_pre_r1`，绑定实际 start/call/run/solver_completed seal和根 `terminal_review_r1.json`。从实际新generated XML生成 `configs/c08_h18_wend_psi2p5_native_r2.material.csv`，精确15keys锁定Kernel2、DP_PS、E20MPa、ν.33、φ=φr25°、nφ0、coh5000/cohr1000/ncoh5、ψ+2.5°、DilationDecay.2、原FOS1.65和fresh_trigger_active0。角度由原C++ `float(TORAD*XML-float)` 转换，无自行近似弧度。

唯一新native目录为 `outputs/c08_h18_wend_branches_psi2p5_pre_r1/native_r2/`，七个原输出：completion.json、typed22.bin、typed22_layout.csv、clocks.csv、summary.csv、layers.csv、snapshots.csv。新收据为 `logs/c08_h18_wend_psi2p5_native_r2.check.json`。source1001 PART身份沿当前根终态seal继承，读完做一次必要stat对照；不重扫旧源码或SHA。

全部原门保持：7060 IDs/22 typed finite、P0位继承、float excess、2060固定标记、5000soil单J ledger和float rho、κ非负单调、actual scalar +=5us/原1000 signed间隔<=1e-14、initial空区间、law2/sf/schema2最终certificate。全史FS2/3符号仍为保存态观测；原final要求非空且positive0。native不独立重建完整材料合同，不证明非event kernel，不等于平衡/精度验收。无solver/VTK/其他ψ/接收collapse/通知自动启动。
