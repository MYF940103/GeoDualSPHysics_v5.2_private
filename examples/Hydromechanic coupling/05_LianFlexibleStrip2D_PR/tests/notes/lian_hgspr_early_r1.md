# Lian HG+SPR：0–1 s 早期保存间隔补充

仅新增 tests/configs/lian_hgspr_early_r1_Def.xml、xlian_hgspr_early_r1_win64_GPU.bat、tests/scripts/lian_hgspr_early_r1.py 和本记录，之后新增同标签 outputs/logs/figures。根目录正式100 s数据和旧输入、已封存脚本与哈希完全保留。没有生产源码改动、CPU/GPU重编译、Git操作或新watcher。

从根目录正式XML复制，仅有效 parameter 数值 TimeMax=100→1 s、TimeOut=.05→.01 s及相应描述变化。DtIni/DtFixed=.00001 s、原source-clock排水、13节点外载、HG=.1、SPR=1、grad1、eta=.04、dp=.1、侧mk0/2自由滑移和底mk1无滑移均不变。同support/bin程序260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c及原运行库。

显式 --prepare 封输入与程序/运行库；--run 仅启动一个全新GPU进程。无同名输出/日志/清单、无活跃DualSPHysics GPU进程才可启动。主线程负责等待和最终审图，不创建监控/通知任务。若求解已正常完成而后检查失败，仅 --analyze 使用已封completion离线修复，不重跑物理程序。

期望101帧0–1 s；固定10 us累加可能需100001实际步且末帧约1.000009999998 s，绝不为凑整数终时刻改步长/截断。HG调用/复用计数按实际Run.out步数检查。每帧20301不变ID、finite、正rho、kplastic=0、无排除、double位置/应力、mass/h/dp不变、实际载荷观测、几何和原机械dterror≤1e-14；独立孔压扩散上限约12.709us也须满足。合力按 source t−dt、原13节点13000N/m、既有.002N/m容限，不更改求积或斜坡。

正式100s保留前21帧与新0.01s cadence只在实际time+saved_step同时相同处比较全部34物理/身份/标志列0ULP。唯一允许不相同的是输出区间统计dterror_s，两个结果仍各自满足原≤1e-14门；记录raw35列是否一致，任何其他差异拒绝合并，不插值/改步号。因1s末帧source时钟可能仍低于1，此短窗通常没有活跃排水样本，必须报告“未覆盖”，不能空掩码宣称复验排水；已有100s全历史排水检查保留有效。

A=(0,10)固定ID1744；B=(1.25,8.75)固定2943/2944/3044/3045各.25，不使用旧nearest诊断。早期history.csv在tests/figures保存。通过后新r2正式history/pressure/settlement图和paper_points.csv放根figures；按实际saved_step连接新early与原100s晚段，保留每行来源，不重启或拼接HG内部状态。原Fig10场图/100s有符号水平剖面无需重算，原样核验后引用。新图不是新的精度修正、半步或论文复现验收。

CPU Debug build不适用本轮：没有任何源码、项目文件或编译参数变化。既有RTX3050同物理66.62步/s推算求解约25min；另约2–4min原生核查/绘图，实际进度以新Run.out为准。CSV生成前已执行本轮Spreadsheets operation marker，不额外导出xlsx。

