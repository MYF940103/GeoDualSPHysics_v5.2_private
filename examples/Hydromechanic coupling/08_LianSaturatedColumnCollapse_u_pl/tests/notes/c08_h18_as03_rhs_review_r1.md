# AS03 two-state RHS review

Only this note and `support/c08_h18_as03_rhs_review_r1.py` were authored.
No execution/import, component, solver, decoder, build, VTK, Git or SHA scan
was performed by the author. The entry reuses only the existing work-review
CSV/stat/budget helpers; importing that module later does not run its main.
Root must read the complete files and admit the one offline invocation after
the real RHS component has passed.

From the C08 case root, after admission:

```powershell
D:/anaconda3/python.exe -B tests/support/c08_h18_as03_rhs_review_r1.py --execution-authorized
```

The sole component is `c08_h18_as03_rhs_r1`, not old AS05 storage/late probes
and not the AV0.2 trajectory. Its root check must bind the actual owned
component call/build/completion and four output CSVs using `files`, with
component_invocations=1 and physical_steps/solver_invocations/native_invocations=0.
The review consumes the original 301-row clock table through its already
sealed analysis receipt, without reading typed22/BI4 again. Parts38/76 are
actual completed steps2076001/2152001; no n*dt clock or interpolation.

Coverage is exactly 10000 soil rows (5000 native IDs2060..7059 per state),
30000 additive donor rows (`all`, `fluid_donors`, `fixed_donors`), 18 original
summary rows and 3610 fixed-wall rows. Only inactive wall derivative/C scratch
may be empty. The original literal source's final float must match the actual
rate bitwise. Original per-row float/expanded/donor and global reconciliation
budgets are preserved; there is no new physical tolerance. No additional FS
equality gate is added. The baseline_same_time_step identity remains required;
the old pair-force Ace/rate/theta differences and FS equality are descriptive.
The original component enforces its donor dbudget, which is not separately
exported. The review records the independent additive donor residual but does
not attempt to recover dbudget by subtracting two rounded budget columns.

Seven signed contributions retain the original order: compression, LP,
Taylor_pressure, Da, FS_Ace_Lx, chain_pressure, chain_Ace. Their original Pa/s
and `Q=(nV/Kw)*rate` values are retained. Compression is present only in the
`all` donor row: adding all+fluid+fixed double-counts the hydraulic terms, and
adding all compression again double-counts its source. Donor partitions are
additive bookkeeping on one complete fresh CPU force, not counterfactual runs.

The new disjoint receiver cohorts use the actual frozen tool's rule: FS first;
then non-FS with at least one fixed Darcy donor is wall_adjacent; remaining
non-FS is interior. Original summary `interior` continues to mean **all non-FS**
and is checked using that definition. New cohort summaries are made separately.
The global-weighted graph uses each signed cohort Q divided by the entire
state's sum(nV/Kw), so cohort contributions are comparable without changing
normalization by region. The actual/coefficient/storage columns repeat across
the three donor rows for context and must not be summed three times.

Outputs under `tests/figures/c08_h18_as03_rhs_review_r1_`:

- `cohorts.csv` and `terms.png`: eighteen disjoint-cohort/donor summaries,
  signed and absolute Q, original coefficient-change/storage proxies and
  equivalent globally storage-weighted rate. The seven terms remain separate.
- `normal_stats.csv`: valid/null normal counts, signed-target RMS/extrema,
  local shadow RMS, pressure/rate and old-baseline descriptive differences
  for every state/cohort. Empty cohorts are marked by their zero counts;
  placeholder zero statistics are not physical zero evidence.
- `materials.csv` and `fields.png`: all10000 original soil rows, all three
  donor partitions' seven signed terms/Q, original p/P0 and full field ranges.
  The four field columns show p, actual fresh CPU RHS, theta, and H dot n at
  FS nodes with a valid normal. Invalid FS normals are separately marked.
- `focus.csv`: fixed material pairs6767/6865 and4953/4954, prior front ID7010,
  and the actual maximum/minimum RHS and valid-FS absolute Hdotn extrema IDs.
  Selection reasons remain explicit; no new trajectory is inferred from two
  frozen states and no ID is substituted to fit a conclusion.

`H=original corrected grad(p)+rho_w*actual Ace`; no extra gravity is added.
The original normal direction and length are retained. A zero normal makes
the dot product algebraically zero, but **does not establish zero flux**.
Only normal_valid rows enter Hdotn/shadow normal statistics; invalid counts
remain visible. H and Hdotn have unit Pa/m; the original CSV `Pa_m` suffix is
retained. `q_n_local_shadow=−k/gamma*Hdotn` is a local nonconservative shadow,
not a measured pair flux, phase-integrated leakage or boundary acceptance.

The storage proxy sum(nVp/Kw), its rate and coefficient-change contribution
are not fluid mass. Signed Q need not sum to zero. CPU corrector-mode force
evaluations on saved completed GPU states do not replay omitted GPU predictor
or corrector substages. Instantaneous source imbalance is not integrated
pressure-error proof. Maps use complete shared signed scales with display-only
symlog; no smoothing, clipping, time/radius fitting or zero-pressure filtering.
Pressure is p, and the extra p-P0 column is diagnostic rather than the paper's
plastic excess pore pressure. Actual shear order is Sigma_ij=(xy,yz,xz).
In particular, a positive instantaneous whole-domain Q is not evidence of an
increase in fluid mass over the full time history.

Normal exit or arithmetic agreement does not admit final AS/AV selection,
new physical operators, another psi, PRE, solver, half chain or paper/physics
acceptance. Failure preserves the fresh partials and failed receipt; diagnose
offline rather than overwriting or rerunning a completed physical job.
