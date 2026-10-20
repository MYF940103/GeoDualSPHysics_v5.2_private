"""Fixed short-window diagnostics only; a rejected 100-Pa result never admits a long run."""
import argparse
from decimal import Decimal
import io
import json
from pathlib import Path
import re
import subprocess
import numpy as np
import pandas as pd
from formal_release_sequence import CASE, TESTS, REPO, STEM, utc
from mdbc_gpu_vector_run import bound, read, verify

READER = TESTS/"outputs/k5_part_r1/ReadHydroMechPart.exe"


def native(folder, index):
    p = subprocess.run([str(READER), str(folder/"data"), str(index)], capture_output=True)
    assert p.returncode == 0, p.stderr.decode(errors="replace")
    return pd.read_csv(io.BytesIO(p.stdout), float_precision="round_trip")


def metrics(a, initial, dp):
    nx, nz = round(.1/dp), round(1/dp)
    assert len(a) == nx*nz and np.array_equal(a.id, initial.id)
    assert np.array_equal(a.id, np.arange(a.id.iloc[0], a.id.iloc[0]+nx*nz))
    assert np.isfinite(a.select_dtypes("number").to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all()
    layer = np.rint(initial.z.to_numpy()/dp-.5).astype(int)
    assert np.array_equal(np.bincount(layer), np.full(nz, nx))
    total = np.bincount(layer, weights=a.sigma_zz-a.pressure)/nx
    disp = (initial.z-a.z).to_numpy()*1000
    t = float(a.time_s.iloc[0])
    dx = (a.x.to_numpy()-initial.x.to_numpy()+.05) % .1-.05
    span = max(np.ptp(a.z.to_numpy()[layer == i]) for i in range(nz))*1000
    assert abs(dx).max()*1000 < .5 and span < .5 and a.z.gt(0).all()
    load_available = bool(a.load_available.eq(1).all())
    force = float(2100*dp*dp*a.load_az.sum()) if load_available else None
    if t >= .1-1e-7:
        assert set(a.id[a.drained.eq(1)]) == set(a.id[layer == nz-1])
        assert a.pressure[layer == nz-1].eq(0).all()
        if load_available:
            assert abs(force+1000) < .001
    r = dict(time_s=t, step=int(a.step.iloc[0]), mean_pressure_pa=float(a.pressure.mean()),
        max_layer_total_error_pa=float(abs(total+10000).max()), top_gap_pa=float(abs(total[-1]-total[-2])),
        Q_pa=float(np.sqrt(np.mean(np.diff(total, n=2)**2))), top_settlement_mm=float(disp[layer == nz-1].mean()),
        bottom_settlement_mm=float(disp[layer == 0].mean()), max_dx_mm=float(abs(dx).max()*1000), max_layer_span_mm=float(span),
        load_available=load_available, load_resultant_N_m=force)
    r["stress_guard_applicable"] = t >= .1-1e-7
    r["stress_guard_passed"] = not r["stress_guard_applicable"] or (r["max_layer_total_error_pa"] <= 100 and r["top_gap_pa"] <= 100)
    return r


def prepare(args):
    text = (CASE/(STEM+"k1em5_Def.xml")).read_text(encoding="utf8")
    for key, value in (("DtIni", args.dt), ("DtFixed", args.dt), ("TimeMax", "0.10001"), ("TimeOut", "0.01")):
        text, n = re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")', lambda m: m[1]+value+m[2], text)
        assert n == 1
    text, n = re.subn(r'(<newvarcte Dp=")[^"]*(")', lambda m: m[1]+args.dp+m[2], text)
    assert n == 1
    steps = Decimal(".10001")/Decimal(args.dt)
    assert steps == steps.to_integral_value()
    exe = "DualSPHysics5.2_GEO_win64.exe" if args.backend == "gpu" else "DualSPHysics5.2CPU_win64.exe"
    option = "-gpu:0" if args.backend == "gpu" else "-cpu"
    bat = f'''@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0\\..\\.."
set case={args.tag}
set dirout=tests/outputs/%case%
set diroutdata=%dirout%/data
set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/{exe}"
set partvtk="%dirbin%/PartVTK_win64.exe"
if exist "%dirout%" goto fail
rem Short diagnostic only: original 100-Pa acceptance limits are unchanged.
%gencase% tests/configs/%case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail
%dualsphysics% {option} -ompthreads:1 -stable -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -nsteps:{int(steps)}
if not "%ERRORLEVEL%" == "0" goto fail
%partvtk% -dirin %diroutdata% -savevtk %dirout%/particles/PartFluid -onlytype:-bound -vars:+idp,+mk,+vel,+rhop,+sigma_kk,+sigma_ij,+kplastic,+porepress,+fstype
if not "%ERRORLEVEL%" == "0" goto fail
popd
exit /b 0
:fail
echo Diagnostic failed or output already exists; retained files were not deleted.
popd
exit /b 1
'''
    files = {TESTS/"configs"/(args.tag+"_Def.xml"): text, TESTS/"configs"/("x"+args.tag+"_win64_"+args.backend.upper()+".bat"): bat}
    patch = "*** Begin Patch\n"
    for path, content in files.items():
        assert not path.exists()
        patch += "*** Add File: "+str(path)+"\n"+"\n".join("+"+line for line in content.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def run(args):
    output = TESTS/"outputs"/args.tag
    bat = TESTS/"configs"/("x"+args.tag+"_win64_"+args.backend.upper()+".bat")
    check = TESTS/"logs"/(args.tag+".check.json")
    assert not check.exists() and not output.exists()
    definition = TESTS/"configs"/(args.tag+"_Def.xml")
    exe = REPO/"bin/windows"/("DualSPHysics5.2_GEO_win64.exe" if args.backend == "gpu" else "DualSPHysics5.2CPU_win64.exe")
    evidence = [bound(p) for p in (Path(__file__), READER, bat, definition, exe)]
    log = TESTS/"logs"/(args.tag+".log")
    with log.open("xb") as stream:
        p = subprocess.Popen(["cmd.exe", "/d", "/c", str(bat)], cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        print(json.dumps(dict(tag=args.tag, pid=p.pid, diagnostic_window_s=.10001)), flush=True)
        code = p.wait()
    assert code == 0, "Inspect retained BAT/solver log; do not restart this tag"
    verify(evidence)
    assert "Finished execution (code=0)." in (output/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
    parts = sorted((output/"data").glob("Part_*.bi4"))
    first = native(output, 0)
    rows = [metrics(native(output, i), first, float(args.dp)) for i in range(len(parts))]
    assert abs(rows[-1]["time_s"]-.10001) < 1e-7
    assert rows[-1]["step"] == int(Decimal(".10001")/Decimal(args.dt))
    passed = all(r["stress_guard_passed"] for r in rows)
    csv = TESTS/"figures"/(args.tag+"_history.csv")
    pd.DataFrame(rows).to_csv(csv, index=False, mode="x")
    evidence += [bound(p) for p in output.rglob("*") if p.is_file()]+[bound(log), bound(csv)]
    with check.open("x", encoding="utf8") as stream:
        json.dump(dict(valid_short_diagnostic=True, original_stress_guard_passed=passed, backend=args.backend,
            dp_m=float(args.dp), dt_s=float(args.dt), final=rows[-1], frames=len(rows), exit_code=code,
            owned_process_exited=True, utc=utc(), release_admitted=False, evidence=evidence), stream, indent=2, allow_nan=False)
    print(json.dumps(dict(tag=args.tag, original_stress_guard_passed=passed, final=rows[-1]), indent=2), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag", required=True)
    p.add_argument("--backend", choices=("cpu", "gpu"), required=True)
    p.add_argument("--dt", required=True)
    p.add_argument("--dp", default="0.01")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true"); g.add_argument("--run", action="store_true")
    args = p.parse_args()
    assert args.tag.replace("_", "").isalnum()
    return prepare(args) if args.prepare else run(args)


if __name__ == "__main__":
    main()
