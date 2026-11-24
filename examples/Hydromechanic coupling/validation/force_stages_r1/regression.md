# 求力阶段拆分的同后端回归

比较拆分前后的 Windows x64 Release 程序。CPU 固定单个 OpenMP 线程，GPU 使用本机单卡。所有输入从已有 GenCase 粒子种子派生，脚本从原目录复制几何、法向并记录实际求解命令。短窗用于验证调度、字段依赖和临时数组生命周期。

| 短窗 | 原种子 | 测试动作 |
|---|---|---|
| 干柱 Verlet | `Elastoplastic_basic/12_GranularColumnCollapse/tests/outputs/basic_a05_dp002_r2_seed` | mDBC、Verlet、标准全 shifting，16 步 |
| 干柱 cDBC | 同上 | cDBC、Symplectic，6 步 |
| C02 模型 0 | C02 `tests/outputs/tpi_r_public_compat_gpu_r1/0_default/seed` | 固定 mDBC、带载、HG、排水，8 步 |
| C02 模型 1、2 | C02 `tests/outputs/tpi_r_public_compat_gpu_r1/3_default/seed` | 相同几何、带载，时间步各为 1 µs、10.00023 µs。2 步加载，3 步闭态，4 步后顶部排水 |
| C04 模型 2 | C04 `tests/outputs/public_tpi_sphere4hist_cpu_hist1/seed` | 三维自由球体原渐加围压，从头 4 步，三轮末端压力历史 |

在本目录准备已封存的 `old` 和 `validated` 两组 Release 可执行程序，使用同一仓库 `bin/windows` 的其余运行组件。四套原始几何和定义的 11 个文件收录在 [回归输入包](regression_inputs.zip)，共 441206 字节。源目录缺失时脚本会读取该包。已在独立临时目录核对，六组重建 XML、初始粒子和法向均与实际运行输入逐字节相同。以下命令只写新输出，同名运行及已有结论不会被覆盖。两次程序使用完全相同的准备输入。

```powershell
foreach ($version in @('old','validated')) {
    python -B regression.py run --version $version --lane dry_verlet column0 column2 sphere2
    python -B regression.py run --version $version --lane column1 --trial _stable
    python -B regression.py run --version $version --lane dry_cdbc --trial _cdbc
}
foreach ($backend in @('cpu','gpu')) {
    python -B regression.py compare --version validated --backend $backend --lane dry_verlet column0 column2 sphere2
    python -B regression.py compare --version validated --backend $backend --lane column1 --trial _stable
    python -B regression.py compare --version validated --backend $backend --lane dry_cdbc --trial _cdbc
    python -B regression.py bench --version validated --backend $backend
}
```

每帧核对 JBinaryData 的层级、字段类型、数组顺序、实际 ID、完整原始数值和实际保存时钟；对模型 2 额外核对所有非初始帧里的压力历史。最终同时比较整个 PART 字节流。两端的稳定输出模式在保存前把随机运行码、日期、墙钟用时设为其确定值。逐字节比较包括这些实际写入值，真实运行时间从 `Run.csv` 与 Python 外部壁钟单独读取。此处只比对同后端新旧实现。三个柱算例还核对原始 `Run.out` 中全部 HG 最终摘要行，按首次保存时的材料 ID 固定十个顶层土粒，并检查第 3 步时孔压为正、第 4 步起全部为零。

本轮首次显式模型 1 沿用 TPI 种子的 10.00023 µs，旧 CPU 在 step=0 被原必要步长界 6.37650 µs 拒绝。现场在 `runs/column1_cpu_old`、`seeds/column1`。新 CPU 用原输入得到相同首因和退出码 1，只有相同的初始 PART。有效显式比较采用两端均满足原条件的 1 µs，结果另存 `_stable`。

计时使用 C02 模型 2 原渐加荷载与排水时钟、每 0.001 s 保存一次、384 步。四组成对试验交替以旧、新程序开头，各记主循环计时 `TSimul`、总壁钟和输出数。计时过程与编译、其他求解和 GPU profiler 错开。此窗口只测相同荷载演化阶段的单位运行成本。

## 最终 Release 回归结果

表中帧数为每个后端实际保存的原生帧数，包含起始状态。两端分别与各自旧版比较。

| 算例 | 每帧粒子数 | CPU 帧数 | GPU 帧数 | 各后端的数组对数 |
|---|---:|---:|---:|---:|
| 干柱 Verlet 和 shifting | 7,028 | 17 | 17 | 187 |
| 干柱 cDBC | 7,028 | 7 | 7 | 77 |
| C02 模型 0 | 1,040 | 8 | 8 | 120 |
| C02 模型 1 | 1,040 | 8 | 8 | 176 |
| C02 模型 2 | 1,040 | 9 | 9 | 214 |
| C04 模型 2 | 37,181 | 5 | 5 | 118 |

108 个 PART 的完整字节流一致，CPU 共 66,696,287 字节，GPU 共 66,701,255 字节。模型 2 在各后端保存了 12 帧上步压力历史（C02 八帧、C04 四帧）。[CPU 主回归](compare_validated_cpu.json) · [CPU 显式](compare_validated_cpu_stable.json) · [CPU cDBC](compare_validated_cpu_cdbc.json) · [GPU 主回归](compare_validated_gpu.json) · [GPU 显式](compare_validated_gpu_stable.json) · [GPU cDBC](compare_validated_gpu_cdbc.json) · [原步长拒绝](reject_validated_cpu.json)

## C02 模型 2 计时

每格为旧版 / 新版主循环秒数，按配对编号列出。第一、三对先跑旧版，第二、四对先跑新版。配对中位变化使用每对新旧比值的中位数，与两个独立中位数之比有区别。

| 后端，384 步 | 第 1 对 | 第 2 对 | 第 3 对 | 第 4 对 | 主循环中位，旧 / 新 | 配对中位变化 |
|---|---:|---:|---:|---:|---:|---:|
| i7-12700，单线程，绑定逻辑核 2 | 9.933 / 9.936 | 10.389 / 10.191 | 10.128 / 10.779 | 10.036 / 10.235 | 10.082 / 10.213 | +1.01% |
| RTX 3050，默认主机线程亲和性 | 29.835 / 17.777 | 39.856 / 42.026 | 19.763 / 68.280 | 7.251 / 15.104 | 24.799 / 29.901 | +56.87% |

这八对计时运行每次各保存 5 帧，每对的 5 个 PART 均逐字节一致。CPU 总墙钟的配对中位变化为 −0.14%，GPU 为 +121.07%。在 GPU 各对中，主循环变化从 −40.42% 到 +245.50%。同一张卡曾分别处于 P8（367 MHz）和 P2（1912 MHz），这些瞬时读数无法单独解释耗时差异。[CPU 全部回执](bench_validated_cpu.json) · [GPU 全部回执](bench_validated_gpu.json)

另做一次 GPU 补测，将两个程序的主机线程绑定到同一性能核（Windows efficiency class 1，逻辑核 2）。两版各以 48 步暖机一次，再交替运行 4 对 192 步。每对 3 个实际保存的 PART 均逐字节一致。未锁定显卡频率或修改系统电源策略。可在空闲机器用 `python -B gpu_timing.py --version validated` 重现。

| 192 步，各组主循环秒数 | 第 1 对 | 第 2 对 | 第 3 对 | 第 4 对 | 各版主循环中位 | 配对中位变化 |
|---|---:|---:|---:|---:|---:|---:|
| RTX 3050，旧 / 新 | 3.213 / 3.542 | 3.242 / 3.226 | 3.189 / 3.217 | 3.203 / 3.205 | 3.208 / 3.221 | +0.48% |

本组主循环变化范围为 −0.48% 至 +10.22%，包括进程启动等开销的总壁钟配对中位变化为 +5.35%。整个补测期间 38 个 GPU 样本中有 36 个为 1912 MHz，功耗范围 11.65–41.72 W。四组同机短窗的主循环中位值接近，默认调度和包含启动开销的实测时间波动更大。现有数据无法把默认调度下两版的全部耗时差异归因于源码拆分，也不足以外推长程加速比。[补测完整回执](bench_validated_gpu_pinned192.json) · [逐秒 GPU 状态](bench_validated_gpu_pinned192.csv)
