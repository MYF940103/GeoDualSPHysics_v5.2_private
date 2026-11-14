# C08 pressure–AS–force–Darcy conditional component r1

Status: author-only preparation. No build, component, solver, reader, VTK, Git, SHA scan, new physical window or parameter change is authorized by this file. Root must independently read all three files and separately admit a build, then a single component invocation.

## Narrow question and frozen state

At the already reviewed original AS.3/n2.55 full3 completed states Part38 and Part76 (completed steps2076001 and2152001), can pressure perturbations produce positive or negative conditional pressure-subsystem work through the actual current total-stress/AS momentum and same-stage dynamic Darcy RHS? This is not a complete coupled Jacobian, stability spectrum, time-integrator test, reconstruction of the saved GPU force substage, or a repair claim.

The source is the unchanged schema2 Wendland H=.072/dp=.04 original AS03 full301 native, with its original same-material psi0 PRE, bed-last retirement255, active6805=1805fixed+5000soil, fixed5us, total-AS.3/n2.55, AV.1, CompletedOnly FS pressure policy and fixed-plane NoPen. ReactionClosed remains false. All sigma-effective/v/J/kappa/P0/rho/k/positions/time are held at each completed state. Only soil pressure is changed. Actual original force code lawfully reconstructs wall ghost pressure and wall/soil acceleration and recomputes the AS tensors. No synthetic acceleration or held-AS counterfactual is substituted. Constant pressure at fixed effective stress changes total stress, so a constant mode is not a gauge-null test.

## Exactly34 actual force/RHS evaluations

There are17 per state: one baseline; four modes, each with requested amplitudes1Pa and10Pa, both signs. Modes are constant, initial altX, dipole4953(+)/4954(-), dipole6767(+)/6865(-). Initial altX uses only the5000 genuine ID-to-initial_ix entries in passed global_modes Part38/altX_Uz fields (100×50), not current x or sorted particle order. The two dipoles are unweighted ±1, not capacity-rebalanced. The existing34 calls are the entire component; no additional control, PRE, material step, time advance, PONDING/cap, half chain or solver is included.

Each pressure is actually committed as float(double(native_p)+sign*h*phi). The requested-to-actual quantization error is reported per ID/sign. Central pressure is dp_c=(p_plus-p_minus)/2 from the two actual stored floats, not h*phi by assumption. Every original force call is followed by original scratch cleanup and restoration of the unchanged completed state.

## Reused implementation and necessary checks

The builder generates four private includes under its new build directory. shared.inc is the complete passed AS03 RHS source with only protected member access and diagnostic AppInfo changed; inverse replacement must reproduce the original bytes. Its original main is renamed and never called. setup.inc is the original genuine PRE release/configuration guard block. rhs_literal.inc is the original source-ordered raw-FS literal, seven-channel decomposition, float commit and donor partition arithmetic, copied byte-for-byte. interior_mask.inc is the passed global_modes no-fixed-neighbor receiver mask copied byte-for-byte. No numerical force implementation is copied/replaced; Interaction_Forces(INTERSTEP_SymCorrector) is the original object implementation.

Exactly one private entry object links86 original DebugCPU physical objects. Archived headers, material source archive and7 runtime companions remain original. No CUDA/object/public/source/canonical program is rebuilt or modified. The builder uses stat bindings once, not SHA sweeps, and never invokes the component. Original receipts/CSVs and native layout/clocks are consumed with existing stat bindings; it does not requalify the historical solver chain.

The two baseline calls require all5000 actual CPU Ace, six stress-rate components, theta, pressure rate and fresh FS fields to bit-match the already passed AS03 RHS CSV at the genuine part/time/step. All34 calls retain original Restore/Map/Roles/Ledger/Unchanged primary-state checks and literal-final-float/expanded/donor reconciliation budgets. Under pressure-only changes, all soil theta/six stress rates/C/FS/FS-normal/cohort/weight must match baseline bits. Wall nonpressure state (pos/velocity/sigma/J/P0/mode) must match baseline; derivative/tangent velocity and C equality apply only to active walls. Inactive derivative/C storage is deliberately not inspected. Actual ghost p and Ace may change and are rebuilt rather than artificially held. A changed FS/mode/cohort is a failed frozen-stage interpretation; no mask override is performed.

The seventh-channel decomposition remains compression, LP, Taylor_pressure, Da, FS_Ace_Lx, chain_pressure, chain_Ace. The **eighth channel is signed actual_float_R minus the expanded double sum**. It contains rate float quantization/source-order arithmetic residual and is not relabelled a physical source. Source per-row float budget FLT_EPSILON*abs(literal)+float_denorm_min and original operation-count double reconciliation budget are unchanged. They are arithmetic gates, not loose physical tolerances. AS tensor and actual Ace changes are retained, without claiming the entire AS formulation is correct merely because signs or baselines pass.

## Conditional work and outputs

For receiver cohorts all5000, original no-fixed-neighbor receivers, and baseline fresh FS2/3 receivers, calculate w=n*V/Kw, dp_c=(p_plus-p_minus)/2, dR_c=(R_plus-R_minus)/2:

Q=sum(w*dp_c*dR_c), N=sum(w*dp_c^2), Q/N when N>0.

The weight is conditional storage capacity, not the gamma coefficient from the earlier row component, and is not fluid mass. Cohorts can overlap; all donors stay present. Q/N has units1/s and is descriptive. No Q sign, near-null value, amplitude similarity or cohort count is a physical pass gate. Zero N is explicitly undefined with an empty ratio cell, never clamped. Both actual central derivative and R_plus+R_minus-2*R_base are reported; the weighted RMS of that second difference describes finite-amplitude nonlinearity/float effects. Compare1Pa/10Pa descriptively, preserving quantization and possible spectral branch changes. Negative pressure is retained; no projection is called for the artificial perturbed states, including positive perturbations at frozen FS.

Outputs use the fresh exclusive component directory:

- trials.csv:34 actual calls, perturbation counts, quantization error, changed AS-tensor count, frozen soil/wall qualification.
- responses.csv:80000 central rows (2×4×2×5000), baseline p, separately labelled fixed P0, actual p+/p-/R+/R-, quantization, weight/cohorts, actual central Ace, AS tensor-change norms and eight signed central rate channels.
- focus.csv:64 rows (2×4×2×4), original four fixed IDs with baseline pressure, separately labelled fixed P0, rates and full actual baseline/plus/minus AS tensors (xx,yy,zz,xy,yz,xz).
- summary.csv:48 rows (2×4×2×3), Q/N, weighted norms, nonlinear second difference, eight work channels and quantization.
- completion.json:exact coverage, original arithmetic maximum ratios and zero physical/material steps. Exit0/completion is implementation evidence only.

No interpolation, changed native metadata, pressure filtering, parameter selection, threshold relaxation, full coupled eigenanalysis or claim about unsaved/substage causation is allowed. In particular the dynamic pressure-to-momentum feedback is conditioned on fixed geometry/velocity/effective stress and the original frozen FS classification; material/geometry evolution and same-stage contact reaction are absent. Total-AS spectral activation can be nonsmooth, so1Pa and10Pa differences must be interpreted with that limitation.

## Root-only later commands

Build only (separately admitted):

python -B tests/support/c08_h18_pressure_feedback_r1_build.py --execution-authorized

Use the already established Python interpreter in the root environment. No runner is created. A later unique root-owned invocation must use the existing real owned-call helper, --check --native followed by the exact original full301 native path, then -cpu -ompthreads:1 -stable -svres -mdbc_freeslip:1, the original full3 seed and the exclusive outputs/c08_h18_pressure_feedback_r1 output. Existing/failed partial output is never overwritten/reused. No automatic solver or next stage follows.
