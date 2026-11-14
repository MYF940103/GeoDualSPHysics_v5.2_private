# C08 frozen-state work-conjugacy review

Author-only preparation: `support/c08_h18_work_conjugacy_review_r1.py` and this
note. No import, execution, build, solver, decoder, VTK, Git, SHA scan or next
physical stage was performed by the author. Root must read the complete files
and independently admit the one offline invocation after the component passes.

The sole component input is **c08_h18_work_conjugacy_r2**. The failed r1 build
is preserved and is not a data source. The four states are the original
AS0.3/n2.55 full-3s Parts38/76/92/300, not the later AV0.2 trajectory. Their
actual completed steps are 2076001/2152001/2184001/2600000. Actual times and
release-relative times are read from the already sealed 301-row clocks.csv;
no nominal n*dt clock, interpolation, native rewrite or fresh decoding is used.

After root admission only, from the C08 case root:

```powershell
D:/anaconda3/python.exe -B tests/support/c08_h18_work_conjugacy_review_r1.py --execution-authorized
```

The entry expects `tests/logs/c08_h18_work_conjugacy_r2.check.json` to seal the
unique real component call, successful build, completion and five output CSVs.
It verifies actual Popen/Win32 zero exits, owner-parent/program/argv consistency,
the bound stat records, original 86-object CPU build and no physical/material
advance. It neither restarts a failed component nor creates a replacement
completion. Any failure preserves its fresh derived partials and a failed
review receipt; do not rerun or overwrite it without separate diagnosis.

Coverage is 20000 soil rows (all5000 IDs2060..7059 at each state), 40000
soil/wall donor-partition rows, 7220 retained-wall rows (IDs0..1804 at each
state), eight summary rows and sixteen predeclared virtual probes. Each soil
force, stress-rate and theta error must remain within the **component's original
arithmetic budget**. Every raw soil closure / wall ghost-port residual and
virtual raw closure must remain within its original arithmetic budget. No new
physical tolerance is introduced. Exact float bit flags are reported, not
silently upgraded into an additional CPU/GPU equality gate. Source code and
raw BI4/22-array payloads are not rescanned or SHA-hashed. FSsaved/FSfresh are
retained observations: this reviewer adds no equality gate after the original
force preparation's allowed reclassification.

The three derived CSVs and three PNGs have prefix
`tests/figures/c08_h18_work_conjugacy_review_r1_`:

- `summary.csv` / `powers.png`: original total-stress force power, raw and
  corrected strain power, G1 gap, AS/AV powers, algebraic residual/budget,
  conditional gravity and mixture-mass proxies. The gravity/mass values in
  the original two-group summary are retained per group and are not summed
  twice. Four frozen points are not represented as a dense history.
- `spatial.csv` / `spatial.png`: every material ID's separate soil/wall and
  combined corrected-minus-raw work gap; both suspect pairs are marked.
  Each panel displays its complete signed range with an explicit independent
  color scale. No smoothing, clipping, fitting or color-based acceptance.
- `virtual.csv` / `virtual.png`: the two fixed-ID radial probes, the declared
  spacing-qualified interior comparator and all-soil x translation. The
  healthy pair can change identity between states according to the original
  predeclared rule; the CSV and tick labels retain its actual IDs.

The original virtual headers `symLraw_over_u_s_1` / `symLC_over_u_s_1` are
preserved. Dimensionally, norm(grad u)/norm(u) has unit **1/m**, because u is a
velocity. The figure uses that physical unit. Symlog thresholds (1e-7 W/m and
1e-6 inverse-m) are display-only choices; signed zeros and full values remain
in CSV and no threshold is used as a physical gate. Virtual probes are
soil-only: no virtual wall reconstruction, NoPen projection or reaction closure.

`P_stress + Iraw` closes for soil-soil under the component's frozen raw
double shadow. The soil-wall identity instead includes the actual reconstructed
ghost port. That port is not a measured physical fixed-wall reaction. The G1
gap `IC-Iraw` is descriptive; a nonzero value is not itself a failure, a proven
zero-energy mode, a trajectory root cause or evidence that deleting C is a
valid correction. Ordered Python partition sums are reported descriptively and
are not made into a new rounding or physical tolerance. The ordered group
ghost-port sum and a reconstructed raw residual are also retained descriptively;
the actual pass/fail check remains the original component residual and budget.

This is not a total coupled energy theorem. Darcy, pressure storage, plastic
return, variable mixture inertia, free-surface projection and fixed-plane
contact are not closed by this single frozen-state identity. The mixture
mass/storage proxies are not fluid mass. Shear fields retain actual storage
order `Sigma_ij=(xy,yz,xz)`. This review does not plot p-P0 as the paper's plastic
excess pressure, select final AS/AV parameters, unlock another psi, authorize a
new PRE, solver, half-step chain or claim paper/physical acceptance. Root must
inspect all three PNGs and interpret them with the prior force/pair evidence.
