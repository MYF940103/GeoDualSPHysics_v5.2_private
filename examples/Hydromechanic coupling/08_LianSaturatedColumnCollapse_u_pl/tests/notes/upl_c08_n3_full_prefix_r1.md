# n3 短窗66帧与根 r6 全程300帧的离线前缀核验

仅新增同名 support Python / 本说明，事前查不存在且未跟踪；作者未执行或 import。输入为既有 retained n3 `native_r1` 与根ψ0 r6 `native`，其各自正常run/native已通过；不解码BI4、不导VTK、不运行solver或构建，不改变旧前缀结果。

实际 C08 native 只有一个二进制 `typed22.bin`，并无 case02 的“五个binary exports”；此外实际比较 layout / clocks / history / plane_gaps CSV，不补造导出凑数。原头分别必须为6805/22/66与6805/22/300，并原样保留，不能把count改成相同。逐真实共同record流式读前66条，每条实际f64 time及按实际typed_layout的22数组完整逐byte比较；每字段报告66条中相同数量及首个差异part/字段byte，不使用5Pa或近时容差替代bit证据。

clocks 的原header和前66整行字节均比较，包含 signed dterror / empty / Step 等全部列，不排除初始或其他诊断。另核两方真实completed steps为4000000+4000×(part+1)、saved_step少1、dt2.5µs、非空signed≤1e-14，确保同 .01s 保存节拍；实际CSV时钟必须等于二进制time。history / plane_gaps 原header+前66整行分别报告并核一致，不改计数/文本格式/元数据。metadata stage及总样本数差异不伪比较为同一文件。

记录 trace-window 与 formal-program 两份各自封存 source_build / source_capture / source_archive 及实际program stat，只引用归档、不重读ZIP或扫描对象/SHA。两程序因trace观测编译配置不同，samebinary不是门；前缀相等必须由真实payload决定，不由源码或程序名推断。源PRE及实际源clock仍须一致。

root 全文审阅后的唯一离线入口（作者未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_n3_full_prefix_r1.py --execution-authorized
```

只写 fresh `logs/upl_c08_n3_full_prefix_r1.check.json` 和 `figures/upl_c08_n3_full_prefix_r1_fields.csv` 23行（实际time加22字段）。若不相等，保留原header和首差异，不重读/重跑或放宽门。通过仅说明两个既有结果的共同前缀观测相同，不是half、理论或完整物理验收。
