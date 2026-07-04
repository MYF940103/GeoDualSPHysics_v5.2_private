# MLS ghost mDBC pore-pressure boundary test, 2026-07-04

## Purpose

Test whether replacing the mDBC pore-pressure boundary extrapolation from zeroth-order / boundary linear extension to first-order MLSs recovery of excess pore pressure at the ghost/projection point improves the self-weight Scenario 2 late-time bottom-pressure plateau.

The boundary pore pressure still participates in the Darcy term. The tested value is:

```text
PorePress_b = PorePress0_b + q_MLS_ghost
q = PorePress - PorePress0
```

## Code state

- `source/JSphCpu.cpp`: mDBC pore-pressure extrapolation uses first-order MLS recovery of `q` at the ghost/projection point, with zeroth-order fallback when the determinant is too small.
- `source/JSphGpu_ker.cu`: GPU kernels use the same MLS ghost `q` logic for standalone and merged mDBC correction paths.
- `source/DualSphDef.h`: extra mDBC slip modes are enabled so XML `SlipMode=2` is honored. Test BAT files do not pass command-line `-mdbc`, because that would force the default slip mode.
- Pore-pressure-rate computation keeps boundary pore pressure in the Darcy term.

## Runs

### Linear recovery diagnostic

Output:

```text
figures/mdbc_pore_mls_recovery_neumann_ghost/
```

Result:

- Boundary count: 40
- Zeroth-order average vs ghost/projection target RMS: 120.781 Pa
- MLS ghost/projection recovery RMS: 1.416e-12 Pa
- Old boundary-extension recovery RMS: 4.327e-12 Pa

Interpretation: boundary linear extension recovers a linear `q` field exactly at the boundary particle, but that is not the zero-normal-gradient ghost value needed for the no-flow boundary in this test.

### Platform short-window restart

Input restart:

```text
outputs/CaseSWSc2_MLSs2_Tv2_from_p0053_GPU_out/data/Part_0180
```

Output:

```text
outputs/CaseSWSc2_MLSg2_PlatformShort_from_p0180_GPU_out
figures/CaseSWSc2_MLSg2_PlatformShort_from_p0180
```

Result over Delta Tv=0.1:

- Initial bottom excess pore pressure: 10.839 kPa
- Final bottom excess pore pressure: 6.992 kPa

Interpretation: the MLS ghost boundary immediately breaks the old frozen platform state.

### Full 2Tv run

Stage 1:

```text
configs/CaseSWSt1_MLSg2_Def.xml
outputs/CaseSWSt1_MLSg2_GPU_out
```

Selected restart:

```text
Part_0040, t=0.200 s
```

Reason: lowest Stage 1 pore-pressure RMS against the undrained profile.

Scenario 2:

```text
configs/CaseSWSc2_MLSg2_Tv2_Def.xml
outputs/CaseSWSc2_MLSg2_Tv2_from_p0040_GPU_out
figures/CaseSWSc2_MLSg2_Tv2_from_p0040
```

Runtime status:

- Full GPU run completed to 2Tv.
- 401 PART files written.
- Excluded particles: 0
- `SlipMode="No-slip"`, `mDBC-Corrector=True`, `mDBC-FastSingle=False`

Bottom excess pore pressure:

| Tv | Theory kPa | MLS ghost kPa | Error kPa |
|---:|---:|---:|---:|
| 0.0 | 10.696 | 10.403 | -0.293 |
| 0.1 | 6.912 | 6.992 | 0.080 |
| 0.5 | 2.537 | 2.656 | 0.119 |
| 1.0 | 0.739 | 0.866 | 0.127 |
| 1.5 | 0.215 | 0.573 | 0.358 |
| 2.0 | 0.063 | 0.561 | 0.498 |

Comparison files:

```text
figures/CaseSWSc2_MLSg2_Tv2_from_p0040/bottom_dissipation_mls_boundary_compare.png
figures/CaseSWSc2_MLSg2_Tv2_from_p0040/bottom_dissipation_mls_boundary_compare.csv
```

## Conclusion

The MLS ghost/projection boundary is a real improvement over the old boundary-extension behavior: it removes the severe 10.84 kPa frozen platform and gives good early-to-mid consolidation agreement.

However, a smaller late-time residual plateau remains. At Tv=2 the bottom excess pressure is about 0.56 kPa instead of the Terzaghi value of about 0.063 kPa. The remaining discrepancy is therefore not the old linear boundary extension alone. Further diagnosis should focus on late-time low-gradient behavior near the bottom mDBC support, especially consistency among mDBC velocity, stress update, and the pore-pressure-rate terms after the main pressure gradient has become small.

## SlipMode=1 short isolation

Run:

```text
configs/CaseSWSc2_MLSg1_Tv01_Def.xml
outputs/CaseSWSc2_MLSg1_Tv01_from_p0040_GPU_out
figures/CaseSWSc2_MLSg1_Tv01_from_p0040
```

This run changed only Scenario 2 `SlipMode` from 2 to 1 and stopped at Tv=0.1, inheriting the same MLSg2 Stage 1 `Part_0040`.

Result:

- `SlipMode=1` was confirmed in `Run.out` as `SlipMode="DBC vel=0"`.
- Excluded particles: 0
- The Tv<=0.1 bottom-pressure and RMS errors are almost identical to the `SlipMode=2` MLS ghost run.

Representative bottom excess error:

| Tv | MLS ghost SlipMode=2 error kPa | MLS ghost SlipMode=1 error kPa |
|---:|---:|---:|
| 0.005 | 0.077262 | 0.077260 |
| 0.05 | 0.063502 | 0.063511 |
| 0.1 | 0.079871 | 0.079857 |

Conclusion: the early MLS ghost error increase relative to the old zeroth-order run is not caused by changing from `SlipMode=1` to `SlipMode=2`.
