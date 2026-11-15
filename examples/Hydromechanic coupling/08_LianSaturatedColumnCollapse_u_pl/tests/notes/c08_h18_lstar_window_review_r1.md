# C08 Lstar .90s offline physical diagnostics r1

Author-only preparation of `support/c08_h18_lstar_window_review_r1.py` and this note. Root must fully read and separately execute it only after the one actual `c08_h18_lstar_window_GPU_r1` run and unique native read have passed. The author has not read active new body data, executed this script, called an API/decoder/solver/build/VTK, or changed any consumed asset. It imports existing pure typed parsers and the passed source-material reference helper; it never calls an older analysis main or rereads the240000manufactured prediction rows.

## Exact shared clocks, material IDs and evidence

Consume the actual new run/native check, owned calls, original AS03 .90s run/native control, source/build/program/input/PRE/17-key bindings and complete unchanged91-row plan. Both bodies must have91actual6805-ID/22-array records,5000soil/1805fixed, and original native coverage and clock/ledger/signed safety. Every saved actual step and binary64 clock must match exactly, including first2000001 and forced final2180000; no interpolation, n*dt, count/header rewrite or old3s endpoint is substituted. Old AS03 is an operator reference, not theory truth or an accepted universal collapse solution. Differences are not half-step errors and receive no5Pa/0.005mm bound.

New export stats come from its genuine unique native receipt. Original AS03 exports use existing consumed stats from passed `c08_h18_lstar_cpu_off_r1.build.json`; source exports use the already passed `c08_h18_rv_window_review_r1.check.json`. These are transparent later reference seals, not invented old decoder-exit seals. Source typed22 is memory-mapped and only actual source frames0/1000 are read by the existing `source_reference` helper; the1.5GBsource is not swept or decoded again. Actual IDs/initial positions must establish50layers×100columns; fixed top and bottom cohorts are those real initial material layers and retain the actual full PRE position/P0/kappa reference. No ID is guessed from later deformed height.

## All-state statistics and descriptive cohorts

Read each actual receiver frame once into the calculations, retaining all5000soil IDs. Native `float(p-fixedP0)` bits and actual fixed P0 are checked. This native excess is a fixed reference, not newly reconstructed hydrostatic excess or the paper's plastic reference. Accumulated kappa must stay nondecreasing from PRE and the previous saved state. Kappa>0 and saved-interval kappa increments are history observations, not declarations of currently active plastic flow.

History has2cases×91frames×6cohorts=1092rows. Cohorts are all5000, fixed initial top100, fixed initial bottom100, current near bed0<=z<=2H, current FS2/3, and current non-FS with x>2H/z>2H. The last three are descriptive current-coordinate/FS masks, not proof of contact, absence of boundary donors or a legal manufactured interior. They can overlap; their sums must not be interpreted as a partition. Empty cohorts retain count0 and blank statistics rather than deleting rows or inventing zero averages.

Each cohort retains signed pressure/native excess minima/maxima/mean/RMS/5th/50th/95thpercentiles; NN distributions; J/n/rho/k/kappa/speed, effective and total stress distributions, settlement and material motion. It also records negative-pressure and FS counts, exact unchanged non-FS pressure-bit counts, FS label changes and kappa-history increments. Whole-soil front is the actual maximum x, including an isolated moving particle. No particle is dropped to improve a front, pressure or gap statistic.

## Stress convention and real3D spacing

The archived dynamic force convention and the already passed native physical helper use `sigma_total=sigma_effective-p I`. Native `SigmaState_kk` order is xx/yy/zz; `SigmaState_ij` order is xy/yz/xz. Both stress norms use `||sigma||_F²=xx²+yy²+zz²+2(xy²+yz²+xz²)`. Reported cohort Frobenius RMS is the square root of the mean of that six-component weighted sum, not the mean norm or an unweighted six-component average. Effective/total norm and trace distributions are in history; every selected spatial row includes all six effective and total components. The pressure-only diagonal shift leaves total/effective shear equal. These are state stresses, not an observed separated stress-force work budget.

One SciPy KDTree per actual frame uses actual XYZ coordinates and a nonself nearest-neighbor definition robust to duplicate positions. All5000NN values remain. For strict distances<0.7/0.5/0.3dp, independently reconcile global close-node counts against unique pair endpoints. Cohort reports distinguish unique pairs incident to at least one cohort node from pairs with both endpoints in the cohort; incident pairs are not summed across overlapping cohorts. Worst-pair actual material IDs are retained. No planar projection, smoothing, arbitrary pair exclusions or change to a native gate is introduced.

## Storage and energy wording

`W=nV/Kw`, `S=Σ Wp` is a signed storage proxy in m² per unit thickness; positive and negative contributions and Wsum are separate. `E_p=½Σ Wp²` has units J/m but is only a conditional pressure-storage quadratic, not total energy. `½Σ rho V |v|²` is an instantaneous mixture kinetic proxy; varying J/rho/V and external work prohibit interpreting it as a closed energy ledger. Neither S nor its drift is fluid mass or measured drainage flux. Native last-stage theta cannot be integrated as an unsaved interval source history.

For each later saved interval, the exact algebraic observed-storage decomposition is

`ΔS_C = Σ_current Wbar Δp + Σ_current pbar ΔW + Σ(mask_current-mask_previous) W_previous p_previous`.

The last membership term is retained for changing FS/geometric cohorts; it vanishes for the fixed cohorts. All terms use saved data. The remaining double-arithmetic residual is checked against a forward gamma(64N+16) accumulation scale formed from the sums of absolute terms; this is an arithmetic identity check, not a physical conservation threshold. First-frame interval terms remain blank because there is no previous receiver save. No pressure-rate, flux, correction-matrix spectrum or causal force is invented from the22arrays. See `c08_h18_lstar_conservation_audit_r1.md` for the LP-only reciprocity loss and its conditional stability limits.

## Fresh figures and data, without changing the run

Five CSVs: complete1092-row history;91actual-clock matched differences;30000spatial rows (2cases×parts30/60/90×5000IDs);5000source material cohort records;2observed timing rows. Timing uses180000new updates divided by actual positive `TSimul`, with raw Hardware/TTotal. It is not a controlled benchmark: trajectories, neighbor costs and host load may differ; inherited global2180000 is never the throughput numerator.

Three PNGs: full91-frame history with pressure, spacing, close pairs, front, speed, storage proxies, J, effective/total stress and fixed-material top settlement; native signed pressure maps; NN maps. Spatial plots use actual parts30/60/90 times, all5000points per panel, identical coordinates/limits across cases and one shared full-data colorbar for each physical field. There is no clipping/saturation, fitted shift, interpolation, smoothing or paper-color tuning. All history axes have sparse visible linear ticks. They are bounded diagnostic figures, not formal paper acceptance; root must inspect the rendered PNGs and the check begins with visual QA pending.

Root-only future invocation:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_lstar_window_review_r1.py --execution-authorized`

Outputs use only new `tests/figures/c08_h18_lstar_window_review_r1_*` names and `tests/logs/c08_h18_lstar_window_review_r1.check.json`. Existing complete or partial names block overwrite. Analysis failure preserves completed solver/native results and new partials; no repeat solver/decoder, half chain, next psi, PRE, source edit, parameter relaxation, SHA sweep, Git action or automatic physical admission follows.
