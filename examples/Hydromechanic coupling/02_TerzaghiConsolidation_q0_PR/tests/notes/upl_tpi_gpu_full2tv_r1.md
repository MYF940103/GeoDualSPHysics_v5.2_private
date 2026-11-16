# C02 GPU 2Tv：仅扩展时间窗准入的源准备

本轮新增support/upl_tpi_gpu_full2tv_r1_prepare.py及本说明，作者尚未执行。
只从已passed完整GPU r2/source269复制到新outputs/upl_tpi_gpu_full2tv_r1_source，
唯一变更为JSphGpuSingle.cpp Init资格的TimeMax表达式：

```cpp
TimeMax<=.15
```

替为：

```cpp
(TimeMax<=.15 || (TimeMax==72.88428690075874 && NstepsBreak==11661219))
```

原同一行TimeMax>0、fresh ID/物理/material/边界/时步/内核条件不动。
其余268文件(包括host实现、全部原headers、CUDA TU和private h/cuh)逐byte原样复制。
这不是新的数学/物理设置或新精度证明，不增加C full准入；只建立可审查程序来源。

实际基座为logs/upl_tpi_gpu_r2.prepare.json与已passed Release_r3.build.json。
prepare不修改任何旧源/obj/程序、正式XML/BAT或已验收结果，不运行工具或Git/hash。
新source269逐个stat绑定，复制后直接byte核对；没有旧objects/BI4 SHA扫描。
新source_diff给出唯一替换及完整diff，原class/header/外部kernel ABI不变。
若任意新目录/receipt已存在(含failed/partial)拒绝覆盖或换标签自动重试。

独立root admission为stage=upl_tpi_gpu_full2tv_r1.prepare_admission、passed/prepare_only=true，
inputs含本script/note、公用CPU build_r2 helper、base prepare/Release_r3 build和269源stat。
入口需--execution-authorized --admission。唯一receipt为
logs/upl_tpi_gpu_full2tv_r1.prepare.json；不自动build/run/native/VTK/下一动作。

原完整计划仍应为1682frames/11661219updates，dt6.250143051147461e-6，
actual scalar end72.88428689946836；它与原A full保存计划一致。
本prepare不生成/重写clock、runner或reader，不由正常构建宣称full物理验收。
后续根线程另审一条freshB full；oldA完整控制复用，不自动C full/half/reference新链。
