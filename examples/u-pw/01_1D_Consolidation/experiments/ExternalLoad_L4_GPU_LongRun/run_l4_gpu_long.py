#!/usr/bin/env python3
"""Run the L4 GPU long-run 1D consolidation gate without interactive BAT prompts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


CASE = "Case1DConsolidation_PR_ExternalLoad_L4_GPU_Long"
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


def run_case(kind: str, clean: bool) -> None:
    cwd = Path(__file__).resolve().parent
    outdir = cwd / f"{CASE}_{kind}_out"
    if clean:
        remove(outdir)
    outdir.mkdir(exist_ok=True)

    run([str(GENCASE), f"{CASE}_Def", str(outdir / CASE), "-save:all"], cwd)
    exe = GPU_EXE if kind == "gpu" else CPU_EXE
    flag = "-gpu" if kind == "gpu" else "-cpu"
    run([str(exe), flag, "-mdbc", str(outdir / CASE), str(outdir), "-dirdataout", "data", "-sv:csv,binx"], cwd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu", action="store_true", help="Run CPU as well as GPU. This is expected to be slow.")
    parser.add_argument("--no-clean", action="store_true", help="Keep existing output folders.")
    args = parser.parse_args()

    run_case("gpu", clean=not args.no_clean)
    if args.cpu:
        run_case("cpu", clean=not args.no_clean)


if __name__ == "__main__":
    main()
