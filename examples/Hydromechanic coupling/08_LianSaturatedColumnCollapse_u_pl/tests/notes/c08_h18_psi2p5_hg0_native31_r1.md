# ψ=+2.5° HG0 的31帧离线入口作者稿

本轮仅作者稿：新增 `support/c08_h18_psi2p5_hg0_native31_r1.cpp`、同tag `_build.py` 与本说明。未执行脚本、编译、help、求解器、native或VTK，不触碰当前ψ−5源及全部程序/源码/PRE/输入依赖。根完整阅读并独立准入后，builder的 `--execution-authorized` 才能执行一次工具构建；无后续自动动作。

现有AS255可执行仅暴露91/301帧；内部 `h18receiver::wmain` 虽接收显式end/count，但还依赖外入口初始化的材料与H18Rows，不能从现有exe直接调用。因此新工具只机械收窄外入口，保留原source/core/header的静态闭包及全部数值门，不修改任何物理程序。新私有目录为 `tests/outputs/c08_h18_psi2p5_hg0_native31_r1_build`，新程序为 `C08H18Psi2p5Hg0Native31R1_win64.exe`。

唯一CLI：`--receiver window31 psi2p5 DATA PRE PLAN PROFILE_CSV FRESHOUT`。严格31帧、末completed step2060000、60000新更新、5μs；前30个保存step为2000001+2000×part，最后一帧为强制final2060000，不能冒充保留HG1 full3的Part30=2060001。原头真实写 `[6805,22,31]`，不重写header/保存step/时钟。不开放source、window91或formal入口。原17键group材料严格ψ2p5、coh5000、ψ+2.5°、sf.2，共同φ25°等仍由原parser检查，并额外锁定AS.3/n2.55。

从已封存 `c08_h18_as255_native_r1.build.json` 的实际entry派生，透明列出并逆变换证明仅改CLI范围/计数/分组上下文、HG侧车不存在检查及新metadata stage。其余entry字节与原数值core保持；`h18_receiver_core_r1.cpp`、pure22/header/source body逐字节拷贝。只编译一个读取器TU，链接原6个BI4 utility对象（Functions/JBinaryData/JException/JObject/JPartDataBi4/JPartDataHead），不编译或链接JSph/CUDA。沿用原MSVC14.36、precise/MT/GL-工具ABI及原CL/link参数，只有新私有路径和新entry输出；记录真实CL/link Popen与Win32出口。环境以无空格TEMP env.cmd可靠取得，只在内存接收set输出。原header归档用于一次新私有静态闭包，不做SHA或对象/源码哈希扫描。任何已有完整或部分新标签都保护不覆盖。

工具要求DATA父目录中 `C08OptPlasticHG.csv` 和 `C08OptPlasticHGPolicy.json` 均不存在，并在新metadata明确HG_expected=false/sidecars_absent=true；没有602 HG门，也不宣称从缺侧车证明了HG kernel正确。求解阶段实际OFF还须根后续绑定同groups程序、子进程环境删除 `C08_HG_OPT_H18`、XML SoilHourglassXi0及真实owned run。字面环境值0会报错，不能作为OFF。缺变量也让cached ConsumePre/Cor返回原非cached材料积分路径；HG0/HG1同材料公式对照不自动等于纯HG力唯一差异或全程材料bit等价。

保留原22类型/finite、6805完整IDs、5000soil/1805fixed、P0位继承、κ从PRE单调、单J n/V/rho/k ledger、rho float cache、FS2/3 p<=0、actual scalar +=dt及signed dterror、同材料schema2/PRE与NoPen fixed-plane/plane-gaps门。保持ReactionClosed=false、冷HG源不是exactHG restart等原限制。.001是solver内部wall准入阈值，不是该native工具可见的矩阵检查，不伪造native已核.001。

构建成功仅为工具实施证据。根仍须独立准入唯一31帧解码及同材料HG0物理窗；新物理进程不得与当前ψ−5源并发。后续HG0/HG1差异是描述性算子比较，不是5Pa half误差、理论精度或论文验收。本稿不启动这些步骤，不改论文原p<=0自由渗流边界。
