# 私有ReleaseShepard40候选：构建作者稿

本轮只新增 `tests/support/upl_c08_shepard_release_r1_build.py`、本说明，以及 `tests/outputs/upl_c08_shepard_release_r1_source/` 的私有Single.cpp、diff、source.json/source.zip；尚未构建、运行求解器或解码。正式源码、旧程序、PRE、XML/BAT和历史输出不变。这是待验证的existing-operator诊断，不是生产默认策略或物理验收。

基线只取已封口 `upl_c08_bedkeep_{Debug,Release}_r1.build.json` 及二者共同的bedkeep源码归档；不采用effective-AS程序或源码。完整私有ZIP与原归档相比只有 `src/source/JSphGpuSingle.cpp` 变化；四处替换可逆还原原CPP全部字节：显式标准头；原Shepard调用前后加入只读计量；撤墙时只关闭damping而保留loaded Shepard flag；release日志真实输出ON/OFF、interval，并声明旧公共preload-only描述不适用于该私有候选。原PRE导入临时hold和合同完全保留，无新参数、无类布局/CTE/原生数组变化。

原AS仍是total-stress实现，参数由后续case选择 `.2/n3`；本构、V0J、核、Darcy、接触、积分器及原filter kernel都不改。原XML `PoreShepardRegularization=1 / PoreShepardInterval=40` 必须由实际执行输入绑定证明；本程序不强制改写配置。撤墙日志为：

```text
GravityPreload: phase=released actual=... completed_step=... retired=...; damping=OFF Shepard=ON interval=40 FreeSeepage=ON.
Private ReleaseShepard: retains loaded XML flag after release; old public preload-only description is not applicable; metering covers smoothing plus FS projection, not fluid-mass conservation.
```

滤波仍位于原RunCellDivide完整步分支：FS/原边界处理→墙状态→Shepard wrapper→墙状态。仅 `!PorePressPreg && (Nstep+1)%Interval==0` 触发；half不滤波。wrapper平均的是 `p−P0`，用self/soil/有效mDBC墙的V0J权重，再加回P0，并对同一FS mask作原positive-only投影；不硬截负压。论文Eq46仅明确用于§4.5，不能把本C08候选说成论文默认设置，且此实现保留自身excess-pressure基线政策。

仅在实际 `GravityPreloadReleased` 时记录 `DirOut/C08ReleaseShepard.csv`，每个成功完成的wrapper调用一行；static vectors复用容量。完整header：

```text
call,Nstep,completed_step,step_start_time_s,operator_dt_s,soil_IDs,interval,storage_before_m3,storage_after_m3,delta_storage_m3,sum_abs_weighted_delta_m3,max_abs_delta_p_Pa,changed_pressure_bits,p_before_min_Pa,p_before_max_Pa,p_after_min_Pa,p_after_max_Pa,primary_bitcheck_performed,primary_bitcheck_passed
```

`call`从1实际递增，不由计划推断；completed=Nstep+1。TimeStep尚在外循环`+=dt`之前，因此保存为step_start_time_s；operator_dt_s是原SymplecticDtPre字段，候选固定步应为2.5µs，不把日志标签当native保存时钟。对同一份filter前J求n=1−(1−n0)/J、V=(MassFluid/RhopZero)J及 `S=Σsoil(nV/Kw)p`；before/after只比较该wrapper（平均＋其内部FS投影）的合成作用。它不是fluid mass，也不承诺守恒；二维体积按模型单位厚度解释。changed_pressure_bits计float位变化（含有符号零）。首调用另下载P0/J/κ，逐字节检查未变；首行performed=1、passed=true，后续performed=0、passed为空。这只是实现侧检查，不是输运/耗散/物理精度证明。任何IO/CUDA/实现检查失败保留真实部分CSV。

预期80update smoke为2次、0.90s/360000update为9000次，但必须用实际CSV计数证实。每次计量下载土粒p前后与J；5000土粒的9000次主体约0.72GB，首调用额外字段和同步开销另计。原滤波还新增每40步一次邻域平均及前后墙重建；不得预称开销可忽略。滤波可削弱真实压力峰、改变相位及储水指标，需要独立对照。PoreShepardActive将由既有metadata真实输出true；旧要求false的reader不能直接用于该候选。

根全文审阅后，每个配置单独准入一次构建：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_shepard_release_r1_build.py --configuration Debug --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_shepard_release_r1_build.py --configuration Release --execution-authorized
```

新路径为 `tests/outputs/upl_c08_shepard_release_{Debug,Release}_r1/`；程序分别 `DualSPHysics5.2_win64_debug.exe`、`DualSPHysics5.2_GEO_win64.exe`；收据 `tests/logs/upl_c08_shepard_release_{Debug,Release}_r1.build.json`。从每配置权威CL/link tlog重编一个host TU，保留原112对象并链接113对象；冻结归档全部source/headers，核实际sourceDependencies使用同一类布局。编译保持原MSVC14.36、Debug/Release原选项；无CUDA重编、无project/canonical写入。各新目录复制原runtime_r6的7个DLL/config并核copy2 bytes/stat。构建器拒绝已有/部分构建路径，捕获真实CL/link出口，完整记录source/object/runtime stat；无SHA扫描。构建通过后仍需根独立准入smoke/原生/计量检查，任何正常退出都不代表物理通过，不自动衔接窗口或其他ψ。
