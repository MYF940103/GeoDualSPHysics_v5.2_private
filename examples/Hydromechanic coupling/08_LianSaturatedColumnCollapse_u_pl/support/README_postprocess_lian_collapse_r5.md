# C08 r5 ψ0 后处理

本文件与新脚本目前为作者稿，待根线程审核后使用。r5仅准入ψ0的完整3秒诊断；ψ+2.5°、ψ−5°和preload后处理入口在本脚本中拒绝，不把预备XML当作已准入算例。旧r3/r4程序、runtime、PRE、失败partial和已生成图全部保留。正常结束及后处理通过均不是论文物理验收。

需要Windows x64、Python3及NumPy/Matplotlib，以及根线程安装到 `support/runtime_r5/` 的匹配 `C08Native_win64.exe`、`PartVTK_win64.exe` 和既有依赖。不会自动安装依赖、切回旧reader或启动solver。

```powershell
D:/anaconda3/python.exe -X utf8 -B support/postprocess_lian_collapse_r5.py --check-tools
D:/anaconda3/python.exe -X utf8 -B support/postprocess_lian_collapse_r5.py --group psi0 --outdir CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out --source-pre CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4
```

正式双击BAT在唯一solver成功后调用同一脚本；公共launcher的 `--postprocess` 模式只调用后处理，不能落回GenCase或solver。post脚本不依赖尚未写出的owner总Run.json：实际外层owner在整个BAT结束后另封口，脚本先验证已完成的Run.csv/Run.out和实际生成XML。若solver正常而派生步骤失败，保留 `postprocess_r5.failed.json` 中的 `solver_completed=true` 和工具调用记录；只修后处理，不能重算原始轨迹。

脚本接受global5200000、300个真实保存帧及原Run.csv注册7060/2060/2060、无粒子排除。Run.csv仅允许已验证的 `Configuration` 中 `AS_Bui2008(0.2;2.55)` 单个未引号分号修复；不泛化猜列、不改写文件。实际XML必须为ψ0/coh5000→1000/eta5、Cubic h/dp1.2所用配置、dt2.5µs、TimeOut.01、TimeMax13、Model1/Ck2、FreeSeepage、AS1/.2/2.55及 `keep_bed_overlap=true`。NoPen政策为 `FixedPlaneStageProjectionReleaseOnly`；AS为 `ReleaseOnly`。

先对 `out/native` 调用一次已审核正式reader：

`C08Native_win64.exe --read psi0 CPU|GPU DATA PRE 5200000 FRESHOUT`

backend由真实Run.csv Hardware推断，reader自身不证明硬件。实际6805=1805 fixed+5000 soil；保留原ID1800/1852/1904/1956/2008，原release target仍260、实际退休255且ID集合不连续。kept5保持原固定MK code，但事件后的法向/NoSlip是逐粒子覆盖，不应只据VTK的MK12判断为右墙。全部22数组、source PRE认证、J/ρ-cache/κ/P0/FS/clock/signed/平面原门及逐帧bedkeep/AS元数据由新reader校验；不重新解码source的1001帧，也不把首post帧当PRE/t0。

随后用相同数据各导出300个 `particles/PartFluid_####.vtk`（5000点）和 `PartBound_####.vtk`（1805点），不生成PartAll。沿用变量表、`-filexml`实际生成XML、`-threads:1`；每套有独立成功调用清单。VTK位置为既有工具的float输出，精确物质位移采用native/history的double PRE基准。

GPU图默认在 `figures/collapse_psi0_r5`，实际CPU数据使用单独 `_CPU_r5` 目录；这不是授权CPU新求解。可显式 `--figdir` 指定新目录。history PNG/CSV含压力均值/极值、mean材料沉降（向下为正）、真实PRE位移RMS/最大值、实际前缘x与最大高度、κ/n/k、速度、总应力和J。没有per-ID double PRE位置出口，因此不伪造顶部/底部材料层位移。

保存态散点PNG及同名5000点CSV覆盖τ=.1/.3/.5/.6/1/1.2/2/3秒，并另合成 `paper_times_psi0_fields` 的.3/.6/1.2秒面板；这些时刻沿用既有Fig14原文视读记录，不重采或改写论文图。图中使用真实actualτ，不插值。总孔压 `PorePress` 与原生 `ExcessPorePress` 分列显示，CSV分别保存 `PorePress_Pa` 和 `NativeExcessPorePress_Pa`；history另画已有的 `native_excess_mean_Pa`。原生超孔压是p减去固定材料初始P0，不是推断的当前水位静水场，也不能直接称为纯塑性超压或论文唯一的参考定义。Lian2023 Fig14–15展示excess，Fig16才展示total；`paper_times`仅表示时刻对应，两种压力口径不可混同。总孔压、原生超孔压、κ、n、k各自颜色范围均来自**全部300帧的原始土体min/max**，保留负值，不clip、不平滑、不调色域贴图；常数场单色并标实际常数，不造假色条。论文时间面板用于初步查看，不是自动精度评分。

成功native/VTK调用仅在argv、输入和输出stat全部匹配时复用，不重复工具。已有失败调用或无清单partial拒绝自动覆盖。图形首次生成要求空目录；中途图形失败后保留该目录，修复时使用新的 `--figdir figures/collapse_psi0_r5_repair1`，成功native/VTK仍复用。最终 `postprocess_r5.json`、各call及图形manifest记录完成项；已有成功收据不覆盖，首个失败记录也保留。无自动下一材料、额外求解、half链或参数试探。
