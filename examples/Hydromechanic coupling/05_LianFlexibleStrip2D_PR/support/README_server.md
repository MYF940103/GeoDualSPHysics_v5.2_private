# Lian 2D：Windows / RTX A6000 运行说明

## 运行

1. 将 `Lian_HGSPR_Windows_RTXA6000.zip` 完整解压到服务器本地磁盘；不要在 ZIP 内运行。
2. 服务器使用 Windows x64、RTX A6000 和适配的 NVIDIA 驱动。程序以 CUDA 11.7 / sm_86 构建；建议驱动不低于 516.01。不需要 Visual Studio、CUDA Toolkit 或 Python。
3. 双击解压目录中的 `xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat`。
4. 完成后将**整个** `CaseLianFlexibleStrip2D_PR_release_HGSPR_out` 目录复制回来，并保留本运行包及 `support/server_manifest.json`。不要只带回 VTK 或最后一帧。

运行包附带经过核对的 Release、GenCase、Chrono 依赖、OpenMP 和可用的微软应用本地运行库；Windows 系统 UCRT 和 NVIDIA 驱动仍由服务器提供。如果启动提示缺少运行库，安装微软官方 x64 VC++ Redistributable 后再试。服务器实际运行兼容性需以其日志为准，本机 RTX 3050 的短测不是 A6000 实机验收。

BAT 只执行 GenCase 和完整求解，保存原生 BI4/Extra/日志；不运行 Python、不批量生成 VTK、不自动绘图。命令行可加 `--unattended` 关闭结束时的暂停。输出目录已存在时直接退出，不覆盖、不清空、不重启。若中断，保留部分输出后联系分析；当前 HG 不支持精确历史/PART 续算，不能把改名或 PART 启动当作精确重启。

## 本次配置

- 时长 100 s；显式固定步长 10 µs，约一千万步；原生保存间隔 0.05 s，不是 Tv，也不是固定格点排水。
- `dp=0.1 m`，域 20×10 m；原 u-pw/Darcy，孔压/孔压率 float、应力与保存位置 double；无 TPI/u-pl 扩展。
- 非周期弹性沙漏 `SoilHourglassXi=0.1`，`SoilBoundaryDerivativeSPR=1`，`SoilStressRateGradCorr=1`；阻尼 0.04。
- 左/右墙分为 mkbound 0/2，均 FreeSlip；底墙 mkbound 1，NoSlip。三个平面的向内法向显式配置。
- 模式4条载：10 kPa、1 s斜坡；x=0处镜像接触，右边界仍1.25 m。保留13节点求积，后期合力约13000 N/m，比理想半条载12500 N/m高4%，并未暗中归一化。
- 1 s后仅基础外开放顶面排水；保持原源码时钟判定，不引入 case02 的固定格点排水。

程序与已完成 HG+SPR 3 s 对照相同；当前组合已通过3 s粗步安全/排水检查，HG短窗0.15 s独立半步已通过。用户明确取消该组合新的完整3 s半步，旧半步任务已停止且保留部分结果。这不是100 s完成或论文精度验收。请预留至少15 GB可用磁盘（2001个原生状态约7 GB，另有辅助文件；不含VTK）。不要按本机小显卡速度估计A6000耗时。

## 回拷后的对比

采样定义见 `support/paper_observables.json`：Fig10在0.5/1/3/50 s使用论文各行色限；Fig11为A/B超孔压；Fig12(a)为A/B向下正沉降；Fig12(b)为100 s、初始x=1.25 m整条竖向材料线上的**有符号**水平位移—高程。A=(0,10)m，B=(1.25,8.75)m，固定初始ID/插值权重，不逐帧寻找新粒子。

0.05 s保存沿用已测试设置，因此论文0.01–0.05 s的起始曲线未解析保存，不能插入伪数据。正式图片和配套CSV在回拷后生成到根目录 `figures`。历史 `postprocess_lian_release.py` 的固定帧索引、调色和HG关闭描述不适用于本包，不要直接作为新正式后处理。论文SPH/FEM是数值参考，并非解析真值。

## 程序与许可

`support/server_manifest.json` 记录输入/程序 SHA256 和构建来源；ZIP不包含 tests、历史输出或后处理运行环境。Git保存配置、脚本和证据，原生数据/程序/ZIP另行保存，不等于已上云Git。

- 项目许可：包内 `LICENSE`（LGPL）；对应源码版本和变更文件哈希见清单，源码可从原项目仓库或本项目交付者取得。
- Chrono 及其许可证：https://github.com/projectchrono/chrono/blob/main/LICENSE
- 微软运行库：https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
- CUDA 11.7 驱动说明：https://docs.nvidia.com/cuda/archive/11.7.0/cuda-toolkit-release-notes/index.html

后续主线在等待服务器结果时推进 Cryer，再做1D自重；不启动新的本地Lian 100 s计算。
