# u-pw 已有验证基线与证据索引 r1

日期：2026-11-01，UTC+09:00。汇总时 Git HEAD 为 `9894aeab15ae510a6c1c07e1edf2d6be78e4c9b4`。本文件整理保留结果，不重算、不改物理模型，也不将历史数据追认为该 HEAD 或后续补丁的全程验证。

## 结论边界

| case | 已有结果 | 保留的结论 | 不能据此声称 |
| --- | --- | --- | --- |
| 02 顶载一维固结 | 三组完整 2Tv；相同 dp=.01 m、宽 .1 m | 用户已接受的一维弹性基线；压力、沉降及空间起伏的正式图和 CSV 已发布 | 三组仅渗透率不同、全程半步收敛或一般边界/塑性通过 |
| 01 自重一维固结 | 新鲜重力初始化、完整有限 Kw 的 Tv≈2，403 帧 | 完成并记录剩余误差；用户已要求暂缓继续修正 | 全部精度条件通过或残余平台已经消除 |
| 05 Lian 二维条形基础 | 100 s、2001 帧；补充 0–1 s 每 .01 s 输出 | 稳定的固定平面混合滑移弹性算例，原生安全检查和图表交付完成 | 与论文完全一致、全程半步收敛或一般接触验证 |
| 04 Cryer 三维球体 | ν=.30 完整返回数据，1065 帧 | 有限 Kw、固定材料点参考下峰幅约 1% 的保留基线；其余三 ν 组等待服务器返回 | 当前程序身份已追溯到旧服务器执行，或其余 ν 的精度已通过 |

所有结果必须区分“求解器结束”“实现/短窗一致性”“物理精度决定”三层。各 case 的加载、初始化、排水、开关和程序并不相同；改善不能统一归因于“双精度写回”或 SPR 单独一项。

## 02：三组已接受的一维顶载基线

依据 [full_validation_three.check.json](../02_TerzaghiConsolidation_q0_PR/figures/full_validation_three.check.json) 的 `cases`、`metadata`、`limitations`，以及后续 [visual.json](../02_TerzaghiConsolidation_q0_PR/figures/full_validation_three.visual.json)。前者保留了发布时的 `visual_review_pending=true`；后者绑定同一 check SHA 并完成六图视觉检查，不能只读前者的旧状态。

| k / m·s⁻¹ | 后端 / HG ξ | 末态压力剖面 RMSE / Pa | 顶部材料沉降相对理论误差 | 原指标 Q / Pa |
| --- | --- | ---: | ---: | ---: |
| 1e-3 | GPU / .1 | 2.428830 | −.454054% | 10.027038 |
| 1e-4 | GPU / .1 | .881094 | −.416672% | 10.108110 |
| 5e-5 | CPU8 / .05 | 1.160195 | −.430014% | 12.447627 |

三组均到实际 Tv≈2；HG 强度不同，因此不是仅改变 k 的严格对照。正式发布按 ΔTv=.005 选择原生实际时刻，无 SPH 时间插值；既有原生保存间隔不完全相同。1e-4 数据来自已接受的生产步长 companion，随后发布，不是再次由正式 BAT 重跑。记录的全程耗时不是受控 CPU/GPU 基准。范围仍为弹性、固定平面、小转动、新鲜 HG 起算；没有全程半步或精确 HG PART 重启证明。

## 01：完成但保留误差的自重固结

控制记录为 [sw_freshpr_review_r1.check.json](../01_SelfWeightConsolidation_PR/tests/logs/sw_freshpr_review_r1.check.json)。`stage_status=completed_with_limitations`；`physical_acceptance=false`、`formal_acceptance=false`，继续精度排查已由用户暂缓，不应改写为“全项通过”。

- 实际末时刻 7.316858768463135 s，有限 Kw 的 Tv=2.000000167；RTX 3050，20,459,420 步，403 帧、每帧 1040 个材料 IDs。
- 末态顶部材料沉降 1.990814409 mm；条件性 H1 有限 Kw 参考为 1.981117772 mm，约 +.48945%。末态压力 RMS 误差 40.875685 Pa。
- 当前随动静水参考的底部超孔压为 91.072724 Pa，原生固定初始 `float32(p−p0)` 为 22.709961 Pa；两者不可混用。底部/均值残余常数诊断为 28.452878/14.763702 Pa，原 5 Pa 预算未满足；该诊断也不等于已证明的无限时刻平台。
- 与旧结果近时刻比较，当前静水定义的底部超孔压下降约 84.16%，沉降交错 RMS 下降约 76.50%；这是多项改进的描述性比较，不是隔离的精度 A/B。

已按用户要求发布超孔压、总孔压、沉降合并图和匹配 CSV，见 [combined manifest](../01_SelfWeightConsolidation_PR/figures/CaseSelfWeightConsolidation_Scenario2_FreshPR_compare_combined_r1_manifest.json)。参考为实际保存时刻的条件性准静态 H1，不是惯性启动的精确解。没有全程半步或完整 longwin 前缀继承。

## 05：Lian 100 s 与论文数值参考

以 [完整原生检查](../05_LianFlexibleStrip2D_PR/tests/logs/lian_hgspr100_r1.check.json)、[返回结果总结](../05_LianFlexibleStrip2D_PR/tests/logs/lian_server_return_r1.final_review.json)、[早期补充](../05_LianFlexibleStrip2D_PR/tests/logs/lian_hgspr_early_r1.final_review.json) 和 [加密论文采样](../05_LianFlexibleStrip2D_PR/tests/logs/lian_hgspr100_r3.final_review.json) 为准。

100 s 数据为 RTX A6000 运行日志报告，dt=10 μs、10,000,000 步；侧壁 FreeSlip、底面 NoSlip，SPR=1、G1=1、HG ξ=.1、η=.04，孔压 float、应力 double。原 13 节点加载合力 13000 N/m 相比理想 12500 N/m 为 +4%，未暗中归一化。末态 A/B 孔压 .168874/.199475 Pa，材料沉降 1.832605/1.110029 mm；id1744 接触切换次数为 0。

本地 0–1 s 补充仅改变保存间隔/终止时刻，使用封存程序 SHA `260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c`；21 个共有实际时刻/步数的 34 个物理/身份字段逐位一致。输出区间统计 `dterror_s` 的两处差异单独记录并分别保持原安全条件，不得称为全部 35 字段 0 ULP。

论文图 11/12 加密采样为 730 行，其中 640 行可配对、90 行为 A/B 合并尾段而未分支；不是旧 25 点比较。论文 SPH/FEM 是栅格读取的数值参考，非解析真值，存在遮挡和读取包络。当前早期 A 点孔压及顶部水平位移仍有可见差异。保留 2081 行组合原生历史、100 s 竖向材料剖面以及匹配图/CSV，未重写正式求解数据。

服务器旧运行缺少独立实际加载 EXE/DLL SHA 与进程退出回执；本地可核包及原生结果，但不能用后来的本地程序哈希补认旧服务器执行身份。完整结果交付不等于完全复现论文、100 s 半步或一般大变形接触验收。

## 04：Cryer ν=.30 基线与三个待返回正式组

控制记录：[原生安全](../04_CryerProblem_PR/tests/logs/cryer_full_native_r1.check.json)、[理论与峰值](../04_CryerProblem_PR/tests/logs/cryer_full_review_r1.check.json)、[正式对数图](../04_CryerProblem_PR/tests/logs/cryer_full_review_r1_log.check.json)。ν=.30 实际结束 .9187412261962891 s，排水后 legacy Tv≈1，不是 2Tv；服务器 dt=2^-20 s，18 个固定材料点初始 r/a=.05。

有限 Kw、有限半径参考峰 12439.175960 Pa；原生峰 12310.520779 Pa，幅值 −1.034274%、峰时刻 +3.978928%，末态误差 −.404678 Pa。排水相对时间以 tD 为起点，Part64 是排水开启前状态，启动全过程不删除。旧 2^-21/2^-22 峰窗半步证据不能继承为该服务器步长的全程半步。原检查的 `physical_acceptance/full_cycle_acceptance/formal_acceptance` 均为 false；用户允许按约 1% 基线权衡交付，不代表取消安全阈值。

根目录 `figures/formal_validation/cryer_server_symc_full_r1_log.png` 及其 `*_native.csv`、`*_theory.csv` 已发布，原生 CSV 保留全部 1065 行启动/演化数据；只有正时间的 1000 行能显示在对数横轴上。详细状态/径向图仍在 tests/figures，不能说正式图缺失。旧服务器实际程序 SHA 尚未证明。

ν=.10/.20/.45 新正式包复用封存 EXE SHA `652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096`，不是按当前 HEAD 新编译；本地每组 128 步、两帧的启动检查通过，见 [便携检查](../04_CryerProblem_PR/tests/logs/cryer_nu_portable_r1.check.json) 和 [发包说明](../04_CryerProblem_PR/tests/notes/cryer_nu_release_review_r1.md)。该检查中 `full_run_started=false` 是当时本地交付范围。当前三组在服务器计算中仅依据用户报告，本汇总没有远端进程访问，也不声称观察到完成或通过。各 ν 必须使用自身 K/G、有限 Kw 理论和实际时刻复核。

## 本轮核对与后续入口

本汇总重新核对六组既有 manifest 中的 38 项 PNG/CSV：文件均存在且 SHA256 与记录一致；另核 C01/C05/C04 三个本地保留程序的 SHA，与上述记录相符，但不补认旧服务器身份。仅是交付完整性核对，没有重新读全量 BI4、重算理论或再次视觉验收。15 项控制记录的当前 SHA 和字段入口见 [机器可读索引](upw_baseline_r1.json)。已封存结果不等于当前源代码或今后 CPU/GPU 改动的自动回归证明；新的三壁速审计/最小测试必须独立给出构建与回归证据，不能改写历史记录。

接下来只完成当前壁速一致性审计及真正缺失的小测试，整理其适用范围；等待 Cryer 数据回拷后逐 ν 审阅。Yao 暂缓，retrogressive landslide、u-pl 变孔隙/渗透率与 TPI 尚未进入本轮实现/计算准入。自重剩余精度问题保留登记，不重启无界排查。
