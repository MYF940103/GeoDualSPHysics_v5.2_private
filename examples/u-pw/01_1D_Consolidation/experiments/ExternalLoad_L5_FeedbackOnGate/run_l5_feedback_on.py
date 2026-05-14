#!/usr/bin/env python3
"""Run L5 feedback-on 1D consolidation coupling-gate cases."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


CASES = {
    "low": "Case1DConsolidation_PR_FeedbackOn_L5_LowAmp",
    "target": "Case1DConsolidation_PR_FeedbackOn_L5_TargetAmp",
}

ROOT = Path(__file__).resolve().parents[5]
BIN = ROOT / "bin" / "windows"
GENCASE = BIN / "GenCase_win64.exe"
GPU_EXE = BIN / "DualSPHysics5.2_GEO_win64.exe"
CPU_EXE = BIN / "DualSPHysics5.2CPU_win64.exe"


def run(cmd: list[str], cwd: Path) -> None:
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def remove(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def run_case(case_key: str, kind: str, clean: bool) -> None:
    cwd = Path(__file__).resolve().parent
    case = CASES[case_key]
    outdir = cwd / f"{case}_{kind}_out"
    if clean:
        remove(outdir)
    outdir.mkdir(exist_ok=True)

    run([str(GENCASE), f"{case}_Def", str(outdir / case), "-save:all"], cwd)
    exe = GPU_EXE if kind == "gpu" else CPU_EXE
    flag = "-gpu" if kind == "gpu" else "-cpu"
    run([str(exe), flag, "-mdbc", str(outdir / case), str(outdir), "-dirdataout", "data", "-sv:csv,binx"], cwd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["low", "target", "all"], default="all")
    parser.add_argument("--gpu-target", action="store_true")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    keys = ["low", "target"] if args.case == "all" else [args.case]
    for key in keys:
        run_case(key, "cpu", clean=not args.no_clean)

    if args.gpu_target:
        run_case("target", "gpu", clean=not args.no_clean)


if __name__ == "__main__":
    main()
