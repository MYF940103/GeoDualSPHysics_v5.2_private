# r3：服务器待完整物理验证的共享预载包

本机续算补充：已回传的 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out` 保持原名。当前根目录三个 GPU 接收 BAT 明确绑定该源，交给 r3 的 legacy MR1 弹性 PRE 加载器认证，避免重算10 s。CPU 入口仍使用自己的源。本机先作短窗审查再开展完整分支；原 ZIP/manifest/SHA 清单作为冻结历史保留，未改写为当前 BAT 的清单。旧 r1/r2 根输入已可恢复归档，见根 README。

本页说明当前工作目录的新版双击流程。`support/LianCollapse_upl_win64_r3.zip`仍是更新前的冻结历史快照，未重新打包，不能代表当前BAT及新增后处理；旧manifest/SHA记录不改写。服务器部署新流程时须同步当前入口、`support/postprocess_lian_collapse_r3.py`和`support/runtime_r3`所需工具，不能在ZIP内运行。

运行环境为Windows x64、Windows UCRT及合适的NVIDIA驱动，CPU默认8线程、GPU默认GPU0。完整流程另需Python 3、numpy、matplotlib，以及`support/runtime_r3/C08Native_win64.exe`和`PartVTK_win64.exe`。启动器优先使用`D:/anaconda3/python.exe`，不存在时使用PATH中的`python`；在任何GenCase或求解前调用`--check-tools`检查这些依赖，缺失即停止，不自动安装。预编译程序不要求安装Visual Studio或CUDA Toolkit。

对全新计算先选择一个后端，运行共享源CPU或GPU入口；源正常结束并通过原schedule检查后，自动调用后处理的`--group preload`。接收入口仍先检查同后端源，再GenCase、求解；求解正常退出后，以对应`--group psi0/psi2p5/psim5 --outdir --source-pre`调用原生检查、两套VTK及PNG/CSV。CPU/GPU源不混用，同一GPU0的三receiver应顺序运行。启动器没有backend并发锁，不自动接着启动下一组；已有物理输出仍拒绝覆盖，不删除、不重试求解。

已有正常完成输出可只做后处理，例如：

```bat
xCaseLianSaturatedColumnCollapse_psi0_shared_r3_win64_GPU.bat --postprocess --unattended
```

`--postprocess`在已有输出拒绝分支之前进入，只检查源并调用后处理，绝不GenCase、求解或覆盖原始物理数据。`--unattended`与它可任意顺序并用，仅关闭暂停。后处理只复用自己已闭合且完全匹配的记录，遇到未绑定或失败的部分结果会保留并拒绝覆盖。本机回传r2 PRE的两套1001帧particles已单独完成，无需再对它执行后处理，更不能重跑10 s。

源从零有效应力和ConstantZ H=2m静水p0开始真实重力预载。dt=2.5微秒，TimeOut=0.01s，event=10s/TimeMax=13s；源BAT用`-nsteps:4000000`停在完整PRE、尚未撤墙，调度为1001帧、末文件`Part_1000.bi4`。本机已有真实r2 GPU源，不在本轮重算。接收必须继承实际标量时钟，不能强写为10或0。每个Pre/Cor材料trial都必须Elastic，保存κ=0本身不够；资格失败必须保留证据并停止，不能提高源强度或绕过loader。schedule和预载VTK后处理均不替代加载器对原生PRE的认证。

三组共用φ=25°、cr=1kPa、黏聚衰减5。psi0为ψ0=0°/cp=5kPa/sf=0；psi2p5为+2.5°/cp=5kPa/sf=0.2；psim5为−5°/cp=7.5kPa/sf=0.2。新的统一DP v2替代旧算法选择，材料参数及保存κ仍为float，局部返回使用double；新XML不再带MaterialReturn选择项。本版κ历史处理和顶点修复可使结果与r2不同，完整软化响应需重新比较。源PRE为专用认证弹性状态，接收延续全部原生状态及真实时钟，在首循环仅撤去右mkbound2的260个样本，关闭预载阻尼0.02和Shepard40，保留Model1/Ck=2变k及自由渗流，继续到总时刻13s。τ按实际撤墙时刻计算；接收Part0不是伪t0或重复PRE。

其余物理配方保留：5000土+2060初始墙，dp=0.04m，Cubic核h/dp=1.2，E=20MPa、ν=0.33、n0=0.35、Kw=1GPa、k0=2e-4m/s，侧壁FreeSlip、底面NoSlip。保留负孔压，不引入论文额外负压松弛、TPI、HG、独立SPR、NoPen或shifting。公开u-pl塑性范围仍为该二维固定φ、DP_PS、Symplectic容器；没有任意塑性/HG/通用PART重启，也不声明三维动态塑性、曲墙或大转动已经验收。

已有CPU/GPU实际调用、Version2 PRE接续、分面mDBC与两ψ组历史兼容短接收证据；这些历史短窗κ始终0，不能当作非零塑性ψ衰减验证。当前新ψ0 r3接收短窗在撤墙后τ=0.1s已有maxκ=0.64613086、3014个ID的κ非零，实际10帧native→PartFluid→PartBound→PNG/CSV联调通过。本包仍待完整物理验证；上述结果均不等于完整塌陷精度或论文验收，三组完整塌陷、预载平衡和论文对比仍须实际结果审查。原必要稳定门失败同样停止，不自动换步长或方案。

源码来源分开记录：实际编译快照base=6912e824b7cd15a4503097fb9c0d019e90ef2474加当时捕获的未提交修改；后来保存代码checkpoint=22723a1dd21a5be460a11b8da5c26194aa50c0e7。不声称程序在该后来提交或当前HEAD上重编。精确冻结快照及四build收据见SOURCE_VERSION_r3.txt/server_manifest_r3.json。r2程序、包和原始结果保持原样；本机仅显式读取其认证弹性PRE，不扩展为通用r2塑性PART重启。

后处理保留原始BI4，在各输出目录生成`native`及`logs`记录（接收组）、`particles/PartFluid_*.vtk`和`PartBound_*.vtk`两套序列，不使用PartAll。预载每帧5000土/2060固定墙；撤墙后接收每帧5000土/1800墙。接收的历史、场图及匹配CSV进入case的`figures`，三组同后端完整时再生成三组比较。当前`preload`分支做源完成检查及两套VTK，不声称额外完成预载原生认证或平衡绘图。

官方PartVTK的显示坐标为float，BI4中的Posd及原生应力保留原类型；SigmaState和六个Poro字段为double，κ是标量历史而非完整塑性应变张量。正常求解退出或后处理完成均不等于物理验收。完成后保留并回传完整源/接收输出，包括初始BI4/Normals、全部PART、Run.out/Run.csv、native、particles和日志，不能只拷最后一帧。物理求解已经正常完成而后处理失败时，先查后处理记录，再使用`--postprocess`处理已有数据，不重算物理过程。
