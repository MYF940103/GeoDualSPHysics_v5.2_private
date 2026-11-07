# r5: one psi0 GPU 3 s diagnostic, other groups locked

Double-click xCaseLianSaturatedColumnCollapse_psi0_shared_r5_win64_GPU.bat. It checks Python/NumPy/Matplotlib, runtime_r5 tools and the original source schedule before GenCase; then performs one fresh receiver, native review, separate PartFluid/PartBound series and PNG/CSV. Nothing is installed automatically. Python prefers D:/anaconda3/python.exe, otherwise PATH python. Runtime contains only the matched GPU Release solver, GenCase, PartVTK, new C08Native and their supplied configuration/DLLs; no old-exe fallback.

All three group XML/GPU BAT files are prepared with their original material values. Only psi0 is admitted. psi2p5 and psim5 stop before any GenCase, solver or postprocessing; there is no automatic three-group sequence. No CPU or new PRELOAD entry is provided.

The GPU wrapper explicitly binds CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4. Keep the entire original source folder. The loader imports actual time/p/p0/J/theta/stress/kappa and certifies the PRE; it does not rerun10 s, assign a geostatic stress field or provide a generic plastic PART restart.

Original geometry/materials/Model1-Ck2/free-seepage and required stability limits remain. New release choices are keep_bed_overlap=true, fixed-plane NoPen1 and AS1 with epsilon .2/exponent2.55, both release-only. Five original shallow fixed IDs1800,1852,1904,1956,2008 become the NoSlip bed with +DpZ normals;255 other right-wall IDs retire. Native counts are6805=5000soil+1805fixed. NoPen is FixedPlaneStageProjectionReleaseOnly; same-stage Darcy reaction is not closed. Initial CfgInit normals are not post-release boundary-normal telemetry.

dt2.5us/DtMin1e-8, event10, TimeMax13 and output .01 are unchanged. Actual imported scalar clock is retained; tau uses actual source time and Part0 is post-release, not PRE. The intended new updates are1.2M, global end5.2M and300 real saves, verified by actual native output. The original Run.csv registry remains7060/2060.

The prior .6 s/60-state diagnostic completed and crossed the old .53 wall-fit failure, with all original native guards. Negative-pressure transients remain a stated limitation. This admits one bounded extension, not equilibrium, full-collapse physical accuracy or paper acceptance. The independent decision is tests/logs/upl_c08_bedkeep_window_decision_r1.json.

Output is CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out. Existing output refuses a physical run. If the solver completes but postprocessing fails, repair derived outputs only and run the same BAT with --postprocess --unattended (either order; -unattended is also accepted). This mode never GenCases/restarts/solves and does not alter BI4. It resumes only compatible completed post-tool records; incompatible partial derived data are preserved for diagnosis.

particles/PartFluid_####.vtk contains5000soil; PartBound_####.vtk contains1805fixed, all actual frames, never PartAll. Native Posd/double stress remain available; official VTK storage precision is reported separately. Kplastic is scalar plastic history, not the full plastic strain tensor. Keep all source/receiver data and logs. Old r3/r4 inputs, runtimes, failed outputs and ZIP snapshots are unchanged.
