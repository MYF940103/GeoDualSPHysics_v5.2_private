# M3e MCC Feedback-Off Package

This package consolidates existing M3c, M3d, M3d2, and M3d3 MCC feedback-off
triaxial diagnostics. It does not contain new solver runs.

Key package conclusion:

- high-pc MCC remains elastic-like in the feedback-off platen workflow.
- mild MCC yields and updates pc, void ratio, and plastic strain.
- original-rate mild MCC still has local return failures.
- adaptive fallback removes final -3 status by marking partial fallback (-5), so it is
  a safety diagnostic rather than a validation setting.
- half-speed adaptive is the cleanest final-frame route:
  `0:12|1:395`.
- fallback final status is `-5:17|0:2|1:387|2:1`.

Generated tables and figures are kept in this directory. Heavy solver outputs are
not included.
