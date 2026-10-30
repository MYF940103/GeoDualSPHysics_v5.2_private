# Cryer symC / ν=0.30：Windows RTX A6000 服务器运行

本包是新的 **symC 孔压扩散**计算入口，不是旧根目录的无斜坡 5 µs 输入。解压 `Cryer_symC_nu030_Windows_RTXA6000_r1.zip` 到服务器本地磁盘后再运行；不要在 ZIP 内执行 BAT。

## 先检查启动，再独立启动完整计算

服务器需 Windows x64、RTX A6000 和支持 CUDA 11.7 的 NVIDIA 驱动；CUDA 11.7 GA Windows 工具包基线为 516.01。运行不需要 Visual Studio、CUDA Toolkit、Python 或后处理环境。本机只在 RTX 3050 上测试，不能据此声称 A6000 已实机验收。

在解压目录打开命令行，先执行：

```bat
xCaseCryerProblem_PR_symc_nu030_win64_GPU.bat --smoke --unattended
```

`--smoke` 仅运行到绝对时间 2^-13 s，保存两帧，用于服务器启动检查，不包括开排水、峰值或完整物理验收。烟雾测试不会自动接着跑正式计算。保留其日志，确认正常结束且显卡识别正确后，再单独启动：

```bat
xCaseCryerProblem_PR_symc_nu030_win64_GPU.bat --unattended
```

也可双击根目录 BAT；`--unattended` 仅取消结束暂停，不改变数值配置。入口必须为 smoke 和正式计算使用不同的新输出目录；同名输出已存在时直接失败，不覆盖、不清空，不自动续算。若中断，保留全部部分输出及日志，不改名伪装完成，不自行进行 PART 重启。

包内仅有已验证 Release、GenCase、Chrono/OpenMP 依赖和可安全再分发的微软运行库，不含 CPU/Debug 程序、tests、旧结果或 Python。若清单标明运行库须预先安装，或启动报缺少运行库，请先安装微软官方 **x64 VC++ Redistributable**；不要从其他计算机随意复制系统 DLL。

## 时钟与配置

- 原球体分布、R=0.05 m、dp=0.0025 m、k=1e-5、ν=0.30，原始模式2围压 q=10 kPa；未改质量、粒子布局或外载算子。
- 固定 dt=2^-21 s≈0.476837 µs；斜坡持续 2^-8 s，随后闭合持载至 tD=2^-7 s=0.0078125 s。
- `HydroMechDrainageFixedGrid=1` 保持已验证时钟策略。保存态 t=tD 仍是开排水前态；t>tD 的真实 FSType2/3 表面粒子施加 p=0。理论排水时间为 **τ=t−tD**，不能直接把绝对 t 当排水时长。
- `PoreDarcySymmetricCorr=1` 仅将土—土 Darcy 收缩改成两端修正矩阵的平均；压力压缩项、有效应力/动量、围压、时间积分不变。孔压、孔压率、密度仍为 float，应力及保存位置为 double，不是全双精度/u-pl/TPI。
- `SoilStressRateGradCorr=1`，阻尼 0.00004；SPR、沙漏及 shifting 均关闭。
- 完整目标为排水后 LegacyTv=1，即 τ=12753/14000=0.9109285714285714 s。绝对结束时刻向上取到固定步长整数格：1926740 步、TimeMax=0.9187412261962890625 s，对应 LegacyTv≈1.0000001699010466；仍须回拷后核对实际原生末帧。
- 开排水前保存间隔为 2^-13 s，保留 Part64 初态；之后以 tD 为锚，使用 ΔLegacyTv=0.001 的特殊输出间隔。不是全程均匀物理时间保存，也不是每一个后期输出时刻恰好落在固定步长格上。后处理须读实际原生时间，不能硬套旧帧号。
- 预计保存约 1065 个原生状态，包括最终态，不为终时刻另重复输出一帧。实际保存时钟与名义排水后 Tv 刻度可差一个固定步长，以原生数据为准。

当前已完成实现回归、闭态初态检查及先前隔离 symC 峰窗/独立半步验证；并未完成本包新的完整服务器计算。正常退出、两帧 smoke 或旧峰窗一致性均不等于完整 Cryer 验收。现有结果仍有峰时偏差，不能宣称已完全符合解析解。

## 完成后回拷

请回拷**整个正式输出目录**及整个 smoke 输出目录，包含 `data/` 下全部原生 BI4/Extra、`Run.out`、GenCase 和 BAT 日志，不只复制 VTK、最后一帧或图片。同时保存原 ZIP、`support/cryer_server_manifest_r1.json` 和外部 ZIP SHA256。

BAT 只负责生成初态和求解，不自动绘图或批量转换 particles。原生结果回拷后再核对实际末时刻、ID、哈希、排水、步长、载荷及孔压/应力，然后更新根目录 `figures` 的解析对比图与配套数据。建议至少预留 15 GB 磁盘，不按本机 RTX 3050 的耗时估算服务器速度。

## 来源、打包与许可

`support/cryer_server_manifest_r1.json` 记录正式 XML/BAT、程序、运行库及白名单文件 SHA256，也绑定已通过的实现审阅与 Release 构建收据。源码节点由打包者显式提供完整 40 位 Git ID，并记录相关源码/文档哈希；该节点属于本项目私有开发交付，不冒充上游官方二进制。对应源码及改动可向项目交付者获取。Git 备份不等于原生输出、EXE 或 ZIP 已上云。

六个物理源码与 GPU 项目文件须精确匹配已验收输入；同步更新的 XML 指导文档另记当前哈希，不冒充编译输入。旧指导文档已独立归档，不重写旧运行的哈希记录。

`pack_cryer_server.ps1` 仅供原工作仓库在正式输入和验收收据齐全后制作白名单 ZIP；解压后的运行包不含 tests/构建树，服务器无需再次执行打包脚本。脚本拒绝覆盖既有清单/ZIP，也不会启动任何程序或计算。

- 项目许可：包内 `LICENSE`（LGPL），保留原有声明。
- Chrono 许可：https://github.com/projectchrono/chrono/blob/main/LICENSE
- 微软运行库及许可/下载：https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
- CUDA 11.7 驱动说明：https://docs.nvidia.com/cuda/archive/11.7.0/cuda-toolkit-release-notes/index.html
