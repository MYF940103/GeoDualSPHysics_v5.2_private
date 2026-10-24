# CPU静止多平面SPR候选

2026-10-24。基线`e696271`，源码和CPU Debug/Release程序副本保存在`outputs/spr_planes_base`，哈希见`logs/spr_planes_base.snapshot.json`。根正式一维输入和结果不修改，不重启旧worker。

## 先验范围与最小补丁

只改`src/source/JSphCpuSingle.cpp`的初始化几何检查：从所有墙共用一个平面，改为每个墙mk独立满足原法向方向和共面容差；周期位移必须与所有平面相切。`JSphCpu.cpp`已有逐粒子三分量重构与局部法向反射，不改MLS、S/P/R接线、Darcy、真实速度、积分或滑移模式。没有引入参数或新持久数组。

多平面候选要求显式分开的平面墙mk，统一Vel0/NoSlip/FreeSlip；曲面、同mk混合多个面、平均角点法向、NoPen、运动墙和GPU多平面仍未开放。若角点的镜像支持不足，记录降阶/无效回退；不能以只选远离角点的ROI宣布整个墙角通过。HG关闭，和SPR几何推广分开验证。候选能启动不等于通过物理验收。

## 运行前验收安排

1. 默认CPU Debug及CPU Release构建；单平面既有18组制造场继续通过，原水平一维和SPR关闭短窗相对冻结生产程序按原生ID保持所有物理字段0 ULP。
2. 新的二维正交墙角、非正交双墙、三维棱边，分别三种SlipMode；检查每mk真实坐标/法向、镜像点和重构辅助速度。常量映射误差限沿用`32*FLT_EPSILON*max(.125,abs(expected))`。相容仿射场要核对S/P/R真实生产交互入口；应力率20 Pa/s、孔压率2000 Pa/s、密度率0.02 kg/(m3 s)，再加`2e-5*abs(reference)`的MLS/解析辅助速度对照限额。原始R核矩偏差单列，不冒充解析精确。
3. 报告所有墙粒子的mDBC有效性、零阶/无支持回退及角点ROI。原生真实速度/孔压/位置/ID不得被导数重构改变；曲面和同mk非共面仍应拒绝。未通过项保留失败记录，不放宽限额。
4. 制造场通过后再做静止墙约束下的独立短窗和半步长物理检查；NoPen另列下一小步，不同时取消限制。之后才接入已有二维固结/Cryer，不复制当前一维HG的适用假设。

新配置/BAT在`tests/configs`，测试源码/脚本在`tests/support`，结果在`tests/outputs`，日志在`tests/logs`，CSV/PNG在`tests/figures`。正式根figures本轮不改。

## 非零短窗的先验检查

制造场通过后，仅对二维正交角/非正交双墙，三种SlipMode，施加初速度`v=-0.001(x,0,z)`，不施加外力、不排水、HG关闭，运行生产Symplectic积分器0.002 s；dt=1e-6/5e-7 s，按相同10微秒物理时刻输出。此初场对FreeSlip相容；Vel0/NoSlip存在切向起始瞬变，不能拿它作仿射边界解析解。该独立小幅脉动不是新固结验收。

先验半步限额：所有共同保存时刻孔压RMS差<=0.5 Pa、最大材料位移差<=1e-5 mm。原生粒子不得排除或穿墙，保持弹性和有限正密度，固定步长不超过程序实际机械/孔压限制。记录动能+线弹性应变能+孔压储能；无外力情况下最大总能量应不超过初值1.1倍，不用这一近似能量等同于离散能量守恒证明。失败则先诊断，不因制造场已通过而开放NoPen。

## 当前实现与有界结果（上文保留为最初先验计划）

单纯放开几何保护未通过：角点原ghost落到另一面墙外，MLS支持降阶，辅助速度误差达0.012 m/s。因此没有保留“只取消限制”的方案。当前最小补丁为：

- `JSphCpuSingle.cpp / ConfigDomain`：每mk检查一个平面；多面必须有凸共同内域。仅当ghost在另一面外时，将**拟合中心**移入各面内一个dp，按原生墙ID缓存偏移；不是移动墙、土粒子或真实ghost。
- `JSphCpu.h`：一个静态偏移向量`BoundDerivativeFitShift`，单平面为空；共享MLS入口增加默认关闭的`recenter`参数。
- `JSphCpu.cpp / InterpolateBoundaryGhostFieldT`：只对SPR速度拟合启用偏移，在新中心求一次多项式，再求原ghost的值；孔压外推仍沿用原算术。初始化清空及CPU内存统计同步。
- 无新XML开关，无时间步/真实速度/动量/黏性/Darcy/加载/应力率方程改变。两份VS CPU配置构建通过；类布局变化已完整重编译。失败的编译/输入和守卫放开原型均保留，不改历史收据。

`logs/spr_planes_review_r2.check.json`及同前缀PNG/CSV汇总：Debug/Release合计18个正交角、3D棱边、斜双墙三SlipMode制造场通过，辅助速度最大差3.7253e-9 m/s；S/P/R对解析辅助速度的最大差分别0.25 Pa/s、64 Pa/s、0.00048828125 kg/(m3 s)。既有18单平面制造场通过；SPR关/开两条31帧×1000粒子一维轨迹相对冻结旧程序为0 ULP。后者在最终NoPen准入保护改动之前执行，数值函数未再改变；收据按当时程序保留，不改写为最新根目录exe的哈希。

六条无NoPen和两条轴对齐NoPen的2-ms短窗半步对通过；最大孔压RMS差0.0077575 Pa、材料位移差2.4267e-8 mm，能量最大倍率约1.0195。不是二维固结长程验收，也未验证有限墙端/自由面交接、塑性或大转动。

### NoPen范围不能静默扩大

`spr_nopen_reference_r1`实测原SPR关闭的NoPen：30°墙上的纯切向速度0.01 m/s产生约0.0064952 m/s伪法向修正；水平墙为零。原因在原逐坐标NoPen算式，不是SPR重构。因此原动量NoPen公式不改，CPU只准入**轴对齐**平面的NoSlip/FreeSlip组合；斜墙NoPen+SPR仍明确拒绝，GPU尚未移植本轮扩展。

新源码/Debug/Release程序已冻结为`outputs/spr_planes_cpu_short_verified`，见同名snapshot收据。Yao二维条形加载的独立短窗在case06的`tests/scripts`/`notes/spr_yao_r1.md`继续；不把一维均匀应力100 Pa门套用到非均匀条形荷载。

最终准入保护改动后的CPU Release另作`logs/spr_planes_final_regression_r1.check.json`：只新跑两条SPR关/开0.03 s，采用保留的旧程序控制，不重跑旧控制。两条各31帧×1000原生粒子全部已输出物理/边界字段继续0 ULP；新程序哈希绑定上述不可变快照。

34个成功制造场/脉动XML已补齐同名可点击BAT（准备脚本`support/spr_prepare_bats.py`）。手动重现统一写入新`*_manual_r1`及`*_manual_r1_input`，拒绝覆盖；调用当时的诊断伴随程序，生成CSV/JSON，不冒称普通正式固结或自动生成总对比图。失败原型/斜NoPen拒绝试验不混入这些成功入口。
