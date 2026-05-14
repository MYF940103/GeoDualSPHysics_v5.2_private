# L3 1D Consolidation Top Load Literature Audit

## Scope

This audit reinterprets the L2 external-load 1D consolidation result against
the u-pw notes and extracted paper text.  The goal is to decide whether the
current `AccInput` top-layer route is a paper-faithful representation of the
Terzaghi surcharge `q0=-10 kPa`, and to identify the smallest route that can
separate pressure diffusion from mechanical loading artifacts.

## Paper / Notes Setup

The local u-pw notes list the 1D Terzaghi setup as:

| Quantity | Value |
| --- | ---: |
| Height | `H = 1.0 m` |
| Width | `0.1 m` |
| Particle spacing | `Delta = 0.01 m` |
| Young modulus | `E = 2e6 Pa` |
| Poisson ratio | `nu = 0.3` |
| Water bulk modulus | `K_w = 2e8 Pa` |
| Porosity | `n = 0.3` |
| Hydraulic conductivity | `k = 1e-3 m/s` |
| Top hydraulic boundary | drained / zero pore pressure |
| Bottom and lateral hydraulic boundaries | undrained / no-flux |
| Top load | `q0 = -10 kPa` |

The extracted paper text says the external load is applied to free-surface
particles as an equivalent acceleration.  That is an implementation detail in
the paper extraction, but the continuum benchmark and analytical comparison are
still the standard Terzaghi problem: a surface surcharge generates an initial
undrained excess pore pressure field which then dissipates through the drained
top boundary.

## Required Answers

1. **Meaning of `q0=-10 kPa`**

   In the continuum benchmark, `q0` is a top surface surcharge / mechanical
   load.  For the analytical Terzaghi comparison it is equivalent to an
   initially uniform excess pore pressure `p_w^0 = |q0|` after instantaneous
   undrained loading.

2. **Surface traction, loading plate, or equivalent initial pressure?**

   The physical boundary is a top surface load.  Numerically, it can be
   represented by a loading plate or traction boundary.  For a diffusion-only
   analytical gate, it can also be represented by an initial excess pore
   pressure field.  The current L2 `AccInput` route is a reduced implementation
   of the paper's "equivalent acceleration" wording, but it is not a strict
   quasi-static surface traction.

3. **Instantaneous or ramped loading?**

   The analytical Terzaghi series assumes the load-generated initial excess
   pressure exists at `t=0` and drainage starts immediately.  The notes do not
   provide a paper-level load ramp.  L2 added a ramp to reduce dynamic shock,
   which makes it a staging approximation rather than the analytical initial
   condition.

4. **Analytical initial condition**

   The analytical solution assumes an initial excess pore pressure profile
   consistent with the applied surcharge, usually uniform in the saturated 1D
   column, with the top drained boundary enforcing zero excess at the drained
   boundary.

5. **Top drained and top load together**

   They are different boundary conditions on different fields.  The top
   mechanical boundary carries the surcharge; the top hydraulic boundary
   enforces zero pore pressure/excess pressure.  The analytical solution permits
   the resulting near-surface discontinuity at the start of drainage.

6. **Bottom and lateral undrained**

   Bottom and lateral boundaries impose no hydraulic flux.  The current 1D XML
   uses an x-periodic narrow column, which avoids an explicit lateral hydraulic
   boundary and leaves the bottom layer correction as the primary no-flux
   approximation.

7. **Difference between `AccInput` and `q0`**

   `AccInput` adds body acceleration to selected particles.  It is mass- and
   layer-thickness-dependent, applies through the momentum equation over a
   finite material layer, and can excite stress waves.  A surface traction or
   loading plate applies a boundary load/reaction at the surface.  The
   analytical initial-pressure route bypasses the mechanical wave-generation
   stage entirely and directly tests diffusion.

8. **Why AccInput excites strong dynamics**

   A large acceleration on the top material layer perturbs velocities and
   `DivVel`.  With the explicit PR update, the term `K_w/n * DivVel` can create
   large pore-pressure rates.  When pressure feedback is enabled this feeds back
   into acceleration, but even without perfect feedback stability the finite
   accelerated layer is not equivalent to a quasi-static surcharge.  L2's
   `~6.25e5 Pa` excess peak is the signature of this route mismatch.

## Implication

For L3, the most faithful first step is not a damping sweep.  It is a route
split:

- use initial excess pressure as an analytical diffusion gate for PR and
  hydraulic boundaries;
- design a separate mechanical surface-load/plate route for load-generation
  validation.
