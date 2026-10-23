# 当前三组正式图与数据（2026-10-24）

三组均已完成2Tv并按用户暂时接受的一维弹性孔压/材料沉降范围验收。共同dp=.01 m、宽.1 m；k=1e-3/1e-4使用GPU、xi=.1，k=5e-5使用CPU八线程、xi=.05。不是仅改变k的严格控制实验，也不代表复杂边界、塑性、大转动或全周期半步长验收。旧图及原始输出不改写。

- [三组孔压耗散、晚期放大、材料沉降及误差](full_validation_three_history.png)
- [三组总应力、顶部应力差、Q及底层偏差](full_validation_three_diagnostics.png)
- [Tv=1、1.5、2三组独立晚期剖面](full_validation_three_late_profiles.png)
- 各Tv孔压剖面：[k=1e-3](full_validation_three_profiles_k1em3.png)、[k=1e-4](full_validation_three_profiles_k1em4.png)、[k=5e-5](full_validation_three_profiles_k5em5.png)
- 数据：[历史表](full_validation_three_history_data.csv)、[剖面长表](full_validation_three_profiles_data.csv)、[实际目标/原生PART](full_validation_three_targets.csv)、[终点/耗时汇总](full_validation_three_summary.csv)、[输入/保存频率元数据](full_validation_three_metadata.csv)
- 自行绘图宽表：[k=1e-3](full_validation_three_profiles_wide_k1em3.csv)、[k=1e-4](full_validation_three_profiles_wide_k1em4.csv)、[k=5e-5](full_validation_three_profiles_wide_k5em5.csv)

每组历史400行，目标Tv=.005,.010,...,2；10组剖面包含Tv=.005、.05、.1、.25、.4、.5、.7、1、1.5、2。均使用最近真实保存帧、实际Tv和初始原生材料坐标，不插值SPH场。第三组没有排水开启瞬间的正式帧；共同图不拿未加载t=0的零孔压作为初始超孔压。原生402帧仍完整保留，其中包含未加载初态和最后非整间隔帧。最大目标/实际Tv偏差约.00013723。

| k(m/s) | 后端/xi | 2Tv压力剖面RMSE(Pa) | 顶部材料沉降(mm) | 沉降相对理论误差 | 记录主循环(h) |
|---|---|---:|---:|---:|---:|
| 1e-3 | GPU / .1 | 2.42883 | 3.657380 | -.45405% | 9.6254 |
| 1e-4 | GPU / .1 | .88109 | 3.658754 | -.41667% | 9.2079 |
| 5e-5 | CPU8 / .05 | 1.16019 | 3.658263 | -.43001% | 10.9760 |

耗时对应不同k、步数和输出频率，不作受控CPU/GPU速度结论。k=1e-4为已验生产步进伴随数据的明确发布复用，计时来自其`complete.json`，不是新正式BAT重跑。k=5e-5原生间隔约.3643714 s；旧两组原生间隔分别.001/.01 s，汇总选择间隔约.0182/.1822 s。`metadata.csv`将原生间隔与发布选择间隔分开，当前三组根XML的TimeOut均对应DeltaTv=.005。

第三组完整402帧独立复核、1657条哈希/证据核验及全部原安全门通过。Tv≥.1压力RMSE最大11.24 Pa；Tv=1至2的平均压力剩余比例相对理论差-1.03%，无持续伪平台。Q仍12.45 Pa，底层相对理论偏差.00127465 mm，不能称所有交错/空间应力误差已消除。经典理论未包含.01 s斜坡、有限Kw和移动粒子效应，理论g=9.81与Darcy回退9.80665之差亦未通过调参隐藏。

重绘脚本为`../support/publish_three_permeabilities.py`，无求解器调用，默认保护已验证输出；[数据检查](full_validation_three.check.json)及[六张图审阅](full_validation_three.visual.json)独立记录。新汇总草稿中的原生/发布频率标签已在审阅前修正，旧草稿源/CSV/清单保留于`../tests/outputs/three_metadata_draft_r1`，没有改任何原生场或旧验收清单。后处理还显式兼容了旧清单缺少dp/width元数据以及k1e-4采用伴随计时的来源差异。

## 历史两组发布索引（2026-10-21，以下仅描述当时状态）

当前索引仅包含已接受的k=1e-3、1e-4完整2Tv结果。k=1e-5仍在tests计算，不混入正式完整对比。下列`full_validation_latest`是当前展示入口；原`full_validation_release_*`及其验收哈希保持冻结，旧`full_validation_q0_*`是历史版本。历史图中的`k5em4`表示5e-4，不是本次尚未完成的1e-5。

## 图片

- [孔压耗散、晚期放大、固结度、顶部材料沉降](full_validation_latest_history.png)
- [k=1e-3各Tv孔压剖面及晚期横轴放大](full_validation_latest_profiles_k1em3.png)
- [k=1e-4各Tv孔压剖面及晚期横轴放大](full_validation_latest_profiles_k1em4.png)
- [Tv=1、1.5、2独立面板：两组晚期剖面与解析值](full_validation_latest_late_profiles.png)
- [总应力残差、顶部相邻层差、Q和底层材料偏差](full_validation_latest_diagnostics.png)

剖面为Tv约0.005、0.05、0.1、0.25、0.4、0.5、0.7、1、1.5、2；空心圆是实际原生SPH粒子层平均，实线是实际保存Tv下的经典Terzaghi理论。纵轴是初始材料位置z0/H，沉降跟踪同一组顶部/底部原生材料粒子，不与移动分层或整面墙漂移混用。理论为理想加载、不可压水、小应变参考；数值仍有有限Kw、.01 s斜坡和移动粒子。

1.5Tv、2Tv在上一版图与CSV中已经存在，并非漏算。新增晚期图每列单独显示一个Tv，每行对应一组k，单位改为Pa，标注实际Tv、实际时刻与剖面RMSE；同列两组使用相同横轴，不同Tv列为便于读数使用不同横轴范围。

## 配套CSV

| 文件 | 内容 |
|---|---|
| [history_data](full_validation_latest_history_data.csv) | 每组401行，目标Tv=0,.005,...,2；孔压、固结度、材料沉降、总应力/Q等 |
| [profiles_data](full_validation_latest_profiles_data.csv) | 两组各10个时刻、各100个材料层，数值与同位置解析孔压 |
| [late_profiles_data](full_validation_latest_late_profiles_data.csv) | 晚期独立图的600行：两组各Tv=1、1.5、2，数值与解析孔压 |
| [k1em3宽表](full_validation_latest_profiles_wide_k1em3.csv) / [k1em4宽表](full_validation_latest_profiles_wide_k1em4.csv) | 各时刻孔压为列，便于自行绘图 |
| [k1em3解析曲线](full_validation_latest_theory_curves_k1em3.csv) / [k1em4解析曲线](full_validation_latest_theory_curves_k1em4.csv) | 图中实际使用的201点平滑解析曲线 |
| [targets](full_validation_latest_targets.csv) | 实际原生PART、实际时刻/Tv和各剖面RMSE |
| [summary](full_validation_latest_summary.csv) | 两组末时孔压、沉降误差、Q等汇总 |
| [output_cadence](full_validation_latest_output_cadence.csv) | 积分dt、原生保存间隔、发布目标间隔及换算值 |

`target_tv`只是目标采样位置；`actual_tv`、`time_s`、`native_part`/`native_file`记录真正的数据来源。历史表每组从原生密采样中选择401个不同的最近真实帧，未插值SPH场，也没有改写原生输出；最大目标Tv偏差约0.00013723。Tv=0选择排水开启附近的加载后帧，不拿未加载t=0的零孔压当作起始超孔压。解析曲线在Tv=0使用精确初始条件，不用有限傅里叶项的截断残差冒充初始沉降。

诊断图的应力/Q只绘制物理t≥.1 s部分；该发布采样不是全历史安全门的替代品。原验收的全部原生保存帧和密采样检查记录继续保留，不能靠减少输出规避早期峰值。

## 输出间隔、积分dt与排水事件不是一回事

Tv=Cv(t-tD)/H²，Cv=kM/(rho_w*9.81)，M=E(1-nu)/[(1+nu)(1-2nu)]。本算例H=1 m、E=2e6 Pa、nu=.3、rho_w=1000、tD=.01 s。

| k(m/s) | 当前根XML的TimeOut(s)，对应ΔTv=.005 | 保留结果原生间隔(s)，不改写 |
|---|---:|---:|
| 1e-3 | .0182185714285714 | .001 |
| 1e-4 | .182185714285714 | .01 |
| 1e-5 | 1.82185714285714 | .1 |

TimeOut的单位一直是秒；按Tv要求输出，需要先换算成秒。根目录三份正式XML已按上表恢复ΔTv=.005，CPU/GPU BAT共享这些XML，不必改BAT。积分dt、TimeMax及其他物理/数值参数不变。k=1e-3/1e-4已完成，不重跑、不改其生成XML、原生帧及旧哈希；表中保留结果仍是原密采样，约比.005密18.2倍，k=1e-5右列仅指旧失败运行。运行中的k5使用独立tests配置，保持不变。output_cadence.csv描述已发生的完整k3/k4运行，不随当前根XML更改而篡改。正式展示CSV仍为目标ΔTv=.005的最近真实帧。

默认TimeOut保存网格以物理t=0为原点，Tv则从排水tD=.01 s起算，因此恢复间隔不等于每帧精确落在整数目标Tv；实际保存还有至多一步的落点差。此轮没有新增special/timeout或改变积分时间，理论比较继续使用实际Tv。加载/排水初期的安全门须继续使用既有密采样诊断，不能以降低发行保存频率规避峰值。

核对旧k1e-3/k1e-4的生成XML与401帧历史：其TimeOut为.0182185714285714/.182185714285714 s，实际ΔTv约.005，用户的记忆正确。当前发布恢复此目标间隔；规范应以目标Tv间隔换算，而不是只看秒数。积分dt仍是求解器推进一步的秒数，与TimeOut不同。

`HydroMechDrainageFixedGrid`实际含义是固定时间步下的排水开启时刻对齐，不是空间网格。常dt且tD恰落在N*dt上时，只在机器舍入量级内补偿TimeStep累计误差，避免本应在tD开启的排水被推迟一步；排水位置和p=0边界值、积分dt与输出频率均不因此改变。实现：CPU `src/source/JSphCpu.cpp:1165`、GPU `JSphGpu.cpp:1104`，初始化限制在`JSph.cpp:597`；只支持已明确检查的恒定步长新鲜启动。

## 来源与重绘

来源是原`full_validation_release_k1em3_GPU`与`k1em4_GPU`的已验CSV和原生BI4；脚本先核对源CSV、读取工具、生成XML和所选原生帧的旧记录哈希，并独立重算20个原生剖面及初末材料状态。没有重新调用物理求解器。

脚本为`../support/refresh_full_validation_q0.py`，本次数据检查见[check](full_validation_latest.check.json)，目视检查见[visual](full_validation_latest.visual.json)。再次运行默认保护已存在结果；未批准图的布局修复使用`--repair-layout`，本次授权更新使用`--refresh`且先验证旧发布完整快照，`--snapshot`可指定`tests/outputs`内的快照名。上一版ΔTv=.01的图、CSV、检查记录、脚本和索引在`../tests/outputs/latest_figures_tv01_before_r1`；本次晚期图例移至图外前的快照在`../tests/outputs/latest_figures_late_layout_r1`；更早布局在`../tests/outputs/latest_figures_layout_r1`。原始验收数据不改写。
