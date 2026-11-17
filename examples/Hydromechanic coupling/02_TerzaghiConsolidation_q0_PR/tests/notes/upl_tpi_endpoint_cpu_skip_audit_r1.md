# CPU endpoint scratch-skip audit r1

2026-11-17. Read-only design reserve, not a selected implementation or admission. Only this new note is written. No source/import/program/process is changed; no prepare/build/profiler/solver/native/analysis/hash command executes. P3 solver completion is not treated as a physical pass.

Anchors use frozen `outputs/upl_tpi_m0_dt_CPU_r2_source`; relevant physical function bodies were also compared as text with frozen P2 CPU_r1. PreInteractionVars/PreInteraction/PosInteraction, Fluid/Bound pairs, CpuT dispatcher, Single Interaction_Forces and complete dynamic-rate bodies are identical. This is not a claim that both complete CPPs or their timestep transaction are identical. Read the existing pressure_only_feasibility and observer_split notes first; this is a narrower CPU def-use audit.

## What really survives an endpoint

Single.cpp754-821 orders: PreInteraction; derivative-wall setup; full wall/FS/C tracking; direct load; original fluid-fluid then fluid-bound then bound-fluid pair work; damping;2D Y zero; ViscDtMax; top-band normalization; readonly HG; complete dynamic Darcy rate; AceMax. The future path must preserve this order and existing Pre/Pos scratch lifetimes.

P2 Single.cpp1406-1425 then performs DtVariable, readonly checks/PrepareFinal, PosInteraction, pressure Write/real BC and provisional/final commit. It does NOT call ComputeSymplecticPre/Corr. Those ordinary mechanical updates remain at Single.cpp975/986 only; J/material/HG history updates remain once. Thus a written derivative is not automatically a required endpoint result.

| Actual write | Actual later reads / endpoint fate |
|---|---|
| Float gradvp three rows: Cpu2687-2690; corrected2745-2749; e/spin2752; elastic rsigmap2754; Rsigma2800-2805 | Mechanical readers are Cpu4722-4727 and4846-4851, outside endpoints. Extra endpoint Rsigma is freed at2055 before any material integration. These calculations are discard candidates under the present qualified elastic AV-only C02 scope. |
| Arc continuity:2603,2784; boundary Arc2120/2136 | Used by ordinary density integration at4685/4819 and fluid step; not by the endpoint loop/Darcy or DtVariable. Freed2045. BUT arp1 also affects the shared store predicate2771; its calculation cannot simply disappear without an independent bit proof. |
| PoroThetac double div:2550-2575 and2770 | Read by full Darcy R at4436/4487/4499 and exposed as native endpoint theta. Required, even though endpoint never integrates J again. Do not use trace(float gradvp) or Arc/rho as its replacement. |
| Ace:2473-2481 total stress/pore force, interleaved AV2681-2706, damping3008-3025, load normalization, readonly HG | Required by periodic extension4419, wall acceleration4308-4318, Da4469-4470, closed-FS Neumann4482-4484, AceMax and force timestep bound5000. Must refresh from each actual q. |
| visc/res.viscdt:2683-2685,2788/2808 and boundary2123-2142 | Required by Single807 and DtVariable5002/5017. The bound-fluid pass is not removable just because its Arc output is discarded. |
| CorrMat/FSType/FSNormal/PosDiv plus wall J/sigma/p/derivative velocity | Rebuilt1162-1202 and4259-4302; feed theta, current momentum, row gradients, masks and nonsingularity/domain checks. Required in this first patch; no geometry/fit cache is selected. |
| PorePressRate and Row(S,R,theta,q)4499-4501 | The actual complete final residual/rate, still required. It is not dp/dt and cannot be replaced by LP-only or a rearranged Kw/n scaling. |

The active C02 path has DynamicPorePressure=true, so useporerate is false at2338: the legacy static Kw compression/Darcy branch does not consume Arc. PoroTheta uses its independent double corrected-gradient expression, current-J volume and SPR velocity. Its summation must remain unchanged in both fluid-fluid and fluid-bound passes.

## First local patch to consider

Select only **skip stress-rate-only work at true pressure endpoints**: float gradvp accumulation2687-2690; post-loop stress-gradient correction and strain/spin/elastic rate2744-2754; Rsigma accumulation2800-2805. Keep the original local declarations/zero initialization and the intervening dsigmap-to-rsigmap block2776-2783 for the first minimal patch; do not leave a dangling variable reference by deleting only its declaration. Retain every native sigma load/cast used in momentum: sigmap1/2 at2404/2441 also feed2476-2481, so deleting the stress-rate code does not delete those force inputs.

Keep all Arc calculation/stores, its aggregation predicate, both pair calls, bound-fluid viscosity, Pre allocations/zeroing/free and all observer/error/safety calls for this first candidate. In particular do not combine a scratch-pool/allocation change, theta/C caching, pair fusion, map caching, pressure-force split, observer removal or gradient-kernel modification with it. Keep the now-unused Rsigma buffer allocated/zeroed/freed initially, avoiding null access or pool/address-lifetime changes while qualifying the narrower arithmetic skip.

Density removal is a separate step:2771 is `shift || arp1 || acep1.x || acep1.y || acep1.z || visc`. It controls the actual `ace=ace+acep1` at2785 and LoadAce store2786. Dropping arp1 can remove an otherwise executed addition of zero and change signed-zero bits, not just an unused Arc store. Retaining old per-neighbour force arithmetic while changing this final write gate is insufficient. Arc-only stores might later be omitted while retaining the original arp1/predicate, but that is not selected here.

TDensity=None already compiles out stress-diffusion branches2608-2642; AV-only already avoids SPS allocation/tau2966-2967. Shifting/AS/NoPen/DEM are off. Do not count disabled branches as measured new savings. Pressc EOS preparation1947-1954 is another possible later discard under this exact momentum path, but press[p1] is still an unconditional load2396: passing null/removing allocation without a paired load change is unsafe and is outside the first patch.

## Template cut and ABI constraint

The smallest numerical cut is inside existing InteractionForcesFluid2321-2808, wrapping only the stress-only accumulations/post-block. Keep neighbour search/support tests, group and neighbour order, every total-stress/pressure contribution and float add, raw load, theta, AV and the final shared store predicate literally ordered as before. The two separate fluid calls at2954/2958 must remain separate; fusing them changes the float rounding of their separate ace additions. Bound-fluid at2971 and all timestep reductions stay.

A naive new bool template parameter on the JSphCpu member declarations changes JSphCpu.h337/353 and class-definition tokens in retained objects. It should not be advertised as a two-host-object-only ABI-neutral patch. To preserve the authoritative shared header, a private candidate can instead put the existing per-particle/neighbor body inside a C++14 generic lambda/local tag dispatch in the same CPP, selecting a compile-time full-rates tag once per pair invocation. The true tag is used on all original mechanical/default-A paths; only qualified pending pressure endpoints use false. This is a design option, not implemented code. A runtime bool guard is smaller textually but may add per-neighbour branches and is not a measured performance result.

The local-template approach avoids changing class declarations, public XML, CTE or device tokens, but moves the body into a callable and can alter compiler allocation/inlining. It can increase code size. It must preserve original MSVC flags/OpenMP policy and cannot claim binary or floating-point equality from source ordering alone. Root must review the actual minimal diff before any private preparation/build.

## Must remain and proof before use

Retain fresh hydraulic wall pressure4259-4278 and wall acceleration4308-4318; current FS/C/periodic extension1162-1202 and4415-4422; SPR derivative data; q0/ramp/sourceTime; raw-load normalization; exact current-J readonly HG add; full LP/gp/Da/closed-FS correction4464-4486; all invalid-domain/row/core/HG/error gates; fresh AceMax/ViscDt/necessary limits and original signed intervals. Geometry and velocity being fixed inside the endpoint do not justify substituting half-stage theta or a prior pressure/acceleration ghost.

Possible retained-result bit equality is credible because the selected skipped expressions do not feed those retained operations under current qualifiers. It is not yet demonstrated. Required future evidence is default-A unchanged actual native states, and controlled closed/open same-state endpoint comparisons of Ace/native+periodic+wall values, theta, S/R and legacy rate, real BC, force/wave/hydro bounds/signed records, all22 typed arrays/IDs/clocks and actual hidden HG/history. Existing saved five exports are not an all22 proof, and norms/counters are not hidden-array equality. Where previous hidden snapshots do not exist, report that gap rather than reconstructing them.

Only discarded scratch Rsigma/gradients may intentionally differ; no original committed/native state or rejection gate is removed. No speedup is claimed without later comparable end-to-end timing including all endpoint evaluations, guards and output. This note authorizes no solver, extra half/reference chain, change of physical budget or production merge.
