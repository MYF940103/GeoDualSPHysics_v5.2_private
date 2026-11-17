# C02 M0 步长策略私有构建r2作者稿

只新增 `tests/support/upl_tpi_m0_dt_build_r2.py` 与本说明。作者没有执行 prepare、
build、help、求解、原生读取、VTK、Git或任何旧数据SHA扫描。
本稿不修改公共源码、Visual Studio项目、canonical程序或任何旧构建归档。

## 三个独立配置

每次调用只构建一个配置，需要根完整审读后分别给出 build-only 准入：

| CLI configuration | 已实际通过的对象基座 | 新编译 | 保留 |
| --- | --- | --- | --- |
| `DebugCPU` | `upl_tpi_cpu_DebugCPU_r2.build.json`，真实完整CPU Debug闭包 | Cpu.cpp、CpuSingle.cpp两host | 84/86 |
| `Debug` | `upl_tpi_gpu_Debug_r2.build.json` | Gpu.cpp、GpuSingle.cpp两host | 109/111 |
| `Release` | `upl_tpi_gpu_full2tv_Release_r1.build.json` | Gpu.cpp、GpuSingle.cpp两host | 109/111 |

这里没有新增CPU Release构建分支。CPU准备的源祖先仍绑定真实 passed
`upl_tpi_cpu_release_link_r3`，不能把旧失败ReleaseCPU_r2称为通过构建。
CPU Debug保留对象来自其完整86源实际Debug构建，不借用Release对象或Release库表冒充。

CPU Debug真实CL/link recipe来自其 `CL.command.1.tlog`、`link.command.1.tlog`，
保留原MSBuild child出口与tlogs的证明范围，不虚构历史per-tool句柄出口。
新两CL及link将单独以已有已审 `upl_tpi_cpu_build_r2.invoke` 真实调用并记录
Popen、Win32句柄出口、创建时间、argv与日志。

GPU Debug r2曾只新编CU并采用r1三个host，因此两个host CL recipe分别取真实passed
`upl_tpi_gpu_Debug_r1.JSphGpu/JSphGpuSingle.call.json`，链接取真实r2 link。
GPU Release取r3的Gpu CL、full2tv_r1的Single CL及full2tv_r1 link。
原111对象顺序保持，保留CUDA的两个 `.h.obj` 和全部14个CUDA对象，不调用NVCC。
默认A是否精确仍须后续实际原生资格，不由“未执行分支”或构建成功推断。

## 源边界与ABI

读取唯一 passed `upl_tpi_m0_dt_CPU_r2.prepare.json`（267平铺文件）或
`upl_tpi_m0_dt_GPU_r2.prepare.json`（270平铺文件）。
新host-only接口为 `upl_tpi_m0_dt_r2.h`。

CPU仅两个host源码变化。GPU仅两个host源码和原 `upl_tpi_gpu_r1.h` 的
`UPL_TPI_GPU_R1_IMPLEMENTATION` 主机实现块变化，device可见声明前缀不变。
构建前逐字节核私有公共类/外部kernel头、旧CU/cuh/HG body及TPI声明前缀；
如变化，拒绝两host复用而不是静默采用旧对象。
这没有新增类成员、布局、虚函数、CUDA参数或device描述符。

CL保留实际VS recipe的优化、CRT、`/fp:precise`、OpenMP等选项。
只重定向新源、首位私有 `/I`、Fo/Fd及sourceDependencies；旧私有源include被删除，
CUDA/toolchain include不删除。实际依赖必须包含新policy头和冻结JSph.h，且不能读live源头。
编译器PDB、程序PDB、ILK、LTCG、import lib、exe及所有新中间产物各自新路径，
旧 `/Zi` 对象仍需要的原compiler PDB以stat保留为只读依赖。

## 库和运行依赖

沿已成功验证的相对 `environment.cmd`/cwd方式加载MSVC14.36与SDK10.0.22000。
GPU保持此环境；CPU Debug原实际MSBuild使用Windows8.1和UCRT10.0.10240，
所以只在CPU分支按其两个host的真实CL.read取UM/shared/UCRT三个include roots和
所有实际读取SDK头stat，前置到完整vcvars INCLUDE；按真实link.read库目录前置LIB。
旧SDK与GPU不同，不能称两者使用相同SDK或仅靠Release库表证明CPU Debug。
保留原vcvars完整INCLUDE/LIB作为原样后缀，不覆盖或漏掉隐式CRT目录。
对每个配置按真实link recipe和实际旧link读取记录/已审搜索记录核first-existing库，
CPU Debug使用自己的23个实际Debug库；GPU Debug/Release各自27/26个真实库。
不运行新程序来验证依赖；只复制原passed对应配置的runtime目录叶并记录stat。
Debug保留vcomp140d，Release不借Debug DLL。

## 新路径、准入和证据

标签：`upl_tpi_m0_dt_{DebugCPU,Debug,Release}_r2`。
输出：`tests/outputs/<tag>/out`。
新IntDir：`%TEMP%/upl_tpi_m0_dt_build_r2/<configuration>/int`。
收据：`tests/logs/<tag>.build.json`。
所有目标、收据或partial已存在即拒绝，不重试或覆盖。

根准入：`stage=upl_tpi_m0_dt_build_r2.build_admission`、`passed=true`、
`build_only=true`、单一 `configuration`，`inputs`覆盖所有实际消费的path/bytes/mtime_ns。
包括本脚本/note、两个复用build helper、vcvars/cmd/CL/link、实际VS项目/solution、
新prepare/完整源树及其源祖先/差异、各原build/program/objects/compilerPDB、
CL/link recipe/tlog与Debug真实库、相应runtime；CPU另外包含两个host实际CL.read
消费的旧SDK头（按路径去重），不扩为扫描整个SDK。

收据记录完整86/111的有序对象和新2/保留84或109、源准备、真实CL依赖、
库搜索、runtime、tool调用出口、源/对象stat保持情况及所有新输出。
仅对新生成EXE做一次SHA身份；旧源码/objects/BI4均不扫SHA。
构建成功不代表device fixture、必要时步、native或物理验收，不自动执行任何后续工作。

```text
python -B tests/support/upl_tpi_m0_dt_build_r2.py --configuration DebugCPU --execution-authorized --admission ROOT_JSON
python -B tests/support/upl_tpi_m0_dt_build_r2.py --configuration Debug --execution-authorized --admission ROOT_JSON
python -B tests/support/upl_tpi_m0_dt_build_r2.py --configuration Release --execution-authorized --admission ROOT_JSON
```

## r1失败保留与r2最小修复

原r1实际CPU Debug编译因base `JSphCpu` 不含derived的 `HourglassCpu` 成员而C2065；
旧失败收据、call、log、全部作者和源树均保留，不重试或覆盖。GPU base同样不持有derived HG成员。
r2 source只把该Record参数改为DBL_MAX，并在policy/summary声明
`HG_limit_reference_available=false`。CSV的min_HG列是unavailable sentinel，
不能把它当作实际HG限制观测。原derived HG硬安全检查和实际HG summary继续保留；
不改物理方程、类ABI或CUDA。builder相对r1仅改新prepare/header/build/source/输出标签，
旧passed基座、SDK闭包、2host编译及有序链接逻辑均不变。
