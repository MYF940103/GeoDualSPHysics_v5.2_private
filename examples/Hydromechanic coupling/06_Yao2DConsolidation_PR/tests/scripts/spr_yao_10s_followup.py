"""One terminal queue for the new 10-s sequence; never starts/restarts a solver."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from spr_yao_short import TESTS,CASE,bound
from spr_yao_10s_run import TAG
from spr_yao_followup import alive,utc


def worker(codex,thread):
    source=TESTS/'logs'/(TAG+'.status.json');watch=TESTS/'logs'/(TAG+'.followup.status.json');assert not watch.exists()
    r=dict(status='waiting',pid=os.getpid(),thread=thread,started_utc=utc(),watched=str(source),never_runs_solver=True)
    def save():
        tmp=watch.with_suffix('.tmp');tmp.write_text(json.dumps(r,indent=2),encoding='utf8');os.replace(tmp,watch)
    save();misses=0
    while True:
        try:
            s=json.loads(source.read_text());misses=0
            if s['status']!='running':event=s['status'];break
            if not alive(s['owned_sequence_pid']):
                time.sleep(2);s=json.loads(source.read_text())
                if s['status']=='running' and not alive(s['owned_sequence_pid']):event='sequence_exited_without_terminal_record';break
        except Exception as error:
            misses+=1
            if misses>=5:event='status_unreadable';r['read_error']=repr(error);break
        time.sleep(10)
    r.update(status='terminal_observed',event=event,observed_utc=utc());save()
    message=(f'User-authorized same-thread Yao 10-s GPU SPR continuation {TAG}, not a new human observation. Detected {event}. '
        f'Read {source}, {watch}, its queue_attempt.json, tests/notes/spr_yao_10s_r1.md and spr_yao_axis_review_r1.md before claims. '
        'Only three fresh GPU runs: SPR off20us, SPR on20us, SPR on half10us; each10s/1001 native frames at.01s, 20301 soil IDs, dp.1, original strict strip load/material/drainage, HG/NoPen off. '
        'All earlier per-run native gates must pass before the next run; inspect frozen run/build/input/output hashes, owned exits, actual times/IDs, original geometry/load/drainage/elastic/natural-step safety. '
        'Verify off31 shared .01-s prefix states against retained .3-s off, on/half101 shared states each against retained same-dt1-s controls: all native fields0ULP, not all1001 dense prefix frames. '
        'Independent GPU half must satisfy original all1001-sample5Pa/.005mm; SPR off/on changes are not half errors or theory errors. Same-dt off/on force difference<.002N/m; preserve original59/61-node quadrature, no1D100Pa uniform-stress guard. '
        'Inspect all single/pair/final receipts and history PNG/CSVs; produce and inspect native field/near-wall/bottom-corner plots at justified actual saved times, A/B native material-point histories, settlement/stress and late pressure decay. '
        'Paper Yao5.2.3 provides numerical references, not an exact settlement truth; no new diffusion/damping/load change. There is no10-s CPU control; do not claim10-s backend speedup. '
        'If only analysis failed repair fresh analysis without rerunning completed solvers. If runtime/check failed inspect exact reason/time/surviving owned processes, preserve evidence, diagnose without relaxed gates, duplicate solvers or overwritten outputs. '
        'Proactively report quantified Chinese result and continue justified authorized delivery/cleanup/selective verified Git without a progress prompt. This is longer bounded comparison, not automatic full2D theory/general boundary release. '
        'NoPen .1-s prior stage was inactive and native on/off0ULP; do not reopen it or start pointless duplicate1-s NoPen. Static convex planar source candidate checkpoint7fda9ffe and reviewed1-s evidence759d34a remain; inspect newer backup receipts for latest head. '
        'Case02 accepted three groups/figures/CSVs stand; never rerun/rewrite or reopenKEEP. Inclined NoPen/curves/motion/plasticity/large rotation/exactHG restart unaccepted. '
        'This one-shot queues once and runs no solver. Never restart/rearm it or any old worker, and no connectivity self-tests. Use one verified completion only for a genuinely new admitted later long stage.')
    with (TESTS/'logs'/(TAG+'.queue_attempt.json')).open('x',encoding='utf8') as f:json.dump(dict(utc=utc(),thread=thread,event=event,message=message),f,indent=2)
    try:
        p=subprocess.run([codex,'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(status='queued' if p.returncode==0 else 'queue_failed_no_retry',queue_exit_code=p.returncode,reply=(p.stdout+p.stderr).decode(errors='replace'))
    except Exception as error:r.update(status='queue_uncertain_no_retry',error=repr(error))
    r['finished_utc']=utc();save()


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--codex');p.add_argument('--thread');a=p.parse_args()
    if a.worker:worker(a.codex,a.thread);return
    for suffix in ('.followup.launch.json','.followup.status.json','.queue_attempt.json'):assert not (TESTS/'logs'/(TAG+suffix)).exists()
    state=json.loads((TESTS/'logs'/(TAG+'.status.json')).read_text());assert state['status']=='running' and alive(state['owned_sequence_pid'])
    codex=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID']=='01a07683-bc64-7463-8db7-9ee6243967d8' and codex.is_file()
    argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--codex',str(codex),'--thread',thread]
    with (TESTS/'logs'/(TAG+'.followup.log')).open('xb') as f:child=subprocess.Popen(argv,cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/'logs'/(TAG+'.followup.launch.json')).open('x',encoding='utf8') as f:json.dump(dict(pid=child.pid,argv=argv,thread=thread,inputs=[bound(__file__),bound(codex),bound(TESTS/'scripts/spr_yao_followup.py')],no_connectivity_test=True),f,indent=2)
    print('One new 10-s terminal follow-up launched:',child.pid)


if __name__=='__main__':main()
