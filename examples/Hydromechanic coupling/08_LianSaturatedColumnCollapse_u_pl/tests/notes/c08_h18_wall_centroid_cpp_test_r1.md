# Minimal C++ checks for the moment-based centroid retry

Author-only test design. This note is the only new file; no public source,
existing harness, build, component, solver, native reader, receipt or Git is
changed or executed. It is not a smoke/memcheck acceptance receipt and must not
be used as Release-owner qualification. Root full-read precedes any later code
authoring/build. The actual CPU/GPU Debug smoke and admitted AS.7 run remain
separate evidence of real compiled paths.

The implemented candidate uses the existing failed-nearest first moment row,
not an extra donor accumulation: CPU `JSphCpu_mdbc.cpp:289–297`, GPU
`JSphGpu_mdbc_ker.cuh:140–147`. It is eligible only after the existing nearest
geometry failure, once, for Wendland dynamic2D/nonperiodic walls with finite nearest
fields and finite positive M11. Let C be the failed-nearest centre, G the
original evaluation mirror, d=(M12/M11,0,M13/M11):

```text
C_new = C - d
fitshift_new = fitshift_old - d = C_new - G
centroidretried = true; retried remains true
```

All new-centre accumulators reset and the original kernel search runs again.
The original det/domain/finite gates remain, and the original value/gradient
writer evaluates at G. CPU `shifted` follows the cumulative shift. Existing SPR
`BoundDerivativeFitShift` cache is not a centroid input or output.

## One small component, using existing numerical scaffolding

Prefer a tiny host C++ table driver, reusing `FunSphKernel.h`,
`FunctionsMath.h`, `TypesDef.h`, and the existing component `Need/Bits` style.
Do not introduce another BI4/typed22 loader, source/PRE qualification or receipt
framework. For branch tests, author source-bound test includes from the exact
CPU and GPU centroid blocks above using unique start/end anchors; retain their
text unchanged inside a bounded test loop with local input variables. Review
the produced includes before compiling. Do not handwrite a second gate and
then claim its success tests the public gate. Host-compiling a GPU block is
still not execution of the real CUDA kernel.

Existing zero-step scaffolds available if an actual field-writer check is
needed: `support/upl_gravity_wall_gpu_component_r1.cpp` has small array upload,
canaries and real `DynamicPoreWall(0/1/2)` calls; the CPU
`support/upl_cubic_cpu_wall_r1.cpp` has `Copy/NoStep` state guards and a real
periodic exclusion control. Derive a fresh fixture rather than modifying those
sealed files. No `Interaction_Forces`, `ComputeStep_Sym`, or integrator call is
needed. C08-specific fixtures use H=.072f, massf=3.316f/rho0=2072.5 and original
solid0=1-double(.35f), with the actual `fsph` W/Fac and original rawdet .001.

## Required test rows and independent expected results

1. **Moment versus positive WV centroid.** Use positions (x,z)=(1/8,1/4),
   (3/8,1/2), (5/8,1/8) and positive weights2,1,1. At C=(3/8,1/2),
   M11=4, M12=1/4, M13=7/8; the independent direct weighted centre is
   (5/16,9/32). With G=(3/4,3/4), old shift=(-3/8,-1/4), expect d=(1/16,7/32)
   and new shift=(-7/16,-15/32). These are exact binary values. Separately
   compare an actual-WV fixture's moment centre to a long-double direct weighted
   sum; use an explicit summation-roundoff bound, not bit equality to the Python
   absolute-coordinate sum. Translate the fixture to exercise cancellation.
2. **Gate/state controls.** Require one candidate only after `retried=true`
   and geometry failure. Independently set tker=Cubic, dynamic=false (CPU legacy), 2D=false,
   periodic=true, retried=false, centroidretried=true, nearestfinite=false,
   M11<=0/NaN/Inf, nonfinite ratio/centre, and centre unchanged after rounding.
   Each ineligible row keeps centre/shift/flags bitwise unchanged. Cubic retains
   its old primary/nearest path; no unsupported Cubic candidate is exercised. A successful
   primary or nearest never enters the new block. An already used candidate
   cannot create a fourth attempt. Include shift cancellation back to G.
3. **Constant/affine11 and gradients.** For component k=0..10 define
   c=1+k/16, a=(k+1)/8, b=-(2k+1)/16, and
   f(x,z)=c+a*(x-Gx)+b*(z-Gz). Constants use a=b=0. Independent expected
   f(G)=c and physical gradient=(a,0,b). The stored q is minus that gradient.
   Check the original anchoring expression, including both nearest and centroid
   offsets, returns G rather than C and does not translate the gradient.
   A real-fit check uses the existing numerical matrix/kernel functions, not a
   duplicate Python fitter. For actual stage0 writers: J is at G; pressure
   restores normal head at B; NoSlip stress extrapolates to B, FreeSlip stress
   uses Q at G; physical wall velocity remains zero. Do not compare every writer
   output blindly to f(G). Include nonzero gradients in all11 slots.
4. **Nonlinear J at original G.** On one predeclared actual-WV stencil use a
   positive quadratic J with all donor J>solid0. Obtain an independent discrete
   reference by a small long-double3x3 solve of the declared moment equations
   and native nearest anchor, then evaluate that fitted function at G. Compare
   actual returned J to this discrete G reference; record error against analytic
   J(G) descriptively, without demanding quadratic reproduction. The reference
   at C must differ beyond its propagated rounding budget, giving a nonvacuous
   wrong-target witness. J field and quadrature J must be the same values.
5. **Unrepairable rank and state rejection.** All-positive collinear donors
   retain rank deficiency after recentering: never invert a failed matrix or
   accept a zeroth-order dynamic result. CPU retains the original missing-wall
   failure; GPU retains the actual wall slot/atomicMin and tail canary. Invalid
   donor J or finite-order reconstructed nonfinite/J<=solid0 remains an immediate
   state rejection, not a new geometry retry. Native soil arrays/IDs/normals,
   unrelated slots, Cubic, legacy and periodic controls remain unchanged.

Keep existing primary/nearest success-control values and budgets unchanged.
The GPU scaffold's `Condition():67–73` requires success at the original GP and
must not be reused unchanged for a candidate whose GP failed. At an admitted
candidate centre, derive value/gradient roundoff there, then propagate to G:
anchor error + (abs(C-nearest)+abs(C-G)) dot gradient-error + arithmetic budget.
Declare that propagation before execution; no arbitrary relaxed tolerance or
new condition-based solver gate is permitted. Affine consistency, finite J and
successful candidate branch tests do not establish conservation, physical
accuracy, stable contact, hydraulic-reaction closure or a full trajectory fix.
