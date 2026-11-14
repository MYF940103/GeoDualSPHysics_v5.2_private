# C08 private receiver-C/bare CPU implementation assets r1

Only author preparation of `support/c08_h18_lstar_cpu_r1.cpp`, its `_build.py`, and this note is authorized here. Neither mode has been built or executed by the author. Root must independently read all three and separately admit each build and each zero-advance component. No public source, XML interface, canonical program, PRE, native output, previous component or trajectory is modified. No GPU asset or physical window is admitted by this preparation.

## One private change, two closed modes

The full private `JSphCpu.cpp` comes from the already passed current schema2/law2 `outputs/c08_preload_schema2_source_r1/full_source.zip`, member `src/source/JSphCpu.cpp`. The builder preserves every decoded UTF-8 byte, including any BOM/newline outside the inserted block, and tests an exact reversible one-anchor transformation. It does not derive the physical TU from an older bedkeep/RV/centroid/free-surface candidate or the mutable public working tree.

The original dynamic-Darcy weight at archive CPU line3230 is

`w_old = Vj [d·(Gi+Gj)] / (r²+Eta²)`, with `Gi=Ci*g`, `Gj=Cj*g`.

The privately compiled ON branch is

`w_Lstar = Vj [d·(Gi+Gi)] / r²`.

The addition `Gi+Gi` and the shown scalar operation order are deliberate. The original positive-distance/support gate remains before division: self/zero-distance candidates are excluded by the unchanged `rr2<ALMOSTZERO` test. This removes the radial denominator regularization only in this already guarded pressure weight; it is not removal of matrix-rank guards or every use of Eta².

The macro `C08_H18_LSTAR_ON` is compile-time only, set to exactly0 or1 by the closed builder for both physical TU and entry. OFF contains the exact original weight expression. ON changes only the shared weight consumed by `LP+=w*dp` and `Lx+=d*w`. The original receiver-C `Gp`, acceleration-divergence `Da`, J-gradient, variable-k chain, FS/closed-surface formula, source-clock handling, force/AV, wall stage1/2, time-step gates, material return and all state layouts remain unchanged. No production/XML toggle is introduced.

The entry's independent same-neighbor `Assemble` has the same visible compile-time weight block. Its other expressions and all seven other generated includes are copied bytewise from the passed joint component. Actual Rate reconciliation still compares the real newly linked API output to the independently assembled formula; it never assigns the formula into Ratec.

## Reason for the candidate, and limits

The passed four-weight offline algebra review showed a large Eta-dominated reduction on the fixed manufactured N/X fields. It cannot resolve a fine ranking such as receiver-bare7.864 versus pair-bare8.88Pa/s when the independent source-FP enclosure is roughly123–126Pa/s near the bed and128–232Pa/s in the interior. This candidate is chosen because receiver-C/bare agrees with the constant-J/k, isotropic2D trace of Lian's Eq23 and uses the same receiver correction as Da, not because a small measured residual advantage is certified.

Actual tiny MLS wall-J departures, current C and current FS remain present. This is not the whole Lian pressure formulation, an exact polynomial reproduction theorem for arbitrary C/particle disorder, conservation/energy proof, or physical repair. The prior H1.2 pair-bare physical failure remains preserved and is a different candidate. No change is accepted from normal completion or a zero-step rate improvement alone.

## Original state route and actual calls

Reuse the passed `c08_h18_joint_darcy_probe_r1` lifecycle without adding calls: original P28–34 Restore/CellDivide, then radial P28–34,14 restores total. Only original P29/P30 each receive one true force; the other12 remain sorting-only. The current same-material Wendland H1.8 schema2 PRE is imported once by the existing source handoff, not regenerated. Original5000 soil/6805 total IDs and the original bedroles retire255/keepfalse contract are retained.

For each actual geometry, capture all defined original primary/C/FS and force scratch; ignored/inactive scratch is not read. For each H/N/X field restore the original state; set all temporary J=1, theta=0, velocity=0 and analytic stored p, refresh the original CSF/stage1/C/FS lifecycle, assign analytic soil Ace, then call the real mode-specific Darcy API once. The actual real-wall rate is independently assembled on all5000 soil nodes. For the analytic-ghost oracle change only fixed p/Ace while preserving actual J/C/FS/quadrature; no Darcy API is called and no generated rate is written into Ratec. Restore all defined state and scratch before the next field/state.

Thus each independently run mode performs2 actual bare forces,2 contained Darcy calls,6 manufactured Darcy calls,6 actual literal reconciliations and6 analytic-only literal evaluations. Total actual Darcy API calls8; output60000 manufactured rows,12 summaries,all active walls and2 selected exact clock rows. It performs no time update, PRE solve, material return, filter, RV, half-step or new native decode. The original5us necessary force/wave/pore/k-gradient gate is checked on the two actual bare states; it is not borrowed as an ON manufactured stability or future trajectory certificate.

## OFF and ON evidence are different

OFF requires all58 old external scalar bits per actual soil row:580000 total, including actual Darcy R, Ace, theta, FS, nine C components, six Rsigma components and all raw/corrected fluid/bound gradient/pass-theta controls. Literal theta10000 and Rsigma60000 checks remain separate. All30000 actual manufactured float rates must equal the mode-specific literal float bits and retain the original source arithmetic budgets; the30000 analytic-oracle rates remain explicitly generated values.

After all six streams are flushed and closed, OFF compares every byte and length of genuine `manufactured.csv`, `summary.csv`, `walls.csv`, `baseline.csv`, `restore_route.csv` and `selected_clocks.csv` against the sealed original joint outputs. Headers and body are compared as stored, with no rewrites or omission. The old `Run.out` and `completion.json` are deliberately excluded: they contain distinct program identity/counters and are not numerical control data. The OFF completion reports six matched files and actual byte total only after equality succeeds; any mismatch is a real preserved failure, not permission to weaken the comparison.

ON deliberately excludes only old R from the external bare control:57 scalar bits per row,570000 total. It retains all other actual state/force/gradient/C/theta/Rsigma controls unchanged. Its30000 real manufactured rate bits must equal the new receiver-C/bare literal formula, not the old pair-C/Eta rate. ON does not claim all six CSVs equal old data or that R is0ULP to the old API. Both modes preserve original float-commit, expanded arithmetic and donor-partition budgets; there is no5Pa trajectory/half threshold here. Signed clock/native safety requirements are inherited unchanged from the passed closed91 snapshots and original setup.

Outputs preserve the original six CSV schemas. Mode identity is in the distinct build/entry/completion and output path; completion adds `receiver_C_bare_enabled`, `external_CPU_rate_compared_to_old`, actual external scalar count and OFF byte-comparison counters. `total_mode_Darcy_API_calls` describes the actual eight calls to the selected private API. All retained P0/J/kappa/FS/ledger/clocks remain actual inputs or explicitly declared temporary manufactured fields; analytic output is not assigned a native truth label.

## Build closure and isolated execution contract

Separate closed modes and exclusive paths:

* OFF: `outputs/c08_h18_lstar_cpu_off_r1_build/C08H18LstarCpuR1.exe`, actual component output `outputs/c08_h18_lstar_cpu_off_r1`, first CLI token `--check-off`.
* ON: analogous `c08_h18_lstar_cpu_on_r1_build`, output `c08_h18_lstar_cpu_on_r1`, first CLI token `--check-on`.

Each mode links exactly87 objects:85 unchanged original physical objects, one newly compiled private JSphCpu object, one new entry. The original JSphCpu object is retained and bound as evidence but removed from this link. Original JSphCpuSingle, mDBC and material-law objects stay original. The physical compile recipe is parsed from the authoritative restored DebugCPU `CL.command.1.tlog` via the passed object inventory; the entry and link recipe are those of the passed joint component. Both preserve MSVC14.36, DebugCPU/MTd/Od/RTC1/fp:precise/OpenMP flags. Only source/output/include/dependency/mode tokens change. No GPU or original other physics TU is compiled.

All160 frozen headers are bound from the same archived root and their bytes checked against the full schema2 archive before compilation. Compiler dependency output must show that root, never public `src/source` headers. This prevents a law1/old-bedkeep StSoilCte, JSph or FunSoilMaterial header from silently mixing with law2 objects. Seven original runtime companions and resolved original libraries are retained. Actual tool Popen/Win32 exits are sealed by the existing owner-aware invocation helper. No SHA scan is introduced; existing stat bindings and the narrowly required reversible/header/CSV byte comparisons serve explicit implementation questions.

After full independent review, root may admit exactly one build at a time:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_lstar_cpu_r1_build.py --mode off --execution-authorized`

Then, in a separately admitted owner call, the OFF executable may receive `--check-off -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1 ORIGINAL_AS03_SHORT_SEED FRESH_OFF_OUT`. ON uses its own separately admitted build, executable and `--check-on`/output. Builder only compiles/links its selected mode and never invokes a program, prepares the other mode or chains any later action. Existing output/call/receipt paths are exclusive; failure preserves the first error and partials without retry or overwrite. Neither mode implies GPU admission, physical acceptance, source merge, production interface or a new receiver window.
