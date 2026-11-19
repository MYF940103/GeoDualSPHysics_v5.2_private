# Cryer 共享压力行接入私有 CPU 求解器

采用 ν=0.30、固定材料集合的三维 Cryer 球体。B 的机械预测和三个端点更新调用同一份 `TpiPressureRow.h`。预测使用本步起点与上一个完整步的 float 压力，按 double 计算后写回 float。每个端点消费实际边界处理后的邻域压力、原三维离散残差和对角项。整步第三轮完成时一次提交压力历史。默认 A 沿用有限 Kw 积分。

## 构建与复核

基于已核验的 `outputs/upl_tpi_cryer_p3_cpu_r1_source` 建立新副本。VS2022 DebugCPU x64 编译全部 86 个翻译单元，`JSphCpu.cpp` 和 `JSphCpuSingle.cpp` 的包含依赖均指向新副本的共享头。构建日志有 1 条 MSB8029、86 条 D9035 和 52 条 LNK4099，分别涉及中间目录、原项目的 /Gm 选项以及预编译库调试符号。构建退出值为 0。[构建及文件哈希](../logs/cryer_row_cpu_r1_DebugCPU.row.json)

每个工况有 37,173 个土粒和 8 个固定粒。A128 使用原始输入，清除所有私有选择器。B64 使用同一份粒子输入和封存的较大步长，开启 B、三轮修正和 Eq.40 Rh=1 检查。A 的基线为 `upl_cryer_freebody_smoke128_CPU_r1`，B 的基线为 `upl_tpi_cryer_p3_cpu_B64_r1`。两者分别在 0 和 0.0001220703125 s 保存。这段时间处于围压爬升阶段。

| 工况 | 固定步长 μs | 末帧中心 18 粒平均孔压 Pa | 末帧带符号的 dt−限值 s | 原生数组逐位相同 |
|---|---:|---:|---:|---:|
| 默认 A，128 步 | 0.95367431640625 | 382.645357 | −6.4044993903×10⁻⁷ | 两帧各 22 项 |
| B，64 步 | 1.9073486328125 | 329.572735 | −1.0714208008×10⁻⁶ | 两帧各 22 项 |

两组均以 0 退出，排除粒子数为 0。按材料 ID 排序后，两帧的全部字段和实际保存时间、步长、带符号的限步误差均与各自基线逐位相同。B 的逐材料各轮压力 CSV、五相步长 CSV 及两个汇总 JSON 与原 B64 字节一致。B 实际执行 64 次历史提交、192 次端点写回和 49,960,512 次只读字段位检查。两项并行运行的 CPU 循环耗时分别为 555.96 s 与 617.65 s。此段只覆盖开排水前的初始爬升，峰值与相位需由后续窗口检验。[A128 对照](../logs/cryer_row_cpu_A128_r1.compare.json) · [B64 对照](../logs/cryer_row_cpu_B64_r1.compare.json)

从本 case 的 `tests` 目录执行以下命令可在新的修订号复算，最后两条分别在进程退出后自动核验本次 BI4 与封存基线。

```powershell
py -3.11 -B support/cryer_row_cpu_r1.py build --revision 2
py -3.11 -B support/cryer_row_cpu_r1.py A128 --revision 2
py -3.11 -B support/cryer_row_cpu_r1.py B64 --revision 2
```

所需 Python 包为 NumPy 和 psutil。私有 VS 目标、运行库和上述封存输入沿用既有 Cryer 构建环境。源码准备程序记录了实际修改的预测和端点计算调用，生成的统一差异保存在私有源副本根目录。[复算脚本](../support/cryer_row_cpu_r1.py)

## 私有 XML 选择器

在上述行算术完全相同的基础上，另建 CPU Debug 候选，由 `case.execution.special.hydromechanics` 下的 `HydroMechPressureIntegrator` 选择压力积分。与上一轮程序分别在相同步长做两步、保存初末两帧，三个合法用法均通过。两次完整构建的告警类型和数量一致。选择器头文件进入 `JSph.cpp`、`JSphCpu.cpp` 和 `JSphCpuSingle.cpp`。[构建收据](../logs/cryer_xml_cpu_r1_DebugCPU.source.json) · [源码生成器](../support/cryer_xml_prepare_r1.py)

| XML 选择 | 实际积分 | 末帧时间 μs | 末帧带符号的 dt−限值 s | 两帧对照 |
|---|---|---:|---:|---|
| 省略 | 有限 Kw | 1.9073486328125 | −6.40451522963×10⁻⁷ | [22 项逐位一致](../logs/cryer_xml_cpu_absent_r1.native.json) |
| `value="0"` | 有限 Kw | 1.9073486328125 | −6.40451522963×10⁻⁷ | [22 项逐位一致](../logs/cryer_xml_cpu_explicit0_r1.native.json) |
| `value="1"` | M0，三轮 | 3.814697265625 | −1.07142128358×10⁻⁶ | [22 项逐位一致](../logs/cryer_xml_cpu_explicit1_r1.native.json) |

三个候选都保有 37,181 个材料 ID，排除数为 0。保存时间、步长和带符号的限步误差与各自新运行的两步基线逐位相同。显式 B 完成 2 次提交及 6 次端点写回，压力和步长的 CSV 及两个汇总文件均与通过原环境变量启用的 B 逐字节相同。

六个错误输入逐项启动实际程序，均在写出首个原生 PART 前以码 1 停止并给出对应原因。涵盖取值 2、重复元素、关闭动态渗流时启用 B、选择器放在 `soils`、残留旧环境选择器，以及从真实两步 B 的 `Part_0001.bi4` 重启 B。CPU 候选继承原 Cryer 专用限制，包括 ν=0.30、HG0、指定材料集合与至多 128 步的显式短程限制。[错值](../logs/cryer_xml_cpu_invalid_r1.reject.json) · [重复](../logs/cryer_xml_cpu_duplicate_r1.reject.json) · [渗流关闭](../logs/cryer_xml_cpu_dynamic_off_r1.reject.json) · [位置错误](../logs/cryer_xml_cpu_misplaced_r1.reject.json) · [旧环境](../logs/cryer_xml_cpu_stale_env_r1.reject.json) · [重启](../logs/cryer_xml_cpu_restart_r1.reject.json)

已有私有 XML 源副本时，可在 `tests` 目录用下一可用修订号完成独立构建和全部短测。

```powershell
foreach ($check in 'build','refA','refB','absent','explicit0','explicit1','invalid','duplicate','dynamic_off','misplaced','stale_env','restart') {
    py -3.11 -B support/cryer_xml_cpu_checks_r1.py $check --revision 2
    if ($LASTEXITCODE -ne 0) { throw "CPU XML check failed ($check)" }
}
```
