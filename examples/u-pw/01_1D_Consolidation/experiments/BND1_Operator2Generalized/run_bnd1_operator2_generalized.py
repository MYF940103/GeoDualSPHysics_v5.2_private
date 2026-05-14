#!/usr/bin/env python3
"""Run BND1 CPU boundary-operator verification cases."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIN = ROOT.parents[4] / "bin" / "windows"
GENCASE = BIN / "GenCase_win64.exe"
CPU = BIN / "DualSPHysics5.2CPU_win64.exe"

CASES = [
    "Case1DConsolidation_PR_BND1_L3c_Mode1",
    "Case1DConsolidation_PR_BND1_L3c_Mode2",
    "Case1DConsolidation_PR_BND1_L5_Mode1",
    "Case1DConsolidation_PR_BND1_L5_Mode2",
]


def run(cmd: list[Path | str]) -> None:
    print(" ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=ROOT, check=True)


def main() -> None:
    for case in CASES:
        out = ROOT / f"{case}_cpu_out"
        if out.exists():
            shutil.rmtree(out)
        run([GENCASE, f"{case}_Def", out / case, "-save:all"])
        run([CPU, "-cpu", "-mdbc", out / case, out, "-dirdataout", "data", "-sv:csv,binx"])


if __name__ == "__main__":
    main()
