# Lian 2023 饱和土柱塌陷：Windows 运行包

完整解压 `LianCollapse_upl_win64_r1.zip` 后运行，不要在 ZIP 内双击。目标为 Windows x64、NVIDIA RTX A6000；GPU入口默认GPU0，CPU入口默认8线程。同一组择一后端，输出已存在会拒绝，绝不删除或自动续算。

根目录三组入口为 `xCaseLianSaturatedColumnCollapse_psi0_r1_win64_GPU.bat`、`..._psi2p5_r1_...`、`..._psim5_r1_...`；CPU入口把GPU换成CPU。可加 `--unattended` 仅关闭结束暂停。各组输出为对应同名 `_out`，请保留并复制整个输出目录回来，包括初始BI4/Normals、全部Part/日志/Run.csv及本运行包。BAT只做GenCase与一次完整求解，不运行Python、不转换VTK、不绘图。

| 组 | 初始剪胀角 | 峰值黏聚力 | 残余黏聚力 | 黏聚力衰减 | 剪胀衰减sf |
|---|---:|---:|---:|---:|---:|
| psi0 | 0° | 5 kPa | 1 kPa | 5 | 0 |
| psi2p5 | +2.5° | 5 kPa | 1 kPa | 5 | 0.2 |
| psim5 | −5° | 7.5 kPa | 1 kPa | 5 | 0.2 |

三组均φ=25°固定、MaterialReturn1、现有Model1/Ck2，dp=.04m、Cubic h/dp1.2、E20MPa、ν=.33、n0=.35、Kw1GPa、k0=2e-4m/s。左/右墙FreeSlip、底NoSlip；床长12m是数值域裕量，不是论文指定尺寸。

每组从零有效应力和ConstantZ H2静水p0开始，真实重力预载10s；同进程撤去右mkbound2后继续3s，TimeMax13s，dt=2.5µs、输出间隔.01s。预载阻尼.02/Shepard40由撤墙事件关闭，p0/J/应力/塑性历史连续，不加载PART、不复用另一材料组的预载。τ应按原生实际撤墙时间计算，不重写保存时钟。保留初始Normals与主22数组，不逐帧重复输出墙法向Extra。

已通过的是受限实现/组合短窗，不是13s论文精度或严格初态平衡验收。保留常k10s预载仍有较弱固结及参考残差；本组三个变k材料预载需各自回看。没有TPI、论文负压松弛、HG、独立SPR、NoPen、shifting、三维塑性或精确重启。负孔压保留；不支持的材料顶点或原稳定门失败会停止，保留部分输出供诊断，不自行放宽限制。

运行库放在 `support/runtime`；附带C05已署名VS14.36应用本地CRT三件组。Windows系统UCRT和适合显卡/程序的NVIDIA驱动由服务器提供；BAT不需要Visual Studio、CUDA Toolkit或Python。本机RTX3050短测不是A6000实机验收。若系统运行库提示缺失，使用微软官方x64 VC++ Redistributable，不复制未知System32 DLL。

复制回来后再生成实际时间的孔压/超孔压、位移/形态、应力、κ/n/k及论文Fig14–17对比PNG和CSV。纸面停止时刻不是强制数值门，孔压负值也不自动等于数值错误。

源码节点 `d1dcba9fd8662a6d377c0d535b11711cc75bcc3b` 由根线程提供；程序及输入SHA256、构建/短窗来源在 `support/server_manifest_r1.json`，校验清单在 `support/SHA256SUMS_r1.txt`。项目许可证为根目录LICENSE；对应完整修改源码请通过交付者取得。其余来源见 `support/THIRD_PARTY_NOTICES_r1.txt`。本包不含tests或历史输出。
