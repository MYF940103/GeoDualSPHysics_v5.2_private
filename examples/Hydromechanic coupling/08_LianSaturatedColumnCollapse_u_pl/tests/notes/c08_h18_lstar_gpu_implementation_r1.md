# C08 receiver-C bare Darcy GPU implementation qualification

Three private GPU builds passed: Debug ON, Release OFF, Release ON. Each retains 112 original objects and replaces only the GPU pressure kernel object; the only formula change is the LP/Lx weight. Public source, canonical programs and formal inputs remain unchanged.

The independent Release OFF one-update run and unique native read passed. Its genuine header stays 1 frame versus the old 91-frame reference; the first payload (actual time plus all 22 arrays), layout and signed-clock row are byte-identical. No count rewrite or interpolation was used.

The Debug ON two-update run passed actual compute-sanitizer memcheck with zero errors and leaks, and unique native checks for two frames / all 6805 IDs. This is four force substages, not a 2-ms physical test or Release bit truth. Native clock error is zero; ledger error is zero. Original signed dterror <=1e-14, geometry, P0, FS, material and fixed-marker guards remain intact. The old utility metadata is retained verbatim; new operator identity is established by the actual private program/source/macro binding, not by metadata relabelling.

CPU manufactured-rate improvement and this implementation qualification justify considering one independently admitted 0.9-s dynamic psi0 window. They do not select the operator, establish paper accuracy, resolve clumping or admit other psi/formal/half runs. The original AS.3/n2.55 control, PRE and all rejected candidates remain protected. No SHA scan was made.
