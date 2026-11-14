# C08 H1.8 AV.2：schema2私有host覆盖与两后端构建（作者稿）

本次只编写`tests/support/c08_h18_av20_build_r2.py`与本文。没有导入/执行准备脚本，没有生成source/build outputs，没有构建、程序help/smoke、求解、原生读取、VTK、哈希或Git。公共C++/CUDA、VS项目、原程序、PRE、XML/BAT和旧失败/结果均不改。根线程完整审阅后须分别准入prepare及各次build；build不授权运行程序、下一物理窗口或其他ψ。

目标是一个机制驱动的有界敏感性候选：原AS.3/n2.55/H1.8状态的零推进审查显示，人工黏性对某些持续接近材料对提供明显分离方向的相对加速度，但被其他邻域贡献抵消。这里只准备将**真实撤墙之后AV从.1改.2**的私有程序，以供根线程后续另行决定smoke及唯一.90s窗口。它不来自Lian表中alpha=.5（该值是TPI历史系数），也不预先保证消除静态小间距团聚。

## 原始来源和最小数值干预

源码唯一来源为已通过`logs/c08_preload_schema2_Release_r1.build.json`绑定的`outputs/c08_preload_schema2_source_r1/full_source.zip`，不是当前public或旧H1.2/keep5/AV15原型。CPU基线为`logs/c08_h18_restore_DebugCPU_r1.build.json`及已经封存其87对象的`logs/c08_h18_late_rhs_r1.build.json`。两后端必须指向同一full_source capture/archive，真实原MSBuild Popen/Win32出口均0。

原早期`source.json/changed_source.zip`的四个变更记录另作窄审查：`JGravityPreloadState.h`、`JSph.cpp`、`JSph.h`与full ZIP对应成员逐byte一致；第四项`doc/xml_format/_FmtXML_ElastoplasticSoil.xml`是编译源ZIP范围外的文档，仍在changed ZIP中，不是缺失的编译源。没有据Single未直接引用某个继承成员就推断归档错误。

prepare在新的`outputs/c08_h18_av20_source_r2`中只改变ZIP的三份host CPP：

- `JSphCpuSingle.cpp`和`JSphGpuSingle.cpp`：原schema2导入、retire255、divide/count检查完成，且实际`GravityPreloadReleased=true`之后、最后phase=released日志之前，检查当前候选的bedroles/keepfalse、原2M-step事件、6805/1805活动数、同材料塑性容器资格、NoPen固定平面、Wendland/dp.04/H.072/5us、AS.3/n2.55、Visco.1/BoundFactor1/无ViscoTime及ψ0材料，然后唯一设置`Visco=.2f`。
- `JSph.cpp`：仅对真实handoff且已释放的target保存三个typed键：`DynamicArtificialViscosityPolicy`文本`ReleaseOnly`、`DynamicArtificialViscosityOverrideActive`布尔`Visco==.2f`、`DynamicArtificialViscosityCoef`为实际Visco。若有未预期后续改值，Active不再冒称true，独立native应拒绝。

原PRE、XML、schema2合同和startup Configuration保留AV.1。新程序先以原输入认证并继承实际p/P0/σ/κ/J等历史，再覆盖释放阶段黏性；不改PRE、材料公式、AS、Darcy、积分/接触、FS或必要步长。AV=.2由每stage的当前host参数传入原CPU/GPU邻域函数，不修改CUDA常量或kernel，不需要新数组/接口/类字段。实际AV加速度仍进入同阶段Darcy，其耦合影响须靠后续真实窗口审阅，不能仅凭机械耗散增加认定改善。

每处插入须唯一、能删除插入后逐byte恢复原CPP；ZIP其余成员逐byte保持，成员顺序不变。准备输出为三份私有CPP、`source.patch`、`source.zip`、`source.json`，以及`logs/c08_h18_av20_build_r2.prepare.json`。不修改或提取到旧source目录。

两份Single另在原Single头包含后明确加入`JDsFixedDt.h`，因为新增guard首次直接调用`FixedDt->GetFixedValue()`，不能依赖转接头偶然补齐类型。该private include同样逐byte可逆，不改变类布局或物理公式；无第四份源码或公共头变化。

## 构建闭合

脚本只接受`DebugCPU`与GPU`Release`两种构建。每后端只编译common JSph和对应Single两个host TU，其余原对象和原main全部保留；DebugCPU为87对象，GPU为113对象（包含原CUDA对象）。没有GPU Debug、CUDA编译、公共默认CPU Debug重建或canonical程序安装；这是冻结源私有覆盖，后续公共源码若变化应另按项目规则构建。

对象和编译/链接命令来自两个原真实MSBuild call中的IntDir及其权威VS tlogs。CPU对象当前stat必须与已成功late-RHS封存记录逐项一致。原GPU构建收据未逐项保存对象stat，因此本文**不虚构历史对象哈希/封存**：GPU使用原私有IntDir及权威tlogs，拒绝晚于原构建完成时刻的对象mtime，在本次prepare首次记录该清单的实际stat，之后build前后保持。原程序/capture/archive及构建call也被绑定。若这些绑定有变化应诊断，不重建旧目录或盲目采用。

本次只读来源核对未见共享覆盖或矛盾：GPU IntDir为专用`C:/Users/syosh/AppData/Local/Temp/c08_schema2_build_r1/Release/int`；原MSBuild call真实窗口为2026-11-09 11:16:10.677785至11:18:47.710289 UTC。113个当前对象（含12个`.cu.obj`）mtime范围11:16:27.983至11:18:39.963 UTC，全部处于原窗口。CL/link tlogs同窗，CL `/Fo`及全部链接对象指向该私有目录；CUDA read tlog列原`src/source`成员，write tlog的12个CUDA对象全部写入该目录，无外部对象输出。对tests/logs中引用此IntDir的真实call参数只读检索，唯一写入该目录的已记录调用是原schema2 MSBuild，未见后续私有候选覆盖。CUDA read/write tlog也加入本次准备的stat绑定。上述是合理来源证据和当前首次stat封存，不能倒称为原构建时已经保存了对象hash，也不能证明不存在未记录的外部写入；当前没有要求clean重建的实际证据。

CL参数沿MSVC14.36原DebugCPU `/Od /MTd`或Release `/O2 /MT`，保留`/fp:precise`、OpenMP和对应`_WITHGPU`。prepare不执行MSVC环境。build才提取私有ZIP全部源码到新build的`frozen/src/source`，把160个原归档头置于include首位，禁止实际依赖泄露到current public。两TU独立PDB/OBJ及`sourceDependencies`，链接命令只替换两个OBJ和新输出位置，原库从实际link.read tlog解析；不重建VS项目或换构建系统。

源程序、对象、tlogs、库、runtime及本次依赖在所选build前后检查stat。按原runtime复制9个文件（含GenCase/PartVTK、config和DLL）到新目录并验证复制bytes；没有反复SHA扫描。工具调用沿既有`m.invoke`保留实际Popen/Win32出口与日志。失败保留首因和新partial，无自动重试、清理或下一动作。

成功产物/收据：

- CPU：`outputs/c08_h18_av20_DebugCPU_r1/DualSPHysics5.2CPU_win64_debug.exe`；`logs/c08_h18_av20_DebugCPU_r1.build.json`。
- GPU：`outputs/c08_h18_av20_Release_r1/DualSPHysics5.2_GEO_win64.exe`；`logs/c08_h18_av20_Release_r1.build.json`。

build收据中`program`是私有exe，`source_capture/archive`指私有source.json/zip；`base_original_source_capture/archive`、`base_program`、`baseline_source_build`保留实际原来源；`runtime`为复制目标Entry列表。`allowed_runtime_backend`分别为CPU/GPU：GPU构建只重编GpuSingle，不得用其`-cpu`路径冒称已经实施AV.2。`class_layout_changed=false`、`physical_objects_recompiled=2`、`CUDA_compile_invocations=0`、`trace_macros_enabled=false`。成功build本身不表示数值或物理验收。

## 后续显式动作

根线程全文读完后可分别决定以下命令，本作者阶段均未执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_av20_build_r2.py prepare --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_av20_build_r2.py build --configuration DebugCPU --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_av20_build_r2.py build --configuration Release --execution-authorized
```

之后先单独准备/准入CPU小smoke和对应schema2/bedroles native适配器，检查真正释放后typed AV.2、原22数组、P0/κ/J/ledger/FS/clock/必要步长，再由根决定唯一GPU.90s窗口。原AS255 reader明确拒绝AV私有键，不能直接拿它代替新适配器。源PRE不要求target新元数据，不能把缺键认作原PRE失效。原Visco.1启动文字不是AV.2的独立证据，必须结合私有源码/构建、实际override日志、每帧typed值及真实输入程序绑定。没有自动decoder、VTK、solver、PRE重算、half链、其他ψ或watcher。

## r2 packaging repair

The original r1 prepare exited1 before any build/solver. ZipFile.writestr modified the reused source ZipInfo CRC in memory; a later original read then raised Bad CRC for JSphGpuSingle.cpp. A fresh original ZIP instance successfully read all three original host members and original archive size/mtime remained unchanged. This r2 uses copy.copy(entry) when writing each destination entry. Original r1 script, failed receipt/log and partial source directory are preserved. Numerical insertions/guards/build recipes remain identical; backend build tags remain r1 because no backend build had been started.
