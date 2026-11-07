# C08 Release-only人工应力短序列（author-only）

本轮只新增 `tests/support/upl_c08_as_short_r1.py`、`upl_c08_as_bounded_native_r1.cpp` / `_build.py`，两份 `tests/configs/upl_c08_as_short_r1_{off,on}_Def.xml` 及本说明/读取器说明。不修改生产源码、正式三组XML/BAT、runtime_r3、服务器包或旧收据；目前未构建、求解、读取或布防。

## 唯一执行计划

先由根完整审阅并构建新的bounded reader；新AS Release build `logs/upl_c08_artstress_Release_r1.build.json` 与独立CPU/GPU组件聚合 `logs/upl_c08_as_unit_r1.check.json` 必须真实passed。owner仅消费聚合passed及stat，根负责审聚合内实际调用/比较。读取器两份build也必须在启动求解前通过。

1. OFF配置逐字节复制原失败运行实际生成的 `CaseLianSaturatedColumnCollapse_psi0_shared_r3_GPU_out/CaseLianSaturatedColumnCollapse_psi0_shared_r3.xml`，默认AS0，未显式添加AS项。一个全新GenCase＋新AS代码GPU求解器，沿原r2弹性PRE连续启动，global cap4044000（44000次新更新）。TimeMax13、dt2.5us、TimeOut.01、材料/墙/FS/SPR/阻尼/Ck全部不变。实际退出0且11帧完整后直接调用已经通过的 `outputs/upl_c08_partial_native_r1_build/C08NativePartial_win64.exe`，不调用其硬编码旧失败owner。
2. 新OFF11帧的typed22.bin原12B header、每帧真实double time＋全部22 SoA字段，以及整个signed clocks.csv和layout，都与保留 `outputs/upl_c08_partial_native_r1` 原失败11帧逐字节一致。这个比较只认证原失败前已保存的轨迹未被AS0分支改变，不把旧失败改称成功。
3. 仅前两项通过才运行ON。ON相对OFF只追加 `ArtificialStress=1, ArtificialStressCoef=.2, ArtificialStressExp=2.55` 三项已有参数（旧默认值，不是论文拟合参数）。一个新GenCase＋一个GPU目标，global cap4120000（120000次新更新，约τ.30）。原PRE不重算、不使用失败后的PART重启。
4. ON求解正常退出0且实际30帧完整才调用新bounded reader一次。11/30帧均核实际零基Step+1和scalar +=dt时钟，不用n*dt代替，不改元数据。所有22数组/6800原ID、5000soil、1800retained fixed、P0 bit、κ单调、J/n/V/rho/k、FS2/3非正孔压和signed dterror<=1e-14等既有门保留。ON逐帧必须typed元数据 `DynamicArtificialStressPolicy=ReleaseOnly`、bool Active=true、float Coef=.2f、float Exp=2.55f。

ON源预载AS0，候选仅撤墙后启用AS1，是明确的阶段算子改变；不宣称相同算子PRE合同覆盖AS，不构成论文吻合/全塌陷/half收敛验收。失败只保留实际partial、真实wait/Win32退出和最后完整Run.out行；不解码为30帧，不重试、不覆盖、不自动half/正式长跑。后续如需读失败partial由根单独审阅新任务。

## 产物、所有权、通知

隔离运行时 `outputs/upl_c08_as_short_runtime_r1`，OFF/ON `outputs/upl_c08_as_short_r1_off` / `_on`，新解码同级 `_off_native` / `_on_native`；日志/immutable start/call/run/native checks在logs。状态每30s原样记录最后完整PART console行，六位console时间不冒充精确native/failure时间。调用直接持Popen Win32句柄及实际创建时间/exe/argv/parent，不杀其他进程。GenCase/solver/reader各一次。所有绑定只stat，不扫描SHA。失败/partial存在时拒绝重复序列。

根审后显式命令（本稿未执行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as_bounded_native_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_as_short_r1.py --build-check tests/logs/upl_c08_artstress_Release_r1.build.json --unit-check tests/logs/upl_c08_as_unit_r1.check.json --execution-authorized --notify
```

只在终态run收据封口后，当前根线程ID与固定原线程一致才queue一次45s。timeout可能已送达，禁止重发/重新布防/自测；通知本身不启动solver/decoder，只引导原授权离线图表审查和下一步诊断。当前阶段没有额外half/10s预载/三组长算。
