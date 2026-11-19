# 私有 CPU/GPU 候选的压力积分选择

在候选运行时 XML 的 `case.execution.special.hydromechanics` 中使用以下设置。原有限 Kw 积分对应缺省值 0；显式 1 在已支持的动态 u-pl Cryer 工况中使用 M0、α=0.5、β=0、三轮端点修正和五阶段必要步长检查。0 和 1 均沿用已有 `DtFixed` 和输出设置，水力因子为 1。

```xml
<HydroMech value="1" />
<HydroMechDynamicSeepage value="1" />
<HydroMechPressureIntegrator value="1" />
```

测试准备脚本将选择器接入独立的 JSph.cpp 配置读取，以及两后端的压力与步长路径。配置在首个压力阶段前一次读取；无环境变量开启 B 的旁路。实时系数、材料、孔压空间算子、荷载和排水策略沿用原实验。已发到服务器的 ZIP 与公共发布程序仍使用各自原来的配置方式。

| 真实程序验证 | CPU Debug | GPU Release |
|---|---|---|
| 缺少选择器、显式 0 | 与新的默认 A 两步对照逐位一致 | 与新的默认 A 两步对照逐位一致 |
| 显式 1 | 与三轮 B 两步对照逐位一致 | 与三轮 B 两步对照逐位一致 |
| 无效选项 2、重复定义、动态 u-pl 关闭、误放 soils、旧环境开关冲突、B 请求从现有 PART 重启 | 六组均在写首帧前退出 1 | 六组均在写首帧前退出 1 |

每次正常短测有 37,181 个原生 ID（其中 37,173 个土粒），两帧共 22 种数组和有符号时间步记录均逐位匹配。共享压力更新函数已接入实际 CPU 和 CUDA 编译单元，另外复核 A128/B64 当前两个保存时刻的全部字段以及 B 的三轮记录。GPU Debug 两步 memcheck 为零错误。私有 CPU 程序适用于现有三维短窗；这些回归检验实现等价性。服务器回传后在相同材料 ID 与排水相对时钟上评估峰高、相位和尾段。

原生库已在派生 PART 副本上验证上一完整步孔压的读写、材料重排和损坏拒绝。支持完整求解器重启还需要实际保存路径接入、后端历史恢复与重启连续性试验。本版本明确拒绝 B 的旧 PART 重启。

[可复现配置生成器](../support/cryer_xml_prepare_r1.py) · [CPU 测试](../support/cryer_xml_cpu_checks_r1.py) · [GPU 测试](../support/cryer_xml_gpu_r1.py) · [压力历史复核](cryer_history_io_r3.md) · [步长放大量](../../../validation/upl_tpi_r_selection_r1.md)
