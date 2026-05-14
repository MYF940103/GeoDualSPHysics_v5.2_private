#!/usr/bin/env python3
"""Generate M3k very-short dense-output MCC platen/edge diagnostic case."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "M3h_MCCAdmissibleReturn" / "CaseM3h_MCCMildBaseline_Def.xml"
CASE = "CaseM3k_MCCMildDenseOnset"
TIMEMAX = "0.0025"
TIMEOUT = "0.0001"


def find_param(root: ET.Element, key: str) -> ET.Element:
    for elem in root.findall(".//parameter"):
        if elem.get("key") == key:
            return elem
    raise KeyError(key)


def main() -> None:
    tree = ET.parse(SRC)
    root = tree.getroot()
    root.set("date", "M3k very-short dense-output MCC platen/edge onset diagnostic")
    for elem in root.findall(".//begin"):
        if elem.get("mov") == "1":
            elem.set("finish", TIMEMAX)
    for elem in root.findall(".//mvrect"):
        if elem.get("id") == "1":
            elem.set("duration", TIMEMAX)
    find_param(root, "TimeMax").set("value", TIMEMAX)
    find_param(root, "TimeOut").set("value", TIMEOUT)
    # Keep the old single-step baseline to reproduce the first onset cleanly.
    out_xml = ROOT / f"{CASE}_Def.xml"
    ET.indent(tree, space="  ")
    tree.write(out_xml, encoding="utf-8", xml_declaration=True)

    bat = ROOT / f"xRun_{CASE}_win64_CPU_release.bat"
    bat.write_text(
        "@echo off\n"
        "setlocal\n"
        "set dirbin=..\\..\\..\\..\\..\\bin\\windows\n"
        "set gencase=\"%dirbin%\\GenCase_win64.exe\"\n"
        "set dualsphysicscpu=\"%dirbin%\\DualSPHysics5.2CPU_win64.exe\"\n"
        f"set name={CASE}\n"
        "set dirout=%name%_out\n"
        "if exist %dirout% rd /s /q %dirout%\n"
        "%gencase% %name%_Def %dirout%\\%name% -save:all\n"
        "if not \"%ERRORLEVEL%\" == \"0\" exit /b 1\n"
        "%dualsphysicscpu% -cpu %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx -svres\n"
        "if not \"%ERRORLEVEL%\" == \"0\" exit /b 1\n"
        f"echo M3k CPU Release completed for {CASE}.\n"
        "exit /b 0\n",
        encoding="ascii",
    )
    (ROOT / "README.md").write_text(
        "# M3k Platen/Edge Dense Diagnostic\n\n"
        "Very-short dense-output MCC case around the first return-failure onset. "
        "Generated from the M3h mild MCC baseline with `TimeMax=0.0025` and "
        "`TimeOut=0.0001`.\n",
        encoding="ascii",
    )


if __name__ == "__main__":
    main()
