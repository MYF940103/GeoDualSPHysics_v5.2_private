# 三维边界第一组审阅与后续顺序

2026-10-25。原二维Yao 10 s和case02三组正式结果不重跑。当前按原计划完成“静止边界适用性”，再进入适用的二维/三维正式验证；不要求先实现任意曲面和运动墙。

## 已完成

edge3（三维x/z双墙棱边）FreeSlip，1600土粒子+1104墙粒子，三方向非零初速度。CPU Debug 20步、CPU/GPU Release 2 ms各粗/半步已完成。每个完整算例201个匹配实际时刻，dt=1/0.5 µs；HG、NoPen、阻尼、排水和外载均关，原float u-pw和double应力保留。

| 检查 | 最大孔压RMS差（Pa） | 最大三维材料点位移差（mm） |
| --- | ---: | ---: |
| CPU独立半步 | 0.0148593320 | 8.70660243e-10 |
| GPU独立半步 | 0.0148595174 | 8.70988845e-10 |
| CPU/GPU同dt，全两对 | 4.49696439e-5 | 6.29684845e-10 |

原门限0.5 Pa/1e-5 mm不改；最大近似能量倍率1.020236984<1.1，原生ID/几何/弹性/自然步长检查通过。四张CPU半步、GPU半步、合并历史、原生切片PNG已逐张检查，配套CSV在figures同标签下。见logs/spr_3d_admission_r1.json。压力存在初始脉动和回弹，不冒充静态解析解或完整3D固结精度结论。

本轮发现并修复一个既有GPU退出问题，具体见spr_3d_cleanup_r1.md：JSphGpu.cpp析构中在cudaDeviceReset前释放GaugeSystem。真实正式程序和非零伴随的memcheck均从1错到0错，全部保留物理字段0 ULP。它只改变资源释放顺序，不改变数值。当前生产源码差异仅该注释与delete/置NULL两行；尚未作为最终完成批次推送Git。

## 正在自动推进的未跑组合

新序列spr_3d_next_r1仅依次运行corner3 FreeSlip、edge3 NoSlip、corner3 NoSlip，各CPU/GPU粗/半步；不重跑已完成edge3 FreeSlip。每组CPU、GPU及跨端全部原门通过才进入下一项。三面角是1000土粒子，所有方向都实际演化。NoSlip有切向启动瞬变，不宣称初速度场是其仿射精确解。图在批次结束后逐张复核，正常退出不等于完整三维验收。

按首组非隔离观测CPU粗113.09 s/半224.51 s、GPU粗38.31 s/半72.39 s，剩余顺序预计15–25分钟；仅作等待估计，不作为受控CPU/GPU性能验收。

只启动一个新序列和一个一次性终态通知。已核对本机codex queue --help及[官方命令文档](https://learn.chatgpt.com/docs/developer-commands?surface=cli)，以明确会话UUID排队同会话后续；不发送连通性测试，不重启任何旧worker。launch/status/followup/queue_attempt收据在logs；电脑关闭可能中断，不能保证断电后仍计算或自动重启，恢复时必须先核对拥有的进程和证据。

## 后续交付安排

1. 本批完成后核验全部原生数据、图和边界限制，必要时修复本轮实现/分析问题，不降低门限。
2. 同步doc/xml_format/_FmtXML_ElastoplasticSoil.xml中已实际通过的支持范围，做依赖清理与选择性Git备份；失败和未验收项不写成支持。
3. 二维Yao已完成10 s数据优先正式整理/采纳，避免只为改文件标签重复长算。其他二维目标按其边界需求先短窗，再决定正式算例。
4. 三维Cryer是排水自由球面问题，不能拿固定平面SPR去冒充其曲面支持；Selborne输入目前只完成建模，还缺多材料与局部时间孔压边界，不绕过停用BAT。它们的正式计算先明确缺项与可用范围；三维短脉动通过不等于塑性滑坡可以直接运行。

## 本轮文件位置与目的

- src/source/JSphGpu.cpp：唯一生产修改，修复CUDA上下文与测量缓存的释放顺序。
- tests/support/spr_3d_test.cpp：复用生产积分器，记录XYZ原生状态/应力/能量；不重写物理求解。
- spr_3d_build.ps1及既有gpu_fixture_build.ps1：链接VS权威项目对象；不增加新构建系统。
- spr_3d_run.py / spr_3d_review.py / spr_3d_cleanup_check.py：逐运行安全、独立半步、跨端、退出修复与逐位回归。
- spr_3d_continue.py：仅调度尚未运行的既定短测试；一次终态接续不负责物理验收。
- configs/spr_3d_r1_*_Def.xml与xspr_3d_r1_*_win64_CPU/GPU.bat：沿用既有XML/BAT结构；BAT执行粗/半步检查并拒绝覆盖。正式case根目录输入不动。
- outputs/spr_3d_*及logs/figures/notes同标签文件：原始证据、SHA清单、PNG/CSV与结论。修复前程序/源码/旧脚本保存在outputs/spr_3d_precleanup_r1，历史清单未改写。
