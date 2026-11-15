# 三组材料入口：已验证范围及当前运行

私有 `c08_h18_hg_groups_build_r1` 已完成一个host TU编译及链接，两次实际Win32/Popen出口均0。114个链接对象中只替换JSphGpuSingle；其余113个保留，包括C-quality CUDA、host fault capture及另外两个optimized HG对象。材料返回、HG Node、积分和物理CUDA算子未改。旧ψ0的精确输入仍在准入范围；新增ψ+2.5/coh5000/sf.2与ψ−5/coh7500/sf.2，φ/φr明确限定25°。弧度存储采用原XML的float(TORAD*float_degrees)表达式。

随后单独构建并运行了CPU Debug制造解probe。实际生产EvaluateMaterial按三组完整参数共21点：6 Elastic、6 Smooth、2 Apex、4 TensionRepair、3 Invalid；另3次无效输入ReturnMaterial确认六应力与κ输出均不提交。triggerON的3个Smooth确实进入塑性分支，无空检查。对比独立指数律、DP系数及张量弹性compliance制造解，保留原预算：最大应力误差2.1827872842550278e-11Pa，正屈服误差1.3642420526593924e-12Pa，κ误差1.5178830414797062e-18，体积流动误差1.1519648082658485e-19。材料常数与持续κ仍为原float；不是将所有材料参数改double。

probe的生产头已与实际新私有程序对应的冻结头逐字节对齐。它是单独的CPU代数验证，不是GPU dispatch、HG producer、完整空间求解或物理验收。仍需实际GPU的ψ0原短prefix回归和每组精确材料/阶段检查；不能将缓存13输入/7提交一致性充当独立材料解。当前不并发GPU回归以免干扰唯一活动源计算，也不新增half链。

唯一活动物理任务为 `c08_h18_wend_branches_psi2p5_pre_r1`：owner50100、原solver40384，2026-11-16约06:37 JST启动。它使用独立原generic schema2/law2程序，非新HG私有程序；H1.8/Wendland/dp.04/5us，目标10s/2M更新/1001帧，阻尼.03与Shepard40，AS/HG/NoPen off。源材料κ/σ/J/p保留，不借用ψ0 PRE。新host构建没有修改该活动程序、输入或依赖。完成后只有一次direct-owner同线程终态通知，无额外watcher或重挂。

ψ0完整3s的严重材料折叠及极小间距已改善，但局部负孔压尖峰仍记录为未解决。ψ+2.5的源完成后必须独立native及应力/压力/速度收敛审查，才决定短接收和3s塌陷；ψ−5源/所有新接收尚未启动。正常出口、制造解或guard编译通过不替代论文/完整物理验收。原案例、源及全部失败/程序/源码/BI4/typed/图CSV保持原状。

本轮仅新增tests脚本、输入、冻结候选和记录；公共源码与根正式XML/BAT未改。原公共C-quality补丁在已有检查点46fc573中，新的三组HG仍是私有候选，尚未宣称正式公共接口。零SHA扫描；只有新归档及必要小文件的字节比较/身份stat。
