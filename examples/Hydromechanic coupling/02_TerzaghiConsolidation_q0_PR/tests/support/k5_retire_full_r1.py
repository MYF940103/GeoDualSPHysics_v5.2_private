"""User-authorized intentional retirement before a bounded larger-step trial."""
import hashlib
import json
from pathlib import Path
import subprocess
import psutil
import k5_cell_sequence as cell
from formal_release_sequence import TESTS, save, utc
from mdbc_gpu_vector_run import read, bound, verify


def main():
    state=TESTS/"logs/k5_full_r1.status.json"
    audit=TESTS/"logs/k5_full_r1_acceleration_stop.json"
    if audit.exists():
        r=read(audit);assert r["phase"]=="monitor_retired_without_rearming"
        r["finalization_note"]="Resume audit only after asynchronous exit; do not repeat termination commands."
        return finalize(state,audit,r)
    raw=state.read_bytes();s=json.loads(raw);assert s["status"]=="running"
    verify(s["inputs"])
    worker=psutil.Process(s["worker_pid"]);cmd=psutil.Process(s["owned_cmd_pid"])
    assert "k5_full_sequence.py" in " ".join(worker.cmdline()) and "--worker" in worker.cmdline()
    assert cmd.ppid()==worker.pid and "xk5_full_r1_win64_GPU.bat" in " ".join(cmd.cmdline())
    children=cmd.children(recursive=True)
    solvers=[p for p in children if p.name().lower()=="dualsphysics5.2_geo_win64.exe"]
    assert len(solvers)==1 and "tests/outputs/k5_full_r1" in " ".join(solvers[0].cmdline())
    owners=[dict(pid=p.pid,created=p.create_time(),argv=p.cmdline()) for p in [worker,cmd]+children]
    r=dict(started_utc=utc(),action="intentional stop for user-authorized acceleration trials",physical_failure=False,
        full_2tv_completed=False,reason="Tested CPU 1/2/4/8 threads did not beat GPU; day-scale GPU cost led user to authorize a bounded larger-step trial.",
        ordinary_PART_exact_HG_restart=False,before_status=s,before_status_sha256=hashlib.sha256(raw).hexdigest(),ownership=owners,phase="verified_ownership")
    save(audit,r)
    # The monitor queues on terminal outcomes: retire it first, without touching
    # its children, then stop only its verified command/solver tree.
    worker.terminate();worker.wait(timeout=10)
    r["phase"]="monitor_retired_without_rearming";save(audit,r)
    stopped=subprocess.run(["taskkill","/PID",str(cmd.pid),"/T","/F"],capture_output=True)
    r["taskkill_returncode"]=stopped.returncode;r["taskkill_reply"]=(stopped.stdout+stopped.stderr).decode(errors="replace")
    assert stopped.returncode==0
    save(audit,r)
    return finalize(state,audit,r)


def finalize(state,audit,r):
    owners=r["ownership"];s=r["before_status"];waiting=[]
    for item in owners:
        try:p=psutil.Process(item["pid"])
        except psutil.NoSuchProcess:continue
        if p.create_time()==item["created"]:waiting.append(p)
    psutil.wait_procs(waiting,timeout=10)
    for item in owners:
        try:p=psutil.Process(item["pid"])
        except psutil.NoSuchProcess:continue
        assert p.create_time()!=item["created"],"Owned process survived: "+str(item["pid"])
    folder=TESTS/"outputs/k5_full_r1";files=sorted((folder/"data").glob("Part_*.bi4"),key=lambda p:int(p.stem.split("_")[-1]))
    unreadable=[]
    for path in reversed(files):
        i=int(path.stem.split("_")[-1])
        try:last=cell.probe.native(folder,i)
        except Exception as error:unreadable.append(dict(path=str(path),reason=str(error)));continue
        break
    initial=cell.probe.native(folder,0);m=cell.metrics(last,initial)
    reference=cell.probe.native(TESTS/"outputs/k5_long5_r1_c",i)
    assert last[cell.FIELDS].to_numpy(dtype="<f8").tobytes()==reference[cell.FIELDS].to_numpy(dtype="<f8").tobytes()
    r.update(phase="retired",finished_utc=utc(),owned_processes_exited=True,last_readable_part=i,last_readable=m,
        last_readable_same_dt_reference_0_ulp=True,unreadable_tail_retained=unreadable,
        retained_files=[bound(p) for p in folder.rglob("*") if p.is_file()])
    save(audit,r)
    s.update(status="intentionally_stopped_for_step_trial",stage="retired_preserved",finished_utc=r["finished_utc"],
        owned_processes_exited=True,last_readable_part=i,last_readable_metrics=m,physical_failure=False,completed_2tv=False,
        queue_status="intentionally_retired_without_terminal_queue",retirement_audit=bound(audit))
    save(state,s)
    print(json.dumps({k:r[k] for k in ("phase","physical_failure","full_2tv_completed","owned_processes_exited","last_readable_part","last_readable","unreadable_tail_retained")},indent=2))


if __name__=="__main__":main()
