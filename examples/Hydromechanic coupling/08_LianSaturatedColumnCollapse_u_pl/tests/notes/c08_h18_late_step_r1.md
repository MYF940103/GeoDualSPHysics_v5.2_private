# C08 late one-step material/volume attribution — author-only

New files are `tests/support/c08_h18_late_step_r1.cpp`, its `_build.py` and this note. No build, component, trajectory, native reader, VTK or hash scan is authorized by authoring. Root must fully read them before a separate build and separately admitted component calls. No production/source/input/program/PRE changes occur. Each component performs only one original CPU symplectic step from one selected already saved GPU state, not a GPU replay, restart qualification or new collapse trajectory.

The completed full3 diagnostic has a late negative pressure drift. Its fresh zero-step RHS at Parts200/250/300 shows net dilatational/compression contributions larger in magnitude than the opposing hydraulic aggregate. The observed interval quantity `delta(logJ)-delta(trace(sigma_effective))/(3K)` is largely nonnegative despite psi0. That observation does not by itself prove wrong material history, volume or a programming bug. Smooth psi0 flow preserves stress trace; the explicitly separate existing tension-face return can decrease trial trace without deviatoric kappa growth. The proposed attribution distinguishes this policy from gradient inconsistency, quadrature and floating-point error.

## Original code audit and scope

The schema2 CPU and GPU predictor use sigma_n plus half-dt elastic/Jaumann rate, project the trial and retain kappa_n. The corrector independently uses sigma_n plus full-dt midpoint rate, then commits its own returned history. J uses the corresponding J_n and midpoint J_h/theta_h. No wrong stress base or double-advanced history was found by the source read. A limited instantaneous CPU RHS trace/(3K) agrees closely with its J divergence, but this is not an integrated GPU trajectory proof.

The new entry inherits the retained late301 RHS fixture. Its only generated shared-source changes are protected access and diagnostic AppInfo name. It links one new entry with exactly86 original physical DebugCPU objects and archived headers, with no hooks and no physical TU compilation. The exact1027-byte original `ComputeStep_Sym` call/capture block from `c08_h18_step_balance_r1.cpp` remains byte-identical. The existing original J/p midpoint, positive FS cap, sort/base, arithmetic, time and contact observations are retained; source snapshots are only full3 Parts200/250/300, completed2400001/2500001/2600000.

Each is initialized through the genuine original PRE handoff/release, then independently restored by ID; the PRE itself is never rerun or modified. The root must retain completed full3 native301 and RHS receipts plus all actual program/input/PRE bindings. No part91/profile/count substitution is allowed. First state clocks and signed native records remain original. Source and receiver numerical material/AS/AV/contact controls remain unchanged.

## Additional observation, not a model replacement

Capture reads actual stress, saved kappa and original float Rsigma in each of seven existing stages. While predictor ownership exists, sigma_n and kappa_n are checked against the restored same-ID base, in addition to the original p_n/J_n checks. No capture changes any primary state or rate.

After **all** original physical step calls finish, two pure `fsoil::EvaluateMaterial` shadows reconstruct each actual predictor/corrector trial from the captured sigma_n and exact float rate. They use the same archived header, input coefficients, fit, softening and actual `PartBegin && StrainSoftening` trigger. All six actual committed stress components must match the corresponding pure result bitwise. Predictor actual kappa must remain kappa_n; corrector actual kappa must match the returned float history. A mismatch is a real failure, not relaxed to a new numerical tolerance. `shadow_status`/reason/lambda fields are inferred from this same-input bit-matched function, not a hook that recorded the original call's status. These10000 extra pure evaluations occur after the step and never feed back.

Each new `material_shadow.csv` has10000 rows, reporting trial/committed trace and q, continuous/saved kappa, shear/apex/tension multipliers and shadow status/reason for5000 IDs at both stages. New `trace_balance.csv` has5000 full-step rows. `stages.csv` retains35000 actual stage rows with additional sigma/kappa/Rsigma columns. Original5000-row p/J balance and3 summary rows stay unchanged. The completion records one physical step, two actual force/Darcy calls,10000 no-feedback material evaluations and original actual clocks.

For `I=trace(sigma_effective)` and `R=trace(Rsigma_h)`, define

`inferred = delta(logJ) - (I_next-I_n)/(3K)`

`quadrature = delta(logJ)-dt*theta_h`

`rateMismatch = dt*(R/(3K)-theta_h)`

`addition = ((I_trial-I_n)-dt*R)/(3K)`

`returned = (I_trial-I_next)/(3K)`.

Then the measured arithmetic identity is `inferred=quadrature-rateMismatch-addition+returned`. The closure uses the original roundoff helper and an explicit128-operation binary64 envelope. It is an arithmetic check only, not a new physical error threshold. `rateMismatch` includes float stress-gradient/stiffness/Jaumann trace error and must not be silently set to zero. The trace of the exact Jaumann commutator is zero, but finite float arithmetic need not give exact cancellation. Finite midpoint log-J quadrature must remain separate. Returned stress trace changes can be a deliberate tension/apex model response, not automatically an implementation error or physical truth.

## Build and three separate one-step commands

After root review, build only once:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_late_step_r1_build.py --execution-authorized`

The build deliberately retains the inherited executable basename `C08H18LateRhsR1.exe` inside the fresh `tests/outputs/c08_h18_late_step_r1_build` folder; stage/output/source identities distinguish it from the zero-step tool. It never runs the program. No canonical executable, VS project/solution or frozen physical object is replaced. Existing complete/partial names refuse overwrite.

After its successful receipt and a **separate root admission for each selected part**, invoke with absolute paths, replacing PART and its matching output label:

`tests/outputs/c08_h18_late_step_r1_build/C08H18LateRhsR1.exe --check --native tests/outputs/c08_h18_n255_full3_r1/native_r1 --part PART -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 tests/outputs/c08_h18_n255_full3_r1/c08_h18_n255_full3_r1 tests/outputs/c08_h18_late_step_r1_pPART`

Only PART=200/250/300 is accepted. Each fresh flat output directory has its own ordinary diagnostic Run.out plus stages/balance/summary/material_shadow/trace_balance/completion. There is no automatic loop or third-party solver launch. Retained old components and their snapshots are not repeated. A real component failure stays failed, with original exits, first error, last output and partials preserved. Successful completion is not physical, server, full-collapse or other-psi acceptance. This stage does not admit half chains, PRE/other-psi solves, changed AS/filter/contact/pressure policy or a repair.
