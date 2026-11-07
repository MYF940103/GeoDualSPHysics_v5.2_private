# C08 r4失败与固定平面接触候选

r4原正式ψ0 GPU solver exit1，最后保存43帧至10.430000000510745 s。未保存力阶段报告stage0/native823、step_start=10.43789250051325；不能将最后保存数据冒作该瞬间。既有原始r2 10 s预载、r3/r4失败out和runtime全部保留；其余ψ未启动。43帧只读reader仅执行一次，typed22和所有原门通过，前15帧与已封存旧NoPen短窗逐byte一致。离线wall review有两次新分析错误（字段名、matplotlib接口），已修新分析并复用逐byte相同CSV，没有重跑或重解码物理数据。

实际首次保存穿底part20（τ约.21 s）为7010/7011；全窗4个材料ID曾穿底，最小z=−.02502556 m，末帧最低p=−259254.8 Pa。其结果不构成3 s稳定性或论文精度验收。首穿底时最近bed779位于(3.98,−.02)，与两个土点的距离约.0553/.0581 m，已超过旧接触的1.25dp=.05 m。真实床面法向与静态NoPen筛选还存在局部不相容区，另见`upl_c08_bed_nopen_mask_r1`；不声称整个右侧床面都无效。

源码另确认旧shift来自half速度，再加回v_n；平床当前factor2使v_new=v_n−2v_half。恒加速代数反例可把自由离墙速度翻成入墙；43帧未导出完整substage，故不据此认定本次直接因果。stage scratch每次清零，已排除旧值残留。

本候选只作用于已准入的u-pl固定轴容器、认证弹性PRE接收、NoPen显式开启且撤墙之后。由已有法向校验得到左面/床面P=B+normal/2；不改变墙拟合、半径、det阈值、材料、孔压、J或时间步。每个predictor/corrector先算自由位移d和自由速度v，若x_n+d<=P，则令d=P−x_n，并仅将v<0的法向分量置0。独立轴的切向速度不变，不加反弹系数或10 mm数值停留带。端点只受IEEE舍入影响；组件明确记录非零小数平面的消减误差，没有增加物理epsilon。

涉及`JSph.h/.cpp`保存已验证平面及候选policy；`FunFixedPlaneContact.h`为CPU/CUDA同定义标量函数；`JSphCpu.cpp`在两阶段调用且跳过本受限路径的legacy corrector重放；`JSphGpu.cpp`同样控制调用、`JSphGpuSimple_ker.h/.cu`增加小投影kernel。旧u-pw/NoPen0保持原分支。没有新增XML参数。policy为`FixedPlaneStageProjectionReleaseOnly`，`ReactionClosed=false`：仍未将接触冲量回馈同阶段Darcy或迭代J/应力，不能称反力闭合算法。

独立构建来源为`upl_c08_plane_source_r1`；组件`upl_c08_contact_component_r1`只验证有限host例子，不能替代真实CUDA/塌陷。随后按根逐项审查实际CPU smoke、GPU Debug/memcheck、旧OFF回归及覆盖原失败时刻的0.6 s候选。dt保持2.5 µs，短检查用规整1 ms，窗口用10 ms输出，不追加half链。安全/IDs/22数组/ledger/clock/signed门保持；完成与精度验收分开记录，尚未准入新的完整正式计算。
