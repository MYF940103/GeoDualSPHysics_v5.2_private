# Cryer u-pl ν=.30：服务器完整衰减验证候选

本入口准备排水后 legacy Tv≈1 的新鲜运行，不是完整物理通过声明。
本地只完成启动、闭态及577帧峰窗；没有启动本候选的完整计算。
不覆盖旧u-pw正式输入、发行包、输出或本次u-pl峰窗。

## 运行与文件

完整包应包含根目录 XML/BAT、`support/upl_seed_nu030_r1/` 下同名
`CaseCryerProblem_u_pl_nu030_r1.xml/.bi4`，以及
`support/bin_upl_r1/DualSPHysics5.2_GEO_win64.exe` 和所需运行库。
种子保留37173个土粒子、8个远端固定标记及原始ID/坐标。
BAT只复制提供的种子并求解，不调用GenCase、不重新采样、不做PART重启。
根目录 `_Def.xml` 记录完整配置；实际执行的是包内种子XML。

解压到服务器本地磁盘后双击
`xCaseCryerProblem_u_pl_nu030_r1_win64_GPU.bat`，默认执行完整候选。
命令行无人值守形式为：

```bat
xCaseCryerProblem_u_pl_nu030_r1_win64_GPU.bat --unattended
```

新输出为 `CaseCryerProblem_u_pl_nu030_r1_GPU_out`。同名目录存在即退出，
不清空、不覆盖、不自动续算。中断后保留全部部分结果。
`run_command.txt` 保存命令；求解器返回后立即把原始ERRORLEVEL写入
`solver_exit_code.txt`。退出0只表示等待原生和物理审查，不自动绘图或排队。

## 参数、时钟和范围

- 保留峰窗物理值：R=.05 m、dp=.0025 m、E=2 MPa、ν=.30、n0=.30、
  Kw=200 MPa、k=1e-5 m/s、q0=10 kPa、零重力、原始模式2围压。
- u-pl dynamic=1、legacy Darcy symC=0、G1开启；Wendland/Symplectic、
  AV=.1、阻尼4e-5；SPR/HG/shifting关闭。应力及保存位置double，孔压仍float。
- dt=2^-20 s；ramp结束2^-8 s，排水事件tD=2^-7 s。
  t=tD的保存态仍pre-open；只在t>tD对真实FSType2/3排水粒子施加零压。
- 963370步，TimeMax=.9187412261962890625 s；τ=t−tD，目标legacy Tv≈1。
  不把绝对t、ramp终点或第一排水保存帧当理论时间原点。
- 前65帧保留每2^-13 s的闭态历史；之后以tD锚定Δlegacy Tv=.001，
  预计1065帧。分析读取实际保存时刻；本保存计划不是577帧峰窗的完整前缀。
- 限定新鲜、弹性、常k、无接触自由体；远端DBC标记必须保持支持域外。
  不授予其他ν、接触墙、重力、塑性、变k、重启或一般三维算例的验收。
- 本候选没有论文负压稳定α、非饱和或空化模型，不推广为负压主导工况通过。

## 已有误差和参考约定

本次577帧峰窗的原生22数组、37181 IDs、ledger/排水及首69帧
common26和signed-clock前缀检查通过。Mandel窗u-pl采样峰值12253.447 Pa，
对有限Kw、同初始r/a=.05参考的幅值差−1.4931%、峰时差+2.4708%。
旧u-pw ν=.30采样峰为12310.521 Pa，幅值差−1.0343%、峰时差+3.9789%。
新结果幅值略差、相位较好，不能标作“1%物理通过”。

两者是全框架比较，不能套5 Pa跨模型等价门槛；旧ν=.30实际执行EXE/DLL身份
仍未证明。旧四ν结果、旧半步或旧服务器包不授予本u-pl完整周期精度。
固定原18材料ID，初始r0=.0025 m，压力取算术平均，不是精确球心r=0。
理论用实际τ；legacy Tv与有限存储衰减时钟分别标注，Mandel窗仍为Tv≥.005。
保留开启瞬态；不拟合半径、压力或时间，不把峰窗RMS冒充完整周期RMS。
有限Kw参考为小应变准静态条件参考，不重放惯性、阻尼或粒子离散误差。
保存态J质量乘LoadAce仅为载荷proxy，不代替实际力阶段预算。

## 服务器与回传

目标Windows x64/NVIDIA RTX A6000；本程序尚未在A6000实测。
本程序以CUDA 11.7、sm_86/compute_86构建；需要兼容驱动。包内附本轮使用的运行库和项目LICENSE。
服务器运行不需要Python、Codex、Visual Studio或CUDA Toolkit。
本地RTX3050峰窗耗时不能作为A6000速度保证。先确认可用磁盘空间，
不要只根据退出码、图片或末帧认定完成。

请回传整个 `CaseCryerProblem_u_pl_nu030_r1_GPU_out`，包含全部`data`原生文件、
初始种子、Run.out/Run.csv、命令及退出码记录，并保留原包和清单。
回传后独立检查1065帧实际时钟、IDs、22数组、J/n/V/rho、排水和完整衰减，
再生成压力、固定材料位移/应力及理论比较的匹配CSV/图。不得只回传VTK或图片。
