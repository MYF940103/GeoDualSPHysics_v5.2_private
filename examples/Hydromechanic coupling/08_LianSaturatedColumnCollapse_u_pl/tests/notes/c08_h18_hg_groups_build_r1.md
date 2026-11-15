# C08 私有 cached-HG 三组材料入口构建稿

状态：仅作者稿，尚未执行。脚本只允许一次 host 编译和一次链接，不运行 help、smoke、求解器、native、VTK 或通知器。它不改变公共源码，也不触碰现有 PRE、程序、归档及其他组的活动计算依赖。

新增 `tests/support/c08_h18_hg_groups_build_r1.py` 与本说明。未来必须经根线程完整阅读并另建 `logs/c08_h18_hg_groups_build_r1.root_build_admission.json` 后，才能执行脚本的 `--execution-authorized`。准入须绑定脚本、本说明、基础和 optimized 两份构建记录的实际 stat，`allowed_stage` 为 `c08_h18_hg_groups_build_r1`，configuration 为 `Release`，`build_only=true`，`automatic_solver=false`，`automatic_reader=false`，并绑定当前根线程 ID。缺少这些条件就停止，保留已有产物，禁止自动重试。

## 唯一修改

基于已经通过 full3 实际运行的 `logs/c08_h18_wall_c_retry_GPU_r1.build.json` 私有闭包，在新的 source/build/TEMP 标签中，仅修改 `JSphGpuSingle.cpp` 的 cached-HG 材料准入 guard 与对应错误文字，允许以下三个精确元组：

| 组 | cohesion (Pa) | 初始 dilation | DilationDecay |
| --- | ---: | ---: | ---: |
| psi0 | 5000 | 0° | 0 |
| psi2p5 | 5000 | +2.5° | 0.2 |
| psim5 | 7500 | −5° | 0.2 |

共同限制为 `phi=phi_r=25°`、`coh_r=1000 Pa`、`n_coh=5`、`n_phi=0`，其余既有 guard 原样。旧 guard 仅要求 `phi==phi_r`，新 guard 将其收紧到 25°；这是私有入口范围收紧，不是摩擦参数或材料公式的修改。新增局部 bool 没有更改 class/CTE 布局。

已读冻结的 `JSph.cpp`：角度实际经 `float(TORAD*ReadElementFloat(...))` 写入，`TypesDef.h` 中 `TORAD=0.017453292519943295769`。故 C++ guard 使用 `float(TORAD*2.5f)`、`float(TORAD*-5.f)`、`float(TORAD*25.f)`，保留同一个 binary64 乘法后 binary32 写回表达式；不以角度直接比较弧度字段，也不使用人为截断的小数弧度。`psiDecay` 等仍按原 float 参数读取。本脚本不替代逐组 schema2 PRE 材料认证。

## 构建闭包与隔离

复用既有 `c08_h18_hg_wall_host_capture_r2_build.py` 已审的一 TU/link 思路和 `c08_h18_wend_matrix_r1` 的实际进程调用/stat 工具；不调用旧 helper 的 build/action。权威 CL argv 来自 optimized 实际 host compile receipt，link argv 来自当前 C-quality retry 实际 link receipt。

114 个实际有序对象中，仅替换 optimized `JSphGpuSingle.obj`。其余 113 个保留原顺序及实际身份，包括新 C-quality CUDA、异常 host capture、另外两个 optimized HG 对象。旧的三个 optimized 对象不能宣称全部未替换：其中 host 对象正是本次唯一重编目标。HG CUDA、单一材料 producer、Node 材料内核及 GPU main TU 不重新编译；C-quality nearest retry 保留。

新 source.zip 完整收录基础 frozen 源码闭包；只有唯一 host member 改变，逆变换必须恢复原字节。保留原私有 header 与 integrator include。CL 只重定向私有源码/include、obj/PDB/sourceDependencies 输出；其他 flags 采用原实际调用。链接只重定向一个对象及新输出，不覆盖 canonical。实际依赖集合经 frozen 根路径归一化后须与原 host `/sourceDependencies` 相同，外部 header 路径不归一化。源码归档与必要对象做 stat 绑定，不扫旧归档、BI4 或 SHA。

环境使用无空格 TEMP 中的 `env.cmd`，以可靠 `cmd /d /c env.cmd` 调用 `vcvarsall.bat x64 10.0.22000.0 -vcvars_ver=14.36`；原 GPU host 的实际 header 依赖是 SDK 10.0.22000.0，不能套用之前 CPU 的 8.1/UCRT 混合闭包。环境 stdout 仅留内存，不写整套环境。原实际 `cl.exe`/`link.exe` 都是 MSVC 14.36.32532；PATH 定位到原工具。记录 setup 实际返回值、CL/link 的实际 owned Popen/Win32 出口及原依赖集合对照，不声称任意未记录的编译环境逐字节相同。

## 后续限制

即使构建通过，也仅证明新私有入口能编译链接；不证明非零 dilation 的 HG/塑性更新、流动形态、论文精度、三组 PRE 可共用或任何物理验收。根线程仍需独立材料 probe，以及原 psi0 同输入实际短 prefix 的原生对照，之后才决定逐组接收计算。脚本不自动准入这些步骤，不增加 half 链，不把该私有 guard 写成正式 XML 接口文档。
