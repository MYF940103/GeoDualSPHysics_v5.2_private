# AS＋固定平面：实现检查通过，0.6 s物理对照待完成

继续使用原服务器r2的10 s GPU认证PRE，不重算、不改源。固定平面AS0候选在真实保存的0.54 s内无穿底，但0.49 s的内部ID4808出现−973054.5 Pa，随后在未保存力阶段触发必要时步门。该失败及54帧全部图CSV/条件压力诊断已在本地与远端提交`4688bd1b0890559f67494127cb770b42d9ac48a8`保存；原BI4/程序/源码ZIP仍是本地保护数据，不属于云端Git备份。

本候选只组合已存在的总应力人工应力与新的固定平面NoPen。AS仍以σeff−pI计算，ε=.2、exp=2.55，ReleaseOnly；接触仍为FixedPlaneStageProjectionReleaseOnly、ReactionClosed=false。原压力/Darcy/塑性公式、dt2.5 us、墙拟合阈值及全部必要稳定门不改，未增加half链或负孔压截断/滤波。

生产修改仅四处：`JSph.cpp`在严格GravityPreload＋handoff＋NoPen范围去掉AS互斥条件，其余范围门保留；`JSphCpu.cpp`和`JSphGpu.cpp`只扩充DtVariable拒绝时的17位精度及力/波黏/孔压/渗透率梯度分项信息；`doc/xml_format/_FmtXML_ElastoplasticSoil.xml`同步参数能力说明。日志pore是已经与k-gradient取min的孔压限值，不是纯扩散项。编译源快照保持原base6668bbd与实际production.diff，不因后续Git提交改写历史清单。

四种权威配置DebugCPU/ReleaseCPU/Debug/Release构建全部通过，原正式程序与runtime_r3/r4的保护检查通过。CPU/GPU Debug各40更新、1帧独立原生检查通过；GPU memcheck为0错误/0泄漏。全部5000土粒子的跨后端孔压RMS差=.001724343157 Pa，XYZ位移最大差=1.252067894e−9 mm，实际时钟差0。此为实现短检查，不是全程后端误差或物理精度。AS0/NoPen1 Release两帧相对保留AS0的54帧共同前缀，完整22数组＋double time、layout、signed clock行逐byte相同；原头仍分别2和54，旧solver仍exit1。

AS1/NoPen1 Release独立0.03 s短窗正常完成：12000更新、3帧、6800 IDs和22数组全原生门通过，P0/ledger/rho-cache/κ/FS/时钟/30000项平面检查通过；最大保存速度.19115178 m/s，最小z=.01740428 m，无保存帧越墙。末帧孔压范围约−4.842至25.092 kPa，仅说明短窗状态有效，未达到原0.49 s负峰窗口。

CPU短测原owner在实际exit0后因Run.csv说明字段未转义AS分号而误解析Nbound；保留原failed收据/CSV，单独offline adoption重核原post门，之后只读取一次原生。新owner r2仅修该分号、实际AS日志的等号以及绑定parser；native r2仅在新build生成的core中修同一已识别CSV片段，原core/数值门/原始CSV不变。没有因解析问题重复求解。

两项完成review消费的新说明误用了旧`upl_c08_as_short_review_r1.md`文件名。历史说明已从Git恢复，新说明按实际消费字节及mtime另存`upl_c08_asplane_short_review_r1.md`；明确映射及恢复记录见`logs/upl_c08_as_note_collision_r1.json`。原两份check/执行脚本/数值CSV不改不重跑，不能再声称旧说明路径仍匹配其当时stat；按该映射审阅。此为说明文件命名纠正，不改变物理准入或活动窗口依赖。

已由根核原短窗/CPU-GPU/默认关闭收据后，准入唯一新窗口`upl_c08_asplane_window_GPU_r1`：GPU RTX3050，目标τ=.6 s、240000更新、TimeOut=.01 s、60帧。start/call/run由直接owner留存，唯一一次同线程终态通知；先正常run封口再独立native，之后对AS0真实54个共同step/time分析压力、固定初始材料层沉降、应力、速度、κ/J/n/k及极端ID，不插值、不以5 Pa作为算子变更误差门。正式r4程序/输入未替换，三组3 s未准入。

后续离线脚本`upl_c08_asplane_window_review_r1.py`已准备，只有正常60帧与原生检查通过后才执行。固定初始top/bottom层使用既有PRE VTK float坐标，明确保留舍入限制；全土均值沉降仍用native的double PRE。完整0.6 s也不自动构成论文精度或正式3 s物理验收。
