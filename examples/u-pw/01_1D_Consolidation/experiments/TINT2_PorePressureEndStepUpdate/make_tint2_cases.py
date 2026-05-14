#!/usr/bin/env python3
"""Create TINT2 pore-pressure time-integration XML/BAT cases."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
EXAMPLES = REPO / "examples" / "u-pw" / "01_1D_Consolidation" / "experiments"
BND1 = EXAMPLES / "BND1_Operator2Generalized"

TEMPLATES = {
    "l3c_op1": BND1 / "Case1DConsolidation_PR_BND1_L3c_Mode1_Def.xml",
    "l5_op1": BND1 / "Case1DConsolidation_PR_BND1_L5_Mode1_Def.xml",
    "l3c_op2": BND1 / "Case1DConsolidation_PR_BND1_L3c_Mode2_Def.xml",
    "l5_op2": BND1 / "Case1DConsolidation_PR_BND1_L5_Mode2_Def.xml",
}

CASES = [
    ("Case1DConsolidation_PR_TINT2_L3c_Op1_Mode0", "l3c_op1", 0, 2, "L3c feedback-off operator 1 current mode"),
    ("Case1DConsolidation_PR_TINT2_L3c_Op1_Mode1", "l3c_op1", 1, 2, "L3c feedback-off operator 1 end-step mode"),
    ("Case1DConsolidation_PR_TINT2_L5_Op1_Mode0", "l5_op1", 0, 2, "L5 feedback-on operator 1 current mode"),
    ("Case1DConsolidation_PR_TINT2_L5_Op1_Mode1", "l5_op1", 1, 2, "L5 feedback-on operator 1 end-step mode"),
    ("Case1DConsolidation_PR_TINT2_L3c_Op2_Mode0", "l3c_op2", 0, 2, "BND1 operator 2 feedback-off current mode"),
    ("Case1DConsolidation_PR_TINT2_L3c_Op2_Mode1", "l3c_op2", 1, 2, "BND1 operator 2 feedback-off end-step mode"),
    ("Case1DConsolidation_PR_TINT2_L5_Op2_Mode0", "l5_op2", 0, 2, "BND1 operator 2 feedback-on current mode"),
    ("Case1DConsolidation_PR_TINT2_L5_Op2_Mode1", "l5_op2", 1, 2, "BND1 operator 2 feedback-on end-step mode"),
    ("Case1DConsolidation_PR_TINT2_Verlet_L3c_Op1_Mode0", "l3c_op1", 0, 1, "Verlet L3c operator 1 current mode smoke"),
    ("Case1DConsolidation_PR_TINT2_Verlet_L3c_Op1_Mode1", "l3c_op1", 1, 1, "Verlet L3c operator 1 end-step mode smoke"),
]


def parameter_map(root: ET.Element) -> dict[str, ET.Element]:
    return {elem.attrib.get("key", ""): elem for elem in root.findall(".//parameter") if elem.attrib.get("key")}


def set_param(root: ET.Element, key: str, value: str, comment: str | None = None) -> None:
    params = parameter_map(root)
    if key in params:
        elem = params[key]
    else:
        parent = root.find(".//parameters")
        if parent is None:
            raise RuntimeError("No <parameters> node found")
        elem = ET.SubElement(parent, "parameter", {"key": key})
    elem.set("value", value)
    if comment is not None:
        elem.set("comment", comment)


def write_bat(case: str) -> None:
    text = f"""@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set name={case}
set dirout=%name%_cpu_out
set diroutdata=%dirout%\\data
set dirbin=..\\..\\..\\..\\..\\bin\\windows
set gencase="%dirbin%\\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\\DualSPHysics5.2CPU_win64.exe"
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\\%name% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysicscpu% -cpu -mdbc %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx
if not "%ERRORLEVEL%" == "0" goto fail
echo All done
goto end
:fail
echo Execution aborted.
exit /b 1
:end
exit /b 0
"""
    with (ROOT / f"x{case}_win64_CPU_release.bat").open("w", newline="\r\n") as fp:
        fp.write(text)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for case, template_key, mode, step_algorithm, comment in CASES:
        tree = ET.parse(TEMPLATES[template_key])
        root = tree.getroot()
        set_param(root, "StepAlgorithm", str(step_algorithm), "1:Verlet, 2:Symplectic")
        set_param(root, "PorePressureTimeIntegrationMode", str(mode), comment)
        set_param(root, "TimeMax", "0.005", "TINT2 short CPU verification duration",)
        set_param(root, "TimeOut", "0.001", "Dense output for TINT2 comparisons")
        tree.write(ROOT / f"{case}_Def.xml", encoding="utf-8", xml_declaration=True)
        write_bat(case)

    shutil.copyfile(ROOT / "make_tint2_cases.py", ROOT / "make_tint2_cases_used.py")


if __name__ == "__main__":
    main()
