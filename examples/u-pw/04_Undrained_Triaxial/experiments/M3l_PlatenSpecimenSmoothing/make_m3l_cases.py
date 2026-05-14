#!/usr/bin/env python3
"""Generate M3l platen/specimen smoothing diagnostic cases."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "M3k_PlatenEdgeDenseDiagnostic" / "CaseM3k_MCCMildDenseOnset_Def.xml"
TIME_MAX = "0.0025"
TIME_OUT = "0.0001"

CASES = [
    {
        "name": "CaseM3l_BaselineDense",
        "description": "M3l baseline dense reference copied from M3k",
    },
    {
        "name": "CaseM3l_Gap2Dp",
        "description": "Generated platen/specimen center gap increased from 1Dp to 2Dp",
        "gap2dp": True,
    },
    {
        "name": "CaseM3l_PlatenOverhang",
        "description": "Platen radius enlarged to 0.04 m while specimen radius stays 0.03 m",
        "platen_radius": "0.04",
    },
    {
        "name": "CaseM3l_EdgeSelectorBuffer",
        "description": "Lateral confinement cap/edge exclusion increased to 0.025 m",
        "cap_edge_exclusion": "0.025",
    },
]


def set_param(root: ET.Element, key: str, value: str) -> None:
    for elem in root.findall(".//parameter"):
        if elem.get("key") == key:
            elem.set("value", value)
            return
    raise KeyError(f"parameter {key} not found")


def set_soil_value(root: ET.Element, name: str, value: str) -> None:
    elem = root.find(f".//{name}")
    if elem is None:
        raise KeyError(f"soil element {name} not found")
    elem.set("value", value)


def write_bat(name: str) -> None:
    text = f"""@echo off
setlocal
set dirbin=..\\..\\..\\..\\..\\bin\\windows
set gencase="%dirbin%\\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\\DualSPHysics5.2CPU_win64.exe"
set name={name}
set dirout=%name%_out
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\\%name% -save:all
if not "%ERRORLEVEL%" == "0" exit /b 1
%dualsphysicscpu% -cpu %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx -svres
if not "%ERRORLEVEL%" == "0" exit /b 1
echo M3l CPU Release completed for {name}.
exit /b 0
"""
    (ROOT / f"xRun_{name}_win64_CPU_release.bat").write_text(text, encoding="utf-8")


def add_platen_radius_var(root: ET.Element, value: str) -> None:
    predef = root.find(".//predefinition")
    if predef is None:
        raise RuntimeError("predefinition not found")
    for elem in predef.findall("newvarcte"):
        if "Rplate" in elem.attrib:
            elem.set("Rplate", value)
            return
    predef.append(ET.Element("newvarcte", {"Rplate": value}))


def apply_variant(root: ET.Element, case: dict[str, str | bool]) -> None:
    root.set("date", case["description"])
    set_param(root, "TimeMax", TIME_MAX)
    set_param(root, "TimeOut", TIME_OUT)
    set_param(root, "PorePressureFeedback", "0")
    set_param(root, "SavePlatenReactionDiagnostics", "1")
    set_soil_value(root, "SaveMccState", "1")
    set_soil_value(root, "MccSubstepping", "0")
    set_soil_value(root, "MccFailureFallback", "0")

    begin = root.find(".//motion/objreal/begin")
    mvrect = root.find(".//motion/objreal/mvrect")
    if begin is not None:
        begin.set("finish", TIME_MAX)
    if mvrect is not None:
        mvrect.set("duration", TIME_MAX)

    cylinders = root.findall(".//commands/mainlist/drawcylinder")
    if len(cylinders) < 3:
        raise RuntimeError("expected bottom/top/specimen cylinders")

    if case.get("gap2dp"):
        bottom_points = cylinders[0].findall("point")
        top_points = cylinders[1].findall("point")
        bottom_points[0].set("z", "#-3*Dp")
        bottom_points[1].set("z", "#-1.5*Dp")
        top_points[0].set("z", "#Hcyl+1.5*Dp")
        top_points[1].set("z", "#Hcyl+3*Dp")

    if "platen_radius" in case:
        add_platen_radius_var(root, str(case["platen_radius"]))
        cylinders[0].set("radius", "#Rplate")
        cylinders[1].set("radius", "#Rplate")

    if "cap_edge_exclusion" in case:
        value = str(case["cap_edge_exclusion"])
        set_param(root, "ConfiningStressCapExclusionLength", value)
        set_param(root, "ConfiningStressEdgeExclusionLength", value)


def main() -> None:
    tree = ET.parse(BASE)
    base_root = tree.getroot()
    for case in CASES:
        root = copy.deepcopy(base_root)
        apply_variant(root, case)
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(ROOT / f"{case['name']}_Def.xml", encoding="utf-8", xml_declaration=True)
        write_bat(str(case["name"]))
    print(f"Generated {len(CASES)} M3l cases in {ROOT}")


if __name__ == "__main__":
    main()
