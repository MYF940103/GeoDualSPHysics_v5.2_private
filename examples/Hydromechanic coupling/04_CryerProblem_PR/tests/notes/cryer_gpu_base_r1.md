# Cryer GPU 启动基线准备（2026-10-27）

默认仅准备；本记录不是运行或验收结论。待主代理完成外载离线检查并决定后，才可执行
`python -B tests/support/cryer_gpu_base_r1.py --run`。无通知、无自动长算，不重启旧CPU序列。

## 唯一范围

两个全新标签`cryer_gpu_base_r1_dbg`和`cryer_gpu_base_r1_c`。XML逐字节复制已运行的
`tests/configs/cryer_dt_short_r1_c_Def.xml`，不改物理、时间步或输出节奏：dt=2.5us，
TimeMax=.0005s、TimeOut=.000125s，每组200步、5个原生保存帧。dp=.0025m、R=.05m、
k=1e-5m/s、q=10kPa、t=0加载和排水、阻尼=.02、原FlexibleConfinement，孔压/率float、
持久应力及保存位置double；SPR/HG/应力率梯度修正关闭，孔压体积源梯度仍沿现默认开启。

BAT沿用`xcryer_start_r1_win64_CPU.bat`格式，仅新标签、真实GPU程序和-gpu参数。
Debug先在compute-sanitizer memcheck下运行，要求零错误及零泄漏；缺工具即阻断，不跳过。
Debug全部原安全检查通过后，才运行当前GPU Release。不新增GPU半步。

复用CPU `cryer_dt_short_r1_c`的已通过单组5帧。旧CPU粗/半配对未通过，最大孔压RMS差
56.3807372399Pa，不能将它称为已通过半步或因GPU对照通过而抹去。Debug/Release也不是0ULP对照。

## 真正检查与证据

- 现有GPU Debug/Release程序、其386项构建输入和冻结副本哈希，逐项匹配后方可运行。
  Debug SHA256为`57ef82c47d3afd34e2723bdcd1024b6d55137a7bdbd696804b92ff1084053feb`；
  Release为`260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c`。
- 实际Run.out记录硬件/计算能力、精确退出、200步、实际保存时刻；不把Lian或服务器A6000运行
  当成本地Cryer GPU证据。只统计观察到的启动循环时间，不预称GPU更快。
- 复用`cryer_dt_short_r1.inspect`及原生读取器：37173个相同原生土ID、有限/正密度、无塑性/排除、
  激活FSType2/3排水严格零、非空排水掩码、原机械自然步长和孔压扩散步长均检查。
  初态几何/质量/h与CPU相同，球体半径不超R+dp；保留实际外载与体积/合力/力矩诊断，
  不把几何面积比直接解释为真正traction误差。
- Release对CPU同dt全部5对实际时刻，不插值；孔压场RMS<=5Pa，材料位移差最大值<=.005mm。
  原生每列差异单独记录，含总应力、密度、外载、自由表面等；不宣称所有字段逐位相同。
- 只管理当前wrapper子树，启动前拒绝其他Cryer求解器；失败保存旧/新证据，不删文件、不放宽阈值。

## 文件位置及限制

入口为`tests/support/cryer_gpu_base_r1.py`；配置/BAT在`tests/configs`；准备清单、运行与完成
收据在`tests/logs`；两个独立输出在`tests/outputs/cryer_gpu_base_r1_{dbg,c}`；汇总和全部原生
字段差异CSV在`tests/figures`。原始BI4和程序哈希保留本地，并不自动等于云端备份。

本轮不改C++/CUDA、正式XML/BAT、默认值、文档接口或Git，因此不为准备重复重编译。
不准入峰值/半步/完整Cryer物理验收，不绕过旧失败，也不改变当前优先的外载一致性诊断。
