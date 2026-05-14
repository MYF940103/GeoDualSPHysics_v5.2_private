#!/usr/bin/env python3
"""Generate M3m refined platen/edge geometry diagnostic cases."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "M3l_PlatenSpecimenSmoothing" / "CaseM3l_PlatenOverhang_Def.xml"
TIME_MAX = "0.0025"
TIME_OUT = "0.0001"

CASES = [
    {
        "name": "CaseM3m_OverhangReference",
        "description": "M3m self-contained reference: M3l platen overhang geometry",
        "platen_radius": "0.04",
        "geometry": "single",
    },
    {
        "name": "CaseM3m_Overhang045",
        "description": "Optimized overhang diagnostic: platen radius 0.045 m",
        "platen_radius": "0.045",
        "geometry": "single",
    },
    {
        "name": "CaseM3m_TrimmedEdge",
        "description": "Overhang plus trimmed specimen cap edge",
        "platen_radius": "0.04",
        "geometry": "trimmed",
    },
    {
        "name": "CaseM3m_SteppedCap",
        "description": "Overhang plus stepped specimen cap transition",
        "platen_radius": "0.04",
        "geometry": "stepped",
    },
    {
        "name": "CaseM3m_Overhang045Extended",
        "description": "Short extended check for the improved 0.045 m overhang",
        "platen_radius": "0.045",
        "geometry": "single",
        "time_max": "0.004",
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


def ensure_var(root: ET.Element, name: str, value: str) -> None:
    predef = root.find(".//predefinition")
    if predef is None:
        raise RuntimeError("predefinition not found")
    for elem in predef.findall("newvarcte"):
        if name in elem.attrib:
            elem.set(name, value)
            return
    predef.append(ET.Element("newvarcte", {name: value}))


def cylinder_like(template: ET.Element, radius: str, z0: str, z1: str) -> ET.Element:
    elem = copy.deepcopy(template)
    elem.set("radius", radius)
    pts = elem.findall("point")
    if len(pts) != 2:
        raise RuntimeError("expected 2 points in specimen cylinder")
    pts[0].set("x", "0")
    pts[0].set("y", "0")
    pts[0].set("z", z0)
    pts[1].set("x", "0")
    pts[1].set("y", "0")
    pts[1].set("z", z1)
    return elem


def replace_specimen_geometry(root: ET.Element, geometry: str) -> None:
    main = root.find(".//commands/mainlist")
    if main is None:
        raise RuntimeError("mainlist not found")
    cylinders = main.findall("drawcylinder")
    if len(cylinders) < 3:
        raise RuntimeError("expected bottom/top/specimen cylinders")
    specimen = cylinders[2]
    children = list(main)
    idx = children.index(specimen)
    main.remove(specimen)

    if geometry == "single":
        new_items = [cylinder_like(specimen, "#R", "0", "#Hcyl")]
    elif geometry == "trimmed":
        new_items = [
            cylinder_like(specimen, "0.025", "0", "0.01"),
            cylinder_like(specimen, "#R", "0.01", "0.09"),
            cylinder_like(specimen, "0.025", "0.09", "#Hcyl"),
        ]
    elif geometry == "stepped":
        new_items = [
            cylinder_like(specimen, "0.025", "0", "0.01"),
            cylinder_like(specimen, "0.028", "0.01", "0.02"),
            cylinder_like(specimen, "#R", "0.02", "0.08"),
            cylinder_like(specimen, "0.028", "0.08", "0.09"),
            cylinder_like(specimen, "0.025", "0.09", "#Hcyl"),
        ]
    else:
        raise ValueError(f"unknown geometry {geometry}")

    for item in reversed(new_items):
        main.insert(idx, item)


def apply_common_settings(root: ET.Element, case: dict[str, str]) -> None:
    time_max = str(case.get("time_max", TIME_MAX))
    root.set("date", str(case["description"]))
    set_param(root, "TimeMax", time_max)
    set_param(root, "TimeOut", TIME_OUT)
    set_param(root, "PorePressureFeedback", "0")
    set_param(root, "SavePlatenReactionDiagnostics", "1")
    set_soil_value(root, "SaveMccState", "1")
    set_soil_value(root, "MccSubstepping", "0")
    set_soil_value(root, "MccFailureFallback", "0")

    begin = root.find(".//motion/objreal/begin")
    mvrect = root.find(".//motion/objreal/mvrect")
    if begin is not None:
        begin.set("finish", time_max)
    if mvrect is not None:
        mvrect.set("duration", time_max)

    ensure_var(root, "Rplate", str(case["platen_radius"]))
    cylinders = root.findall(".//commands/mainlist/drawcylinder")
    if len(cylinders) < 2:
        raise RuntimeError("expected platen cylinders")
    cylinders[0].set("radius", "#Rplate")
    cylinders[1].set("radius", "#Rplate")
    replace_specimen_geometry(root, str(case["geometry"]))


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
echo M3m CPU Release completed for {name}.
exit /b 0
"""
    (ROOT / f"xRun_{name}_win64_CPU_release.bat").write_text(text, encoding="utf-8")


def main() -> None:
    base = ET.parse(BASE).getroot()
    for case in CASES:
        root = copy.deepcopy(base)
        apply_common_settings(root, case)
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(ROOT / f"{case['name']}_Def.xml", encoding="utf-8", xml_declaration=True)
        write_bat(str(case["name"]))
    print(f"Generated {len(CASES)} M3m cases in {ROOT}")


if __name__ == "__main__":
    main()
