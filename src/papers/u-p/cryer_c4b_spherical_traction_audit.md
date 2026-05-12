# Cryer C4-B Spherical Traction Audit

Date: 2026-05-12

## Objective

Strict Cryer reproduction requires a uniform all-around inward normal traction
`p0` on the spherical exterior. This audit checks whether the current
DualSPHysics / GeoDualSPHysics XML and source mechanisms can express that load
without new source development.

No GenCase, CPU, GPU, or PartVTK run was performed.

## Strict Cryer Traction Requirement

The loading needed for the analytical Cryer benchmark is:

- spherical exterior surface at `r=a`;
- uniform traction magnitude `p0`;
- direction equal to the inward normal, `-n = -(x-center)/|x-center|`;
- conversion to particle force through an associated boundary area;
- no net resultant force by symmetry;
- no body-force interpretation;
- no top-only loading;
- no change to `HydraulicGravity`;
- compatible with `SoilConstitutiveModel=0`;
- compatible with a future drained curved hydraulic boundary.

The traction is a surface boundary condition. A Cartesian acceleration, a
gravity load, a top layer load, or prescribed displacement is not equivalent.

## Existing Mechanisms

| Mechanism | Source / XML evidence | Cryer suitability |
|---|---|---|
| `AccInput` | `JDsAccInput` reads `<accinputs><accinput mkfluid|mkbound=...>` and applies `acclin` / `accang` to selected markers. CPU uses `JDsAccInput::RunCpu`; GPU uses `JDsAccInput::RunGpu` and `cuaccin::AddAccInput`. | Not strict. It applies marker-wise linear/angular acceleration, not a pressure traction with per-particle radial normal and area weighting. |
| Floating `linearforce` / `angularforce` | `JCasePartBlock_Floating` reads `<linearforce>` and `<angularforce>`; `JSph` stores `FtLinearForce` / `FtAngularForce`. | Not strict for the soil sphere. It is a rigid/floating-body total force route, not a deformable poroelastic material surface traction. |
| Prescribed motion | Existing `<motion>` routes and moving boundary updates prescribe displacement/velocity/acceleration of boundary particles. | Not strict. A displacement-control surrogate changes the Cryer boundary condition. |
| mDBC / cDBC normals | Boundary normals are generated/used for mDBC/cDBC extrapolation and geometry handling. | Useful geometry information, but not an external traction input route. There is no current XML path mapping `p0` to normal mechanical force on a spherical material boundary. |
| Chrono / MoorDyn / forcepoints | Existing special routes target rigid bodies, moorings, and coupled objects. | Not suitable as a direct material traction boundary for the poroelastic sphere. |
| Postprocessing `ComputeForces` | Example BATs use `ComputeForces` after a run. | Postprocessing only; it cannot impose the Cryer traction. |

## AccInput Finding

`AccInput` is valuable for the 1D external-load baseline because the load is
applied to a marker layer in a single direction. It is not a strict Cryer
traction route:

- `acclin` is uniform for every selected particle;
- angular acceleration terms represent rigid-body acceleration about
  `acccentre`;
- there is no local surface normal input;
- there is no particle area estimate;
- the resulting force is mass-proportional rather than surface-area
  proportional.

Using `AccInput` for a spherical shell would create a body-acceleration or
rigid-acceleration surrogate, not a uniform all-around surface pressure `p0`.

## Boundary Particle / mDBC Finding

mDBC/cDBC provide boundary particles and normal data for mechanical boundary
conditions and extrapolated density/velocity/pressure-like hydrodynamic data.
The current audited source does not expose a native XML option such as
`normalpressure`, `surfacepressure`, `traction`, or equivalent for applying a
uniform radial pressure to a selected spherical boundary. Existing normals could
be useful for a future implementation, but they are not presently connected to a
mechanical traction load for u-pw material particles.

## Floating Force Finding

Floating-body `<linearforce>` and `<angularforce>` are total rigid-body force
inputs. Even if a spherical shell were represented as a floating object, that
would apply a total force/torque to a rigid body. Cryer requires a deformable
poroelastic sphere with a distributed normal traction on its exterior. A
floating route would also raise mass/inertia and contact-coupling issues that
are outside the analytical benchmark.

## Prescribed Motion Finding

Moving a spherical shell inward can compress the soil, but it imposes a
kinematic boundary. The Cryer analytical solution assumes traction `p0`, not
prescribed displacement. This may be useful as a separate surrogate diagnostic,
but not as a strict Figure 7B reproduction.

## Existing XML Support Verdict

No existing native XML mechanism was found that can directly impose:

```text
force_i = -p0 * area_i * normal_i
```

on selected particles of a spherical exterior, with local radial normals and
surface-area weights.

Therefore, strict Cryer traction is currently a source-development blocker.

## Candidate Implementation Routes

### Route 1: Existing Native Route

Status: not found.

This would have been preferred if a boundary-pressure or normal-traction XML
route already existed. Current evidence does not support this path.

### Route 2: XML-Defined Spherical / Radial Traction

Recommended if strict Cryer proceeds.

Minimal CPU-first feature:

- new XML-controlled generic radial traction block, not named `TopLoad`;
- target selected `mkfluid` or boundary/surface marker;
- center `(x,y,z)`;
- radius / tolerance or marker-selected shell;
- magnitude `p0`;
- optional start/end/ramp;
- apply mechanical acceleration/force only;
- keep `HydraulicGravity` unchanged;
- diagnostics for net force, radial direction error, and area weighting.

This route can be generic enough for future radial loading, while remaining
minimal and disabled unless explicitly requested.

### Route 3: Equivalent Radial Acceleration on a Shell

Possible reduced smoke only.

It is easier than area-weighted traction, but it is mass-weighted and depends on
shell particle mass. It should not be used for strict Cryer comparison.

### Route 4: Prescribed Displacement Boundary

Possible surrogate only.

It can produce compression, but it changes the boundary condition from traction
to displacement. It should not be used as the strict Cryer target.

## Recommendation

Proceed CPU-first with Route 2 only after the drained curved boundary decision
is documented. Do not use AccInput, gravity, top load, floating total force, or
prescribed displacement as a strict Cryer traction substitute.

Strict Cryer simulation should remain paused until the traction route and
drained curved pore-pressure boundary are both resolved.
