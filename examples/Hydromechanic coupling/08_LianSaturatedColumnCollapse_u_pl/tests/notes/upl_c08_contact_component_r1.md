# C08固定下平面接触标量组件（author-only）

仅新增生产共用头 `src/source/FunFixedPlaneContact.h`、`tests/support/upl_c08_contact_component_r1.cpp` 和本说明；本作者未构建/运行。根编辑其它调用点，本文不触碰CPU/GPU积分器或既有材料/孔压代码。

`fcontact::ProjectLowerPlane(double pos,double plane,double &move,float &velocity)` 是CPU/CUDA完全同一个inline定义（`__CUDACC__`时host/device），无任何include、epsilon、margin、nextafter或新参数：先trial=pos+move，若trial<=plane则move=plane−pos且仅把负normal velocity置0，返回true；否则原位移/速度保持并返回false。返回true表示进入接触分支，不保证输入值实际改变（例如恰在面上且速度向外）。不改tangent、σ、J、p，也不声称反力/耗功/J/Darcy一致性闭合。

组件CLI `--out FRESHOUT`，仅standalone C++/标准库，无AppInfo/solver。17个host点覆盖穿越/恰在面上/已低于面、incoming/outgoing/零及signed-zero、非穿越bit不变、正负二进制平面、float位置端点/相邻float、float大位置/小速度、两项明确fractional cancellation witness。各点核normal单位质量动能不增、tangent独立axis bit不变、未受限状态bit不变；15个普通点（含零平面）严格核double端点>=plane。

原公式对任意double并非无条件精确几何：例如pos1、plane=.1，move=plane−pos后重算端点=.099999999999999978<.10000000000000001。按根明确批准，**只对两个已声明fractional-plane cancellation witness** 使用导出算术预算 `2*DBL_EPSILON*(|pos|+|plane|+|move|)` 检查端点舍入差；该预算仅属于测试观测器，不传入header、不是物理接触余量。一次减法及端点加法的绝对舍入界由各操作u≈eps/2与输入幅度构成，这个2eps总幅值为保守界；本测试有限正常double域无溢出。零平面仍严格检查，未以预算放宽物理门，不宣称任意double端点精确>=。

两个解析toy采用实际flat-wall half-stage因子2：halfShift=−2*halfTrial。第一例vn=−1、vhalf=−.25、vfree=+.5、shift=+.5，而旧legacy=−.5；dt=.01/pos=.001时未投影move=−.0025跨墙，新move=−.001并保留向外vfree=+.5，避免翻入壁。第二例vn=+1、vhalf=−.25、vfree=−1.5、shift=+.5，旧legacy=+1.5；新move=−.001且入壁速度投影0，避免反弹。两例独立核限位、当前速度符号和相对vfree的normal动能不增，CSV分别保存两行。toy仍是既有flat-wall平均shift的代数反例，不冒称实际邻域/完整积分轨迹验证。

输出 `points.csv`、`half_stage_toy.csv`、`completion.json`，记录实际coverage/roundoff gap及预算、实际符号/能量。组件成功只说明host单函数数值分支，不证明GPU已执行、塌陷稳定性或全程物理验收；后续根另作真实CPU/GPU闭合构建/调用验证。新输出已存在则拒绝覆盖。
