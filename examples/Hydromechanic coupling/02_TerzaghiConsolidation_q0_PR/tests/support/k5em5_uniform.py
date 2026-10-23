"""Same-dp short diagnostics. Record stress-gate failures; never admit a full run."""
import argparse
import csv
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import time
import numpy as np
from formal_release_sequence import CASE, TESTS, REPO, save, utc
from mdbc_gpu_vector_run import read, bound, verify
import k5_guard_probe as probe

TAG = "k5em5_uniform_dt_r1"
FORMAL = "CaseTerzaghiConsolidation_q0_PR_full_k5em5"


def prepare():
    retained = TESTS/"outputs/k5em5_standard_inputs_r2"
    base = (retained/(FORMAL+"_Def.xml")).read_text(encoding="utf8")
    entries = [(CASE/(FORMAL+"_Def.xml"), base)]
    for backend in ("CPU", "GPU"):
        name = "x"+FORMAL+"_win64_"+backend+".bat"
        text = (retained/name).read_text(encoding="utf8")
        text = text.replace("set dirout=%case%_release_"+backend+"_out", "set dirout=%case%_release_"+backend+"_uniform_out")
        text = text.replace("--label full_validation_release_k5em5_"+backend, "--label full_validation_release_k5em5_uniform_"+backend)
        entries.append((CASE/name, text))
    template = (TESTS/"configs/xk5em5_gpu_r2_c_win64_GPU.bat").read_text(encoding="utf8")
    for suffix, dt in (("c", ".00001"), ("h", ".000005")):
        label = TAG+"_"+suffix
        text = base
        for key, value in (("DtIni", dt), ("DtFixed", dt), ("TimeMax", ".3"), ("TimeOut", ".000999999999")):
            text, n = re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")', lambda m:m[1]+value+m[2], text)
            assert n == 1
        entries.append((TESTS/"configs"/(label+"_Def.xml"), text))
        bat = template.replace("k5em5_gpu_r2_c", label).replace("-nsteps:15000", "-nsteps:"+str(int(Decimal(".3")/Decimal(dt))))
        entries.append((TESTS/"configs"/("x"+label+"_win64_GPU.bat"), bat))
    patch = "*** Begin Patch\n"
    for path, text in entries:
        if path.exists():
            assert path.parent == CASE
            old = path.read_text(encoding="utf8")
            patch += "*** Update File: "+str(path)+"\n@@\n"+"\n".join("-"+s for s in old.splitlines())+"\n"
        else:
            patch += "*** Add File: "+str(path)+"\n"
        patch += "\n".join("+"+s for s in text.splitlines())+"\n"
    print(json.dumps(dict(patch=patch+"*** End Patch")))


def run():
    state = TESTS/"logs"/(TAG+".status.json")
    assert not state.exists()
    assert read(TESTS/"logs/k5em5_stop_r3.json")["owned_processes_exited"]
    r = dict(status="running", started_utc=utc(), worker_pid=os.getpid(), runs=[],
             purpose="Time convergence versus spatial/initial-transient error at fixed dp=.01", full_admitted=False)
    r["inputs"] = [bound(p) for p in [Path(__file__), Path(probe.__file__), probe.READER, REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe"]]
    save(state, r)
    try:
        assert subprocess.check_output(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*' -ErrorAction SilentlyContinue).Count"], text=True).strip() == "0"
        for suffix, steps in (("c", 30000), ("h", 60000)):
            label = TAG+"_"+suffix
            folder = TESTS/"outputs"/label
            bat = TESTS/"configs"/("x"+label+"_win64_GPU.bat")
            assert not folder.exists()
            r["inputs"] += [bound(bat), bound(TESTS/"configs"/(label+"_Def.xml"))]
            item = dict(label=label, expected_steps=steps, checked_frames=0, first_stress_failure=None, numerical_safety_passed=True)
            r["runs"].append(item)
            r["stage"] = label
            log = TESTS/"logs"/(label+".log")
            history = TESTS/"figures"/(label+"_runtime.csv")
            with log.open("xb") as stream, history.open("x", newline="", encoding="utf8") as out:
                p = subprocess.Popen([os.environ["ComSpec"], "/d", "/c", str(bat)], cwd=CASE, stdout=stream,
                                     stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                item["owned_cmd_pid"] = p.pid
                initial, writer, index = None, None, 0
                def consume(i):
                    nonlocal initial, writer
                    a = probe.native(folder, i)
                    if initial is None:
                        initial = a.copy()
                    m = probe.metrics(a, initial, .01)
                    if not m["stress_guard_passed"]:
                        item["numerical_safety_passed"] = False
                        if item["first_stress_failure"] is None:
                            item["first_stress_failure"] = m.copy()
                    if writer is None:
                        writer = csv.DictWriter(out, fieldnames=list(m))
                        writer.writeheader()
                    writer.writerow(m)
                    out.flush()
                    item.update(checked_frames=i+1, last_metrics=m)
                try:
                    while p.poll() is None:
                        n = len(list((folder/"data").glob("Part_*.bi4")))
                        while index < n-1:
                            consume(index)
                            index += 1
                        r["updated_utc"] = utc()
                        save(state, r)
                        time.sleep(10)
                    assert p.returncode == 0, "Diagnostic BAT failed: "+str(log)
                    n = len(list((folder/"data").glob("Part_*.bi4")))
                    while index < n:
                        consume(index)
                        index += 1
                finally:
                    if p.poll() is None:
                        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                        p.wait()
                    item.update(exit_code=p.returncode, owned_exited=True)
                    save(state, r)
            assert item["last_metrics"]["step"] == steps and abs(item["last_metrics"]["time_s"]-.3) < 1e-7 and index == 301
            item.update(completed_diagnostic=True, outputs=[bound(p) for p in folder.rglob("*") if p.is_file()]+[bound(log), bound(history)])
            save(state, r)
        verify(r["inputs"])
        r["status"] = "completed_diagnostic_not_full_admission"
    except Exception as error:
        r.update(status="diagnostic_failed_or_interrupted", reason=str(error))
    r["finished_utc"] = utc()
    save(state, r)
    print(json.dumps(dict(status=r["status"], state=str(state), full_admitted=False)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()
    prepare() if args.prepare else run()
