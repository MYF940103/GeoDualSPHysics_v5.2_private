# AS kernel 距离乘子说明图（author-only）

只新增同名support脚本和本note，先查重不存在/git ls-files为空。只做AST，不运行脚本，不生成曲线/PNG/CSV，不调用物理solver、native、现有owner或hash扫描；生产源码/输入/旧结果不动。

数学定义沿已审 `upl_c08_as_locality_audit_r1.md`：s=r/dp，a=h/dp，`F(s)=epsilon*[w(s/a)/w(1/a)]^n`。Cubic形状为q<=1时`1-1.5q²+.75q³`、1<q<2时`.25*(2-q)^3`；Wendland C2为`(1-q/2)^4*(2q+1)`。按真实2h支持外设0，不将多项式延伸至邻域外。归一化常数在比值消去。原式位置：`src/source/FunSphKernel.h:88-99,206-212`、CUDA `FunSphKernel_iker.h:36-47`；物理pair实际以W(dp)归一化，旧常数wdeltap不是本图分母。

固定六条曲线：Cubic a1.2/epsilon.2，n2.55、3、4；Wendland a1.5/epsilon.2/n4；Wendland a2.16/epsilon.3/n5；拒选Cubic a1.2/epsilon.5/n2.55。n4明确标math-only，不新增物理候选准入；AS05的rejected标记不被本数学图改变。

这只是**含epsilon的距离乘子**，未乘实际sigma谱/密度/体积/gradW，不是实际力或加速度，也不能跨kernel/legacy与u-pl归一化直接排名实际排斥。s=0的F有限，但径向核梯度趋0，实际pair还跳过self/ALMOSTZERO；不能把F(0)称力峰。图按给定理想a作binary64数学多项式求值，不声称production float/packed/CUDA bit replay。

一张两面板：近域s0..1.5线性、尾部s1..4.5对数；零值只因log无定义不显示，CSV保留全部0，不clip正值。支持端2.4/3/4.32dp标出。网格为整数i/200，i0..900，共901点/曲线；另直接求精确s=.5,1,1.5，共18个锚点。CSV包含kernel/a/epsilon/n、q、无量纲w、Wdp形状、ratio/F和支持端/anchor标记，17位文本，可独立复现；F(1)=epsilon作为数学归一化自检。

root读后可运行一次纯数学图生成（本轮未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_as_kernel_curve_r1.py --execution-authorized
```

输出fresh `tests/figures/upl_c08_as_kernel_curve_r1.png`、`_curves.csv`（5406行）、`_anchors.csv`（18行）。任一旧/部分同前缀输出存在则拒绝覆盖，不自动重试；无额外收据链、参数拟合、物理验收或后续计算。
