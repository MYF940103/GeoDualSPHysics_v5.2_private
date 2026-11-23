# Cryer 球 ν=0.30 · 公共 SPH/TPI GPU 版 · 1 Tv

主输入是 `CaseCryer_TPI_nu030_1Tv_Def.xml`。用文本编辑器即可查看球体几何、材料、载荷、排水和时钟。XML 中的 `HydroMechModel=2` 选择三轮 TPI（M=0、α=0.5、β=0、Rh=1）。服务器包名为 `Cryer_public_SPH_TPI_nu030_1Tv_Windows_RTXA6000.zip`。

运行 GeoDualSPHysics 公共 SPH 三轮 TPI、需要标准 Def.xml 和 BAT 时选本包。另一个弱式研究包为可选的独立对照，用于检验配对的应变/内力和真实球面牵引采用不同空间离散时的响应。两套程序、输入和结果不可互换。此前 ν=0.30 的密集峰窗和已经完成的研究轨迹均可直接查阅；本入口单独计算公共程序的 1 Tv 衰减。

## 运行

将 ZIP 完整解压到 Windows x64、有可用 NVIDIA 驱动的新目录，目标 GPU 为 RTX A6000。在解压目录运行下面的 BAT。路径可含空格，服务器使用包内 GenCase、GPU Release、PartVTK 和 DLL，以及 Windows 自带 PowerShell。

```bat
xCaseCryer_TPI_nu030_1Tv_win64_GPU.bat --smoke
xCaseCryer_TPI_nu030_1Tv_win64_GPU.bat
```

第一条从 XML 生成初态并实际推进两步，写入 `tests\outputs\cryer_tpi_1tv_smoke_gpu`。第二条独立从同一 XML 生成初态并计算至 1 Tv，写入 `CaseCryer_TPI_nu030_1Tv_GPU_out`。直接双击 BAT 运行全程。两个入口均在已有同名输出目录时退出，以保护原生资料。修改输入后请在新的解压副本运行，并记录参数差异。案例仓库内的同一 BAT 会使用项目的 `bin/windows`。

两个入口都依次执行 GenCase、公共 GPU 求解器、PartVTK，最后核对运行步数、退出粒子数、原生帧和 VTK 帧数。GenCase 生成 37,173 个土粒和 8 个远端固定标记。求解器在 `data` 保存 BI4，PartVTK 在 `particles` 保存包含材料 ID、速度和孔压的 Fluid VTK。两步短测会保存两帧。公共程序当前从 GenCase 初态启动。

冷启动初帧之后，每个原生 PART 的 `TpiPressureHistory` 子记录按材料 ID 保存上一整步用于外推的源孔压 `PorePressPrev`，同时记录步号、源时刻和保存时刻。首次开启排水时，受控表面点的源孔压已经施加规定的零压边界，上一闭态 PART 的 `PorePress` 仍可能为非零。相邻两个输出帧之间可能包含多个积分步。

| 全程参数 | 数值 |
|---|---:|
| 球半径 / 粒距 | 0.05 / 0.0025 m |
| 固定时间步 | 1.9073486328125 µs |
| 围压增至 10 kPa | 0.00390625 s |
| 排水事件 | 0.0078125 s |
| 结束时刻 / 更新步数 | 0.9187412261962890625 s / 481,685 |
| 排水前输出 / 排水后输出 | 每 64 步 / ΔTv=0.005 |
| 含初始态的输出帧数 | 265 |

Tv 沿用原项目的排水相对时间归一化。排水事件帧为闭态，下一步开启排水。每台设备应以实际结束时钟、排除数和原生数据复核。

## 回传与曲线

回传整个 `CaseCryer_TPI_nu030_1Tv_GPU_out`，保留生成的 XML/BI4、GenCase 日志、`Run.out`、`Run.csv` 和完整 `data`。在本机 C04 仓库目录中运行以下命令，选择新的图表目录。Python 和绘图库只在本机分析时使用。

```powershell
python -B support/plot_public_cryer_tpi.py "CaseCryer_TPI_nu030_1Tv_GPU_out" "tests/figures/cryer_public_1tv_return"
```

程序按实际保存时刻检查全部原生材料 ID、密度、体积、排水和固定 18 个中心材料点，输出中心孔压及 M0 参考 CSV/PNG、径向压力 CSV/PNG 和 Tv=0.5–1 的尾段误差。完整计算的稀疏排水时钟用于衰减曲线。此前原生 P3 的独立密集峰窗幅值误差为 −1.518%，峰时误差为 +2.495%，超出原 1% 与 2% 标准。本入口可提供公共程序的完整衰减数据，新的物理精度结论仍须依据实际回传结果。
