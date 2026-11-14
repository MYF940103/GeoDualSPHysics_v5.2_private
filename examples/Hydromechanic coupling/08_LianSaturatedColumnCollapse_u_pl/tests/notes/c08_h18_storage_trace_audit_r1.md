# C08 storage observer r1: independent static audit

2026-11-14. Independent full read of support/c08_h18_storage_trace_r1.h (1653B), .cu (8857B), _prepare.py (final13598B, mtime10:21:29.400Z) and notes/c08_h18_storage_trace_r1.md (final8677B). The audited source baseline is tests/outputs/c08_preload_schema2_source_r1/full_source.zip. No prepare, import, build, component, solver, native read, Git or SHA was run by this reviewer. Only this audit note is new.

Decision: the identified release-pending guard blocker is repaired. No further static blocker was found in the final narrow output-only design. This is permission-neutral design review, not executed preparation, numerical no-feedback proof or physical acceptance.

## Source isolation

The header adds an independent observer ABI, no JSph member. Its physical input arrays are const. New CU stores only private static device records/exported/global_errors (CU20-22), with one original soil native ID per slot id-2060 (24-28). No device allocation/static-destructor cudaFree is used. There is no extra neighbor traversal or write to original pressure/J/state arrays.

Prepare94-114 inserts guarded host calls and requires removing them to recover all original JSphGpu.cpp bytes. Prepare123-138 declares only that original member modified and two observer members added; copy.copy(ZipInfo) avoids mutating the old source archive CRC descriptors. The old physical JSphGpu_ker/simple objects are retained, rather than rebuilding their arithmetic with observers. Those are predeclared preparation checks, not yet an executed preparation receipt.

## Actual lifecycle and repaired blocker

Original GPU Single1079-1085 disables warmup damping/Shepard, then retires/sorts with RunCellDivide before setting GravityPreloadReleased. RunCellDivide567-581 updates Np/Npb and ID order before entering ApplyPorePressureBoundaries. The handoff rebuild1160 has7060 particles and temporarily disables free-seepage; it cannot trigger the6805/1805 initializer.

The initial draft incorrectly required UseDynamicPorePlaneContact before release. Original JSph.h612 requires GravityPreloadReleased for that active predicate, so it would always reject the intended first cap. Final prepare61 checks underlying NoPenetration/HydroMechDynamicSeepage/GravityPreload configuration during release-pending; line78 checks the active predicate after release. IsDynamicPorePlasticConfig (original JSph.cpp3850) itself has no released-state requirement.

Final initialization is before original tracking/cap at GPU1424, captures inherited soil p/J, and permits release-pending. The release-exposed FS first cap is thus observed separately, not lost before the first predictor. Existing PRE and soil history are neither relabelled nor reset.

The RHS hook after original GPU2102 only observes the real corrector. PoroJPreg/PorePressPreg and current Jh/theta_h/stored float Rh are valid there. CU44-49 copies values per ID; no pointer to Jn is retained until after its free. Original GPU1871/2005 advances J/frees PoroJPreg, while1894 updates p; the post-pressure hook reads actual raw p/Jnew before PorePressPreg is freed at1908.

Original half divide sorts current and predictor arrays consistently (Single491-501,535-538). Private records remain ID-indexed. Pending/update step identity and exact pn/Jn continuity against last accepted values (CU46,53) detect an omitted state writer. Predictor p/J are not counted as additional accepted increments.

Every true original positive-cap invocation is bracketed (prepare104-105, both original host sites). CU64-77 measures before/after values; repeated cap with zero change contributes zero storage and only increments call count. A changed value must be positive-before, zero-after, actual FS2/3. Original cap logic and negative pressure are untouched.

Raw update records completed=Nstep+1 and time=source scalar time+actual dt; release cap is distinct at the PRE completed count. Original outer loop Single1234-1245 divides, adds dt to TimeStep, then saves before incrementing Nstep. Save hook in ParticlesDataDown therefore matches actual saved clock and hoststep+1; repeated same-count downloads do not append another sidecar batch. No n*dt clock replaces scalar +=dt.

## Identity, source labels and arithmetic budget

The implementation evaluates w=(1-solid0/J)*(V0*J)/Kw, mathematically V0*(J-solid0)/Kw. It consistently treats these computed double weights as its observed storage proxy. This does not prove true water mass, saturation or an independently reconstructed geometric volume.

At each accepted update the exact real-arithmetic endpoint identity is:

delta S = wn*(praw-pn) + praw*(wnew-wn) + wnew*(paftercap-praw).

CU54-57 splits the first term into wn*h*comp, wn*h*(Rh_float-comp), their declared reconstruction-roundoff term, and wn*((praw-pn)-h*Rh_float). It deliberately uses wn throughout. Therefore no wh-to-wn capacity compensation is missing, provided the displayed compression remains this pressure-storage contribution; it must not be renamed -V0*h*Jh*theta without adding the explicit coefficient/capacity difference.

Rh_float-comp is correctly labelled Darcy remainder including rate quantization. Original double pre-cast rate is unobserved. CU58-59 gives only an unsigned bound using FLT_EPSILON*abs(Rh)+FLT_MIN, the latter covering possible FTZ/subnormal conversion. This bound is not added as a measured signed source. The pressure-commit residual uses observed old/raw pressure and actual stored float rate; it includes write/add/subtraction arithmetic rather than pretending a separately instrumented original intermediate was captured.

Computing split terms entails additional double reassociation. Exact identity is therefore checked within an arithmetic envelope, not by asserting that independently rounded partitions sum bitwise. CU60-61 uses gamma128 absolute-operand local budgets; cap75-76 uses gamma64. Host40-44 adds a count-dependent gamma term with all accumulated absolute contributions and endpoint magnitudes. The finite profile bounds step counts; the budget is independent of physical pressure tolerances and the signed dterror clock guard. It cannot be tuned after data.

Every saved ID is checked independently before writing; a global cancellation cannot conceal an individual failed residual. A later all-soil sum still needs its own host reduction budget. weighted_pressure_delta is an auxiliary accumulated cross-record, not an additional signed ledger term; counting it again would duplicate the pressure increment.

## What still requires actual evidence

- Actual prepare/build receipts must confirm inverse host bytes, retained physical CUDA object identity, private CU/header and dual macro scope. This audit does not replace them.
- Debug two-update/memcheck evidence must check private device symbols, launch/state coverage and observer counters. Debug is not Release bit truth.
- The first three actual Release records must match retained AS03 .90s native arrays/layout/clocks/signed intervals bytewise before an output-only trajectory claim. Original expressions being unchanged is insufficient by itself.
- All5000 IDs need one init, exact RHS/update coverage, no observer errors, genuine first release cap and no pending observation at saves. Extra kernel/CSV cost must be measured, not declared zero.
- Storage attribution does not separate the Darcy remainder into pure pressure/acceleration/variable-k or independently measure the original rate-rounding sign. It does not establish boundary flux conservation, contact reaction closure, root cause, repaired clumping, TPI or negative-pressure acceptance.

This static review does not start the window, decoder, VTK, PRE, half chain or other-psi computation. The original numerical and native guards remain required.
