#!/usr/bin/env python3
"""Generate M3n smooth-layout feasibility cases from M3m overhang045."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "M3m_RefinedPlatenEdgeGeometry" / "CaseM3m_Overhang045_Def.xml"

CASES = [
    ("CaseM3n_Overhang045Reference", "M3n Dp=0.01 overhang045 reference", "0.01"),
    ("CaseM3n_Dp0075Overhang045", "M3n Dp=0.0075 higher-resolution overhang045", "0.0075"),
]


def set_var(root: ET.Element, name: str, value: str) -> None:
    for elem in root.findall(".//predefinition/newvarcte"):
        if name in elem.attrib:
            elem.set(name, value)
            return
    predef = root.find(".//predefinition")
    if predef is None:
        raise RuntimeError("predefinition not found")
    predef.append(ET.Element("newvarcte", {name: value}))


def set_param(root: ET.Element, key: str, value: str) -> None:
    for elem in root.findall(".//parameter"):
        if elem.get("key") == key:
            elem.set("value", value)
            return
    raise KeyError(key)


def set_soil(root: ET.Element, name: str, value: str) -> None:
    elem = root.find(f".//{name}")
    if elem is None:
        raise KeyError(name)
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
echo M3n CPU Release completed for {name}.
exit /b 0
"""
    (ROOT / f"xRun_{name}_win64_CPU_release.bat").write_text(text, encoding="utf-8")


def main() -> None:
    base = ET.parse(BASE).getroot()
    for name, desc, dp in CASES:
        root = copy.deepcopy(base)
        root.set("date", desc)
        set_var(root, "Dp", dp)
        set_var(root, "Rplate", "0.045")
        set_param(root, "TimeMax", "0.0025")
        set_param(root, "TimeOut", "0.0001")
        set_param(root, "PorePressureFeedback", "0")
        set_param(root, "SavePlatenReactionDiagnostics", "1")
        set_soil(root, "SaveMccState", "1")
        set_soil(root, "MccSubstepping", "0")
        set_soil(root, "MccFailureFallback", "0")
        begin = root.find(".//motion/objreal/begin")
        mvrect = root.find(".//motion/objreal/mvrect")
        if begin is not None:
            begin.set("finish", "0.0025")
        if mvrect is not None:
            mvrect.set("duration", "0.0025")
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(ROOT / f"{name}_Def.xml", encoding="utf-8", xml_declaration=True)
        write_bat(name)
    print(f"Generated {len(CASES)} M3n cases in {ROOT}")


if __name__ == "__main__":
    main()
