# Pressure-only endpoint work: read-only feasibility audit

2026-11-17. Design reserve only, not an implementation or admission. The running
P3 owner, source, program and dependencies were not operated on or modified.
No profiler, script main, solver, build, reader, hardware test or hash scan ran.
Only this new note is written. The complete current R_gamma remains qualification
truth and cannot be replaced by this audit or by P3's pending physical result.

## Inspected baseline and scope

Anchors below use `tests/outputs/upl_tpi_m0_dt_GPU_r2_source` (GPU) and
`tests/outputs/upl_tpi_m0_dt_CPU_r2_source` (CPU). CPU's named physical pair,
dynamic-wall and complete-rate function texts were also compared read-only with
the frozen P2 counterparts; this is not a claim that whole CPP files are identical.
P2/P3 change host pressure transactions, not these physical spatial equations.
No active P3 source/program/process was needed for this audit.

Current C02 qualifiers (`JSphGpuSingle.cpp1159–1175`) are constant k, elastic
material, fixed-wall dynamic closure, periodic X, FreeSlip/SPR, AV.1/HG.1/damping.04,
Wendland, no AS/shifting/filters/DEM/motion, and zero gravity. A cache is valid
only within the endpoint iterations of one already committed mechanical/J state:
full x/v/rho/sigma/kappa/J, owner/slot/neighbor order, C/FS/normal/masks and source
clock must remain fixed. The next mechanical update/RunCellDivide invalidates it.
Half-stage coefficients cannot substitute for full-stage coefficients. This is
not a C08 plastic/AS/contact, Cryer3D free-body, or general-boundary qualification;
the separate free-body exterior/load closure needs its own audit.

## Complete operator and its pressure dependence

GPU `JSphGpu_ker.cu1575–1656` (CPU `JSphCpu.cpp4409–4501`) computes, schematically,
with all sums taken in their existing order:

```text
Vj = V0*Jj, gi = Ci*gradW, gj = Cj*gradW
wij = Vj * dij dot (gi+gj) / (rij^2+eta^2)
LP = sum(wij*(pi-pj))
Lx = sum(dij*wij)
gp = -sum(gi*Vj*(pi-pj))
Da = sum(Vj*(aj-ai) dot gi)

closed free surface:
  gpcorr = gp - n * [n dot (gp+rho_w*ai)]/(n dot n)
otherwise: gpcorr = gp

lap = LP - gpcorr dot Lx + rho_w*Da
R_gamma = -gamma*theta + k*lap
S = -k*sum(wij)                # leading LP only, not the full Jacobian
```

The current velocity/geometry/J state fixes theta during endpoint iterations.
At fixed masks/geometric fits, pressure wall reconstruction and total acceleration
are affine in pressure in real arithmetic, so R_gamma is also affine there. This
does not prove that rounded GPU/CPU implementations are the same affine map, that
its iteration is contractive, or that its real boundary operator has a particular
spectrum. Native pressure floats, rejected states and pressure-dependent rounding
still matter. The variable-k chain at GPU1643–1649 is outside current qualification.

## Cache/fresh inventory with source anchors

| Item | Within one fixed endpoint | Actual source / restriction |
|---|---|---|
| Native ID ownership, cell/neighbor order, geometry/J volumes, raw momentum gradients | Cache candidates, invalidated on divide/sort/owner change | GPU pair2042–2055 and2085; never infer stable slots just from unchanged counts. |
| Darcy C_i/C_j, weights, Lx, sum(w), S | Mathematically fixed; original precision/order still needs proof | GPU1596–1618; CPU4464–4467. Do not substitute momentum's raw gradient for corrected Darcy gradients. |
| Full-endpoint theta, current n/rho and k | Cache candidates under these exact qualifiers | GPU2200–2205 and2521; CPU2569–2575. Keep the full endpoint theta distinct from theta_half used for the once-only J integration. |
| Wall-fit geometry, moment/inverse, nearest sample and active/rank branch | Cache candidates if owners/geometry/J unchanged | GPU1492–1532; CPU1643–1744. Cache actual original fit, not a newly fitted wall or new coefficients. |
| Wall J/sigma/velocity/derivative velocity and wall C | Pressure-independent in this restricted fixed state | GPU1468–1476,1534–1549; CPU4259–4278. Their repeated values may be cached only with original stores and guard domain preserved. |
| Wall pressure | Must refresh from the current p every round | GPU1470,1539; CPU4259–4278. It is a hydraulic ghost, not a fixed assigned pressure. |
| FS classification/normal and source-time drained/closed masks | Fixed within one endpoint; event/source policy remains exact | GPU1142–1153 in `JSphGpu.cpp`; kernel1048–1064. Pre-open/event timing and true +0 projection cannot be changed. |
| Periodic pressure and acceleration images | Must refresh from current native values | GPU `JSphGpu.cpp1843–1860,1876,1884`. C/ownership may be cached only with a valid generation and original roles. Periodic X is active in C02. |
| LP and gp | Must refresh each round | GPU1615–1619 / CPU4464–4467. Reading an old pressure difference changes the method. |
| Native total acceleration a(p) | Must refresh pressure-dependent part each round | GPU2101–2110 / CPU2473–2481; includes skeleton stress plus current p, source loads, AV, damping and readonly HG. |
| Wall/ghost acceleration | Must refresh from that current total acceleration | GPU `JSphGpu.cpp1877`, kernel1477,1551–1554; CPU4308–4316. An immobile wall does not imply its hydraulic ghost acceleration is zero. |
| Da and closed-FS Neumann correction | Must refresh using current native and ghost acceleration | GPU1624–1640 / CPU4469–4486. Updating LP while freezing these is not the complete R_gamma. |
| Native legacy PorePressRate diagnostic | Must preserve current complete last-row evaluation | GPU1641,1656 / CPU4499–4501. Do not replace its arithmetic with `Kw/(n*gamma)*R_gamma` or call it dp/dt. |

## Pressure-independent acceleration sources are not freely reorderable

`JSphGpuSingle.cpp699–766` orders dynamic wall/FS setup, BC, direct load, original
pair loop, damping, top-band normalization, readonly HG, 2D Y reset and complete
Darcy rate. CPU's matching order is `JSphCpuSingle.cpp754–821`. The current endpoint
has no second material/J/HG history update, but the full interaction still repeats
velocity-gradient/stress-rate/density scratch calculations it later discards.

For the present fixed state, skeleton effective stress, AV and its limiter,
damping, readonly HG history/current-J mass scale and external load are
pressure-independent in real arithmetic. The load uses the same original
TimeStep in all rounds: GPU `JSphGpu.cpp1202–1230`, pair2121–2127; CPU1255–1318.
Top-band redistribution must retain its actual add/subtract ordering (CPU1317),
not just a cached integrated resultant. Damping's original float subtraction is
GPU701–716 / CPU3008–3025. HG's acceleration addition is numerical, not a log;
it remains at its original post-load stage using the committed history/J.

Current gravity is exactly zero. More generally Ace used by this dynamic-rate
closure is the existing force acceleration, not an arbitrary acceleration with
body gravity added. The Neumann comment explicitly says it excludes body gravity
(GPU1635); wall1554 uses its particular reflection identity. A pressure-only path
must preserve that convention and gamma=rho_w*9.80665, not invent a new gravity
source or silently reuse the older static-pressure head branch. Stateful external
providers, moving walls, DEM, AS/contact switching and nonlinear pressure controls
need a separate audit and are not covered by this frozen-state argument.

## Main obstacle: algebraic splitting is not floating-point equivalence

GPU momentum uses float PosCell differences and raw float gradients
(`JSphGpu_ker.cu2043–2055`), while Darcy uses double Posxy/z differences, a float
kernel factor and corrected double gradients (1607–1616). A shared generic neighbor
matrix is therefore not automatically the actual pair operator: even support-edge
selection and roundoff can differ. Keep both original representations/orders.

With J feedback the pair first combines sigma' and `(pi+pj)` in double, then casts
each acceleration contribution to float and accumulates it (2103–2110). AV is
added in the same per-neighbor loop (2330–2331). CPU2473–2481 and2681–2701 have
the corresponding interleaving. Caching an aggregate `a_const` and then adding
`G*p`, or updating `a_old + G*(p_new-p_old)`, changes the sequence of float rounding
and generally cannot reproduce the qualification acceleration/R bits. Updating
the mathematical acceleration difference is insufficient evidence of the original
discrete operation. The same caution applies to CPU/GPU FMA, RN/FTZ pressure stores,
and changing a cached double expression into a differently contracted calculation.

## Lowest-risk design reserve, not a selected implementation

First consider a dedicated endpoint template that retains the original neighbor
order and total-momentum arithmetic, including sigma'-p and interleaved AV, while
skipping unused repeated density/stress-rate/velocity-gradient work and reusing
the exact full-state theta/FS/C/fit geometry. It must still rebuild current pressure
ghosts, native acceleration, acceleration ghosts and the complete Darcy row. This
can avoid redundant mechanical work without first relying on an aggregate linear
force split. It is still a new kernel/path requiring proof; no speedup is known.

A later coefficient/pair cache could preserve exact intermediate values and replay
the original per-pair add order, but adds memory/indirection and cache invalidation
cost. A pressure-only linear application with an aggregated fixed source is a
different numerical implementation until its rounding and complete R behavior are
qualified. The full R/S and BC action cannot be replaced by LP alone or by a
rescaled diagonal. A full Jacobian/Poisson solve is separate work.

The initial full endpoint can supply cache data for subsequent defects in that
same step; the cache cannot be carried across the next mechanical advance.
Fresh AceMax remains required for every endpoint necessary-force bound, since a(p)
changes. Some velocity/J-based wave, hydro and AV scales may be identical under
this scope, but no original safety call/counter or signed interval may be skipped
on that assumption without a separately verified design. Existing scratch
ownership/Pre–Pos lifetimes must not be bypassed with stale pointers.

Before replacing qualification truth, a separately admitted variant would need
default-OFF preservation and controlled identical-state comparisons of native and
ghost pressure, acceleration, full LP/gp/Da/Neumann/R/S, legacy rate, actual BC,
readonly material/J/HG state, owner/periodic behavior and necessary bounds. Both
closed and opened drainage states must be represented. This is a description of
the proof obligation, not authorization to run a test, add a reference/half chain,
change an error budget or claim byte equality now.

## Efficiency conclusion

There is a real opportunity to avoid repeated work during P2/P3 endpoint defects,
but not a demonstrated pressure-only production operator. P3's five complete
forces cannot presently be relabelled as five cheap pressure applications. Future
end-to-end cost should separately report setup/cache construction, ordinary
mechanical steps, each pressure defect, safety diagnostics, saved output and
independent postprocessing, on comparable hardware/workloads and observation
settings. TPI must ultimately meet the intended total-cost advantage over the
baseline with its accepted accuracy; this note provides no speed or accuracy
guarantee and cannot replace the current P3 physical gate.
