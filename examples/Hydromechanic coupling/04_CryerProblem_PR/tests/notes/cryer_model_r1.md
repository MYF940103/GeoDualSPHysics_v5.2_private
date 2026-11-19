# Cryer 水力模型单键选择

在本次私有 CPU Debug 和 GPU Release 中，`execution/special/hydromechanics` 只需一个模型选择键。系统总开关 `HydroMech` 的缺省值为 0，打开后可使用下表。缺省按 u-pw 解释的前提是输入中也没有旧式选择键。

| HydroMechModel | 框架 | 压力更新 |
|---|---|---|
| 0（缺省） | u-pw | 原有限 Kw 显式积分 |
| 1 | 动态 u-pl | 原有限 Kw 显式积分，随材料更新 J、n |
| 2 | 动态 u-pl | TPI，α=0.5、三轮端点校正、β=0、水力步长因子 R=1 |

```xml
<hydromechanics>
    <HydroMech value="1" />
    <HydroMechModel value="2" />
</hydromechanics>
```

此片段展示两个开关。其余材料、流体参数和荷载按所选算例设置。旧式 `HydroMechDynamicSeepage` 沿用原布尔读法，旧私有组合也保留相同含义。新键与任一旧键混写时，解析器在首个 PART 前报告冲突。静态及动态求解器内部继续使用原生 PART 元数据。模式 2 现限已有的独立起算验证工况。

## 实际检查

- 在正式 Cryer 定义文件的三个派生副本中分别写入 0、1、2。GenCase 逐一生成运行时 XML；模型值、其余 16 个水力配置元素以及 8 个固定粒子和 37,173 个土粒的分组符合原定义。[三组前处理](../logs/cryer_model_gencase_r1.check.json)
- CPU 和 GPU 各自与相同后端的对应旧实现比较。每组两次实际更新，比较初帧、末帧全部 37,181 个原生 ID 和实际时钟。u-pw 的 15 个字段及两种动态模式的 22 个字段均逐位相同。模式 2 的三轮压力与步长记录也与先前候选一致。[CPU 静态](../logs/cryer_model_cpu_r1_zero.check.json) · [CPU 显式动态](../logs/cryer_model_cpu_r1_one.check.json) · [CPU TPI](../logs/cryer_model_cpu_r1_two.check.json) · [GPU 静态](../logs/cryer_model_gpu_r1_model0.run.json) · [GPU 显式动态](../logs/cryer_model_gpu_r1_model1.run.json) · [GPU TPI](../logs/cryer_model_gpu_r1_model2.run.json)
- GPU 缺省静态作业正常结束后，首轮分析使用了只接受动态 22 字段的读取器。以 u-pw 的实际 15 字段读取同一批输出后通过了逐位对照，原始作业及初次审查记录均保留。[离线复核](../logs/cryer_model_gpu_r1_missing.check.json)
- 越界值、重复键、新旧混写、未开启耦合时选动态模型、键放到 soils、TPI 使用缺少所需历史的旧 PART 均在首帧前报错。旧动态单键及旧双键分别复现模式 1、2。[CPU 测试](../support/cryer_model_cpu_r1.py) · [GPU 测试](../support/cryer_model_gpu_r1.py) · [GPU 汇总](../logs/cryer_model_gpu_r1.check.json)

公共发布和服务器包使用各自原有的配置说明。新键将与支持它的程序一起发布。Cryer 服务器峰高、相位及衰减的验收仍依据原计划。[私有源码准备](../support/cryer_model_prepare_r1.py) · [模型与外载交付顺序](../../../validation/upl_tpi_server_parallel_r1.md)
