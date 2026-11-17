# P3 private source preparation

Author only; no preparation, build, help, solver or native invocation has occurred.
Each later action requires one root-read source-only admission for CPU or GPU.
The actual passed P2 parent and its Debug build must bind the same source manifest.
All 267 CPU / 270 GPU files are captured into a fresh private P3 source directory.

Only Single.cpp's pressure endpoint loop and banner change. The first two rounds
validate and retain provisional pressure evidence; the third alone commits. Every
round still performs a full force/necessary-dt/HG/Prepare/Write/real-BC transaction.
CPU endpoint/temporary flags clear only before the final real BC. NextEndpoint
captures the next round's HG state once; the first capture remains outside the
loop. Material/J/HG history/global time remain outside the three-endpoint loop.

The two private pressure/dt headers replace the same include names and namespaces.
Base.cpp is byte unchanged from P2, but is recompiled because it owns header
implementations. All other sources and shared structures retain exact bytes.
GPU host-only API removal recognizes the actual LF/CRLF marker line and requires
the entire declaration block excluded by __CUDACC__. Removing P2/P3 blocks must
yield the identical original 3850-byte device-visible prefix. No CUDA source or
object is rebuilt by preparation.

P2's failed top budget and its offline decomposition remain failures, not an
acceptance receipt. New P3 algebra is required but not treated as SPH stability.
This source snapshot admits no physical timestep, full run or reference chain.
Inputs use stat binding, not repeated SHA. Preflight checks precede directory
creation; source/diff/receipt writes are exclusive and failures remain preserved.
The actual reused P2/P1 patch modules and defining modules of the invoked
need/stat/read/same/write/once helpers are pinned in this preparation, rather
than inferred from a historical parent's consumed list.
