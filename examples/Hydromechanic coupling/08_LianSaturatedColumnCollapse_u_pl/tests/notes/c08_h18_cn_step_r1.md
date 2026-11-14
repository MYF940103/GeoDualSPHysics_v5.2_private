# Finite-Kw diagonal-CN: one Part300 CPU step — author-only

New files are `tests/support/c08_h18_cn_step_r1.cpp`, its `_build.py` and this note. Authoring does not import or execute any candidate, build, force/component, solver, native decoder, VTK, hash or Git. Public C++/CUDA, root XML/BAT, original PRE/runtime and the current AS03 GPU window are untouched. Outputs, only after separate root full read/build/component admissions, are fresh `tests/outputs/c08_h18_cn_step_r1{,_build}` and matching `tests/logs/c08_h18_cn_step_r1.*`. Existing partial outputs are never overwritten or retried.

## Purpose and actual numerical change

The completed AS.5/n2.55 full3 Part300 is the sole input: actual source time12.999999999592434 s, completed2600000, full301/6805-ID/22-array native layout. A passed original Part300 CPU step already exists in `outputs/c08_h18_late_step_r1_p300`; no new OFF trajectory is allowed. This component advances one5us CPU step to completed2600001 with the same original force, predictor, material, J, velocity, position, NoPen and completed-step free-surface handling. It intentionally replaces just the soil-pressure corrector increment. No PRE, .9s/3s collapse, half chain, other psi or production algorithm is launched or selected by this component.

At the **true force_h** stage, before any full J update, freeze the complete pressure row using the qualified pressure-row stencil:

`M_h=gamma*n_h/Kw; S_h=sum A_h; s_h=S_h/M_h`.

All LP/pair-C/Eta, receiver-C Taylor, variable-k chain, raw-FS signs and original donor exclusions remain. Current walls and acceleration are lagged/frozen. The original source-ordered actual float rate is `R_h`; `p_n` is the real sorted predictor base and `p_h` the real stored half pressure. The only new update is

`delta_CN=dt*(R_h+s_h*(p_h-p_n))/(1+0.5*dt*s_h)`

`p_CN=float(double(p_n)+delta_CN)`.

It is **not** `dt*R_h/(1+0.5*dt*s_h)`. The extra numerator preserves the correct source response and local second-order consistency for smooth constant-coefficient rows. No global matrix, implicit wall solve, complete coupled Jacobian, TPI, beta, artificial capacity, negative-pressure clipping or altered necessary step is introduced. A constant positive/negative/zero pressure source is manufactured at every actual s_h and checked with a binary64 arithmetic envelope. The six original two-node explicit-midpoint/CN rational Taylor tests are copied bytewise from the passed pressure-row fixture. They do not establish nonlinear or switching-stage order.

Nonfinite or exactly-zero denominators fail without clipping. Finite negative denominators are explicitly counted and retained, not silently repaired. They require root review before any later trajectory. No coefficient or tolerance is adjusted to obtain a pass.

## Actual lifecycle and the original temporary commit

The generated RHS include differs from the passed late-RHS source only in protected test access and diagnostic application name. The generated StepProbe include differs from the passed late-step entry only in protected access, the fresh shared include path and an unused original main name. Its Capture/material-shadow methods remain unchanged. The new entry includes these frozen helpers; the old ExecuteStep is not called.

The actual sequence is: restore Part300; original force_n; original predictor; original half cell divide; original force_h; read-only complete midpoint-row capture; original corrector; capture its temporary explicit pressure (`raw_original_commit`); replace only pressure by the formula above; original force scratch cleanup; original completed divide/FS cap. All original two-force/natural-step/material guards still execute. The temporary explicit write is part of this **one** ON sequence; it is not a separately run OFF solution or its completed boundary closure. `original_cap_shadow` is explicitly the original raw pressure capped under the candidate's final FS flags, not an independently recomputed OFF wall/FS state.

The true stored M_h/S_h/p_n/p_h/R_h are retained by native ID. They are never recomputed using J_new. Original midpoint scalar bases, literal final-float rate and the complete row expansion retain their existing arithmetic budgets. The corrector has already computed the other primary variables before the pressure replacement; no later corrector force is invented.

Immediately before/after the direct replacement, all6805 IDs retain the checked code, FS, position, velocity/rho cache, six effective stresses, kappa, P0, PosDiv, J, theta, FS normal and load-acceleration fields bytewise. Fixed pressure is unchanged by the replacement and original wall normal/slip roles remain. The final divide is still allowed to rebuild wall pressure/FS through the original code. The component does **not** claim complete22-export equivalence against the prior OFF run: only fields actually captured/bound are checked. `dterror` is not synthesized, rewritten or used as a new-step equality proof.

Final J/n/V/rho/k domain/cache, fixed P0, normal IDs/roles, finite primary state and nondecreasing kappa are checked. Existing required time-step and original contact/cell gates remain. The two original same-input material shadows validate six stresses and predictor/corrector kappa policy; those pure post-step evaluations do not feed back.

The pressure/J balance reports the explicit new storage contribution

`CN_intervention_storage = c_h*(p_CN_raw-p_original_raw)`.

This term must be present in the discrete arithmetic identity. It is a time-discretization intervention, not new fluid mass, a physical source or proof of restored conservation. Omitting it while claiming the old explicit pressure/J balance would be misleading. J still integrates the total original velocity divergence; no material-return volume is added or subtracted.

## Expected outputs and independent review

- `stages.csv`:40000 rows, eight5000-ID captures including raw original/CN, with the original visible fields.
- `midpoint_rows.csv`:5000 complete true-midpoint rows, capacities, coefficients, signs, denominator and original-rate/row identities.
- `pressure.csv`:5000 records with original temporary pressure, candidate raw/completed pressure, explicit cap shadow, candidate-minus-original differences and final-float envelope.
- `balance.csv`:5000 original pressure/J arithmetic identities with the additional declared CN storage contribution.
- `constant_source.csv`:15000 normalized algebraic source tests, not extra physical trajectories.
- `coupled_CN.csv`:6 retained constant-matrix CN tests.
- `material_shadow.csv`:10000 original pure material evaluations.
- `completion.json` and ordinary diagnostic Run.out. Passing the component is not physical accuracy, stability or collapse repair.

After complete root review, build only:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_cn_step_r1_build.py --execution-authorized`.

The isolated recipe compiles one entry and links86 sealed original DebugCPU objects with the160 archived headers and authoritative VS ABI/library recipe. No public physical TU or canonical program is rebuilt. The inherited executable basename is `C08H18LateRhsR1.exe` inside the new `c08_h18_cn_step_r1_build` folder; use its actual receipt identity.

Only after a separate successful build and root component admission:

`tests/outputs/c08_h18_cn_step_r1_build/C08H18LateRhsR1.exe --check --native tests/outputs/c08_h18_n255_full3_r1/native_r1 -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 tests/outputs/c08_h18_n255_full3_r1/c08_h18_n255_full3_r1 tests/outputs/c08_h18_cn_step_r1`.

Offline review must compare actual common captured fields/stages with the retained original Part300 one-step CSVs without another OFF run. Before intervention the original shared captures should be exact; after intervention the candidate pressure difference is intentional and must not be subjected to a misleading5Pa cross-option/half gate. Other captured corrector fields should remain exact; final wall/FS changes require their actual scope to be recorded. Signed-clock/output-interval statistics cannot substitute for adjacent physical-state comparison.

If the single-step effect is negligible or simply weakens all responses without improving targeted high-frequency behavior, do not expand this component into another physical window. Any future production/default-off CPU/GPU candidate would still require explicit scope, implementation/sorting/boundary tests, XML documentation and a genuinely justified new bounded trajectory. No such transition is automatic here.
