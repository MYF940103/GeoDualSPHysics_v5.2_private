# k=1e-5新鲜CPU完整计算（2026-10-21）

用户最新指令为停止当前对比和正式进程，改用CPU重跑1e-5。此前GPU `k5_full_r1`已主动停止，不是数值失败：最后可读PART6056、实际6.055999999855318 s，末帧与原GPU15 s同dt控制0 ULP；所有部分文件保留，停止审计`logs/k5_full_r1_acceleration_stop.json`。旧worker先退役再停止其归属求解器，不再发终态通知。6.25微秒候选未启动且已归档，后端/步长比较不继续。

## 配置和位置

- XML/BAT：`tests/configs/k5_cpu_full_r1_Def.xml`、`xk5_cpu_full_r1_win64_CPU.bat`，沿用现有XML/BAT风格，无删除/覆盖逻辑。
- 输出：`tests/outputs/k5_cpu_full_r1`；日志/状态：`tests/logs/k5_cpu_full_r1.*`；监测量表：`tests/figures/k5_cpu_full_r1_runtime.csv`。
- CPU Release，8线程；dp=.003125 m，周期宽.025 m，2560土粒子+32固定粒子，dt=5e-6 s，145750572步，名义终时728.75286 s（2Tv）。保持eta=.04、xi=.1、band5、向量SPR、固定步长排水事件；不改物理参数、方程或积分。
- 验证采样沿用GPU长程输入：前15 s为1 ms，之后.1 s，保留切换和末尾非整间隔帧，仅末帧导出VTK。此处是tests诊断采样，根目录正式XML的TimeOut仍为ΔTv=.005，旧正式结果不重跑、不改写。
- 普通PART不含可精确续接的HG历史，本次从头启动；不能在关机后将其当作精确重启文件。

## 唯一生产源码改动：已有量的输出

`src/source/JSphCpuSingle.cpp`的`JSphCpuSingle::SaveData()`五处：

1. 行1355：声明保存用的`hydromechloadace`指针。
2. 行1376：在已有HydroMech分支预留临时float3数组，使用已有池容量。
3. 行1379：`GetParticlesData`使用其已有参数复制`HydroMechLoadAcec`，与原生粒子排序/周期过滤一致。
4. 行1414：将该现有加载加速度写为`HydroMechLoadAce`原生数组，与GPU字段名一致。
5. 行1432：释放临时数组。

不重复施力、不改Acec、不改归一化、压力/应力、时间推进或HG历史；不新增XML开关。同步说明在`doc/xml_format/_FmtXML_ElastoplasticSoil.xml`。修改前CPU程序和该源码文件已按字节保存到`tests/outputs/k5_cpu_loadout_base_r1`；旧CPU计时记录的哈希保持原文。

CPU Debug及Release构建均通过；Debug有既有MSVC D9035（Gm已弃用）警告，Release因旧IPDB不可复用而全编译，无编译错误。输出回归`k5_cpu_loadout_smoke_r1`为新CPU8 .03 s/6000步/31帧：与保留旧CPU8所有旧物理字段0 ULP，仅新增load观察值不同；.02-.03 s恒载时等效.1 m宽总外力最大误差6.12025e-5 N/m，小于.001。该短测不代表已通过.1 s后或完整周期验收。

## 长程检查和接续

运行器`tests/support/k5_cpu_full_r1.py`只启动一个CPU求解器；每个封闭原生帧核对ID、几何、排水、等效1000 N/m总外力、t>=.1 s后100 Pa层总应力/顶层差。前15001帧与已完成GPU15 s的同物理、实际匹配时刻作5 Pa/.005 mm孔压/顶部材料沉降比较，不要求跨后端0 ULP，也不是半步长收敛检查。HG调用数、实际率复用数、dt/tau<=.2、小转角、无粒子排除及终时/步数在完成后核验。

固定dt反复binary64累计的预期终时为728.75285851827402 s，与名义728.75286 s差约1.48微秒；按精确步数、实际终时和实际Tv核验，不误用名义1e-7 s门。正常退出只表示完成计算，必须再审阅孔压剖面/晚期耗散、材料沉降、总应力/Q、底部偏差并检查图片后才决定完整验收。

短计时不是隔离的整周期基准：旧CPU8在GPU同时运行时44.59 s/6000步，新输出回归在GPU停止后37.08 s/6000步，不能将这两个数的差全归因于代码。按新短测外推仍约10.4天，真实长程速度另报。用户指定CPU，不再因此擅自改回GPU。单次终态自动回同会话，失败立即说明精确原因/时刻并保留数据，不另启重复程序；旧通知器均不重挂。
