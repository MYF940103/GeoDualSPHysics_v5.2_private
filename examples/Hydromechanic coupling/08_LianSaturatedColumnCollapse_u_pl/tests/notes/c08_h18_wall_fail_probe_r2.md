# AS.7 terminal printf replay r2 label derivative

Authoring only. Only support/c08_h18_wall_fail_probe_r2.py and this note are new. No helper import/execution, preparation, admission, build, GenCase, solver, native decoder, hash or Git operation is performed here.

The r1 launch stopped at the existing artifact guard: the external launcher had created c08_h18_wall_fail_probe_GPU_r1.launch.json and its launcher log under the protected job prefix. The run never entered claim, GenCase or solver. Preserve all r1 configuration, preparation, admission, launch and launcher artifacts; do not restart that tag.

The new script is an exact two-assignment derivative of the retained r1 script. Original line 10, TAG='c08_h18_wall_fail_probe_GPU_r1', becomes TAG='c08_h18_wall_fail_probe_GPU_r2'. Original line 11, NOTE=T/'notes/c08_h18_wall_fail_probe_r1.md', becomes NOTE=T/'notes/c08_h18_wall_fail_probe_r2.md'. Both anchors matched exactly once. Replacing the new NOTE assignment with the original NOTE assignment, then the new TAG assignment with the original TAG assignment, reconstructed the original r1 byte string exactly. Direct line comparison found only lines 10 and 11 changed; both scripts have 166 lines. No parser import or helper execution was used for this text proof.

All guards and allowed artifact lists are unchanged, including the broad TAG+'.*' protection. External launcher artifacts must therefore use the different prefix c08_h18_wall_fail_launch_r2.*. Do not add launch/launcher files to the run guard's allowed set.

Root must fully read the derivative and independently authorize new-tag preparation and admission. Fresh preparation will create only the new-tag config/prepare evidence when later invoked. A separately admitted run retains the original full 91-frame plan, .9 s target, actual same Wendland PRE, AS.7 input, separately passed private r2 printf build, unchanged actual-handle owner and all original native/source/runtime binding checks. No automatic native/VTK or additional solver action has been added.

Later explicit commands, from the case root and only after the corresponding root authorization, use tests/support/c08_h18_wall_fail_probe_r2.py prepare --execution-authorized or tests/support/c08_h18_wall_fail_probe_r2.py run --execution-authorized. The fresh job tag is c08_h18_wall_fail_probe_GPU_r2. The existing notes/c08_h18_wall_fail_probe_r1.md remains the detailed behavior reference; the two exact assignment substitutions above are the complete code delta.
