"""Emit an apply_patch for formal inputs, preserving the existing case XML/BAT style."""
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

CASE = Path(__file__).resolve().parents[2]
STEM = "CaseTerzaghiConsolidation_q0_PR_full_"


def value(text, selector, v, comment=None):
    text, n = re.subn(r'(<'+selector+r'\s+value=")[^"]*(")', lambda m: m[1]+str(v)+m[2], text)
    assert n == 1, selector
    if comment:
        text, n = re.subn(r'(<'+selector+r'\s+value="[^"]*"\s+comment=")[^"]*(")', lambda m: m[1]+comment+m[2], text)
        assert n == 1
    return text


def inputs():
    original = (CASE/(STEM+"k1em4_Def.xml")).read_text(encoding="utf-8-sig")
    changes, settings = {}, {}
    E, nu, H, rho = map(Decimal, ("2e6", ".3", "1", "1000"))
    M = E*(1-nu)/((1+nu)*(1-2*nu))
    for key, k, dt, interval in (("k1em3", "1e-3", "0.000001", "0.001"), ("k1em4", "1e-4", "0.00001", "0.01"), ("k1em5", "1e-5", "0.00001", "0.1")):
        cv = Decimal(k)*M/(rho*Decimal("9.81"))
        steps = int(((Decimal(".01")+2*H*H/cv)/Decimal(dt)).to_integral_value(rounding=ROUND_CEILING))
        duration = str(Decimal(steps)*Decimal(dt))
        text = value(original, "HydraulicConductivity", k)
        text = value(text, "HydroMechTopLoadMode", "TopKernelBand", "Normalized kernel-support top load; same total q0 as TopVertical")
        for name, v, comment in (("SavePosDouble", "1", None), ("SoilDampingCoef", "0.04", "Accepted case-02 soil damping coefficient"),
            ("DtIni", dt, "Initial step equals the validated fixed step"), ("DtFixed", dt, "Formal fixed step; conductivity-specific stability limit"),
            ("TimeMax", duration, "Formal 2Tv endpoint rounded up to the fixed-step grid"),
            ("TimeOut", interval, "Native particle output interval; references use actual saved times")):
            text = value(text, 'parameter key="'+name+'"', v, comment)
        lines = ('      <parameter key="SoilStressRateGradCorr" value="1" comment="Correct soil stress-rate velocity gradients" />\n'
                 '      <parameter key="SoilHourglassXi" value="0.1" comment="Validated elastic small-rotation HG strength; fresh starts only" />\n'
                 '      <parameter key="SoilBoundaryDerivativeSPR" value="1" comment="Fixed-plane mDBC mirrored velocity for S/P/R derivatives" />\n')
        assert 'key="SoilHourglassXi"' not in text
        text = text.replace('      <parameter key="SoilDamping"', lines+'      <parameter key="SoilDamping"', 1)
        marker = re.search(r'(?m)^([ \t]*)<HydroMechDrainageStartTime[^\n]*\n', text)
        assert marker and "HydroMechDrainageFixedGrid" not in text
        text = text[:marker.end()] + marker[1]+'<HydroMechDrainageFixedGrid value="1" comment="Align the fixed-grid drainage event within accumulated-time roundoff only" />\n'+text[marker.end():]
        root = ET.fromstring(text)
        assert len(root.findall("execution/parameters/parameter[@key='TimeOut']")) == 1
        assert root.find("execution/special/timeout") is None
        changes[CASE/(STEM+key+"_Def.xml")] = text
        settings[key] = dict(k=k, dt=dt, duration=duration, steps=steps, interval=interval)
        for backend in ("CPU", "GPU"):
            executable = "DualSPHysics5.2CPU_win64.exe" if backend == "CPU" else "DualSPHysics5.2_GEO_win64.exe"
            option = "-cpu -ompthreads:1" if backend == "CPU" else "-gpu:0 -ompthreads:1"
            case = STEM+key
            # Same declaration/error-label layout as the existing formal BAT; no delete or -force path.
            bat = f'''@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case={case}
set dirout=%case%_release_{backend}_out
set diroutdata=%dirout%\\data
set nsteps={steps}

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/{executable}"
set partvtk="%dirbin%/PartVTK_win64.exe"
set python=python
if exist "D:\\Anaconda3\\python.exe" set python=D:\\Anaconda3\\python.exe
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress

if /i "%~1"=="-postprocess" goto postprocess
if exist "%dirout%" (
  echo Protected output "%dirout%" already exists. No files were deleted.
  echo Use -postprocess to review a completed run, or choose a new explicit output name.
  goto abort
)

rem Formal elastic u-pw PR consolidation: {k} m/s, 2Tv, HG/SPR/band enabled.
%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysics% {option} -stable -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -nsteps:%nsteps%
if not "%ERRORLEVEL%" == "0" goto fail

:postprocess
set vtkdir=%dirout%\\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

"%python%" -B support/release_case.py --output "%dirout%" --label full_validation_release_{key}_{backend}
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo q0 Terzaghi consolidation {k} formal calculation and plots done.
popd
exit /b 0

:abort
echo Existing results preserved; no solver was launched.
popd
exit /b 0

:fail
echo q0 Terzaghi consolidation {k} stopped. Existing data are preserved.
popd
exit /b 1
'''
            changes[CASE/("x"+case+"_win64_"+backend+".bat")] = bat
    return changes, settings


def main():
    changes, settings = inputs()
    patch = "*** Begin Patch\n"
    for path, new in changes.items():
        if path.exists():
            old = path.read_text(encoding="utf-8-sig")
            patch += "*** Update File: "+str(path)+"\n@@\n"+"\n".join("-"+s for s in old.splitlines())+"\n"
        else:
            patch += "*** Add File: "+str(path)+"\n"
        patch += "\n".join("+"+s for s in new.splitlines())+"\n"
    patch += "*** End Patch"
    print(json.dumps(dict(settings=settings, patch=patch)))


if __name__ == "__main__":
    main()
