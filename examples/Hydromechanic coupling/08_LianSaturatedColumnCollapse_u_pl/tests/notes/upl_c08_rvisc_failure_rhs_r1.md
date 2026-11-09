# Frozen residual-viscosity acceleration-to-Darcy component (author only)

This draft does not run a trajectory. It derives `upl_c08_residual_visc_cpu_r2.cpp` and reuses its already compiled private CPU Single callback object. Production sources, the original bedkeep objects, runtime_r6, PRE, prior helpers, and all sealed results remain unchanged. Root must read these four new files before separately authorizing build and run.

The three explicit inputs are truecausal90 part13 (tau .14, retained implementation control), truecausal90 part51 (tau .52), and the failed residual-viscosity53 export part51 (tau .52). The latter is an actual saved state from a failed .90 job, not its unsaved failure state. Genuine 90/53 headers remain unchanged. Existing native receipts establish all22/6805 = 5000 soil + 1805 fixed, keep5/retire255, P0/J/ledger/cache/FS/kappa/clock/signed/plane qualification. The original r2 GPU law1 PRE and already generated causal seed initialize the CPU receiver once through the real loader and release event; no new PRE, GenCase, BI4 reader, VTK, or physical solver is invoked.

Each state gets an independently restored OFF and alpha=.1 ON actual `Interaction_Forces(INTERSTEP_SymCorrector)` followed by the original `DtVariable(false)` guard and cleanup: exactly six complete force/Darcy calls and zero updates. AS remains total-stress .2/n3; AV remains .1; release Shepard/damping remain OFF. The previously passed matched eta0 LS/force/float-commit calculation, rank/energy/force/torque budgets, and isolated damping bound are unchanged. Original necessary step guards must also pass for each actual snapshot; failure is retained without changing a guard or dt. The old manufactured checks are not repeated.

The new helper changes input selection, labels, counters, and read-only outputs. `Graph`/`Fit`/`Evaluate`, candidate `Apply`, and `Map`/`CopySaved`/`Ledger`/`Restore`/`SoilUnchanged` retain the closed R2 source text. Every evaluation preserves all5000 primary bits and actual scalar clock; ID-owned wall codes/normals/slips retain the real seed/release roles. ON/OFF must agree bitwise in all5000 actual theta, C, Rsigma, and FS. Sorted boundary states are rebuilt by the normal full force path; no hand-made ghost or truncated neighbor stencil is used.

The hook changes only finished soil acceleration, immediately before the original Darcy wrapper refreshes wall acceleration and evaluates pressure rate. Consequently the same-state ON-minus-OFF actual rate is the acceleration-path response, including that wall refresh. It is not the difference between time-shifted trajectories. At fixed geometry/J/C/FS its algebraic form is

`delta(pdot)_i = (Kw/n_i)*(rho_w/gamma)*{ k_i*[div_C(delta a)_i + chi_FS*delta a_i dot Lx_i] + k'_J*gradJ_i dot delta a_i }`.

Here chi_FS is one only on the existing free-seepage FS2/3 branch, and `delta a` includes the actual wall reconstruction. This expression documents the interpretation; the helper does not duplicate this RHS or add a new production hook. The measured quantity is the difference of the two real float rates. The sign of pressure storage work is not a standalone total-energy certificate: skeleton/fluid exchange, boundary work, material return, and subsequent stage changes are outside this zero-time test.

`soil_force.csv` has 30000 rows with actual Ace, total acceleration, actual pressure rate, ON-OFF differences, actual theta/Rsigma6/FS, and candidate ideal/committed acceleration. It appends actual `Kw/n` and `-Kw/n*theta` as the raw volumetric compression contribution before any FS rate rule or pressure projection, plus a `snapshot` label. This single contribution is not a budget for the actual returned rate or projected pressure. `focus.csv` has 48 rows for IDs7011/7012/6230/6231/5941/5897/5895/5294, including actual C9 and state fields. `pairs.csv` retains the original two pair descriptions (12 rows); `damping.csv` and `calls.csv` each have six rows. The actual C equality is checked on all5000 even though only focus C matrices are exported. No full spectrum or manufactured constitutive truth is inferred.

The runner compares both OFF and ON control part13 against the retained R2 soil/focus/pair numeric CSV fields, excluding labels and newly appended fields: 10000 soil, eight old focus, and four pair rows. Any mismatch is kept and fails the stated implementation-control check; no row is discarded or tolerance fitted. This check is same CPU implementation evidence, not cross-backend equivalence. Saved native input and recomputed CPU FS can differ and remain explicitly reported.

Build is one helper CL plus one link, using the sealed R2 actual DebugCPU recipes: MSVC14.36, `/Od /MTd /Zi /RTC1 /fp:precise /std:c++17 /openmp`, same frozen class/material headers, 85 original non-main objects + the adopted private Single object + one new helper = 87 link objects. No physical object is recompiled, no full project build occurs, and the four existing runtime files are copied only to the fresh helper directory. Stat bindings protect consumed sources, objects, programs, and runtime; no SHA scan is added.

After root review, the only intended invocations are separate:

```text
python -X utf8 -B tests/support/upl_c08_rvisc_failure_rhs_r1_build.py --execution-authorized
python -X utf8 -B tests/support/upl_c08_rvisc_failure_rhs_r1_run.py --execution-authorized
```

Fresh paths are `tests/outputs/upl_c08_rvisc_failure_rhs_r1_helper`, `tests/outputs/upl_c08_rvisc_failure_rhs_r1`, and `tests/logs/upl_c08_rvisc_failure_rhs_r1.{build,check}.json`; existing or partial paths are refused. A failed invocation preserves its real typed Popen/Win32 exit and partial outputs, with no retry or subsequent action. This draft has only static/AST checks; no build, helper, decoder, or solver was executed by the author. It cannot establish whole coupled stability, the unsaved GPU failure cause, a physical improvement, or admission of other psi groups.
