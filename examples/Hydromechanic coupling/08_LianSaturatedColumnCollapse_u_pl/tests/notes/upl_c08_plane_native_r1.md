# C08 fixed-plane bounded native reader（author-only）

新 `support/upl_c08_plane_native_r1.cpp`、`_build.py`、本说明，机械派生已审 `c08_post_native_r4.cpp`；未构建/读取/求解。仅psi0，源仍原r2/PRE1000实际累计10秒/4Mstep/dt2.5us，legacyMR1或unified2 qualifiedElastic通道不改。无新增half/长算，不复用作失败partial读取器。

## 显式单次读取接口

`C08Native_win64.exe --read psi0 CPU|GPU DATA PRE ENDSTEP SAMPLES NOPEN STEPS_CSV FRESHOUT`

ENDSTEP/SAMPLES为启动前已授权目标的global结束步/真实保存数，NOPEN必须0或1；没有新的硬编码窗口。正常Run.csv必须同时满足Steps=ENDSTEP、PartFiles=SAMPLES、原7060registry/2060fixed/0exclusions，标准Part文件必须完整连续且数目相同。真实程序exit0、程序/配置/源PRE/stat绑定仍由调用owner核验；库参数本身不能证明backend或实际程序身份。

为避免首帧/输出cadence/forced final猜测，STEPS_CSV由物理owner根据实际配置**在启动前冻结**，不能解码后抄BI4来伪造计划。只两列 `part,completed_step`，恰好SAMPLES行：part从0连续、global completed严格递增，最终等于ENDSTEP。例2ms/1ms输出可为0,4000400和1,4000800；若仅forced final一帧则为0,4000800；off .03s/10ms为4004000/4008000/4012000，.6s60帧为每4000更新到4240000。读取器每个BI4实际Step+1必须等于相应CSV；真实首帧是post-PRE更新后的状态，不能伪t0/PRE。每个actual time仍用原scalar +=2.5us从真实源时钟推进，signed dterror原nonempty及<=1e-14门保持，无n*dt替代、无元数据改写。

## 原生门与NoPen/gap

全部22typed原数组/6800 IDs、5000soil、1800retained fixed、P0 bit、κ单调、J/n/V/rho/k/FS、显示float应力缓存、ledger5e-13、真实clock1e-14、signed dterror门完全保留。

NOPEN1每帧必须typed text `DynamicNoPenetrationPolicy=FixedPlaneStageProjectionReleaseOnly`、bool Active=true、bool ReactionClosed=false。NOPEN0预计无该policy，不强制开启门；若出现Active=true或Active类型错误则拒绝，policy意外存在的帧数在completion记录。源PRE不套目标NoPen active门。

新增 `plane_gaps.csv`，对全部5000土粒每帧独立观测最小x/z与对应native ID、x<0/z<0计数。此专用C08冻结几何的理想左面x0/底面z0用于观察，不从FSNormal推导墙面；真实source normal镜像float偏移可使实际plane约偏1e-9m。NOPEN1逐粒按原几何planetol=1e-6*Dp=4e-8m核x,z>=−planetol，未增加新的容差或修改原核门；NOPEN0仅描述gap，不以该门拒绝原算子。实际derived planes与源normals完整性须由物理owner/原程序原固定面几何准入保证；本读取器不声称支持任意平面/曲面/移动墙。

输出原typed22.bin/layout/clocks/history不增数组、不改字节布局；另plane_gaps和completion范围字段。actual_end_s来自最后真实BI4，scalar_replay_end_s另列。reaction_J_Darcy_closed=false、same_operator_PRE_contract_claimed=false、physical_acceptance=false。接触/J/Darcy未闭合不因gap通过改称闭合；正常summary与native通过不是物理验收。

build helper只取封口mdbc_partition ReleaseCPU build的6个BI4 utility对象＋冻结头，加自己的reader.obj共7对象，不链接JSph、GPU核或正在增长的工程对象，不写旧objects。新程序 `outputs/upl_c08_plane_native_r1_build/C08Native_win64.exe`。根全文审后一次显式build：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_plane_native_r1_build.py --execution-authorized
```

每个actual job使用独立FRESHOUT和实际启动前CSV；此作者不写新物理owner/新solver、不自动读取、queue或retry。已有输出/partial保护，无SHA扫描或正式包修改。
