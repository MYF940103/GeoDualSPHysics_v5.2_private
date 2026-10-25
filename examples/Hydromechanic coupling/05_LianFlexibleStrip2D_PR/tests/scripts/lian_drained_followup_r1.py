"""One terminal notification for the new drained short pair, never a solver."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil
from lian_release_r1 import CASE,TESTS,TAG,utc,bound,write_json

NAME='lian_drained_followup_r1'
SOURCE=TESTS/'logs'/f'{TAG}_drained.status.json'
STATE=TESTS/'logs'/(NAME+'.status.json')


def worker(codex,thread):
    sequence=json.loads(SOURCE.read_text())
    process=psutil.Process(sequence['owned_sequence_pid'])
    birth=process.create_time()
    r=dict(status='waiting',pid=os.getpid(),thread=thread,started_utc=utc(),source=str(SOURCE),sequence_pid=process.pid,sequence_birth=birth,never_runs_solver=True)
    def save():
        tmp=STATE.with_suffix('.tmp');write_json(tmp,r);os.replace(tmp,STATE)
    save()
    failures=0
    while True:
        try:
            s=json.loads(SOURCE.read_text());failures=0
            if s['status']!='running':event=s['status'];break
            if not process.is_running() or process.create_time()!=birth or process.status()==psutil.STATUS_ZOMBIE:
                event='worker_exited_without_terminal_status';break
        except (psutil.NoSuchProcess,psutil.AccessDenied) as error:
            event='owned_process_unavailable';r['error']=repr(error);break
        except Exception as error:
            failures+=1
            if failures>=5:event='status_unreadable';r['error']=repr(error);break
        time.sleep(10)
    r.update(status='terminal_observed',event=event,observed_utc=utc());save()
    message=(f'User-authorized same-thread Lian drained-admission continuation {TAG}_drained, not a new human observation. Detected {event}. '
        f'Read {SOURCE}, {STATE}, tests/logs/{NAME}.queue_attempt.json, tests/notes/poromech_stage1_r1.json and the parent Hydromechanic coupling/validation/poromech_next_r1.json before claims. '
        'Only fresh actual GPU Release Lian 3-s coarse10us/half5us with original mixed mDBC/strip mode4/ramp/drainage, stress double/pore float and SPR/HG/stress-gradient switches off were admitted. '
        'Verify exact exits/owned processes, native IDs, actual final times, frozen executable/input/output hashes and original natural-step/finite/elastic/drainage/geometry checks. '
        'Inspect all-sample5Pa/.005mm half metrics at actual saved times; normal output scheduling can differ by one step and is not exact event alignment. '
        'The original inspector only checks upward FSType2 drainage; additionally check every true drained native node (FSType2 OR3 and outside current x=[0,1.25]) after1s, not a vacuous mask. '
        'Compare retained same-physics float-stress baseline at actual times/material IDs, generate and inspect figures/CSVs. No old-vs-new0ULP or theory-accuracy claim is implied. '
        'Retained Lian old load telemetry is present but zero; never report physically zero applied force. Old initial position data are float while later saved PARTs can be double; distinguish storage types. '
        'Paper section4.3 reports decay through100s; old root only49.95001s. Track id1744 contact/drainage switches and negative spikes separately from a pressure plateau. '
        'If any gate failed inspect exact cause/time and surviving processes, preserve outputs, repair new analysis only when appropriate, no relaxed thresholds or duplicate solver. '
        'On passed short review proceed with justified late-window diagnosis before final independent root XML/BAT actual full run to the paper endpoint, native analysis and matching PNG/CSV. '
        'Cryer frozen load audit rejects correcting only load; it does not accept a replacement operator or a double coupled solution. Continue scoped consistency/precision diagnosis and Yao formal physical delivery, then target slope in the authorized plan. '
        'Each verified change/stage must have selective local AND remote Git backup; raw BI4/exe are not cloud Git backup. Keep accepted case02 results unchanged, do not reopen KEEP/u-pl/TPI. '
        'Proactively report Chinese staged outcomes and continue without another progress question. Never restart/rearm this one-shot watcher or old workers, and no connectivity self-tests.')
    attempt=TESTS/'logs'/(NAME+'.queue_attempt.json')
    with attempt.open('x',encoding='utf8') as f:json.dump(dict(utc=utc(),event=event,thread=thread,message=message),f,indent=2)
    try:
        p=subprocess.run([codex,'queue','--thread',thread,'--message',message],capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        r.update(status='queued' if p.returncode==0 else 'queue_failed_no_retry',queue_exit_code=p.returncode,reply=(p.stdout+p.stderr).decode(errors='replace'))
    except Exception as error:r.update(status='queue_uncertain_no_retry',queue_error=repr(error))
    r['finished_utc']=utc();save()


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--codex');p.add_argument('--thread');a=p.parse_args()
    if a.worker:worker(a.codex,a.thread);return
    for suffix in ('.status.json','.launch.json','.queue_attempt.json'):assert not (TESTS/'logs'/(NAME+suffix)).exists()
    state=json.loads(SOURCE.read_text());assert state['status']=='running' and psutil.pid_exists(state['owned_sequence_pid'])
    codex=Path(r'C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe')
    thread=os.environ['CODEX_THREAD_ID'];assert thread==os.environ['CODEX_SESSION_ID'] and codex.is_file()
    argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--codex',str(codex),'--thread',thread]
    with (TESTS/'logs'/(NAME+'.log')).open('xb') as f:child=subprocess.Popen(argv,cwd=CASE,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    write_json(TESTS/'logs'/(NAME+'.launch.json'),dict(pid=child.pid,argv=argv,thread=thread,inputs=[bound(__file__),bound(codex)],never_runs_solver=True))
    print('New one-shot drained-stage watcher PID',child.pid)


if __name__=='__main__':main()
