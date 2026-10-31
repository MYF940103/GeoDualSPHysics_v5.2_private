# Cryer 有界方案与服务器发行包交付

日期：2026-11-01。根据r7计划完成已有结果/文献/算子和保存态密度—变形审计后，
未找到已证明安全且低成本的局部修复；选择原G1＋Darcy symC基线，不改生产C++/CUDA。
保留峰幅-1.03427%、峰时+3.97893%及局部场误差，不把约1%称为严格1%或全场验收。
详见`cryer_accuracy_decision_r1.md`和`cryer_state_budget_review_r1.md`。

## 新正式入口

- 根`CaseCryerProblem_PR_release_r2_Def.xml`、`xCaseCryerProblem_PR_release_r2_win64_GPU.bat`。
- `Cryer_release_r2_Windows_RTXA6000.zip`和同名`.sha256`；服务器说明在`support/README_cryer_release_r2.md`。
- SHA256：`c3a89c1167a01109fbd3b69fff45ceae16e5e61c0ec15ace303c02f1740fb9a0`。
- dt=2^-20 s，963370步，绝对终点0.9187412261962890625 s，排水后legacy Tv约1。
  相对旧r1根输入只改变DtIni、DtFixed及相关注释，数值设置与已回传服务器全程一致。
  双档输出保留闭态历史和排水后Delta legacy Tv=.001，所有分析继续使用实际保存时刻。
- 复用已验证GPU程序`652baea4…`，不是从当前HEAD新编译。六源码捕获、旧构建/原生桥接链逐项核SHA。
  旧服务器没有执行EXE/DLL SHA的缺口仍保留；新的回执记录实际执行身份，不补认过去。

## 已完成的交付验证

打包检查`tests/logs/cryer_release_package_r2.check.json`验证15个ZIP条目的大小/SHA。
从ZIP解压至独立`tests/outputs/cryer_release_portable_r2b`，实际执行`--smoke --unattended`：

- GenCase、solver退出均0；RTX3050，128步，2帧，终点2^-13 s，无粒子排除。
- 全部37173个土粒子ID及35列在两帧通过原安全检查，并与保留全程的同时间startup逐位0 ULP，包含dterror。
- 原生审阅记录为`tests/logs/cryer_release_portable_r2.check.json`：76个绑定文件，106747201字节；
  28个根/解压payload位置、实际运行库前后及执行回执均验证。
- 完成目录重启动、未知参数和改动XML三个负向检查全部拒绝；原smoke的21个文件哈希完全不变。
  记录为`tests/logs/cryer_release_negative_r2.check.json`。
- 实测循环16.232613 s只属本机启动检查，不是控制性能benchmark或A6000耗时保证。

执行回执本身仍保留`native_completion_verified=false`；独立原生审阅另记`smoke_native_verified=true`，
不改写历史运行记录。两帧不能证明开排水、峰窗、全程半步、物理或A6000实机验收。
现无本轮存活求解器，未启动新的本地全程，也没有新建/重启通知器。

## 打包环节的修复与保留记录

Windows PowerShell首次未加载ZipArchive所需程序集，随后回执File.Replace的null备份路径被转为空路径。
分别补显式Compression程序集与真实`.previous`备份路径；均非物理失败，后者止于GenCase前。
失败草稿、旧清单和ZIP在`tests/outputs`恢复性保留，两个failure JSON和原package check在`tests/logs`。
原生审阅脚本的encoding拼写错误亦只离线修复，失败check/source保留；没有因此重跑已完成solver。
最终清单和ZIP绑定修复后的launcher字节，旧r1包和实际全程结果从未改写。

本次只准备独立服务器复现入口，不要求为打包重算已有完整数据。
如需新服务器全程，先独立smoke再手动全程；同名输出已存在时拒绝，绝不PART续算。
将整个输出、原生数据、运行回执、日志和原ZIP复制回来后再分析/绘图/导出particles。
Git保存输入、脚本、清单和关键检查，不代表原生BI4、EXE或ZIP已上云。
