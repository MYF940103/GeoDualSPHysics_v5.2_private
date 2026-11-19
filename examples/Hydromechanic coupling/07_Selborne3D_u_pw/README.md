# 07 Selborne 3D u-pw — 配置准备版

## 公共版配置

两份根几何定义都采用默认零外载。底部局部孔压加载与普通力学外载分别建模，正式求解入口仍受原有条件限制。
两阶段的 `execution/special/drainage` 均为 `mode="drained"`，从零时刻对已识别的排水自由表面施加零孔压。几何检查可用 GenCase 验证这项配置；底部局部孔压加载仍需实现。

当前状态：**三维几何可由 GenCase 检查；两层材料和底部注水加载尚需求解器扩展，不能开展正式模拟。** 本轮不改 C++/CUDA，不运行 prestress/failure。XML 内全局 `<soils>` 是上层材料的几何导出占位，不代表下层已经正确赋参；禁止直接绕过 BAT 用求解器运行这些 XML。

## 文件与入口

- `CaseSelborne3D_u_pw_prestress_Def.xml` / `CaseSelborne3D_u_pw_failure_Def.xml`：相同三维几何，独立 `<soils>` 与 `<hydromechanics>` 模块。
- `xCheckSelborne3D_geometry_win64_CPU.bat`：双击执行两阶段 GenCase 检查，不调用求解器；按时间标签输出到 `tests/outputs`，日志在 `tests/logs`，不删除旧结果。
- `xCaseSelborne3D_u_pw_prestress_win64_CPU.bat` / `xCaseSelborne3D_u_pw_failure_win64_CPU.bat`：预留计算入口，当前明确报告缺失功能并以代码 2 退出。不是已经可计算的 BAT。
- `support/model_spec.json`：两层真实参数、底部加载和阶段继承规范；是设计输入，当前求解器不读取此文件。
- `support/code_change_plan.md`：最小实现范围、数值后果及验收方案。
- `support/prepare_case.py`：复现初始配置，采用独占写入，已有文件不覆盖。
- `figures`：三维模型及截面示意图；`tests/support`：建模检查脚本；`tests/notes`：本轮检查记录。

## 几何与参考依据

主要依据本仓库 `src/papers/PDF/A GPU-accelerated FSM-MPM framework for efficient soil-water coupling simulation.pdf`，§4.3、Fig.12、Table 5（PDF 12–15 页）；Morikawa 的 `Morikawa u-w-p.pdf` §8.4、Fig.19–20、Table 4 仅用于核对实验和边界含义，**不混用它的三层结构和另一套材料参数**。

取 z 竖直向上，x 从高侧向坡趾，y 为横向：底面 `[0,56] × [0,25] m`，z=0；下层 unweathered Gault clay 为 z=0–6 m；上层 weathered Gault clay 在 x=0–18 m 时顶面 z=15 m，在 x=18–36 m 时顶面 `z=24-x/2`，坡趾 `(36,6)`；x=36–56 m 为下层裸露平台。坡高 9 m，坡比 1:2（26.565°），坡顶平台 18 m，横向宽 25 m。上下层理论体积分别 6075、8400 m³。坐标方向按文献底部注水范围 x=0–24 m 设置；不要将示意图投影方向误读为注水在坡趾侧。

当前 `Dp=0.5 m` 用于首轮建模检查（真正的三维宽度，非单层外推）。FSM-MPM 3D Case 4 的网格尺度为 0.2 m，后续 SPH 可考察 dp=0.25、0.2 m；MPM 网格/积分点数不能当作 SPH 分辨率收敛证明。理论土粒子规模约 V/dp³：dp=0.5 时 115800，dp=0.2 时 1809375；实际数量受表面格点和墙体半 dp 偏移影响，以 GenCase 为准。

粒子采用同一全局格点。下层最后一行 z=6，上层从 z=6+dp 开始，不重复界面粒子，粒子间距仍为 dp。mDBC 有效刚性面位于墙粒子中心向土体偏移 dp/2；所以离散有效域与文献几何有半 dp 误差，必须随分辨率收敛检查，不把粒子中心包络当作精确体积。各侧墙按坡面裁剪，坡顶、坡面及低平台不覆盖刚性顶板。

## 材料（FSM-MPM Table 5）

| 参数 | 上层 weathered，mkfluid=1 | 下层 unweathered，mkfluid=0 |
|---|---:|---:|
| 颗粒密度 kg/m³ | 2700 | 2700 |
| 水密度 kg/m³ | 1000 | 1000 |
| 孔隙率 | 0.38 | 0.38 |
| 饱和混合密度 kg/m³ | 2054 | 2054 |
| E / ν | 20 MPa / 0.33 | 20 MPa / 0.33 |
| 水力传导系数 m/s | 1e-3 | 1e-3 |
| 峰值 / 残余 φ | 24° / 13° | 26° / 15° |
| 峰值 / 残余 c | 15000 / 500 Pa | 25000 / 500 Pa |
| 软化系数 nφ、nc | 5、5 | 0.5、0.5 |
| 剪胀角 / 抗拉强度 | 0° / 0 Pa | 0° / 0 Pa |

密度 `rhop0=(1-n)ρs+nρw=2054`，不能填入颗粒密度 2700。k=1e-3 m/s 是论文为缩短计算时间采用的加速值，不能声称模拟秒数等于现场 196 天。Kw=2e8 Pa 暂沿用 case03 数值选择，**不是 Table 5 提供值**，后续必须检验可压缩性和扩散时间步敏感性。当前 DPCtes=1 是本项目三维 DP 圆锥，不等同论文 SMP 映射；软化参数数值相同也需检查累积塑性应变量定义。零抗拉强度不等同于开启 ArtificialStress，须单独核查本构截断。

## 两阶段和边界

Prestress：原位最终坡形，重力与孔压共同平衡，初始水位跟随地表，自由表面排水；保持两层各自峰值强度，暂关闭软化，阻尼 0.02。当前 20 s / 0.5 s 输出只是待检验设置，不能以到时结束代替平衡收敛。FSM-MPM 不模拟开挖历史；Morikawa 先含开挖土体建立应力再移除，本案不混入该路径。

底面 mkbound=0 无滑移固定；高侧、低侧及两个横向侧面 mkbound=1–4 采用 mDBC free-slip 近似法向约束、切向自由。机械 free-slip 不是水力排水：侧面和底面（注水区之外）均须保持不透水，自由表面零表压。mDBC 的离散实现和角点误排水仍需后续验证。

Failure：继承已验收 prestress 的粒子顺序/标识、位置、速度、有效应力、塑性应变、PorePress、PorePress0 与 PartExtra 法向；重置阶段时间，不重新生成状态。启用各自软化，关闭阻尼，`SoilTriggerFos=1`，防止 case03 的默认 1.65 折减导致额外人为失稳。底面物理范围 x=0–24、y=0–25、z=0，施加 `Δp=110000 min(t_stage/10,1) Pa`，随后保持。按 Fig.12 的 Δp 标注解释为相对 prestress 平衡底压的增量，不是把绝对孔压硬设为 110 kPa；论文正文“pressure head”单位为 kPa，应按压力处理。正式实现时核对该基准并记录。

当前 XML **没有伪造注水配置字段**。`HydroMechTopLoadQ0` 是机械荷载，不能代替孔压 Dirichlet 边界；`HydroMechInitZ` 也不能代替随时间局部注水。

## 后续计算入口约定（尚未启用）

正式输出留在根目录 `CaseSelborne3D_u_pw_prestress_CPU_out`、`CaseSelborne3D_u_pw_failure_CPU_out`。接续 PART 必须从已收敛报告选择，不硬编码 PART=50/40；检查 Part、PartExtra 与材料映射指纹。命令形态沿用 case03：`-cpu -mdbc ... -svres -svextraparts:1`，failure 使用 `-partbegin:N:0 <prestress/data>`（保留 XML 分区 slip，不用全局 noslip CLI 覆盖）。实际重启时钟语义需先用短试验验证。正式 BAT 后续补齐 GenCase、求解、PartVTK/PartVTKOut、错误返回及禁止覆盖检查；本轮入口不声称已完成这些流程。GPU 入口待 GPU 材料与边界实现同步后增加。

先阅读 `tests/notes/preparation.md` 中的实际检查结果，再决定下一轮代码修改。不要把 GenCase 正常退出当成水土耦合求解验证。

粒子坐标检查及图形重建命令（需 Python 3.11、numpy、scipy、matplotlib；当前机器可用）：

```powershell
py -3.11 tests/support/validate_particles.py normals
```

`normals` 对应本轮最终保留的 `tests/outputs/normals_out`；双击几何 BAT 新生成的时间标签可替换它。该检查器针对本轮 dp=0.5 m，改分辨率后必须同步其验收格点定义。GenCase BAT 本身只依赖 PowerShell 和仓库 bin 下的 GenCase，不依赖 Python。生成 VTK 的全局 mk=1/2 对应 mkfluid=0/1；边界全局 mk=10–14 对应 mkbound=0–4，不能混用。
