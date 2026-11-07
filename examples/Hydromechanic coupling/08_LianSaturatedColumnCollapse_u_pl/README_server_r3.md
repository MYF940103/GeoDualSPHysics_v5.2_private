# r3：服务器待完整物理验证的共享预载包

完整解压`LianCollapse_upl_win64_r3.zip`后运行，不能在ZIP内双击。Windows x64，NVIDIA RTX A6000，CPU默认8线程，GPU默认GPU0；服务器需Windows UCRT及合适NVIDIA驱动，不需Python、Visual Studio或CUDA Toolkit。

先选择一个后端，运行`xCaseLianSaturatedColumnCollapse_shared_preload_r3_win64_CPU.bat`或GPU入口。源成功结束后，再用同一个后端依次运行psi0、psi2p5、psim5三个`shared_r3` BAT。CPU/GPU源不混用，不要同时乱点8个入口；尤其同一GPU0上的三receiver应顺序运行。本启动器没有backend并发锁，保留已有输出拒绝覆盖、源完成记录和原生loader认证规则；不是自动顺次运行全部四流程的一键BAT。每个入口只启动一次目标，不删除、不重试、不自动续算。`--unattended`仅关闭结尾暂停。

源从零有效应力和ConstantZ H=2m静水p0开始真实重力预载。dt=2.5微秒，TimeOut=0.01s，event=10s/TimeMax=13s；源BAT用`-nsteps:4000000`停在完整PRE、尚未撤墙，预期1001帧、末文件`Part_1000.bi4`。这是调度预期，不是已跑过10s。实际标量时钟预计10.000000000374257s，接收必须继承实际值，不能强写为10或0。每个Pre/Cor材料trial都必须Elastic，保存κ=0本身不够；资格失败必须保留证据并停止，不能提高源强度或绕过loader。

三组共用φ=25°、cr=1kPa、黏聚衰减5。psi0为ψ0=0°/cp=5kPa/sf=0；psi2p5为+2.5°/cp=5kPa/sf=0.2；psim5为−5°/cp=7.5kPa/sf=0.2。新的统一DP v2替代旧算法选择，材料参数及保存κ仍为float，局部返回使用double；新XML不再带MaterialReturn选择项。本版κ历史处理和顶点修复可使结果与r2不同，完整软化响应需重新比较。源PRE为专用认证弹性状态，接收延续全部原生状态及真实时钟，在首循环仅撤去右mkbound2的260个样本，关闭预载阻尼0.02和Shepard40，保留Model1/Ck=2变k及自由渗流，继续到总时刻13s。τ按实际撤墙时刻计算；接收Part0不是伪t0或重复PRE。

其余物理配方保留：5000土+2060初始墙，dp=0.04m，Cubic核h/dp=1.2，E=20MPa、ν=0.33、n0=0.35、Kw=1GPa、k0=2e-4m/s，侧壁FreeSlip、底面NoSlip。保留负孔压，不引入论文额外负压松弛、TPI、HG、独立SPR、NoPen或shifting。公开u-pl塑性范围仍为该二维固定φ、DP_PS、Symplectic容器；没有任意塑性/HG/通用PART重启，也不声明三维动态塑性、曲墙或大转动已经验收。

已有CPU/GPU实际调用、Version2 PRE接续、分面mDBC与两ψ组短接收证据；本包仍是服务器待验证计算包。两ψ接续短窗κ始终0，不能当作非零塑性ψ衰减或完整塌陷精度。实际10s源能否全程满足弹性资格、三组完整塌陷与论文对比，仍须服务器结果审查。原必要稳定门失败同样停止，不自动换步长或方案。

源码来源分开记录：实际编译快照base=6912e824b7cd15a4503097fb9c0d019e90ef2474加当时捕获的未提交修改；后来保存代码checkpoint=22723a1dd21a5be460a11b8da5c26194aa50c0e7。不声称程序在该后来提交或当前HEAD上重编。精确冻结快照及四build收据见SOURCE_VERSION_r3.txt/server_manifest_r3.json。r2程序、包和其结果保持原样，不应被本包覆盖或接续。

BAT只GenCase和求解，不做绘图、VTK或Python后处理。完成后复制完整源输出、三receiver输出及本包回来，包括初始BI4/Normals、全部PART、Run.out/Run.csv和日志；PNG/CSV及论文对比在本地完成。已有输出请保留，不能只拷最后一帧。
