# PRE partial reader linkage repair r2

The r1 inspector C++ compiled successfully, but its link exited 1120: the mechanically copied neutral-reader prefix retained an unused `JAppInfo` global, requiring constructor/destructor definitions outside the six BI4 utility objects. No reader or solver ran. Keep all r1 source, object, build receipt and call/log evidence unchanged.

This r2 builder changes only generated-core selection: remove the exact unused `JAppInfo.h` include and `AppInfo` global; require no other AppInfo reference. All Need/Load/Original15 code, r1 inspector C++, six sealed utility objects, frozen physical material header and original numerical checks remain unchanged. It creates a fresh r2 build directory and receipt. The r2 run wrapper consumes that build, while retaining the two original profile/output names and all source guards. The original r1 native run wrapper has never been invoked. No production source or physical input is modified.

Root full review precedes a unique r2 utility build and each separately authorized offline read. Use `upl_c08_hdp15_preload_partial_r2_build.py --execution-authorized`, then `upl_c08_hdp15_preload_partial_r2_run.py h15_failed|h12_control --execution-authorized`. The complete profile/physics limits remain in `upl_c08_hdp15_preload_partial_r1.md`. No certification, solver, VTK, guard relaxation or automatic retry follows.
