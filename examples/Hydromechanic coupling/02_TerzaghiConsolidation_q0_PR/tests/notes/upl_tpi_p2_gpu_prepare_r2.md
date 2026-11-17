# GPU P2 preparation r2: exact raw-prefix proof with actual line endings

The original GPU r1 preparation rejected a CRLF host-only declaration block before source-tree creation, compilation or solver invocation. Keep that failure receipt and original writer unchanged. CPU r1 source remains passed and frozen.

This new GPU-only author otherwise clones the reviewed r1 preparation. The marker parser recognizes the actual LF/CRLF ending of the unique end-comment line, requires the entire addition to lie inside exactly one CUDA-excluded guard, removes those exact raw bytes, then still compares every remaining prefix byte against the frozen original. It does not normalize the remaining prefix, loosen a numeric/ABI gate, edit a header or change physics.

New GPU source/receipt/diff paths use upl_tpi_p2_GPU_r2; stage is upl_tpi_p2_gpu_prepare_r2.prepare. The P2 backend header and four-phase writer are unchanged. A new root prepare-only admission is required; no old result is overwritten or reclassified. This is not a build, program or physical acceptance.
