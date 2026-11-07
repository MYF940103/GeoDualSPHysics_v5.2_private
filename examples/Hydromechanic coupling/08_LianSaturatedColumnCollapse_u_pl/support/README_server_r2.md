# r2：一次认证预载，三个材料分支

完整解压 `LianCollapse_upl_win64_r2.zip`；Windows x64，NVIDIA RTX A6000，CPU默认8线程/GPU默认0。先选择一个后端，双击 `xCaseLianSaturatedColumnCollapse_shared_preload_r2_win64_CPU.bat` 或 GPU入口。预载成功后，用同一个后端分别运行 psi0、psi2p5、psim5 三个 `shared_r2` BAT。源与接收输出均含后端名，CPU/GPU源不混用；已有输出拒绝覆盖。每个BAT只启动一次目标，不自动续算、重试或切换方案。

源：ψ0=0°、cp5kPa，MaterialReturn1；从σ′0、ConstantZ H2静水p0开始真实重力预载。dt2.5µs、TimeOut.01s，event10s/TimeMax13s保持既有事件校验，BAT以 `-nsteps:4000000` 停在完整PRE，尚未撤墙。每次Pre/Cor材料trial必须返回Elastic；保存κ0本身不够。如果进入径向塑性、顶点或其它失败，源停止并保留证据，三个分支不得启动，更不能提高源强度或绕过loader。

按当前writer标量时钟与GetNextTime规则，400万步预计1001帧，末文件`Part_1000.bi4`；准备记录在support/preload_schedule_r2.json。BAT核实际Run.csv步数/帧数/普通丢失和实际文件存在，仅属调度自检。真正认证由solver读取PRE时核schema、两阶段弹性来源、精确法向/几何/材料合同、22原生数组/实际时钟/状态/稳定守卫。接口短窗验证不代表这个10s源已经跑过或达到严格平衡。

三分支共同φ25°、cr1kPa、黏聚衰减5；psi0为ψ0=0°/cp5kPa/sf0，psi2p5为+2.5°/cp5kPa/sf.2，psim5为−5°/cp7.5kPa/sf.2。源全程合格弹性后才允许此强度/剪胀分支。每组导入实际PRE时钟和完整材料状态，首循环只撤右mkbound2一次，关闭预载阻尼.02和Shepard40，继续到总时刻13s，保留自由渗流、Model1/Ck2和负孔压。τ=t−实际撤墙时间，不重写为假t0。接收输出没有重复PRE伪初帧；首次Part0为真正后续保存状态。

三个根Def的statefile标记由BAT用Windows自带PowerShell替换成对应实际源绝对路径，副本保存在各新out，再GenCase。根模板不被修改。不要直接绕过BAT对带标记Def启动solver。保留源输出、全部接收输出及本包；源不是通用PART重启，不能替换为旧常k或未经认证的历史文件。

几何/材料其它设置沿r1：5000土+2060墙，dp.04m、Cubic h/dp1.2，E20MPa、ν.33、n0.35、Kw1GPa、k0=2e-4m/s、左/右FS和底NS；12m床是数值域裕量。没有TPI、论文负压松弛、HG、独立SPR、NoPen、shifting或三维塑性。实际顶点/原稳定门失败仍停止，不承诺全程成功或论文精度。

运行库在support/runtime_r2；沿C05已签名VS14.36应用本地CRT。服务器提供Windows UCRT和合适NVIDIA驱动，不需Python/VisualStudio/CUDA Toolkit。BAT只GenCase和计算，PNG/CSV在数据复制回来后处理。r1包/结果保持原样。源码节点`0f244e218003c76103eba904eb220c2475480497`，关键payload校验和、四构建及有界交接来源在support/server_manifest_r2.json/SHA256SUMS_r2.txt。源码归档身份不等于本包包含完整源码；完整修改源码请向维护者取得。
