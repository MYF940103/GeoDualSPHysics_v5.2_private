# M3m MCC Boundary Geometry Refinement Plan

## Why M3m Is Needed

M3l shows that the remaining MCC return failures respond strongly to
platen/specimen interface geometry.  The `platen_overhang` diagnostic reduces
failed records from 1784 to 229 and reduces final negative statuses from 40 to
8, without changing the MCC return mapping or material parameters.

However, `platen_overhang` still has saved-frame `ReturnStatus=-3`, so it is
not a clean validation route.  M3m should refine boundary geometry rather than
return mapping.

## Option A: Refined Platen / Specimen Interface

Recommended first.

Candidate changes:

- retain modest platen overhang because it reduced failures substantially;
- tune platen radius and thickness as geometry, not as MCC parameter
  sensitivity;
- test a smoother platen/specimen contact buffer or transition layer;
- keep explicit top platen and fixed bottom platen;
- keep feedback off.

Success gate:

```text
all saved frames ReturnStatus=-3 = 0
all saved frames ReturnStatus=-1 not worse than M3l overhang
no fallback
reaction, p'-q, and pore pressure bounded
```

Risk:

- if overhang is too large, it becomes an artificial support blanket rather
  than a physically meaningful platen.

## Option B: Edge / Corner Geometry Refinement

Recommended second or combined with Option A if geometry edits are small.

Candidate changes:

- round or soften the top/bottom specimen edge;
- add an edge transition ring;
- avoid a sharp coincident cap/lateral/platen corner;
- keep edge particles excluded from strict measurement metrics while still
  diagnosing them.

Rationale:

M3k first `ReturnStatus=-3` appears at top edge/corner particles, and M3l
overhang reduces but does not remove that edge mode.

Risk:

- postprocessing edge exclusion alone does not fix the physical local path;
- geometry edits must be documented as reduced diagnostics unless they converge
  toward a reference-style specimen layout.

## Option C: Smooth / Fan-Like Specimen Layout

Recommended strict route if M3m interface and edge refinements still retain
negative statuses.

Candidate changes:

- regenerate the cylinder with smoother radial/fan-like particle layout;
- reduce cut-cell support anisotropy at the lateral/cap edge;
- keep explicit platen workflow;
- retest the same mild MCC feedback-off case.

Rationale:

This is closer to the smooth particle layouts emphasized in the Zhao-style
triaxial workflow and avoids relying on local selector exclusions.

Risk:

- higher setup cost;
- invalidates direct one-to-one comparison with the Cartesian/cut-cylinder
  reduced baseline.

## Option D: Stop Clean MCC Validation and Report Caveated Route

If geometry smoothing still fails or costs too much, stop trying to present a
clean MCC validation from this reduced cylinder.

The route can still be reported as:

- CPU-only MCC stress-update prototype;
- feedback-off;
- explicit-platen reduced diagnostic;
- pairwise reaction diagnostic available;
- boundary-induced return failures documented.

This is acceptable for engineering evidence, but not strict MCC validation.

## Recommended M3m Direction

Proceed with Option A plus a minimal Option B check:

1. start from `CaseM3l_PlatenOverhang`;
2. refine platen/specimen interface geometry without changing MCC parameters;
3. add one edge/corner smoothing diagnostic if XML/geometry allows it cleanly;
4. keep dense output around onset;
5. require no `-3`, no `-5`, and no new broad `-1` population before calling it
   a clean candidate.

Full pore-pressure feedback and GPU remain deferred.
