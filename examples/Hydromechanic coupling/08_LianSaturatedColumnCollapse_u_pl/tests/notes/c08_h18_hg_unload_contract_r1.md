# HG unloading: exact fixed-input internal contract

Author-only new assets: support/c08_h18_hg_unload_contract_r1.cpp, support/c08_h18_hg_unload_contract_r1_build.py, and this note. No build, component, solver, native reader, physical stage, Git or SHA operation has been performed by this author. Future build and component calls require separate root admission. This is a new local HG mathematical contract, not Zhang2025's literal formula or a selected C08 implementation.

## Exact prefix and build boundary

The new CPP begins with the byte-exact 6,938-byte prefix of the already executed c08_h18_plastic_hg_adjoint_r1.cpp, stopping BEFORE 'using Basis='. It retains only the small B/V/M arithmetic, original matched-LS graph, ApplyP, and the genuine LS-backpropagating ApplyPT. No basis matrix or previous65-group test suite is repeated. The build checks that exact prefix against the sealed source stat and requires the original actual passed check/build/call/completion (65 groups,119713 scalar certificates, known nonpassive unconditional-history counterexample). It does not reread old certificate CSVs.

The build-only script retains the actual original one-entry DebugCPU/CRT CL/link parameters (/Od /MTd /RTC1 /fp:precise, MSVC14.36). It compiles and links one new entry, no physical objects/project libraries, no public headers or source changes. No program follows the build. The component accepts only FRESHOUT, rejects an existing complete/partial directory and writes contracts.csv, graph.csv, midpoint_comparison.csv and completion.json; actual errors preserve failure.json and partials.

Not executed here:

    python support/c08_h18_hg_unload_contract_r1_build.py --execution-authorized
    outputs/c08_h18_hg_unload_contract_r1_build/C08H18HgUnloadContractR1.exe FRESHOUT

## Frozen local ODE and consistent average force

For one directed residual row, fix P, D=dI>=0, z=P v_bar, target g in[0,1] and a positive manufactured interval T. D has Pa units in the unit-depth2D convention; h has m, z has m/s and E=.5 h^TDh has J/m. The local rule is hdot=z while h^TDz<0 (HG unloading), and hdot=g z while h^TDz>=0 (HG loading). This HG power classification is not a claim about current DP activity.

Let A0=h0^TDz and Z=z^TDz. For Z>0:

    t1 = clip(-A0/Z,0,T); t2 = T-t1
    hnew = h0+(t1+g*t2)z
    Ih = integral h dt = T*h0+(.5*t1^2+t1*t2+.5*g*t2^2)z
    F_avg = -P^T D(Ih/T)
    W_mechanical = -z^T D Ih

If A0>=0, t1=0; if unloading has not reached zero by T, t1=T. At an event exactly at T either expression joins continuously. No event from historical C08 output is reconstructed. These are exact constant-input polynomial segments, not an actual solver time integration or a smaller-step reference run.

For Z=0, PSD implies A0=0. Known zero D or exact zero z is handled without division: t1=0, the all-loading formula with a=g applies. Zero D may still change an energetically invisible h when z is nonzero; reactivating/changing D would require additional accounting and is outside this contract. An unknown nonzero row whose positive Z cannot be certified is rejected, never treated as zero by a tolerance.

The exact dissipation expression is

    loss = (1-g)*[t2*(A0+Z*t1)+.5*g*Z*t2^2] >= 0
    DeltaE + W_mechanical = -loss.

The code preserves signed computed loss/residuals and their roundoff bounds. It does not clamp small negative output to zero. In an unloading-to-end segment t2=0 and the exchange is conservative. Following a zero crossing, loss=.5*g*(1-g)*Z*t2^2. Gamma1 recovers the fixed-input elastic ODE mathematically, not an old floating-point trajectory or a Symplectic history update.

The true time average Ih/T is essential: across a crossing it differs from (h0+hnew)/2 by z*(1-g)*t1*t2/(2T). Substituting the endpoint average would change the claimed mechanical work.

## Manufactured coverage and retained counterexample

Nine scalar/vector fixtures times g=0,.5,1 produce27 contracts.csv rows: loading, before/at/after a zero crossing, cold history, exact zero z, exact zero D, nonzero transverse memory, and an oblique vector. Each checks one full exact segment against two successive exact segments with the SAME fixed inputs: h semigroup, Ih additivity, telescoping energy, work and loss. These are algebraic semigroup tests, not a physical half-step chain. All cases also check a fixed3/5,4/5 rotation; transverse memory is retained. The exact zero-z rotation is first checked as Mul(R,0) within its arithmetic enclosure, then supplied as the same declared exact-zero manufactured field, avoiding a generic interval overestimate being mistaken for an unknown nonzero row.

The rejected midpoint-reflection rule remains a two-row numerical comparison. For h0=1,z=-1,D=1,T=3,g=0, that rule gives hnew=-1 and zero net work, whereas the exact piecewise contract gives hnew=0, DeltaE=-.5 and mechanical work+.5. Both satisfy an energy inequality, so the inequality alone does not select the desired unloading history. The comparison column is fixed_input_contract_under_test, never a physical selection flag.

One perturbed49-point graph uses the original frozen LS/P/PT geometry only once. z=Pv_bar is prescribed. Each directed row has D=beta/2, a nonuniform prescribed binary-dyadic g_ij=(g_i+g_j)/2 including zero/one, and arbitrary history with parallel/transverse parts. Per-row exact Ih supplies the complete adjoint average force. graph.csv records summed DeltaE, loss, row work, actual nodal T*v_bar dot F_avg, their difference, net force/torque and their bounds. No basis reference, force API, material return, filtering, Darcy, physical position/velocity/J update or history producer is called. The retained synthetic mass construction in the prefix is not used to claim any u-pl ledger result.

## Branches and arithmetic are explicit

The passed prefix's local value-plus-absolute-error arithmetic is retained exactly. The process requires IEEE binary64 round-to-nearest and MXCSR FTZ/DAZ both off. Support/rank/inverse domains retain the earlier guards, without a ridge or modified threshold.

For nonzero rows the event ratio -A0/Z is computed only with a strictly positive certified Z lower bound. ClipTime uses the actual computed ratio for its branch label, no epsilon. Its lower/upper times are separately bounded by the monotonic clip function applied to outward endpoints; this also encloses either side of a near/exact event. event_interval_overlaps reports those ambiguous interval classifications rather than falsely proving their sign. It does not count observed physical events. This explicit domain clip is the definition of the finite interval's event time, not pressure/history regularization.

Every equality reports actual discrepancy and propagated bound. contracts.csv contains true DeltaE+W and its bound, dissipation, balance residual/bound and semigroup errors/bounds. graph.csv does the same for the whole graph and average-force work. completion.json records operation/check counts and maximum discrepancy/bound. No empirical physical tolerance or 5Pa acceptance test is introduced.

A future successful result would set fixed_input_energy_contract=true only. It would leave actual_Symplectic_qualified, same_stage_Darcy_qualified, dynamic_D_graph_gamma_qualified, DP_producer_qualified, finite_rotation_integration_qualified, history_restart_qualified and physical_acceptance all false. Changes of D/P/g, neighbour birth/death, rotations during the interval, real DP half/full time layers, force/velocity sampling and fluid feedback still need separate derivation and evidence. This fixture cannot remove any existing production plastic/rank/spin/dt guard or authorize another C08 solver.
