# Synthetic schema1/schema2 loader test (author only)

This is a five-ID, complete22-array native format/loader test. It does not solve
mechanics, generate or certify a physical PRE, or edit any retained BI4. Each
fixture is written from explicit synthetic arrays into a separate new directory
under `tests/outputs/c08_preload_schema2_loader_r1_synthetic`. The application and
case names say SYNTHETIC. No real source state is used or rewritten.

The helper calls the actual new `JGravityPreloadState::Load`, including its old
signature with the optional argument omitted. Three schema1 cases accept the
old law1/law2 zero-kappa states and the weaker source cohesion case. Schema2
accepts both positive and zero soil kappa, and compares every returned primary
state bit, raw ID order, ById map, FS, clock and release registry. The five-ID
array order is deliberately nontrivial within fixed/soil groups. All fixtures
have real typed22 layouts and exact n/V/rho/k(J), density-cache, P0/excess,
signed-step and scalar+=dt relationships; one free-seepage soil has negative p.

Nineteen cases must reject for the expected reason: schema1 positive kappa;
schema2 negative soil kappa, nonzero fixed kappa, legacy law1, unknown schema,
elastic-source flag, empty target contract2, typed source cohesion mismatch,
and contract2 mismatches in cp, psi, decay, DP enum, residual cohesion,
softening rate, K, G, softening/trigger policies or the base phi contract.
Each fixture differs from its accepted control in the stated field. A rejection
must contain the case-specific diagnostic substring; an unrelated failure is
not a pass. The diagnostic tests do not replace actual configuration/parser or
physical-material admissibility tests.

Contract2 serialization follows the new public format, but its base contract is
explicitly synthetic. DP is the internal enum token, not an XML DPCtes value.
These tests establish exact contract comparison and history carriage by the
loader, not completeness of JSph's material/configuration signature generation.
The root's real schema2 integration test must separately exercise that path.

`c08_preload_schema2_loader_r1.py build --execution-authorized` compiles one
test object and links the six sealed ReleaseCPU utility objects only. The
utility archive provides unchanged BI4 ABI headers; the actual new loader
header is copied into the fresh build directory and recorded. Flags are
MSVC14.36, C++17, /O2 /MT /fp:precise /GL-, with wmain entry. There is no
JAppInfo global and no JSph, CPU/GPU force, material update or solver object.
`run --execution-authorized` is separate and invokes the helper once using the
existing typed Popen/Win32 owner. It writes tests.csv, completion.json and a
small check receipt. Existing/partial outputs, calls and receipts are refused;
failure evidence remains. There is no automatic build/run/next job or queue.

## Minimal real-program regression plan (not executed here)

1. Use the same unchanged old H=.048, dt=2.5us, strict elastic source AS0 input
   for retained runtime_r6 and the new program: 8000 updates (20ms), TimeOut .01,
   with the release event still at10s and original source flags. Use fresh tags,
   normal owned exits/necessary dt/IDs/22 ledger/FS/clock guards, then compare
   original22 payloads and actual clocks/signed values bytewise. Exact output
   steps follow scalar replay and the forced final save. This tests the old
   source body; it does not certify a ten-second or plastic PRE. The old
   upl_material_preload_GPU_r1 is NOT a20ms reference: its receipt says8192 steps,
   physical time .03125s and257 frames.
2. Import the actual retained certified law1 r2GPU Part1000 into the new program
   using the old schema1 H=.048/dt2.5us/keep5/AS.2-n3/CompletedOnly receiver
   configuration. Stop after10 updates, END4000010, with one forced final save.
   The sealed C08CausalNative ten-update profile already reads this shape; no
   new one-step reader or source replay is needed. Check the actual typed PRE
   schema1/old contract, loaded4M scalar time, all6805/22/P0/J/ledger/FS/clock/
   signed guards. This proves real schema1 compatibility, not a general restart
   or new bedroles registry. Keep its original PRE and genuine headers intact.

No helper was built or run during authoring. Default CPU Debug and subsequent
private CPU/GPU builds are owned by root after review. These tests do not admit
any collapse model, new source equilibrium, material transfer or other psi.
