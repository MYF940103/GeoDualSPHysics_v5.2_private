# Cryer：既有预载峰窗的独立半步补验

本次只准备新测试文件。默认命令显示帮助；--selftest只读检查AST、XML/BAT和时间格点，不创建清单、不启动程序、不发送通知。主代理须全文审阅后，才可分别显式执行--prepare和--run。不调用任何旧worker的run/prepare/notify，不重启旧监测，也不自动准入正式长程。

## 唯一物理输入差异

基准为已经正常完成的cryer_preload_peak_r1。新XML完整保留其几何、材料、加载、排水、数值选项和注释，只将DtIni/DtFixed两处从2^-21改为2^-22秒。BAT沿用该基准的格式，仅替换测试标签。canonical GPU Release、源码和正式根目录文件全部不改。

| 项目 | 本次独立半步 |
|---|---:|
| dt | 0.0000002384185791015625 s = 2^-22 |
| TimeMax | .0703125 s |
| 计算步数 | 294912 |
| TimeOut | .0001220703125 s = 2^-13 |
| 原生保存帧 | 577，含初态 |
| 加载斜坡 | 2^-8 s |
| 排水开始 | 2^-7 s |

维持R=.05m、dp=.0025m、37173土粒子、k=1e-5m/s、q=10kPa、Visco=.1、SoilDampingCoef=.00004、grad1、原始柔性围压、fixed-grid排水事件、float孔压/密度、double持久应力；SPR/HG/shifting关闭。新输出只放tests/outputs/cryer_preload_peak_half_r1，拒绝任何同名已有输出。

## 来源和检查

准备时核验旧预载粗/半69帧、旧577帧峰窗、各run/build/program/input/completion/prefix及独立复核链接的SHA，并绑定已完成的有限储水、制造场、真实非积分融合算子、局部矩和六帧实际状态审计。后者仅是诊断前提，不是新的模型验收。再绑定本轮四文件、纯函数依赖、canonical程序及运行库；不覆盖任何已绑定程序。

本轮安全函数从原峰窗inspect完整复制，只将原生saved_step的256改为512。--selftest对两函数AST验证这一点；没有改写DataFrame或native步号。原粗步非初态part*256-1，本半步part*512-1。

全部577帧沿用原有限/正密度/弹性/无排除、固定ID与质量/h/dp、double保存位置/应力、实际向内载荷、几何半径、自然步与孔压扩散步检查。saved Part64恰在tD，仍按pre-open处理；只在t>tD要求全部真实非空FSType2/3点p严格0。末四个闭态Part61—64保留原五项平衡诊断，不把闭态均匀目标套用到排水后。

前69帧必须对已完成的cryer_preload_half_r1保持同dt、同cadence的全部35列逐位一致，包括dterror，没有排除项。后续全部577帧按精确实际时刻与原coarse峰窗配对，独立执行原孔压场RMS≤5Pa、材料最大位移差≤.005mm门。不得插值、删启动点、只比较峰附近或继承短窗半步代替本次完整配对。失败也保留完整已读记录，不放宽阈值。

## 生命周期和结果位置

单一worker仅启动一条新GPU BAT；起动前拒绝已有GPU求解器。正常wrapper退出后核对该标签无GPU残留；先封存原生输出完成清单及SHA，再执行离线检查。保留新summary/half CSV、69帧prefix JSON、run/status/check和stdout。求解失败或后检查失败均进入终态，不重跑；仅分析失败时保留已完成物理解，不重复计算。

结束后仅对prepare绑定的同一会话尝试一次codex queue，先封存queue_attempt，再记notification结果；失败不重试、不重新布置旧notifier或发送连通性自检。通知不运行求解器。

全部半步门通过仅表示本峰窗的已保存粗/半轨迹接近，仍需审阅有限储水/有限半径理论峰幅、峰时、压力/沉降/应力及启动响应。若门失败，只报告具体时刻和指标，继续诊断；不自动启动symC、正式完整耗散或服务器长程。

没有新的方程、参数接口、默认值、GPU源码或重启能力变更，因此不修改XML参数规范。相同canonical程序的历史约束仍适用。原coarse结果和所有旧失败记录原位保留，无Git操作。
