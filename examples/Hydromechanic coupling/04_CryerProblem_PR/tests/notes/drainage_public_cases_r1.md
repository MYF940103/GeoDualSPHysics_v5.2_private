# 公共排水配置和旧算例复现

以版本 `7965df7d7cabb1d1ba42f131c4873ea01a242f46` 为修改前基准。下表记录根目录正式入口。逐个 XML 的文件名、生效模式、启动秒数、时钟、粒子数和初始字段列在 [52 个根文件核对记录](../logs/drainage_public_roots_r1.check.json)。

| 算例 | 使用公共程序 | 随原程序保存 | 复现要点 |
|---|---:|---:|---|
| C01 自重固结 | 2 个已迁移，1 个沿用隐式默认 | 1 | Stage1 和 Scenario2 从 0 s 排水。Scenario1 使用相同默认值。FreshPR 的 GPU 和原生读取器使用包内 `support/bin`。 |
| C02 Terzaghi | 7 | 0 | k1em2 在 0.0001 s 开放。其余 6 个在 0.01 s 开放，其中 4 个使用固定步事件，double 和 precision 两个定义使用物理时间判定。 |
| C03 退行滑坡 | 4 | 0 | 旧的 `CaseRetroSlope_u_pw_*` 含未被原程序读取的 `HydroMechFreeSurfaceDrainage*`。两份文件实际用的是默认从 0 s 排水，与两份 8 m 算例一致。 |
| C04 Cryer | 9 | 8 | 4 个 rampclosed 输入在 0.0025 s 开放，新公共 u-pl 在 0.0078125 s 的固定步事件后开放。专用程序、种子和服务器包沿用各自的根 XML。 |
| C05 Lian 条形荷载 | 1 | 1 | 公共输入在 1 s 开放。原服务器 release 仍配套 `support/bin`。 |
| C06 Yao | 5 | 0 | 全部从 0 s 排水。 |
| C07 Selborne | 2 份几何定义 | 0 | 生成器可重建两份根 XML。预应力和破坏 BAT 均以代码 2 退出，实际开放的是 GenCase 几何检查。 |
| C08 饱和柱滑塌 | 0 | 11 | 发布程序、分版本 BAT、预载与接收合同保留原输入。旧 `HydroMechDrainage=0` 与 `HydroMechFreeSeepage=1` 要配合原发布程序和撤墙阶段使用。 |

30 对真实 GenCase 启动均正常。每对生成文件的有效排水设置、其余 special 字段、常数、参数及粒子块一致，逐字节比较了实际 BI4 中各初始粒子数组。合计 1,007,657 个粒子条目。独立核查了水力耦合目录外另 130 个已跟踪定义。物理轨迹由单独的求解器回归检查。

重新处理数据时以该次运行保存的 XML 为准。C02 三个正式结果的后处理读取到 0.01 s 及 10,000 Pa。C04 四组服务器结果读取到 0.0078125 s 的固定步排水，C04 四份初期 rampclosed 的剖面起点为 0.0025 s。C01 两个公共 GPU BAT 在 Release 缺失的实测中均以代码 1 退出，保留已有输出。旧服务器包和返回数据无需修改。[入口、生成器及后处理核对记录](../logs/drainage_workflows_r2.check.json)
