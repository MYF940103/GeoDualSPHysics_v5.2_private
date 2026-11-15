# C08：同对象闭包的 CPU Debug before 基线

本文件与 `support/c08_h18_wall_c_before_CPU_Debug_r1_build.py` 是作者阶段资产，尚未执行。builder 只允许一份私有 before 源文件、一次 CL 编译、一次 link；环境设置单独记录。它不启动程序/help/solver/reader/VTK，不修改公共源码、canonical、旧对象、原结果或物理参数，不计算 SHA，也不安排通知或下一任务。根线程完整审阅并单独建立准入后方可调用。

## 为什么不直接使用旧 canonical

`logs/c08_preload_schema2_DebugCPU_default_r1.check.json` 确实绑定当前 canonical CPU Debug：13068800 B、mtime_ns=1794222698703898200；后来 `c08_h18_restore_DebugCPU_r1.build.json` 也记录过旧 full-source 恢复构建。但这些历史记录没有证明 canonical 与今天新默认 Debug 的其余对象/依赖完全同版。相同名字、大小或历史正常退出不能代替本次精确 before。因此这里保留它作为受保护程序，另建立同一对象闭包的 before。

## 闭包和唯一替换

基线来源是 `logs/c08_h18_wall_c_retry_CPU_Debug_r1.build.json` 的实际成功 DebugCPU MSBuild，权威 IntDir 为：

`C:/Users/syosh/AppData/Local/Temp/c08_wall_c_retry_cpu_debug_r1`

读取 `DualSPHysics.tlog/CL.command.1.tlog` 中唯一 `JSphCpu_mdbc.cpp` 段，保留 `/Od /fp:precise /MTd /RTC1 /openmp` 等原参数。读取 `link.command.1.tlog` 的实际顺序：87 个唯一对象，包含 public `main.obj`。只把 `JSphCpu_mdbc.obj` 替换成新 before 对象；其余86个对象及顺序不变，不重新编译主程序或其他 TU。

私有源直接复制 `c08_h18_wall_c_retry_r1.source.json` 绑定的 `JSphCpu_mdbc.cpp.before`，不从Git猜测版本。运行时按记录的逆替换逐字节验证两个成员：当前公共 candidate 等于冻结 candidate，逆变换完整恢复对应 before。GPU helper 只参加这份两成员字节证明，不用于 CPU 编译或回写公共文件。

原 CL 没有额外 `/I`。私有 `frozen` 目录只有 before `.cpp`，因此新增 `/I<repo>/src/source`，使原 quoted includes 使用与新 Debug 一致的公共头文件。它不是另做头文件版本替换。只stat该TU真实read-tlog列出的项目头文件，以及87对象、工具、收据和两成员绑定；不扫描旧BI4、归档或所有历史源码，也不生成复杂整树快照。

CL 的 `/Fo` 和 `/Fd` 都指向新输出，避免修改原对象、vc143.pdb/idb。link 的 OUT/PDB/IMPLIB/LTCGOUT 都指向新输出；保留原库和其他参数。工作目录始终是 `src/VS`，因为原 `/LIBPATH:../LIB/VS2022` 相对于此目录。清除外部 CL/LINK 参数注入，环境 stdout 只在内存解析，不把可能含用户环境值的 `set` 输出写入日志。

实际权威环境是 **Windows SDK8.1 API＋UCRT10.0.10240.0＋MSVC14.36.32532** 的混合闭包。vcxproj 的 `WindowsTargetPlatformVersion` 是8.1，原CL/link read-tlog也同时含8.1和10.0.10240.0；后者只有UCRT头/库，本机没有该版本完整Win10 shared/um/winrt与UM库。因此不调用不存在的“完整10240 SDK” setup，也不进行多次环境探测。只用原 `vcvarsall x64 -vcvars_ver=14.36` 获取工具环境，再显式覆盖 INCLUDE 为原MSVC include、ATLMFC（仅原实际消费时）、8.1 shared/um/winrt及UCRT10240；LIB为原MSVC x64、实际需要的ATLMFC、8.1 winv6.3 UMx64及UCRT10240 x64。WindowsSdkDir/Version标明8.1，UniversalCRTSdkDir/UCRTVersion标明原10240。原link项目 `/LIBPATH` 保留；显式`.lib` token只重定向到原link.read中唯一同名的已绑定绝对文件，不替换库身份，也不声称这些argv字面不变。

原mDBC TU read-tlog包含270个项目/系统头（含无扩展名的C++标准库头），全部只stat并封存集合。新CL仅增加诊断 `/sourceDependencies`；编译后按实际JSON逐一核全项目/系统头集合，唯一源码位置例外为私有before `.cpp`。缺失/额外头必须保留本次失败、停止于link之前，不重试。tlog不保存原INCLUDE搜索次序，文档和收据如实记录此限制，以实际头集合验证闭包，不能推造原搜索顺序。新选用工具为Hostx64/x64、同14.36.32532；原MSBuild具体CL host架构没有直接捕获，所以不宣称完整compiler二进制身份相同，之后仍须实测before/after原生字节门。

## 根线程准入和产物

新标签固定为 `c08_h18_wall_c_before_CPU_Debug_r1`。准入为 `logs/<tag>.root_build_admission.json`，至少包含：

- `authorized=true`、`allowed_stage=<tag>`、当前 `root_thread_id`。
- `build_only=true`、`automatic_solver=false`、`automatic_reader=false`。
- 精确stat绑定 `execution_script`、`note`、`source_build`（新默认Debug收据）和 `source_candidate`（两成员source.json）。

CLI 只有 `--execution-authorized`。输出为 `tests/outputs/<tag>`，原/新对象、环境/CL/link三个调用收据及最终build记录分别封存。CL/link的 Popen 和同一 Win32 handle 出口均独立保存；无法建立实际工具身份或出口即保留失败，不重试。部分目录/既有收据一律保护。builder没有自动调用新EXE来检查帮助或运行算例。

## 尚未授权执行的最小 CPU runner 方案

此段只是供根线程决定的后续方案，不由builder执行，也没有新runner文件或half链。

1. 复用 case02 已有、未改变的 `tests/outputs/upl_column_public_seed_r1/upl_column_public_smoke_r1` 及其 XML/BI4/Normals；不运行 GenCase，不改物理配置。
2. before 和新 candidate 各用一个新标签、同一直接 project-main 参数运行：`-cpu -ompthreads:1 -stable -mdbc_freeslip PREFIX FRESHOUT -dirdataout data -svres -nsteps:2`。两次各2步、3帧，dt=2.5us、真实终点5us。分开捕获实际 owner/child/出口；没有自动串接长窗、其他case或解码。
3. 两个run真正完成后，再由根线程独立决定各自一次原生读取。可复用 `upl_column_public_native_r1.cpp` 的三帧 public22 验证逻辑，核全部1040 IDs、22 typed数组、3000土体ledger行、120固定marker、实际Step/clock和两条非空signed诊断；初始有符号诊断保留原样。比较真正同时间/同Step的所有保存数组和诊断字节，不改header或掩盖字段。
4. 这是三个动态 writer（state/C/acceleration）的有效旧路径实现回归，不证明新失败分支、峰值或物理精度；新 C 失败重试由单独 GPU packet fixtures 检查。三帧未跨排水事件，不能声称非空排水验证。
5. 旧 u-pw pressure 与非动态 SPR 两个writer的字面逆变换/编译证据先保留。本轮不扩0.03s/31帧链、不新增half。旧固定标签/二进制/SHA绑定的runner不可原封执行，需要根线程新标签、新程序绑定后才可调用。

normal build/run exit 均不是完整塌陷、论文、其他ψ或physical acceptance。原C08 PRE、失败记录、正式输出和活动独立任务保持原状。
