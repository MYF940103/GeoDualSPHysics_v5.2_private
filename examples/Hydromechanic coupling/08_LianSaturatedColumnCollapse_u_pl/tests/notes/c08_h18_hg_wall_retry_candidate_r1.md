# 单包stage1 C质量失败的单次nearest重试：纯离线作者稿

仅新增同名support `.py`和本文，作者不import/执行新脚本，不调用native/GPU/solver/build/VTK/Git/SHA。root完整审阅后可单次运行 `D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_wall_retry_candidate_r1.py --execution-authorized`。已有完成或partial拒覆盖；原源码、旧分析、capture和全部原数据不改。

输入严格为已通过原fault review的真实stage1/wall894/step2196678/source10.983389999668779捕获包。复用原 `fault_review.inputs` 的11数组hex/extent/ownership/clock/cell表解释，不创建新解码工具；保留sorted顺序。先运行同一个原 `recompute`，要求本包确为complete、geometry通过且有限Cdet≤0的原G第一次拟合。该要求限制本次候选范围，不把无效J、非有限分量或另一事件改判。

薄driver用inspect.getsource取得原recompute，唯一可逆替换末尾retry条件：保留原 `complete && !geometry` 分支，另加 `complete && geometry && finite(Cdet) && Cdet<=0`；仍要求 `!attempt && nearestfinite && 非零nearest移位`。Cdet读取已保存的 `row['independent_C_det']`：原函数donor导出循环会复用metric变量，不能误读末donor的Cdet。原G先评、循环仍只有0/1、同一次nearest recenter、并仍锚定外推回原G。原.001几何门、sumW/active、所有9拟合分量有限门和Cdet>0门均不改。invalidJ使complete=false；非有限拟合C使wall row Cdet缺省；nonfinite Cdet显式不触发新增分支。无第三fallback、重心、identity、删除donor、矩阵对称化或新阈值。exec在原module globals的**副本**内定义新函数，不替换原fault.recompute或修改module；全函数逆变证明及条件原文写入check。

同一原包上比较原方法与counterfactual，原G第一attempt及该attempt全部donor记录还须逐float64字节/非浮点值一致，防止薄driver无意改变算式。所有M、C、alpha和特征值仍是独立CPU重算，**不是GPU寄存器、原设备真实分支或已选择的物理修复**；近门限、CUDA fast sqrt/FMA、实际device CTE与host映射的差异保留。原异常仍失败，不能从本离线通过直接启动或验收长算。

只输出新 `tests/figures/c08_h18_hg_wall_retry_candidate_r1_{attempts,donors}.csv`、`_diagnostic.png` 和logs同名check。图给出实际捕获流体/原G及一次retryG、原.001门、重算C行列式/最小对称特征值、anchored权重L1与负系数数量；全部原中间值保留CSV，无paper拟合、滤波或参数搜索。候选若仍未通过原正C门如实输出，不松门、不自动加fallback；root须完整审阅图和数值后再决定是否值得后续实现验证。
