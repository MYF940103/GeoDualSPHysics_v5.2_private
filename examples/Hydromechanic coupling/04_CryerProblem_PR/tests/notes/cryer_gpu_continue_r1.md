# Cryer已完成GPU Debug的离线复核与缺少Release续行（2026-10-27）

默认prepare只读取旧证据，不启动任何求解器；主代理审查后才以
`python -B tests/support/cryer_gpu_continue_r1.py --run`运行唯一未执行的Release。
不重启Debug、不改旧脚本或旧清单，也不把旧失败状态改成通过。

旧Debug实际正常完成200步、5帧、RTX3050；compute-sanitizer原文为
`LEAK SUMMARY: 0 bytes leaked in 0 allocations`与`ERROR SUMMARY: 0 errors`。
旧测试脚本错误要求另一工具格式`All heap blocks were freed`，因此在读取原生帧之前误拒。
新准备器严格检查所有ERROR/LEAK SUMMARY均为零，并复读5个原生帧，沿用原有限、正密度、
弹性、无排除、37173个原生ID、几何、真FSType2/3排水、机械和孔压自然步长检查。
同时核验旧prepared/run/perrun/input/output哈希、真实GPU、200步及实际时间；签认仅写入
新`logs/cryer_gpu_continue_r1.adopt_debug.json`及对应summary CSV。

续行只调用既有`configs/xcryer_gpu_base_r1_c_win64_GPU.bat`，使用原配套XML、程序及物理参数。
其输出、原log、原perrun和新续行清单任何一个已存在时均拒绝重跑。新控制器仅写自身清单，
不覆盖任何旧base JSON。保留t=.0005s、dt=2.5us、5帧、grad0、原外载和阻尼=.02；不新开GPU半步。
Release对照仍为已保留CPU `cryer_dt_short_r1_c`同dt五帧，原5Pa/.005mm门及原生安全不变；
旧CPU独立半步失败仍失败，不以本后端比较代替步长收敛或峰值准确度。

只拒绝其他Cryer GPU求解器；允许正在进行的CPU fine独立检查，记录其并发存在但不终止它。
只管理自身GPU wrapper子树，没有新通知器或自动长算。记录观察循环耗时而不当作隔离性能测量。

新证据在`tests/logs/cryer_gpu_continue_r1*`、CSV在`tests/figures`；Release原生输出按原BAT
放`tests/outputs/cryer_gpu_base_r1_c`。正常求解后先封存独立completion及全部输出哈希，再做
离线比较；若仅后处理失败，只能复用已封存输出修复新分析，绝不重新执行已完成BAT。
没有源码、正式输入、默认值、重编译或Git修改；原误拒证据和旧SHA保持不变。
