# Private GPU normal-Taylor controls r1

Author-only: new `support/c08_fs_normal_gpu_r1.cpp` and this note. No compilation, import, helper/program invocation, public-source edit, existing private-archive edit, XML or PRE change is performed by this author. The separate GPU builder is reviewed and admitted by root. It must compile the identical new entry against matching frozen headers and link it separately with the original and candidate GPU interaction TUs. Neither executable runs automatically.

The source includes retained `upl_cubic_component_r2.cpp` with main renamed, reusing Device/Up/Down/Cu and vector/matrix helpers. The included retained main is not called; its entry must not also be compiled/linked separately. The new CLI is exactly `--expect raw|normal --out FRESH_DIR`. `--expect` selects only the host reference. Both executables call the real production kernel with FreeSeepageON for ON samples, and explicitly OFF for controls. No test-only kernel macro switches the production closure. Wrong executable/reference pairing should fail a resolved formula comparison, not silently switch the operator.

## Frozen manufacture

The valid CPU source is `support/c08_fs_matrix_cpu_r2.cpp`; inspect `outputs/c08_fs_matrix_cpu_r2_{raw,normal}/{nodes.csv,controls.csv,completion.json}` for prior CPU observations. Its r2 cell-code correction is retained evidence. The GPU does not read any CPU CSV or upload CPU C/FS/normals. Same-ID CPU/GPU comparison is a later descriptive/budgeted review; no bit-identical normal or classification requirement is imposed here.

The81 native fluids have ID=(iz+4)*9+(ix+4), ix,iz=-4..4, x=1+ix*.04+(iz<4?.04/8:0), y=0, z=1+iz*.04. Wendland H=.072f, support2H and Eta2=.01f*H*H match CPU r2. Reference mass is float(2072.5*.04*.04), rho0=2072.5, water rho=1000, Kw=1e9f, n0=.35f, k0=.0002f, Ck=2, Gravity=(0,0,-9.81f), gamma=rho_water*9.80665. V0 uses the actual binary32 mass divided by rho0. Profile0 J=1; profile1 J=1+(ix+2iz)/512. n=1-(1-n0)/J, V=V0*J, rho=rho_water+(rho0-rho_water)/J, and k=k0*exp((J-1)/((1-n0)*Ck)); J=1 returns k0 exactly. Native rho-cache values are explicitly uploaded as float(rho), before tracking.

The entry uploads its own double Darcy positions, binary32 packed tracking positions, J, native rho-cache, code and CTE material fields. All native points lie in one legitimate4m cell, cell ID0, with an empty boundary group and the full81-fluid range. CTE poscellsize/scell and the division table agree; actual support-radius tests remain in both production kernels. This avoids manufacturing a multiple-cell bit encoding. It is a private neighbor-search fixture, not a production cell-size change.

Each profile calls actual `ComputeFreeSurfaceTracking(KERNEL_Wendland,true,...,false,jg.p)` once. The nonnull J pointer selects porosity-feedback quadrature. Its C/FS/normals/posdiv are downloaded and frozen. Native outputs must be finite, actual inner and FS receivers must exist, and ID76 must actually be FS. No desired label, normal or correction matrix is injected. GPU tracking uses packed binary32 positions; the Darcy RHS and its host reference use the same double positions. The resulting GPU C can differ numerically from CPU C; the reference always uses actual GPU outputs.

## Fields, real calls and checks

Five prescribed instantaneous fields are evaluated OFF then ON for both J profiles:

1. Hydrostatic F0: p_ideal=-4096+rho_water*g_z*(z-1), p=float(p_ideal), Ace=-Gravity. Pressure quantization is propagated explicitly as in CPU r2. This is stationary a_s=0, not freefall.
2. Nonconstant Ace: p=-16+ix/8+iz/16; Ace=(ix/128+iz/256,0,ix/256-iz/128), exactly binary32. It checks the complete Da/LP/Lx/gp/gradJ/chain expression without a continuum-null claim.
3. Variable-k chain: p=-16+ix/4+iz/8, Ace=0. Profile1 must contain at least one actual ON FS chain contribution above its unchanged whole-rate arithmetic budget; profile0 retains the zero-gradJ control.
4. Affine tangent: p=-16+ix/4, Ace=0. It records the real flat-top normal-target residual. No exact geometric normal is inserted and no affine-null claim is imposed.
5. Constant: p=-16, Ace=0. Both OFF and ON rate/reference must be exactly zero for both profiles.

All native p remain strictly negative; nonhydro fields are exact binary32. Before rate calls, the actual positive-only projection wrapper is called with ponding=true/drainage=false and must preserve the entire p/rate arrays bitwise. This tests device value semantics, not actual host integrator staging. The complete real Darcy wrapper uses conductivity=true/Ck2, no wall/periodic/load, and current GPU J/C/FS/normals. Actual inner OFF/ON rates must match bitwise. `free_off_rates.bin` records810 actual OFF floats in profile/field/native-ID order for root's later original/candidate bit comparison; that cross-executable comparison is not claimed by either standalone completion.

After every projection and RHS, all uploaded positions, packed positions, velocity/rho-cache, code, J/theta, p, prescribed Ace, C, labels, normals, posdiv, cell IDs and ranges must remain bit-identical. Two tail slots have finite distinct input canaries; tracking C/FS/normal/posdiv tails and rate/invalid tails are checked too. Invalid starts at N with a second untouched sentinel and must retain those values. The source does not allocate stress/P0/kappa because these wrappers do not accept or advance them; it does not claim a full native-state or integrator test.

## Reference and unchanged budgets

For each receiver use an independent all-particle enumeration with actual GPU C/J/p/Ace. d=xi-xj, gi=Ci*gradW, gj=Cj*gradW, Vj=V0*Jj, w=Vj*d.(gi+gj)/(r2+Eta2). Assemble LP, Lx, gp=-sum(Vj*gi*dp), Da=sum(Vj*(Aj-Ai).gi), and gradJ=sum(Vj*gi*(Jj-Ji)). k'=ki/((1-n0)*Ck), s=Kw/(n*gamma).

OFF/interior use c=gp and lap=LP-c.Lx+rho*Da. Raw ON FS use c=gp and lap=LP+rho*(Ai.Lx+Da). Normal ON FS use c=gp-n*(n.(gp+rho*Ai))/|n|^2 and lap=LP-c.Lx+rho*Da. Every branch uses chain=k'*gradJ.(c+rho*Ai), rate=s*(ki*lap+chain). Thus the candidate's chain projection is tested, not omitted.

Reuse B=32*FLT_EPSILON+4096*DBL_EPSILON exactly. LPabs=sum|w*dp|, DAabs=sum(Vj*sum|deltaA_component*gi_component|). Arithmetic budget is B*max(1,s*(ki*LAPabs+k'*sum|gradJ_component*(c+rho*Ai)_component|)), with LAPabs=LPabs+rho*DAabs plus rho*sum|Ai_component*Lx_component| for raw FS, otherwise sum|c_component*Lx_component|. No empirical GPU tolerance is added.

Hydro quantization uses epsilon_i=|p_float_i-p_ideal_i|, QL=sum|w|*(epsilon_i+epsilon_j), QG=sum(Vj*abs(gi)*(epsilon_i+epsilon_j)). T is the actual-normal tangent projector for normal ON FS and identity otherwise. QLx=0 for raw ON FS, otherwise T*Lx. Q=s*(ki*(QL+abs(QLx).QG)+k'*abs(T*gradJ).QG). Require hydro |actual_rate|<=2*arithmetic_budget+Q, exactly as the valid CPU control. This does not remove GPU packed-position/tracking arithmetic or turn F0 into a new physical acceptance threshold. A failed gate must be preserved and understood before changing the manufacture or budget.

## Outputs and later root review

Fresh output has `Run.out` with actual device0 name/compute capability and CUDA runtime/driver versions; `nodes.csv` with162 rows and the CPU-compatible ledger/normal/C columns; `controls.csv` with1620 rows and both actual/reference rates, actual bits, budgets and operator terms; `free_off_rates.bin` with810 floats; and completion only after all checks and output writes pass. Completion labels formula reference, GPU-generated FS/C, zero physical steps, no full basis/eigenvalues/coupled-stability or CPU/GPU bitwise proof, and physical_acceptance=false.

Root separately reviews source/build closures, admits actual GPU Debug memcheck with distinct console/sanitizer logs, and checks genuine tool/target exits, zero ERROR/leak summaries and complete outputs. Original/candidate OFF files and same-ID nodes/first-three CPU controls can then be compared offline. Actual GPU C/normal differences must be retained in that comparison; CPU arrays must not be substituted to force parity. Debug/Release equivalence, timestep sufficiency, conservative flux, mDBC behavior, NoPen reaction, C08 causation and any physical trial require separate evidence and authorization. This component creates no new physical run, half-chain, PRE, XML, native decode, VTK or automatic follow-on.
