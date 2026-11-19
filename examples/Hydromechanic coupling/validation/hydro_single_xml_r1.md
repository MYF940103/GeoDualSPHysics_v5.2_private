# 水力模型与外载的正式 XML

## 配置

`special/hydromechanics/HydroMechModel` 缺省为 0，沿用 u-pw。1 选择有限水体积模量的显式 u-pl，2 选择 TPI u-pl。当前公共程序支持 0 和 1；Cryer 验证程序支持全部三个值。公共程序请求 2 时在写首帧前退出。启用水力耦合仍使用 HydroMech。

外载集中在同级的 `special/externalload`。省略时无外载，mode 支持文档中的编号和名称，q0 的单位为 Pa，ramptime 的单位为 s。旧动态开关和三个旧外载键从公共读取路径移除。排水时刻、渗透率模型和材料参数各保留原来的定义。两套 GPU、CPU 加载路径共享原有斜坡、条带与排水遮罩的几何判定。

## 实际回归

公共程序覆盖无载自重、顶面载荷、核带载荷、球面围压、Lian 和 Yao 两个条带。用修改前版本 41d23c4 的同后端输出作对照。各工况跑六步，对全部保存时刻按粒子编号比较全部字段、实际时钟与有符号步长偏差。短窗将有载工况的升载与排水开放分别置于第 2、3 步，使两种事件都进入测试。正式 XML 的时间配置另由真实 GenCase 和迁移前后的定义核对。

| 工况 | 末帧有非零外载的粒子 | 末帧排水粒子 |
|---|---:|---:|
| 自重 | 0 | 10 |
| C02 顶面 | 10 | 10 |
| C02 核带 | 40 | 10 |
| Cryer | 37,173 | 5,153 |
| Lian | 13 | 188 |
| Yao | 59 | 142 |

载荷按已保存加速度乘参考粒子质量统计。C02 两个载荷各约 1000 N/m，Lian 约 13000 N/m，Yao 约 29500 N/m。三维 Cryer 采用指向球心的径向分量。另有缺省模型与干土六步测试，以及旧键、混写、重复、错拼、越界或关闭耦合的输入错误测试。[CPU 记录](hydro_public_single_r1_cpu_single.json) · [GPU 记录](hydro_public_single_r1_gpu_single.json)

私有 TPI 的 CPU、GPU 各检验缺省、0、1、2，以及六种旧键或冲突写法。模型 2 完成两步、六次端点更新，37,181 个原生 ID、22 个字段、积分时钟及三轮压力和五相步长记录与各自原版本逐位相同。[私有模型回归](../04_CryerProblem_PR/tests/logs/cryer_model_strict_r1.check.json)

## Debug 弹窗

旧 exe 的 minidump 与原机器指令显示，main 为 JSphCpuSingle 预留 3288 字节，而其中的构造函数访问到至少 3520 字节。CRT 在 main 返回时发现邻近变量 e 的栈保护字已损坏。计算日志中的 code=0 早于此检查。对照源码干净重编后正常。常用 bin/windows DebugCPU 已通过权威 VS 方案全量重建，Cryer 六步真实退出 0，并逐帧通过同后端数据复核。[转储诊断](hydro_public_xml_r1_debug_dump.json) · [默认程序复测](../04_CryerProblem_PR/tests/logs/cryer_default_debug_r2.check.json)

## 物理结论范围

C02 三轮 TPI 在十个时间因子的孔压和沉降相对显式方案达标，底层总应力原 100 Pa 标准超限 225 帧。Cryer 的正式合入需审核服务器返回的密集峰窗及完整衰减。运行既有服务器包、PRE 或哈希绑定的版本时，应使用各自的原程序与 XML。[C02 物理审查](../02_TerzaghiConsolidation_q0_PR/tests/notes/upl_tpi_p3_full_physics_r1.md) · [Cryer 回传步骤](../04_CryerProblem_PR/README_Cryer_TPI_P3_nu030_r1.md)
