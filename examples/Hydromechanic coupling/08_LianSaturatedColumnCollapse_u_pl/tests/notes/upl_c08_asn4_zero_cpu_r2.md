# n4 爆发前两态的实际 CPU 零步部件（作者稿，未构建/未执行）

仅新增同名 CPP、build.py、run.py 和本 note；不改生产源、旧 helper、正式输入、程序或原结果。输入是已封口失败 n4 的 `outputs/upl_c08_asn4_window_GPU_r1/native_partial_r1`，part29（实际 τ≈.30）与part64（τ≈.65），不是失败子阶段。原求解 exit1 保持失败身份；66帧 native 的22数组/6805 IDs/ledger/P0/FS/κ/plane/clock/signed 门保持。

`build.py` 仅编译一个测试 CPP，再链接 **upl_c08_bedkeep_DebugCPU_r1** 的86非main对象（项目87含main）；不用旧mdbcPartition物理对象。必须与 runtime_r6 的 bedkeep Release GPU build 的 source_capture/source_archive 完全同一 Entry。从这一个封口 source.zip 提取 src/source 的头文件到新 helper 私有目录，CL 的 sourceDependencies 必须证实 JSph/JSphCpu/JSphCpuSingle 来自该目录。使用已有通过的 CPU Debug component CL/link argv，MSVC14.36、/Od /MTd /fp:precise /std:c++17 /openmp，匹配 Debug DLL/config；不做全项目构建或 CUDA 编译，不扫描 SHA。

初始化严格沿真实 `LoadConfig/LoadCaseParticles/ConfigDomain/InitRunCpu → RunGravityPreloadHandoffCpu → RunGravityPreloadRelease`。读取已存在 n4 GenCase seed/XML/Normals 及原 r2 GPU certified PRE；不运行 GenCase、不生成新PRE、不绕 loader 合同。完整PRE一次资格加载、keep5释放一次，得到实际6805=1805固定+5000土。固定 Code/BoundNormal/BoundSlipMode 来自真实种子与释放：保留1800/1852/1904/1956/2008，法向 +float(dp)Z / NoSlip；不从 typed FSNormal 猜墙法向，也不手工设置 Np/Npb。

四次评估明确为：part29 AS4、part29 AS3、part64 AS4、part64 AS3。每次完整按 native ID 恢复输入22主状态、真实 LoadDcellParticles/RunCellDivide，再按 ID 重拷输入防止重建的额外更新混入。调用现有 `JSphCpuSingle::Interaction_Forces(INTERSTEP_SymCorrector)`，到导出后 `PosInteraction_Forces`；其完整路径为 wallState → FS/C → wallC → PrepareAS → ct → finished wallAce → Darcy。全部5000土参与真实邻居循环；81限制只用于输出。四个显式focus7013/7015/6963/7014必在输出内，其余按到focus最近距离、nativeID确定排序，取2R内最多81点。相关墙是这些输出接收点真实R内的固定样本。

每次检查全部5000土的 pos、vel/rho cache、double σ′、κ、p、P0、J 位不变，静态 ID/Code/墙角色不变；保留原 finite/saturation 守卫。重算 θ/Rσ/Ace/rate/FS/C 本身是本部件目的，FS相对saved的改变数量写入 evaluations.csv。无 predictor/corrector更新、无 ReturnMaterial、无 p/J/κ/位置积分；NoPen不执行新的位置/速度投影，reaction闭合仍为false。actual source时间/保存time/global Step和原 signed dterror 全由封口 clocks/native核对，不用 n*dt。

`receivers.csv` 记录实际 C、θ、Rσ（xx,yy,zz,xy,yz,xz）、Ace、rate与输入状态。五项分解只在测试侧按**这次实际完成的 C/Ace/θ/p/J**、完整所有粒子支持重新求和：

- compression = −(Kw/n)θ；LP = (Kw/n)(ki/γ)lp。
- defect = (Kw/n)(ki/γ)[FS2/3时 ρw ai·lx，否则 −gp·lx]。
- divAce = (Kw/n)(ki/γ)ρw ΣVj(aj−ai)·Ci∇W。
- chain = (Kw/n)/γ ·[ki/((1−n0)Ck)]∇J·(gp+ρw ai)，γ=ρw·9.80665。

沿原动态函数的 **exp** k(J) 与原 Eta²、pair Ci+Cj；没有变k公式或分母修改。五项和对实际 float rate 使用既有零步部件的传播预算：`(32 FLT_EPS + gamma_(64N+256))*max(1,传播绝对scale)`，N是实际非self支持数，`gamma_m=m*DBL_EPS/(1−m*DBL_EPS)`。这是算术一致性预算，不是物理压力阈值。`walls.csv` 输出实际 B/normal/slip/mode/J/p/P0/σ′/C/Ace/derivative/tangent velocity；墙没有土体Rσ/rate更新，不伪填这两项。

局限：这是同一保存输入上的 **新CPU完整force-stage评估**；源来自GPU，重建C/FS/墙与保存GPU packed/FMA/真实半步不同，不是原率或失败态重放。AS3是在 n4 几何/历史上作同输入单项对照，不是n3轨迹。完整 ct 含有效应力、孔压、AS、AV等实际贡献，输出总Ace，不能据四次值声称已分离其压力Jacobian/完整耦合谱、已解释爆发因果、或已准入其他ψ。

根全文审阅后，后续显式分开执行；本轮仅 AST/文本静态检查，尚无 CL/link/部件运行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_zero_cpu_r2_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_zero_cpu_r2_run.py --execution-authorized
```

新helper为 `tests/outputs/upl_c08_asn4_zero_cpu_r2_helper/component.exe`；新结果 `tests/outputs/upl_c08_asn4_zero_cpu_r2/{receivers,walls,evaluations}.csv/completion.json`，对应 logs 下 `.build.json/.check.json` 和独立 CL/link/run call。拒已有/部分输出，真实handle等待并先封存typed退出；失败不覆盖、不自动重试，不运行solver/native/VTK/队列。

## r1 ??? r2 ????

r1 ??????????????? Popen/Win32=1??? LoadConfig:636 ?????????? PRE???? force?? r1 ??/??/??/????/?????????r2 ??? main ? LoadConfig ????? Sv_Binx/Sv_Info ????????? argv ???? -svres????? SaveData?ComputeStep ????????????????? loader ??????????r2 ???/??/????????????????
