# r2 GPU ψ=0 接收阶段的顶点拒绝

来源为用户服务器截图及用户确认的ψ=0°；实际失败数据尚未复制至本机。截图显示认证PRE导入于实际时刻10.000000000374257s、completed_step=4000000，下一循环退休右墙260粒子，关闭预载阻尼及Shepard，开启自由渗流；最后打印完整保存帧10.05s，随后GPU corrector以status bits8、code1退出。实际失败时刻、粒子ID和trial状态未知，不用10.05s冒充它们。

从`support/server_manifest_r2.json`指向的`tests/outputs/upl_preload_handoff_Release_r2/source.zip`只读核对：旧FunSoilMaterial.h的Status为Invalid0/Elastic1/Radial2/ApexNeeded3/NonConverged4；旧GPU corrector用`1u<<status`累计错误，因此8对应ApexNeeded。旧CommitAllowed仅接受Elastic/Radial。非弹性trial的q不大于0，或径向区间上界lambda=qtrial/G仍F>0，都会请求旧版未实现的顶点处理。该映射与截图一致；服务器实际exe身份仍须由实际文件/命令核对，不凭源文件名作完整程序证明。

ψ=0使DP_psi=0，不能保证只需径向返回。该旧返回在q=0处仍超出DP面时需要额外顶点/张拉处理。截图不含trial，不能据此断定该局部应力状态是正确物理响应或空间噪声，也不能将它归因于时步、动态Darcy或CSV。不可删除错误门、改用旧fast、抬强度或盲目减dt绕过。

当前r3统一材料实现已经包含合法正剪胀顶点和既有Bui型显式张拉修复；ψ=0的修复不冒称原单塑性势的纯顶点流动解。新版JGravityPreloadState.h接受原合同且无MaterialLawVersion的typed MaterialReturn1认证弹性PRE，仍逐项检查原生状态、源弹性资格、时钟、P0、J、kappa=0、Ck2等。已保存的旧PRE→新核短程证据不等于本次真实10s状态和后续完整塌陷验收。

下一步需用户服务器的共享r2 GPU预载输出及失败ψ0接收输出（包括Run.out/Run.csv、实际输入XML、原始BI4/头/初态）。优先用真实认证PRE作有界短复现，核对新旧材料对触发状态的处理及接续连续性，再准备显式绑定r2源的迁移入口。不改写元数据、不重命名伪装r3源、不从10.05s塑性PART作通用restart，不先重算10s。

本次仅源码归因和计划记录；未启动求解器、未修改生产程序/输入/已有输出或服务器包。
