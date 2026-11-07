# A05 dp=.002 old/new GPU comparison completed

The user-selected a=0.5 case was run with dp=.002, not the stopped dp=.001 preparation. New test Def changes only Dp and its resolution comment from the original formal a05 Def. Geometry dimensions and material remain L.20/H.10m, rho1850kg/m3, E10MPa, nu.3, phi22deg, c=psi0; original Symplectic/Wendland h/dp1.8/NoSlip/AV.1/DDT3(.1)/adaptive dt/no damping and output.01s are retained. It is neither an a10 comparison nor a resolution-convergence study.

One GenCase actual PID74992 exited0 and generated5000soil+2028fixed, h=.0036. Frozen old GPU Release_r2 versus new unified Release_r3 each ran exactly once to1s; source archives/programs/runtime/input stats stayed unchanged. Old solver63104/new14308 and native readers27808/73128 all returned actual Popen/Win320. Both full runs have108926updates/101frames, all native original IDs, finite exported fields, positive density/nonnegative kappa, unchanged fixed geometry/velocity and zero exclusions. Native double SigmaState is available in all101frames; positions are native float32 expanded exactly. No compile, extra short/half or solver retry was performed.

All14 exported initial physical fields match scalar bit patterns. All101 actual saved times coincide, including endpoint1.0000052194934204s. This is not an all22aux-array or trajectory-bit identity claim. Across the101 same-time pairs, maximum stress Frobenius RMS difference is0.683364406879Pa and position XYZ RMS difference7.72600818543e-06m. Final maximum kappa is11.573679924(old)/11.5199756622(new), change-0.46402062%; all5000soil have nonzero saved kappa. Stress/kinematic similarity does not prove identical history or physical superiority. Material is constant-strength here, so these results do not establish softening equivalence.

| final same-original-material observable | old | new |
|---|---:|---:|
| mean settlement (mm) | 13.6886599264 | 13.6889430675 |
| initial-top material settlement (mm) | 37.8925574478 | 37.8931828681 |
| initial-bottom material settlement (mm) | -0.00649208668619 | -0.0064913276583 |
| x maximum (mm) | 431.252807379 | 431.254535913 |
| dry stress Frobenius RMS (Pa) | 1063.92701469 | 1063.94167486 |
| velocity XYZ RMS (m/s) | 0.000188629961796 | 0.000189034953755 |

Both used the actual RTX3050. Recorded main-loop times are183.013931/219.516113s and owned elapsed183.625/220.25s; observed loop ratio1.19945029. This is a shared-machine observation, not a controlled material-cost benchmark or proof of the cause of that difference.

Official PartVTK processes74852/55732 each exited0, exporting101frames/all5000soil for BOTH full runs. Open the separate old/new `outputs/basic_a05_dp002_{old,new}_GPU_r2/particles/PartFluid_0000.vtk` series through0100. Fields include native double SigmaState_kk/ij, float display stress, Kplastic/Vel/Rhop/Press, IDs/MK and original float positions. Stress offdiagonal order is xy,yz,xz. `Press` is the dry WCSPH EOS pressure, NOT pore-water pressure. Per-run particles README records actual VTK declarations. Original BI4/native data are unchanged.

`figures/basic_a05_dp002_r2.png` and matching history/final-perID/difference CSVs preserve all states and IDs. The figure was visually inspected: final contours and stress/velocity curves nearly overlay, while the real kappa difference remains visible. The original review pending flag is preserved; separate visual_qa.json records viewing. Safe finite whole-case compatibility here is not a new physical-error threshold or a general apex/3D/Verlet or continuum-validation verdict.

The only dp=.001 target65368 was intentionally stopped after exact identity verification when the user changed mesh. Its original owner captured actual Popen/Win32 exit15; last saved Part9=.090001s/19691updates. Prepare/partial/start/call/stop/runfalse evidence remains untouched, with no partial decoder call. It is not classified as a numerical regression. No new dp=.001 run followed.
