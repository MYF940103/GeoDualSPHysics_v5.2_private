# Fixed-plane short smoke/OFF review（author-only）

本稿未运行、import或AST检查。只读封口native/owner收据与原typed22，不启动solver、decoder、build、通知或下一物理任务。`smoke`和`off`是独立CLI阶段，各要求自己的新CSV/JSON不存在，不自动串联。

旧OFF选择为`outputs/upl_c08_as_short_r1_off_native`，receipt为`logs/upl_c08_as_short_r1_off.native.check.json`，原owner为`logs/upl_c08_as_short_r1_off.run.json`。已只读核实原Run.out明确NoPenetration=False、ArtificialStress=None，原dt2.5us/TimeOut.01、ψ0/cp5000/cr1000/ncoh5/φ25/sf0、Cubic、Ck2、free-seepage、原r2 PRE及唯一260退休。原native11帧又与最初失败11帧完整记录一致；不能用NoPenON或r4替代，也不将旧失败solver改称成功。该OFF owner本身曾完整正常退出到其显式44k更新上限。

未来smoke输入固定为`outputs/upl_c08_plane_smoke_{CPU,GPU}_r1/native`及各自`logs/<tag>.native.json`；只在两份真正passed、consumed_stat保持且native owned exit0后读。原22数组schema来自已审SCHEMA，速度为独立`Vel` float3，密度为`native_Rhop` float；保留原6800 IDs、5000soil/1800fixed、P0/J/ledger/κ/FS/时钟/非空signed必要界原守卫和原两帧header。每材料实际time/Step匹配后，按原预算逐帧核土体压力RMS差≤5Pa和每个xyz最大差≤.005mm（5e−6m）。这是Debug CPU与Debug GPU的数值比较，不声称Debug/Release 0ULP。两帧计划为global4000400/4000800，真实clock仍读native，不伪造t0。

OFF输入固定为`outputs/upl_c08_plane_off_GPU_r1/native`和`logs/upl_c08_plane_off_GPU_r1.native.json`。核新旧实际NoPen0/AS0、同原PRE，比较材料/水力/分面边界/initialize/constants和原参数（只排除不同的总结束时刻；旧缺省NoPen/AS均按0显式等价），TimeOut.01保持。新3帧为global4004000/4008000/4012000，仅比较旧11帧中实际time/Step相同的首3帧，包含8字节实际时间和22数组的完整record逐字节及原clock header/三行（包含signed dterror）逐字节。3vs11的真实12字节header分别记录，绝不重写、裁短原文件或拿另一算子当OFF。

新native receipt的flat consumed及outputs按已有path/bytes/mtime核验，直接reader actual_call必须Popen/Win32均0且ownership_failure为空；不递归历史或扫描/哈希原BI4。completion原计数与原clock/ledger/signed门保持，不新增物理误差预算。旧receipt没有flat consumed时只核其现有files/native_completion/actual_call，以及原owner直接输入/PRE/Run.out绑定，不虚构缺失字段。

CLI为`python tests/support/upl_c08_plane_short_review_r1.py smoke --execution-authorized`或`off --execution-authorized`。每阶段产物分别为`logs/upl_c08_plane_short_review_r1.<phase>.json`和`figures/upl_c08_plane_short_review_r1_<phase>.csv`；失败也保留首因/已生成CSV，不覆盖或自动重跑。source与所有比较输入前后stat，无SHA、无新half或正式3s接受声明。
