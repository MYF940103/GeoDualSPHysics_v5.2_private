# 本轮修改位置索引（2026-10-27）

## SPR半步长复核：没有新增生产SPR修改

`scripts/lian_spr_half_review_r1.py`新增全61对原生复读、哈希/安全/材料ID检查与粗半对比图；`notes/lian_spr_half_review_r1.md`、`logs/lian_spr_half_review_r1.check.json`及`figures/lian_spr_half_review_r1_*`保存结论/PNG/CSV。本地和远端节点9f8bbac。新旧工况与全61保存样本半步长通过，不是FEM/100s验收。

## 非周期HG候选：7个生产文件，公式和历史积分未改

| 文件与当前行号 | 位置/作用 | 目的 |
|---|---|---|
| `src/source/JSphHourglassCpu.h:22`、`:56` | 适用范围注释及内部Period=0含义 | 说明非周期支持；不是新的XML参数 |
| `src/source/JSphHourglassCpu.cpp:32` | `MinImage` | 周期仍做最小镜像；非周期返回真实dx |
| 同文件`:37` | `Config` | 接受有限period=0；保留正周期支持域限制 |
| 同文件`:59`、`:69`、`:73`、`:77` | `BuildPairs`包围范围/网格 | 非周期按xmin/xmax分箱，格宽Support |
| 同文件`:80`、`:87`、`:91` | X坐标及邻列 | 非周期不卷绕X、不连接相对的边缘；旧周期遍历顺序保留 |
| `src/source/JSphHourglassGpu_ker.h:23`、`:31` | `StGrid`和`StReduce` | 保存X原点与xmin/xmax归约 |
| `src/source/JSphHourglassGpu.cpp:37`、`:94`、`:102` | `Config`、`EvaluateRate` | 同CPU允许period=0，创建真实有界GPU网格 |
| `src/source/JSphHourglassGpu_ker.cu:18`、`:22`、`:85` | 初始化/归约/采集 | 取得原生土粒子的xmin/xmax |
| 同文件`:98`、`:113`、`:130` | `CellX`、`Columns`、`Pair` | 非周期坐标、不跨界邻列、真实粒子距离 |
| 同文件`:143`、`:179` | Moments/Rates调用 | 两个算子均使用同一有界邻居规则 |
| `src/source/JSphCpuSingle.cpp:136`、`:139` | HG启动配置 | 无周期传0；斜x及y/z周期仍拒绝 |
| `src/source/JSphGpuSingle.cpp:171`、`:174` | GPU同位置 | 与CPU适用范围对应 |

`doc/xml_format/_FmtXML_ElastoplasticSoil.xml:166`起同步范围/候选验收限制；case根README新增当前阶段说明。本次没有改动生产`JSphCpu.cpp`的应力/孔压/黏性、Darcy、加载、SPR反射、mDBC或主积分函数。SoilHourglassXi默认0，关闭路径不分配HG；仅测试用XML开启xi=.1。

生产范围改变的数值含义：原HG只支持x周期域，本轮使其可对真正无周期的二维土粒子集合计算同一LS残差/历史力。不是把Lian改为周期域，也没有加入墙体HG力、虚拟土粒子或外力修正。仍限弹性/小转动/固定原生ID/全新启动，不能用作塑性、大转动、3D HG或精确历史重启。

## 新测试入口与记录位置

- `scripts/lian_hg_np_test.cpp`复用原42项G3夹具并增加16项有界场；真实CPU/GPU对象与独立全对参考，不复制生产CUDA算法。
- `scripts/lian_hg_energy_test.cpp`：冻结几何刚度振子，使用另写velocity-Verlet；**不是生产SPH/历史积分器**。
- `scripts/lian_hg_np_review_r1.py`：检查58项Debug/Release、旧周期逐值0ULP、memcheck、冻结振子及能量图；`logs/lian_hg_np_review_r1.check.json`、`figures/lian_hg_np_*`为对应记录。
- `scripts/lian_hg_short_r1.py`：6项全新实际程序启动/关闭回归/0.15s独立半步长；生成`configs/lian_hg_short_r1_*` XML/BAT、对应`outputs`及`logs/figures`，拒绝覆盖。
- `scripts/lian_hg_short_review_r1.py`：独立复核这些实际结果、PNG/CSV；没有启动求解器的代码。
- `scripts/lian_hg3_r1.py`、`notes/lian_hg3_r1.json`：只在上述短窗检查和图审通过后才准入新3s HG×SPR比较；不自动启动100s或宣告独立3s半步长通过。

默认CPU Debug、GPU Debug/Release构建通过；GPU Debug算子memcheck零错误零泄漏。原生算子42→58项，旧/新Release周期快照SHA完全相同。节点3112234已本地/远端核验，是**算子候选备份，不是Lian正式发布**。原始BI4、程序和每份约19MB的逐值周期快照保留本地、不放Git；Git保存脚本、参数、哈希、主要图表和结论。

正式XML/BAT及旧100s部分输出保持不变，未重跑已验收case02，也未开启Yao/滑坡/u-pl/TPI/KEEP。后续依次Lian、Cryer、自重。
