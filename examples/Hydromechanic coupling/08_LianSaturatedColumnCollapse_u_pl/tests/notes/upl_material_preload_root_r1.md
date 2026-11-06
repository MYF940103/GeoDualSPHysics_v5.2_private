# Fixed-container gravity preload: 8192-update observation

The fresh GPU run used the closed `upl_material_gravity_Debug_r1` program, before the later cosmetic parameter-read regrouping. The program/build/source archives and the owned solver/reader receipts remain unchanged. Only the previous startup's end time and step limit were extended: dt=2^-18 s, 8192 updates, actual end 0.03125 s, 257 saved states. No new source, equation, damping, initial stress, half-step run, PART restart, or wall removal was introduced. The GPU reported by this actual Run.csv is RTX 3050; its loop time was 563.766479 s, not an isolated Release benchmark.

## Completed implementation checks

- The actual solver and the unique native reader exited 0. The native review retained all 7060 IDs (5000 soil / 2060 fixed), 22 arrays, all 257 scalar clocks and 256 signed intervals, without excluded particles.
- Original checks passed for 1,285,000 soil ledger/cache records, 529,420 fixed-marker records, 1,280,000 noninitial saved-kappa comparisons, and 25,700 actual FS2/3 soil sign observations. Every frame has 100 true FS2/3 soil receivers. All observed kappa remain zero; this is not evidence of equilibrium or nonzero-plastic wall compatibility.
- The first five **record payloads** of typed22.bin match the retained startup byte for byte, as do the first five raw signed-clock rows and header. The real binary headers retain sample counts 257 and 5; whole-file equality is neither expected nor claimed. The original material-ID/coordinate maps match.
- The single offline analysis produced the complete 1285-row material-band history, 80-row late-quarter summary, and six-panel PNG. The root viewed the PNG: all actual samples and five fixed initial-material bands are visible; no smoothing, pressure clipping, interpolation or fitted reference was used. Bands overlap, so their energies must not be summed.

## Physical observation

For all 5000 soil IDs, over the last quarter of the actual time, t=0.0234375..0.03125 s:

| Native quantity | Range in that window | Final value |
|---|---:|---:|
| XYZ velocity RMS (m/s) | 0.0001470134 .. 0.0075048660 | 0.0034237086 |
| Pore-pressure RMS (Pa) | 5636.8133 .. 41914.1878 | 38158.9277 |
| Effective-stress Frobenius RMS (Pa) | 401.6257 .. 785.5128 | 763.7300 |
| Mixture kinetic energy (J/m width) | 0.0001791710 .. 0.4669163 | 0.09717305 |
| Maximum abs(J-1) | 5.05652e-5 .. 7.14547e-5 | 7.06499e-5 |

The final signed mean vertical velocity is +0.0030793347 m/s, after repeated sign changes. The apparent small final displacement RMS, 0.0233786074 mm, does not establish stationarity. Saved-interval changes of mean velocity are descriptive proxies, not particle acceleration RMS, force imbalance, or wall reaction.

The cold zero-stress/zero-pressure start is still oscillatory and has not established the paper's initial in-situ state. Do not release the wall at this final frame. Normal completion and unchanged startup are implementation checks, not geostatic or collapse acceptance. No new tolerance was chosen to classify it as equilibrated. The next review compares the physical time scales of continued cold equilibration with a consistent initial-state route; the existing analytical 1D mode is an **undrained** reference and must not be relabelled a drained geostatic state.

## Material formulas and subsequent stabilization review

Lian 2023 Eq. (19), psi=psi0*exp(-sf*kappa), is implemented in `src/source/FunSoilMaterial.h`, `fsoil::At`, and evaluated inside each consistent-return iteration. XML `dlt` supplies psi0 and `DilationDecay` supplies sf; CPU and GPU share the function. Nonzero sf requires `MaterialReturn=1`; default sf=0 preserves constant psi. The periodic positive/negative-dilation stages already exercised nonzero sf, whereas this preload deliberately uses psi=sf=0.

The paper's Eq. (47) negative-pressure stabilization is **not** implemented. It temporally relaxes the TPI pressure solve using beta=0.04, separately from TPI alpha=0.5. It is neither a zero-pressure clip nor multiplication of negative pressure by 0.04. The present explicit finite-Kw rate equation lacks that pressure-system diagonal/intermediate history; any adaptation requires a separately reviewed derivation and a controlled plastic-dilation witness before a new public interface. Negative pore pressure alone is not a failure.

Raw BI4, typed exports, executables, and source/object archives remain local protected evidence. Git records the small inputs, scripts, receipts, summary CSVs and figure; it is not a raw-output cloud backup.
