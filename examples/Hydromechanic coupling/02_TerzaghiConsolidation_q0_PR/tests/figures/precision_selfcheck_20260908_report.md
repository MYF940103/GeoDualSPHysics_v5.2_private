# q0 pore-pressure precision comparison

Status: PARTIAL / not a final acceptance

SELF-CHECK: both inputs are the same historical result; this is not a precision-patch result.

Generated XML physical and numerical settings match (output-only timeout segments are excluded). k=0.0001 m/s, dp=0.01 m, dt=1e-05 s, H=1 m, q0=10000 Pa.
E=2e+06 Pa, nu=0.3, n=0.3, Kw=2e+08 Pa. M=2692307.69231 Pa, cv=0.0274445228574 m2/s.
Tv=cv*(t-tD)/H^2, with tD=tL. g_ref=9.81 m/s2 is the conductivity-to-pressure conversion reference; simulation gravity is zero.

| Quantity | Baseline | Current |
|---|---:|---:|
| time_s | 72.87429 | 72.87429 |
| tv | 1.999725672 | 1.999725672 |
| n_particles | 1000 | 1000 |
| mean_excess_pa | 536.9760243 | 536.9760243 |
| mean_theory_pa | 58.33468274 | 58.33468274 |
| u_num | 0.9463023976 | 0.9463023976 |
| u_theory | 0.9941665317 | 0.9941665317 |
| settlement_mm | 4.293811321 | 4.293811321 |
| settlement_theory_mm | 3.692618546 | 3.692618546 |
| max_speed_m_s | 1.638822886e-05 | 1.638822886e-05 |

Final values refer to each last saved snapshot, not to an invented snapshot at exact Tv=2.
Run.out supplies actual times (printed to six decimal places); Part_0000 is time zero. The solver can stop slightly after its last scheduled PART output.

## Historical input A

Input: `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\CaseTerzaghiConsolidation_q0_PR_full_k1em4_out`
Generated XML: `CaseTerzaghiConsolidation_q0_PR_full_k1em4.xml`
Run.csv version: `ha4lo86y-DualSPHysics5 v5.2.274 (02-02-2024)`; date: `08-07-2026 01:31:21`.
Hardware/run mode: `CPU` / `CellsFull - Pos-Double - OpenMP(Threads:4)`.
Snapshots: 401; particles per snapshot: 1000 (verified all snapshots).
Simulation runtime: 19077.048828 s; solver physical end time: 72.884290 s.
Final U error: -0.04786413416; mean-pressure error: 478.6413416 Pa.
Least-squares mean-pressure slope over available Tv>=1: -57.26055238 Pa/Tv.
Last target Tv=2, actual Tv=1.999725672: profile RMSE=525.3958053 Pa; bottom pressure=802.3711426 Pa.
Run.out SHA256: `8643dfc62ca62b1e4682817a600be6bd11bf93331aac9119f214f5f4bd065b4c`
Generated XML SHA256: `bce483ad4bf65fe7a4e84feaa7ff8f2ffd7a2a588a7702e25dbe4e63639e7605`

## Same historical input B

Input: `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling\02_TerzaghiConsolidation_q0_PR\CaseTerzaghiConsolidation_q0_PR_full_k1em4_out`
Generated XML: `CaseTerzaghiConsolidation_q0_PR_full_k1em4.xml`
Run.csv version: `ha4lo86y-DualSPHysics5 v5.2.274 (02-02-2024)`; date: `08-07-2026 01:31:21`.
Hardware/run mode: `CPU` / `CellsFull - Pos-Double - OpenMP(Threads:4)`.
Snapshots: 401; particles per snapshot: 1000 (verified all snapshots).
Simulation runtime: 19077.048828 s; solver physical end time: 72.884290 s.
Final U error: -0.04786413416; mean-pressure error: 478.6413416 Pa.
Least-squares mean-pressure slope over available Tv>=1: -57.26055238 Pa/Tv.
Last target Tv=2, actual Tv=1.999725672: profile RMSE=525.3958053 Pa; bottom pressure=802.3711426 Pa.
Run.out SHA256: `8643dfc62ca62b1e4682817a600be6bd11bf93331aac9119f214f5f4bd065b4c`
Generated XML SHA256: `bce483ad4bf65fe7a4e84feaa7ff8f2ffd7a2a588a7702e25dbe4e63639e7605`

## Interpretation limits

A comparison with a historical executable does not isolate the precision patch. The retained July result predates subsequent u-pw source changes, including pore-pressure mDBC handling. Identical XML and a shared version banner do not prove identical solver source. A same-source unpatched control is needed before assigning the whole improvement to compensated accumulation.
Simulation times are reported for traceability, not as a speedup: compiler/build, hardware load, OpenMP scheduling and executable revisions may differ.
The analytic curve is classical incompressible-water, small-strain Terzaghi theory with an ideal initial q0 field at drainage opening. The numerical model has finite Kw, a load ramp and moving particles. It is a physical accuracy reference rather than an exact solution of every discrete equation.
Finite-water storage indicator n*M/Kw=0.004038461538; no finite-Kw correction has been silently substituted into the historical reference.
Mean pressure uses the same arithmetic mean of the soil particles as the historical analysis. Profiles are averaged in dp-wide current-z layers; settlement follows the mean top layer. No initial high-pressure snapshot is fabricated before the first saved post-load output.
