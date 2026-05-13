# Zhao Flexible Confined Boundary Conditions - Implementation Review

Source converted text: [zhao_flexible_confined_boundary_conditions_sph.md](zhao_flexible_confined_boundary_conditions_sph.md)

## Core Idea

Zhao et al. propose applying flexible confining pressure in SPH without explicitly tracking boundary particles, normals, or surface area. The method adds an isotropic confining-pressure pair term to the SPH momentum equation. For a constant confining pressure field, this term cancels in the domain interior when the kernel support is complete. Near a free or open boundary, kernel truncation makes the same term nonzero and produces an inward traction normal to the truncated surface.

In compact implementation form, the extra acceleration is:

```text
a_i^conf = sum_j m_j * (sigma_c_i + sigma_c_j) / (rho_i * rho_j) * grad_i W^R_ij
```

where `W^R` is the renormalized kernel gradient used by the paper. If `sigma_c` is constant, the interior contribution should vanish and only the boundary layer should feel the confining traction.

## Important Details From The Paper

- The method relies on kernel truncation at free/open boundaries to infer the surface normal and effective surface area implicitly.
- No dummy boundary particles are needed for the confining traction.
- No explicit surface normal or curvature tracking is needed.
- Positive confining pressure is applied as a hydrostatic compression field assigned to the material particles.
- The paper recommends a smooth particle layout for circular/cylindrical specimens; fan-shaped layouts reduce boundary roughness compared with orthogonal cut cells.
- For large deformation, Zhao et al. do not simply apply the confining term everywhere. They identify near-boundary particles using a kernel-sum index:

```text
f_i = sum_j (m_j / rho_j) * W_ij
```

and apply the confining term only to particles judged to be on or close to the free boundary. The reported empirical thresholds are about `f_i <= 0.55` in 2D and `f_i <= 0.70` in 3D.

- The paper also rescales the confining term during large deformation to compensate for smoothing-length/particle-spacing changes. This is described as a way to maintain the confinement magnitude when particle separation evolves.
- Sudden confining loading can launch stress waves; the verification example uses viscous damping unless the equivalent hydrostatic initial stress is already imposed.

## Relation To Current Branch

The current branch already has a CPU-only `FlexibleConfiningStress` path. It adds an isotropic stress-like pair contribution in the CPU momentum loop and keeps GPU as a hard-error path. This is directionally aligned with Zhao's Equation 51.

However, the current implementation appears to be an early/conservative version:

- It uses the existing pair gradient in `JSphCpu::InteractionForcesFluid`.
- It applies the confining pair contribution to selected material pairs through `ConfiningStressTargetMk`.
- It does not yet implement Zhao's kernel-sum free-boundary indicator `f_i`.
- It does not yet implement the large-deformation rescaling using the initial/current confining term magnitude.
- It does not yet expose a specimen-side/lateral-surface selection suitable for strict cylindrical triaxial confinement.
- It does not initialize the material stress tensor to the imposed hydrostatic confining state; it adds only the traction-like pair contribution.

## Implications For Strict Triaxial Compression

For strict triaxial compression, this method is the right mechanical route for lateral flexible confinement, but the implementation should be upgraded carefully:

1. Add a boundary-layer selector based on the kernel-sum completeness index `f_i`.
2. In 3D, start with Zhao's `f_i <= 0.70` as a diagnostic threshold, not a final calibrated constant.
3. Restrict confinement to the lateral membrane/free surface, not the top/bottom loading platens.
4. Use a cylindrical/fan-like particle cloud or another smooth boundary generation route; rough cut-cell cylinder surfaces will directly pollute the implicit normal/area.
5. Decide whether the confining pressure should also initialize the stress tensor hydrostatically before axial loading.
6. Use damping or ramping during the isotropic loading stage to avoid stress-wave contamination.
7. Add diagnostics for boundary-layer particle count, kernel-sum distribution, net confining force, radial/lateral acceleration, and axial leakage near caps.
8. Keep GPU deferred until CPU behavior is validated.

## Recommended Next Step

Before implementing strict triaxial confinement, run a CPU source audit specifically against Zhao's method:

- compare current `FlexibleConfiningStress` with Zhao's Equation 51;
- determine whether the existing gradient should be renormalized for this term;
- add the `f_i` boundary-layer diagnostic without changing behavior first;
- design lateral-only selection for a cylinder;
- only then add the actual flexible confinement update for the T2/T3 triaxial workflow.

This should be treated as a mechanical boundary feature, separate from the Cryer drained pore-pressure boundary work.
