# M3f MCC Return Failure Cause Analysis

## Summary

M3f confirms that the remaining mild MCC failures are local return/staging
issues, not a global MCC implementation collapse.

All M3f CPU Release cases complete with:

```text
code=0
excluded=0
DtMin=0
PorePressureFeedback=0
```

The return failures are therefore constitutive diagnostics, not solver aborts.

## Is Failure Still Concentrated Near Bottom/Platen Regions?

Yes, but M3f shows a broader edge component than the M3d2 final-frame audit.
The original-rate baseline failures are concentrated in:

- edge rings;
- lateral boundary particles;
- bottom cap zone;
- adjacent interior particles near the bottom transition.

The quarter-speed diagnostic reduces the failed set to edge and bottom cap zone
only. This supports the interpretation that platen/edge local deformation is
the dominant trigger.

## Is Local Strain Increment Too Large?

Likely yes, but not as the only cause.

Evidence:

- half-speed loading clears the final negative status frame, although transient
  episodes remain;
- quarter-speed loading reduces bad frames from 22 in the baseline to 7;
- velocity and reaction remain bounded, so the problem is not macroscopic
  blow-up;
- the failures appear early and near geometric transition zones where local
  strain increments are expected to be less smooth.

The rate sensitivity here should be read as local integration sensitivity, not
as a new physical loading-rate law.

## Is p' Near the Tension Cutoff?

Partly. Early transient failures include many `ReturnStatus=-1` particles,
which indicates the local trial state approaches or crosses the admissible
`p'` margin. The final original-rate baseline problem is instead `-3`
line-search failure.

This means there are two related issues:

1. early local admissibility failures during the developing platen/contact
   strain pattern;
2. later line-search failures in a small bottom/edge-adjacent subset.

## Is pc Too Low or Hardening Too Fast?

The mild MCC setup is intentionally low-`pc` to trigger yield. The final mean
state remains bounded:

```text
baseline pc_mean ~= 119.63 Pa
baseline e_mean  ~= 0.80049
```

The state variables do not collapse globally. Low `pc` contributes to a
difficult return path, but the problem is local rather than a global hardening
law failure.

## Is the Return Line Search Insufficient?

Yes for the local boundary path. M3d2 already showed that raising
`MccReturnMaxIter` to 80 and tightening the tolerance to `1e-10` does not clean
the final failed set. M3f improved adaptive substepping at the tested
thresholds also does not clean it.

This points to a need for a more robust admissible Newton path or a better
local staging/strain path, not merely more iterations.

## Is Platen Boundary Deformation Concentration Involved?

Yes. Failed particles cluster in edge, bottom cap zone, and adjacent interior
regions. The explicit platen workflow is still reduced; it does not include a
full contact/platen constitutive treatment or true actuator reaction. The
local stress paths near the platen transition are therefore more severe than
the center measurement-core response.

## Does Smoother Loading Solve It?

No. The tested smoother platen ramp does not produce a clean candidate:

- original-rate ramp reduces final `-3` from 8 to 5 but introduces final
  `-1:4` and more bad frames;
- half-speed ramp is worse than half-speed without ramp in transient negative
  counts;
- ramp plus improved substepping remains non-clean.

Smoother loading alone is not sufficient.

## Does Improved Adaptive Substepping Solve It?

No for the tested M3f thresholds. Mode 2 is implemented and exposes trigger
diagnostics, but the tested original-rate mode 2 cases worsen return-status
counts relative to the baseline.

This does not mean substepping is useless. It means the current trigger and
local return path are not enough. A deeper return mapping improvement or a
different local admissibility projection is needed for clean validation.

## Are Curves Still Useful?

Yes, as reduced diagnostic curves only. Reaction, p'-q, pore pressure, `pc`,
void ratio, and plastic-strain histories are bounded and readable. They should
not be presented as clean MCC validation because all candidates retain
transient negative return statuses.

