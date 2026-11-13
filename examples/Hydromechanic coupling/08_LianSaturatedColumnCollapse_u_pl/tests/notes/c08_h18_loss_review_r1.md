# Failed H1.8 source: offline loss review (author only)

New files only: `support/c08_h18_loss_review_r1.py` and this note. No native
reader, solver, GenCase, VTK, analysis, build, Git, SHA scan or notifier is run
by authoring. Existing source inputs, programs, payloads and receipts stay
unchanged. Root must fully read the script and the new forensic native adapter
before one explicit offline invocation.

The actual source is only `c08_h18_plastic_psi0_pre_r1`. Its process exits0 but
the physical plan fails: Part0533 at reported5.322720s/completed1064544 has
one position-excluded particle,534 native saves total. It is not the requested
10s/2M/1001 source and cannot be certified or used as PRE. The owner field
`solver_completed:true` means the executable returned; this review reports
the whole run as failed. It does not edit that original field or any receipt.

CLI after one separate completed forensic read:

```text
python -X utf8 -B support/c08_h18_loss_review_r1.py --manifest PATH --execution-authorized
```

Manifest requires `tag`, `native_dir`, `native_call`, `material_csv`, `plan`,
`run`, `input_xml`, `excluded_csv`. Paths are absolute or relative to C08 root.
`excluded_csv` is root's separately generated PartVTKOut CSV identifying3060;
it is compared with the native adapter's independently read excluded record.
No manifest or passed runtime qualification is fabricated by this author.

The native stage is explicitly `c08_h18_loss_native_r1`; it is not relabelled
as the earlier plastic-source stage. Its `prefix` contains533 complete original
7060-ID states (parts0..532) and all original22 arrays/212bytes, clocks, actual-
kappa yield summaries and strict original native budgets. The complete1001-row
launch plan remains unchanged. Separate final Part533 has7059 actual particles
in original array order, one missing nativeID3060, a genuine one-state typed22
header, actual scalar clock/step/signed diagnostic and actual PartOut record.
It is not padded, sorted into a false full domain, appended to the fixed-ID
payload or declared equivalent to the planned5.33s output.

The adapter expects `OUT/prefix/{completion.json,typed22.bin,typed22_layout.csv,
clocks.csv,summary.csv}` plus `OUT/completion.json`, `final_part533.json`,
`final_part533_typed22.bin`, `final_part533_layout.csv` and `excluded.csv`.
Final metadata uses `part`, `completed_step`, `saved_step`, `time_s`, `dt_s`,
`signed_dterror_s`, `native_ID_domain`, `present_IDs`, `missing_ids`. Prefix
completion retains the source's original count/ledger/history/clock fields,
with stage `c08_h18_loss_native_r1.strict_prefix` and truthful partial flags.

An additional descriptive comparison reads the retained strict-elastic
`c08_h18_bedroles_pre_r1/native_partial_r1` with its actual successful reader and
failed source receipts. It compares all208 complete actual-time records against
the new533-record prefix: all22 native payload fields including each record's
time, plus raw clock rows including signed diagnostic. The original binary
header counts208/533 and CSV headers are preserved; no header rewriting,
interpolation, omitted records or equivalence threshold is applied. A mismatch
records its first part, field and affected IDs but does not relax any gate or
trigger a rerun. This is not theory accuracy or a new half-step chain.

Actual source call/handle exits, program/build/source captures, generated XML,
CSV material values and untouched launch plan are bound by stat entries. No
recursive source or payload hashing is used. Original start/call evidence is
not rewritten. All533 complete prefix states are analyzed with the unchanged
`c08_h18_compare_r2.read22/analyze_case`; `reference_from` is deliberately not
called because this partial cannot become a receiver reference. The source
plots are reused from the new plastic review, with readable kPa axes and actual
source time t, not release tau. The final partial-ID population is exported and
plotted separately rather than mixed into5000-particle constant-material means.

Additional diagnostics keep lostID3060 plus its eight nearest initial x/z
material neighbours. Selection uses initial position only, with equal-distance
ties resolved by original ID order. Every genuine prefix frame and the separate
final frame gets nearest-neighbour/pairs r<.7dp statistics and counts of saved
soil positions below z=0. First saved below-bed and near-pair observations are
reported as observations, not inferred unsaved crossing/fault times. Missing3060
at final has explicit `present:false` and empty fields; the actual excluded
record is distinct. No interpolation, fitting, clipping, smoothing, phase
correction or new physical gate is introduced.

New outputs remain shallow under `tests/figures/TAG_*`: all prefix pressure,
stress, velocity/energy, settlement, J/n/rho/k/kappa histories, extrema, fifty
original100-ID layer profiles and old focus tracks; additional lost-neighbour
tracks, geometry histories, excluded record and all7059 final present particles;
three prefix PNGs and one loss PNG. Matching CSV values retain native units.
Absolute p and native float(p-fixed initial P0) remain distinct; the latter is
not established as the paper's unique excess-pressure definition. Kappa is the
model scalar history, not a full plastic-strain tensor. KE/pressure quadratics
are not a complete coupled energy or conservation proof.

The new check records `analysis_complete`, all534 frames accounted for and a
pending visual review, while `whole_run_passed`, `certified_PRE`, equilibrium
and physical acceptance remain false. It launches no decoder, physical job,
half chain, receiver, other-psi run, continuation or notifier. Analysis failure
preserves any new partial artifacts and never permits a physical rerun.
