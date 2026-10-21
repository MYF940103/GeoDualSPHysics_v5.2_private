# 当前正式图与数据（2026-10-21）

当前索引仅包含已接受的k=1e-3、1e-4完整2Tv结果。k=1e-5仍在tests计算，不混入正式完整对比。下列`full_validation_latest`是当前展示入口；原`full_validation_release_*`及其验收哈希保持冻结，旧`full_validation_q0_*`是历史版本。历史图中的`k5em4`表示5e-4，不是本次尚未完成的1e-5。

## 图片

- [孔压耗散、晚期放大、固结度、顶部材料沉降](full_validation_latest_history.png)
- [k=1e-3各Tv孔压剖面及晚期横轴放大](full_validation_latest_profiles_k1em3.png)
- [k=1e-4各Tv孔压剖面及晚期横轴放大](full_validation_latest_profiles_k1em4.png)
- [总应力残差、顶部相邻层差、Q和底层材料偏差](full_validation_latest_diagnostics.png)

剖面为Tv约0.005、0.05、0.1、0.25、0.4、0.5、0.7、1、1.5、2；空心圆是实际原生SPH粒子层平均，实线是实际保存Tv下的经典Terzaghi理论。纵轴是初始材料位置z0/H，沉降跟踪同一组顶部/底部原生材料粒子，不与移动分层或整面墙漂移混用。理论为理想加载、不可压水、小应变参考；数值仍有有限Kw、.01 s斜坡和移动粒子。

## 配套CSV

| 文件 | 内容 |
|---|---|
| [history_data](full_validation_latest_history_data.csv) | 每组201行，目标Tv=0,.01,...,2；孔压、固结度、材料沉降、总应力/Q等 |
| [profiles_data](full_validation_latest_profiles_data.csv) | 两组各10个时刻、各100个材料层，数值与同位置解析孔压 |
| [k1em3宽表](full_validation_latest_profiles_wide_k1em3.csv) / [k1em4宽表](full_validation_latest_profiles_wide_k1em4.csv) | 各时刻孔压为列，便于自行绘图 |
| [k1em3解析曲线](full_validation_latest_theory_curves_k1em3.csv) / [k1em4解析曲线](full_validation_latest_theory_curves_k1em4.csv) | 图中实际使用的201点平滑解析曲线 |
| [targets](full_validation_latest_targets.csv) | 实际原生PART、实际时刻/Tv和各剖面RMSE |
| [summary](full_validation_latest_summary.csv) | 两组末时孔压、沉降误差、Q等汇总 |
| [output_cadence](full_validation_latest_output_cadence.csv) | 积分dt、原生保存间隔、发布目标间隔及换算值 |

`target_tv`只是目标采样位置；`actual_tv`、`time_s`、`native_part`/`native_file`记录真正的数据来源。历史表每组从原生密采样中选择201个不同的最近真实帧，未插值SPH场，也没有改写原生输出；最大目标Tv偏差约0.00013723。Tv=0选择排水开启附近的加载后帧，不拿未加载t=0的零孔压当作起始超孔压。解析曲线在Tv=0使用精确初始条件，不用有限傅里叶项的截断残差冒充初始沉降。

诊断图的应力/Q只绘制物理t≥.1 s部分；该发布采样不是全历史安全门的替代品。原验收的全部原生保存帧和密采样检查记录继续保留，不能靠减少输出规避早期峰值。

## 输出间隔、积分dt与排水事件不是一回事

Tv=Cv(t-tD)/H²，Cv=kM/(rho_w*9.81)，M=E(1-nu)/[(1+nu)(1-2nu)]。本算例H=1 m、E=2e6 Pa、nu=.3、rho_w=1000、tD=.01 s。

| k(m/s) | ΔTv=.01对应的物理输出间隔(s) | 当前根XML的TimeOut(s)，本轮未改 |
|---|---:|---:|
| 1e-3 | .0364371428571429 | .001 |
| 1e-4 | .364371428571429 | .01 |
| 1e-5 | 3.64371428571429 | .1 |

TimeOut的单位一直是秒；按Tv要求输出，需要先换算成秒。当前三组根XML的TimeOut恰好都等价于ΔTv≈.000274445，约比要求的.01密36.4倍；它们不是三个不同的无量纲采样间隔。本轮只将正式展示图/CSV整理到目标ΔTv=.01，没有更改XML/BAT、积分dt或正在运行的k5输入。后续若调整原生保存频率，还需保留加载/排水初期的诊断采样，且不得把已经运行过的密采样结果谎称为新频率重算。

另核对旧k1e-3/k1e-4的生成XML与401帧历史：其TimeOut为.0182185714285714/.182185714285714 s，实际ΔTv约.005。无论旧值是.005还是今后约定的.01，规范应以目标Tv间隔换算，而不是只看秒数。积分dt仍是求解器推进一步的秒数，与TimeOut不同。

`HydroMechDrainageFixedGrid`实际含义是固定时间步下的排水开启时刻对齐，不是空间网格。常dt且tD恰落在N*dt上时，只在机器舍入量级内补偿TimeStep累计误差，避免本应在tD开启的排水被推迟一步；排水位置和p=0边界值、积分dt与输出频率均不因此改变。实现：CPU `src/source/JSphCpu.cpp:1165`、GPU `JSphGpu.cpp:1104`，初始化限制在`JSph.cpp:597`；只支持已明确检查的恒定步长新鲜启动。

## 来源与重绘

来源是原`full_validation_release_k1em3_GPU`与`k1em4_GPU`的已验CSV和原生BI4；脚本先核对源CSV、读取工具、生成XML和所选原生帧的旧记录哈希，并独立重算20个原生剖面及初末材料状态。没有重新调用物理求解器。

脚本为`../support/refresh_full_validation_q0.py`，本次数据检查见[check](full_validation_latest.check.json)，目视检查见[visual](full_validation_latest.visual.json)。再次运行默认保护已存在结果；只有尚未目视批准的图允许显式`--repair-layout`并须保留上一布局快照。本次图例位置修正前的图及脚本在`../tests/outputs/latest_figures_layout_r1`，未覆盖历史验收文件。
