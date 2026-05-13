# T4b Triaxial Output Enhancement Plan

## Reason

T4 confirmed that the current triaxial postprocessing can generate useful
diagnostic curves, but the `p'-q` path is still a proxy. T4b keeps output
enhancement as a plan rather than adding broad new output fields, because the
main instability is still in the reduced dynamic loading/confinement response.

## Fields Needed for Strict Stress-Path Validation

| Field | Current status | Need |
| --- | --- | --- |
| `mkfluid` / material block | not written in `PartCsv` | Required to separate load layer, specimen core, lateral membrane candidates, caps, and measurement regions without geometry guessing. |
| Original position | not written | Required for displacement and strain based on particle identity instead of frame geometry proxies. |
| Displacement | not written | Useful for axial strain, radial strain, and visual checks. Can be derived if original position is written. |
| Effective stress tensor | `Sigma` is written but not explicitly labelled | Required to make `p'` strict. |
| Total stress tensor | not written | Required if comparison uses total stress or if pore pressure needs to be combined with skeleton stress. |
| Stress convention flag | not written | Required to avoid ambiguity about compression sign and total/effective convention. |
| Pore pressure | written | Already available as `PorePress` and `ExcessPorePress`. |
| `f_i` | not written per particle | Useful for selector diagnostics and comparing surface truncation with confinement response. |
| Cylinder class | not written per particle | Useful for class-specific leakage, lateral response, and measurement masks. |
| Measurement region tag | not written | Useful after measurement definitions stabilize. For now, keep in scripts. |
| Axial strain/deformation proxy | not written | Could be output as a global gauge later; not necessary until loading is stable. |

## Minimal T4c Proposal

T4c should add only low-risk output support:

1. Write `mk` or equivalent material block identifier to CSV/VTK output.
2. Optionally write original position or displacement when enabled by an
   execution parameter.
3. Document whether `Sigma` is the skeleton/effective stress state and its sign
   convention.
4. Defer total-stress output until the strict stress convention is agreed.
5. Defer per-particle `f_i` and cylinder class output until the confinement
   selector route is stable enough to justify permanent fields.

This keeps T4c focused on postprocessing credibility without broadening the
physics implementation.
