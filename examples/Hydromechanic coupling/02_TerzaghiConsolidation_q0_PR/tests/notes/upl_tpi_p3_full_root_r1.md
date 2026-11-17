# P3 10 us full2Tv launch decision

The completed 2 s P3 window passed the declared bounded physical comparison; the full result is not yet available. No additional half/reference chain was introduced.

| Actual requested legacy Tv | A pressure RMS / Pa | P3 pressure RMS / Pa | A top absolute error / mm | P3 top absolute error / mm |
|---|---:|---:|---:|---:|
| .005 | 114.61486719205124 | 114.64114151974242 | .019980235516578737 | .022543326401409325 |
| .05 | 53.43900655779883 | 52.500763651255745 | .017016521009947105 | .018818056633965186 |

Both original A+10Pa pressure and A+.001*Sinf top budgets passed. Post-.1s maximum layer total-stress error was80.12241833447479Pa and top gap8.344286992065463Pa, below100Pa. Startup oscillation remains visible and P3 is not better in every field. A is retained finite-Kw CPU1 with its own qualified reference; P3 is GPU/M0, so this is not an isolated backend or integrator truth. Ramp/band/current-J/inertia and old u-pw Vel0 boundary qualifications remain.

The exact new full source changes only one M0 allowed-TimeMax expression in each private Single.cpp. All headers/helpers/CUDA sources and retained CUDA objects remain unchanged. Four actual builds passed. New full10us reader was built once with the real Release ABI; it has not read full data. Old programs and formal case inputs were preserved.

Three minimal implementation regressions passed their independent native reviews: DebugCPU B200/18, GPU Debug B2/2 with zero-error memcheck, and GPU Release default A320/18. Every actual shared record in the five exports, including initial/noninitial signed clock bytes and forced final, matched the corresponding original P3 control; B pressure/dt sidecars matched too. All22 raw-array guards were independently enforced. Five exports do not prove all22 raw arrays or hidden HG memory cross-run bit equality. ReleaseCPU has build qualification; GPU Release B has no newly claimed short bit oracle.

Root separately admitted one fresh diagnostic upl_tpi_p3_B10us_full2tv_GPU_r1. Its direct owner51340 created1794930029.7328744 launched GPU35020 created1794930036.8290727; actual executable, parent and argv were observed while live. Start/root_launch_review bind the actual new Release program and all readiness inputs. The original C08 owner36608 and target43828 remained stopped; no process action was performed.

Planned fixed dt1.0000228881835938e-5s,7288262 updates,1653 native frames, scalar end72.88428815806371s. Event1000 remains pre-open;1549 later frames require15490 true drained checks. Full/short share only1262 actual planned records; short forced199996 is not full normal200000. Actual native bytes remain to be reviewed after completion. All ten full-cycle theory targets, late floor and original stress/top/bottom budgets remain unchanged.

The owner preserves actual Win32/Popen exits and raw errors, then makes at most one same-root terminal queue attempt with45s timeout. No watcher, retry, automatic reader, following solver, or physical acceptance is attached. The rough39h cost comes from the unprofiled2s window and is not a controlled speedup or profiling extrapolation. Current loop estimates may change.

Latest completed preparation checkpoint was verified locally/remotely aa04f64994377cfe5e16d6d1f901be2e708e16a4. Programs, source/object archives and raw/native binaries remain local protected artifacts, not cloud Git data. Explicit SHA scans remain zero. P3 remains a private M0 three-defect candidate, not a claimed literal LF, converged implicit solution, second-order method, exact restart or formal release.
