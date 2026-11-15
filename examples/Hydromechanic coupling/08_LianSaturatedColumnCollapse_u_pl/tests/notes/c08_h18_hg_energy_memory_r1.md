# New active-edge energy-normalized HG memory toy

Author-only assets: support/c08_h18_hg_energy_memory_r1.cpp, its _build.py and this note. No build/component/solver/native/GPU/Git/SHA action was performed by this author. Future build and component each need independent root admission. This is a NEW HG internal-state and weight-transport model, not a variable-D GNOG algebraic equivalence, a paper reproduction or a selected C08 trajectory.

## Retained closed algebra and execution boundary

The first9,294 bytes of the CPP are copied exactly from the sealed, actually passed c08_h18_hg_unload_contract_r1.cpp up to (not including) 'struct Fixture{'. This retains B/V/M arithmetic, original frozen matched-LS Graph/P/PT, and the passed ExactStep local contract only. Neither the old basis suite nor the27 local fixtures is repeated. The new build checks that exact prefix, and binds the original passed check/build/call/completion (27 fixture rows,1771 arithmetic certificates, fixed_input_energy_contract=true, actual_Symplectic_qualified=false).

The new build compiles one entry and links that object with the original static Debug CRT recipe; no physical object or project library is compiled/linked. Original /Od /MTd /RTC1 /fp:precise flags, MSVC14.36 ABI, source protections, finite arithmetic/rank/support guards and FTZ/DAZ-off requirement remain. No executable follows the build; no old script, output or public source is modified.

Not executed here:

    python support/c08_h18_hg_energy_memory_r1_build.py --execution-authorized
    outputs/c08_h18_hg_energy_memory_r1_build/C08H18HgEnergyMemoryR1.exe FRESHOUT

The component refuses an existing complete/partial directory. It writes steps.csv(16 rows), frame_covariance.csv(8 rows), completion.json, or an actual failure.json with partials retained. It reads no C08/BI4/native/material/clock input and runs no helper tool or next job.

## Model, units and deliberate change from raw h

For each directed one-sided residual row choose independent e, scalar D=beta/2>0 and S=sqrt(D):

    E = .5 sum_rows |e|^2; u = S P_current v
    F = -P_current^T S e
    edot = a*u + Omega*e

D has Pa units in the inherited2D unit-depth convention, e has m*sqrt(Pa), E has J/m and F has N/m. Gamma g belongs only in the loading drive a=g; HG unloading uses a=1. It never rescales all existing e or multiplies the whole force/memory. The full adjoint, including LS backpropagation, is necessary for force/torque balance with arbitrary row histories.

For skew Omega, same-current P/S and a loading decision by e dot u, the continuous port identity is Edot+v dot F=(a-1)e dot u<=0. There is no explicit Ddot/Pdot/Gammadot term because e and its Euclidean energy are chosen independently. For D>0, expressing this new model in raw h=e/sqrt(D) adds -.5*(Ddot/D)*h to its transport. That term is NOT computed and is NOT present in the old raw-history model. This is a substantive modeling choice, not a way to erase parameter work while keeping the old material law unchanged.

The toy uses the already passed fixed-input ExactStep(e,u,Dlocal=1,g,T), including its true integral Ie. Current S is cached once per row and reused for u=S Pv and F_avg=-P^T S(Ie/T). Thus T sum v dot F_avg equals -sum u dot Ie. It does not substitute an endpoint-average memory, inverse-reconstruct a float rate, or invoke original physical force/material/Darcy APIs.

## Active rows, births and irreversible deletion

A row is owned by its ordered pair of unique manufactured native IDs; the two directions remain independent states. The persistent memory vector contains ONLY the current active graph rows. A kept row receives its previous e. Every born row gets exact e=0, even if the same pair existed earlier; an ID-only ever-seen list counts such returning zero births and cannot restore old energy. Every dead row is removed and its actual .5|e|^2 is recorded as deleted HG numerical dissipation.

This is the chosen active-only policy: no dormant wake-up, no hidden old vector stash, and no reset of physical sigma/kappa/J (none exist in this toy). A shrinking kernel weight need not make e's stored energy small. Deletion can therefore discard finite energy; that is an explicit cost of the model, not evidence that deletion approximates a physical release. The component requires the sequence actually to exercise deaths, returning births and positive finite deleted energy, otherwise it rejects incomplete coverage.

Every active D must have a certified positive lower bound before sqrt; no epsilon weight floor, gamma-based edge erasure or D=0 division is introduced. Inactive graph rows simply have no memory. Exact edge lifetime between these synthetic states is not reconstructed or claimed.

## Eight manufactured geometry states and two coordinate frames

A single49-point perturbed material cloud is externally subjected to eight fixed scale/shear matrices, generating changing P/D and edge birth/death. Their scale factors are1,1.12,1.25,1.05,.92,1.18,1,.97, with the prescribed shears in Records(). Geometry is frozen during each manufactured interval T=.125. Velocity is a prescribed nonaffine field, held fixed in that interval; its variation is not required to be the derivative of the externally chosen geometry sequence. There is no physical elapsed C08 clock, timestep qualification or simulation of those deformations.

The prefix's manufactured per-node volume/mass numbers are fixed by canonical ID in every state. They are not advanced with geometry and are not asserted to form a u-pl J/volume/mass trajectory. This stage deliberately changes geometry-based P/D only, without a dynamic-J test or actual material producer.

The reference frame and a sequence of globally rotated coordinate frames are both evaluated. R_k is the k-th power of the enclosed exact3/5,4/5 orthogonal rotation. Existing e is re-expressed by R_k R_previous^T BEFORE keeping/deleting/updating rows; its energy change is checked and reported. Rotated inputs also add an instantaneous rigid velocity Omega_super*x+b, which P must annihilate. This tests algebraic covariance and correct known-frame mapping, not integration of a physical Omega ODE, a claim that the sampled rigid velocity integrates the chosen R sequence, or large-rotation solver accuracy.

Input records have unique synthetic IDs1000+3i. Each frame/state receives a different deterministic input permutation, then is sorted canonically by ID. IDs/gamma ownership are checked exactly; coordinates and velocities are checked with the inherited arithmetic enclosure. History is looked up by the directed material-ID key, never by the incoming or sorted slot. Cross-frame comparisons check every row key/e/u/Ie/S and every nodal force, with numerical covariance rather than a GPU/native bit claim. CSVs show representative born/dead/kept ID pairs; internal checks cover all active keys, not merely those samples.

## Energy ledger and output interpretation

For each interval, Eold is the previous energy before re-expression, Ekeep is the active retained initial energy and Edead is deleted energy. The fixed-row contracts and complete adjoint imply:

    Enew - Eold + W_nodes + loading_loss + Edead = 0.

Known-frame energy differences are separately recorded within arithmetic error. The cumulative ledger starts from exact zero memory:

    E_current + sum W_nodes + sum loading_loss + sum Edead = 0.

steps.csv retains the actual energies, row/nodal work, losses, frame/step/cumulative residuals AND their bounds, net force/torque and bounds, max nodal force, active/kept/born/dead/returning counts, current D range, LS condition and sampled directed IDs. Positive mechanical work can be a release of stored energy and is not rejected. frame_covariance.csv retains actual history/force discrepancies with associated bounds and differences of energy, work, discarded energy and loading loss. completion.json records actual check/operation counts, maximum discrepancy/bound and event-interval overlap count. The latter refers only to the local manufactured constant-input branch enclosure, not observed C08 events.

All comparisons use the unchanged outward error machinery from the passed prefix; actual discrepancies are retained, no signed residual or loss is clipped, and no empirical physical tolerance is added. The test cannot claim truth just from a boolean: the root must inspect the reported scales and bounds.

Successful completion could establish only the fixed-interval port/lifecycle ledger of this new active-edge model. dynamic_J_qualified, DP_producer_qualified, actual_Symplectic_qualified, same_stage_Darcy_qualified, Omega_ODE_integration_qualified, C08_qualified, history_restart_qualified and physical_acceptance remain false. Real predictor/corrector velocity/force sampling, material half/full commits, finite-rotation transport, changing fluid mass, Darcy feedback, real support-crossing accuracy and restarts are not resolved. No production plastic/spin/rank/dt guard may be removed on the strength of this toy.
