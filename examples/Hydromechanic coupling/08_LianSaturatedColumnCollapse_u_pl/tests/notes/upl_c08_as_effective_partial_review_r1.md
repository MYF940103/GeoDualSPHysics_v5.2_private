# Fresh effective-AS/n3 的51帧保存态对照（作者稿，未执行）

只新增同名 support 脚本与本 UTF-8 note。消费 `outputs/upl_c08_as_effective_partial_r1` 的 passed partial native/check，保留原 solver exit1、51帧与未保存失败态未知身份；对照 `outputs/upl_c08_causal_window_GPU_r1/native` 原90帧。后者的 `logs/upl_c08_causal_prefix90_r1.check.json` 已证明其90帧与正式 r6 全22/time/signed byte exact。新分析只 memmap 前51帧，不改90/51各自文件头，不重读BI4、不调用reader/force/solver。

严格6805=1805固定+5000土，显式kept5/retired255、原22布局、原PRE law1→target law2、AS .2/n3/ReleaseOnly、CompletedOnly、FixedPlane/ReactionClosed=false。原生门由两份 passed receipt 保留；再核每帧原IDs、全22有限、真实completed/saved Step、源scalar每次+=2.5us、signed≤1e−14非空及两组step/time匹配，P0逐bits一致。AS空间身份来自真实run/program/source绑定，reader没有独立证明谱定义。

四个CSV：

- history：每组51帧，全5000的p/v/J/κ、有效/总应力六分量和迹的极值及ID、应力Frobenius RMS、前缘中心/高度、FS、NN/近对计数、保存态下一predictor gap排除。
- focus：固定7013/7015/6963/7014/7017/5944/6814/5208各51帧的真实原坐标/FS及物理字段，不把少量点当全场。
- extrema：每帧各字段min/max实际ID、坐标、p/J/κ/speed/FS，保留极值迁移。
- pairs：只r<.7dp非重合土近对，原坐标/速度/p/J/κ/FS、径向raw总应力和AS条件性得分；重合点另计，不除0。NN基于全部5000土，不冒称完整墙/力邻域。

四PNG为全局history、固定材料focus、spacing/ID迁移/plane margin、末共享τ.51全5000的p/κ/J/speed。raw fields两组使用各字段完整共同范围，无裁切/平滑/拟合；时间压力曲线signed symlog的1kPa仅为显示尺度。无新的5Pa或其他物理通过门。

**保存态下一predictor排除：**当前源码move=(dt/2)*v_n；物理左/底plane=0。逐粒计算 `gap−(dt/2)*abs(v_n)`，两方向均严格>0为充分排除，另记实际自由trial=x+(dt/2)v_n是否≤plane。这里不需要加速度，因为predictor的位移原式只用旧速度；它不能排除10ms采样间未保存的corrector，也不等于全局累计projection hit计数。

**条件性pair shadow：**两程序动量raw tensor均为Σtotal=Σeff−pI；旧AS谱输入total，新effective干预谱输入Σeff。按已有pair_shadow的方法用保存double张量做对称eigh，R=−ε positive_part(谱输入)，F=ε[w(r/h)/w(dp/h)]³（ε只计一次），score=n·[Σtotal_i+Σtotal_j−F(Pplus_i+Pplus_j)]·n；n=(xi−xj)/r，score正吸引、负斥离，(vi−vj)·n<0为正在靠近。Cubic h/dp1.2，shape为1−1.5q²+.75q³或.25(2−q)³。它不是实际GPU float谱/powf/packed-gradient/体积质量权重/AV/全邻域加速度重放。32eps_float应力scale仅沿用符号screen，非认证GPU误差界；chain/FS/材料历史及惯性未由一对得分代表。

该派生用于确定早期失稳关联、是否优先排除保存态直接contact，不据此宣称根因、物理准确性或其他ψ准入。新effective失败原始证据及旧3s/r6结果全部保留。根全文审阅后才执行一次，前缀 `tests/figures/upl_c08_as_effective_partial_review_r1_*` 与独立 `tests/logs/upl_c08_as_effective_partial_review_r1.check.json`；拒覆盖/部分输出重试。作者阶段只AST/UTF-8静态检查，不import或运行。

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as_effective_partial_review_r1.py --execution-authorized
```
