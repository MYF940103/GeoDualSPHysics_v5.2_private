# Cryer grad1二进制精确更细半步检查（2026-10-27）

当前状态仅准备，主代理审查后才运行`python -B tests/support/cryer_grad_fine_r1.py --run`。
旧grad1的2.5/1.25us各单组原生安全通过，但其半步孔压RMS最大56.2603526964Pa，仍未通过5Pa；
原grad0失败56.380737Pa也保留。制造场的一阶收益不等于快启动时间误差已解决，更不是峰值准确度结论。

本次只新启动两组CPU Release：

| 标签 | dt(s) | 总步数 | TimeMax(s) | TimeOut(s) |
| --- | ---: | ---: | ---: | ---: |
| cryer_grad_fine_r1_c | .000000476837158203125 = 2^-21 | 1024 | .00048828125 = 2^-11 | .0001220703125 = 2^-13 |
| cryer_grad_fine_r1_h | .0000002384185791015625 = 2^-22 | 2048 | 同上 | 同上 |

各5个原生保存帧，全部时间点二进制精确。与旧5帧的十进制网格并不相同，绝不插值比较、
不叫旧轨迹same-dt前缀。两XML从对应`cryer_grad_short_r1`复制，仅改DtIni、DtFixed、
TimeMax、TimeOut四项；应力率grad1、原始外载、密度、阻尼=.02、k、排水、几何及精度路径均不变。
不写D、不新增生产/API/默认值，也不改变正式入口。

先c安全通过才启动h。复用原`inspect/native`：37173原生土ID、有限/正密度/零塑性/无排除、
激活FSType2/3排水严格零、机械自然步长及原孔压扩散步长。固定初始r<=dp的材料中心采样。
新粗/半全部5个实际完全相同时间点按原孔压场RMS<=5Pa、材料位移最大差<=.005mm配对；
不放松阈值或隐藏早期样本。绑定旧grad_short检查/运行/准备清单与当前CPU Release程序哈希
`dc4e2a1feb2245e5a9c567d1bc1877e774a6b70b1058e805f4c6d61aa063ca9c`。

预算3072步约13分钟只是基于前窗的非隔离估计；如变慢只打印进度，不因预算自动终止。
允许现有GPU memcheck继续，记录并发进程且不停止它。只管理本序列CPU wrapper子树，
拒绝其他Cryer CPU。没有新通知器、GPU测试或自动峰窗准入；失败保留实际原因和完整已有输出。

文件按既有`tests/support、notes、configs、logs、outputs、figures`放置，
只生成summary/half两份CSV，不重复options/nativeDiff、旧参考循环或本阶段绘图。
源码、正式文件及Git不变；仅prepare不需要重编译。
