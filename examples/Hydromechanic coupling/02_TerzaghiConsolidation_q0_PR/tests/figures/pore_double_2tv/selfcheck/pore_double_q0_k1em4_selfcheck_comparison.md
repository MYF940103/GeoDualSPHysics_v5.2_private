# Same-baseline tool self-check (not a migration result)

Assessment: tool self-check passed; no physical improvement conclusion

Compared 402 complete native BI4 frames, 1000 fixed soil IDs and 7288429 logged steps per run.
Final actual time: 72.884290011934951 / 72.884290011934951 s; Tv=2.00000011795.

| Quantity | Baseline A / high+residual | Baseline B / double state |
|---|---:|---:|
| Final mean excess (Pa) | 536.850397604 | 536.850397604 |
| Final pressure-based U | 0.94631496024 | 0.94631496024 |
| Fixed-top settlement (mm) | 4.29383739216 | 4.29383739216 |

All-frame maximum absolute particle pressure difference: 0 Pa.
All-frame particle pressure RMS difference: 0 Pa.
Maximum fixed-top settlement difference: 0 mm.

The full-run differences are descriptive. They do not establish improved physical accuracy, remove the late plateau, or satisfy the unresolved strict short-run pressure gates by themselves.

## Validation

- Successful completion, zero exclusions and zero DtMin adjustments checked in both Run.out files.
- Native input, reader executable, CSV and generated XML hashes recorded; source/reader-mismatched caches rejected.
- Every frame has all IDs 0..1039, finite saved fields, native types and consistent row/frame times.
- Comparisons use actual native times within 1e-9 s, no interpolation, equal reference pressures and identical initial state.
- Final mean pressure and fixed-top settlement independently recomputed with scalar math.fsum.
- PNG/PDF render files generated; visual inspection by the operator is still required after the formal run.

## Caveats

- This is a representation-migration comparison, not proof of greater physical accuracy.
- Classical Terzaghi is a small-strain, ideal instantaneous-load physical reference; the numerical case has finite Kw, a 0.01 s load/drainage transition and moving particles. It is not an exact reference for this discrete SPH problem.
- Prior strict short-run pressure screening (0.01 Pa RMS / 0.1 Pa maximum) was not fully passed. A completed 2Tv run or a visually overlapping curve does not waive that gate.
- Historical and current executable builds differ; recorded core-source provenance is checked at launch, but this historical comparison is not a controlled timing benchmark.
- The saved initial positions may be float3. Fixed initial IDs and their common saved origin are used for settlement; every frame's native position type is recorded.
- Arithmetic particle mean uses the same 1000 soil IDs at every frame; it is not a current-volume-weighted continuum average. U=1-mean(excess)/q0 is reported only after drainage starts.
- Profiles use the same fixed initial-layer ID sets and z0/H, not changing current-z bins. Requested Tv values select the nearest shared saved frame; neither time nor pressure is interpolated.

## Sources

- Baseline: `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out`
- Compared run: `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out`
- Native reader: `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\tests\outputs\pore_double_vel0\reader\export_state.exe`
- Reproducible script: `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\support\compare_double_q0.py`

Detailed per-frame data types, SHA-256 records, all target times, particle-layer membership and numerical differences are retained in the adjacent JSON and CSV files.
