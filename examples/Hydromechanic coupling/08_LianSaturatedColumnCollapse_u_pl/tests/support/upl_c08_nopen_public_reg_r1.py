"""One isolated legacy-NoPen diagnostic from the certified PRE; no retry or restart."""
import argparse, ctypes, datetime, json, os, re, shutil, subprocess, time
from ctypes import wintypes as w
from pathlib import Path
import xml.etree.ElementTree as ET
import psutil
import mdbc_partition_components_r3 as evidence
from upl_c08_resume_native_r1_run import check_input
from upl_c08_resume_r1 import summary

T=Path(__file__).resolve().parents[1]; C=T.parent; L=T/'logs'
TAG='upl_c08_nopen_public_reg_r1'; OUT=T/'outputs'/TAG; RUNTIME=C/'support/runtime_r4'
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
BASE=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r4_Def.xml'
CONFIG=T/'configs'/(TAG+'_Def.xml'); BUILD=L/'upl_c08_nopen_public_Release_r1.build.json'
need,read,stat,bind,save,invoke=evidence.need,evidence.read,evidence.stat,evidence.bind,evidence.save,evidence.invoke

def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def last_console():
    f=OUT/'Run.out'
    if not f.exists(): return None
    lines=f.read_bytes().splitlines(keepends=True)
    return next((x.decode('utf8','replace') for x in reversed(lines) if re.match(rb'^Part_\d+\s+[0-9.eE+-]+\s+\d+\s+',x) and x.endswith(b'\n')),None)

def publish(owner,child,p,state):
    path=L/(TAG+'.status.json'); tmp=path.with_suffix('.tmp')
    with tmp.open('w',encoding='utf8') as f:
        json.dump(dict(stage=TAG,utc=utc(),owner=owner,child=child,state=state,owned_child_alive=p is not None and p.poll() is None,last_original_console_line=last_console(),physical_acceptance=False),f,indent=2)
    os.replace(tmp,path)

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--execution-authorized',action='store_true'); a=ap.parse_args()
    need(a.execution_authorized,'Root-reviewed isolated diagnostic required')
    need(not OUT.exists() and not CONFIG.exists() and not list(L.glob(TAG+'*')),'Existing output/owner protected; never restart this job')
    result=dict(stage=TAG,passed=False,physical_acceptance=False,legacy_projection_only=True,reaction_Darcy_J_closure_claimed=False,same_PRE_operator_claimed=False,solver_invocations=0,reader_invocations=0,SHA_scans=0)
    consumed=[]; p=None; identity=None; owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()); rc=None; winexit=None; errors=[]
    try:
        # This program deliberately changes the receiver operator; source PRE remains certified AS0/NoPen0.
        b=read(BUILD); need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Closed isolated Release build required')
        for q in psutil.process_iter(['exe','cmdline']):
            need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(x.lower().startswith('-gpu') for x in (q.info['cmdline'] or [])[1:])),'Another GPU solver is active; no process is stopped')
        root=ET.parse(BASE).getroot(); root.find('execution/special/gravitypreload').set('statefile',str(PRE)); params=root.find('execution/parameters')
        keys=[x for x in params if x.get('key')=='NoPenetration']; need(len(keys)==1 and float(keys[0].get('value'))==1,'Actual formal XML must select NoPen1')
        need(not any(x.get('key')=='ArtificialStress' and float(x.get('value'))!=0 for x in params),'AS must remain off')
        CONFIG.write_bytes(b'<?xml version="1.0" encoding="UTF-8" ?>\n'+ET.tostring(root,encoding='utf-8',xml_declaration=False)+b'\n'); check_input(CONFIG,PRE)
        consumed=[stat(x) for x in (Path(__file__),T/'notes'/(TAG+'.md'),BUILD,BASE,CONFIG,PRE,PRE.parent/'Part_Head.ibi4')]+[bind(b['program'])]
        program=Path(b['program']['path']); executed=RUNTIME/program.name; original=stat(program); installed=stat(executed)
        need((original['bytes'],original['mtime_ns'])==(installed['bytes'],installed['mtime_ns']),'Installed public solver differs from its build'); consumed += [installed]+[stat(p) for p in RUNTIME.iterdir() if p.is_file()]
        prefix=OUT/TAG; result['GenCase_call']=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml'); check_input(seed,PRE); consumed += [stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        argv=[str(RUNTIME/program.name),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:4060000']
        started=utc(); wall=time.monotonic(); result['solver_invocations']=1
        with (L/(TAG+'.solver.log')).open('xb') as f:
            p=subprocess.Popen(argv,cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            identity=evidence.ident(int(p._handle),p.pid)
            need(Path(identity['exe']).samefile(argv[0]) and identity['argv']==argv and identity['parent_pid']==os.getpid(),'Actual owner/target/argv differs')
            save(L/(TAG+'.start.json'),dict(stage=TAG,utc=started,owner=owner,child=identity,argv=argv,program=stat(argv[0]),consumed=consumed,NoPen_policy='LegacyOperatorSplitReleaseOnly',actual_GlobalStep_limit=4060000))
            print('GPU_NO_PEN_SHORT_STARTED',p.pid,'owner',os.getpid(),flush=True)
            while True:
                publish(owner,identity,p,'solver_running')
                try: rc=p.wait(timeout=30); break
                except subprocess.TimeoutExpired: pass
            code=w.DWORD(); need(evidence.K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Actual target exit unavailable'); winexit=code.value
        save(L/(TAG+'.call.json'),dict(stage=TAG,owner=owner,child=identity,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=winexit,started_utc=started,ended_utc=utc(),elapsed_s=time.monotonic()-wall,last_original_console_line=last_console(),ownership_errors=errors))
        result.update(actual_exit=rc,actual_Win32_exit=winexit,actual_program=stat(argv[0]),actual_input=stat(seed),actual_PRE=stat(PRE))
        need(rc==winexit==0,'Actual NoPen diagnostic solver failed; preserve partial and inspect first cause')
        r=summary(OUT/'Run.csv'); text=(OUT/'Run.out').read_text(encoding='utf-8-sig'); parts=sorted((OUT/'data').glob('Part_*.bi4'))
        need(int(r['Steps'])==4060000 and int(r['PartFiles'])==15 and int(r['PartsOut'])==0,'Actual bounded count/exclusions differ')
        need('No Penetration=True' in text and 'Dynamic NoPen: LegacyOperatorSplitReleaseOnly' in text and 'ArtificialStress="None"' in text,'Executed NoPen/AS policy differs')
        need([x.name for x in parts]==['Part_%04d.bi4'%i for i in range(15)],'Actual native sequence differs')
        need(all(stat(e['path'])==e for e in consumed),'Consumed program/input/PRE changed')
        result.update(passed=True,runtime_completed_pending_native=True,actual_GlobalStep=4060000,saved_frames=15,Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),PARTs=[stat(x) for x in parts],consumed_stats_unchanged=True)
    except Exception as e:
        result.update(first_failure=str(e),actual_exit=rc,actual_Win32_exit=winexit,last_original_console_line=last_console())
        if p is not None and p.poll() is None:
            # Do not abandon an owned target on an observation/postcheck exception.
            errors.append(str(e)); rc=p.wait(); result['actual_exit_after_observation_error']=rc
        if p is not None:
            code=w.DWORD()
            result['actual_Win32_exit_after_failure']=code.value if evidence.K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)) else None
    result['consumed']=consumed; save(L/(TAG+'.run.json'),result); publish(owner,identity,p,'completed_pending_native_review' if result['passed'] else 'failed_preserved_pending_diagnosis')
    print(json.dumps(dict(passed=result['passed'],run=str(L/(TAG+'.run.json')),first_failure=result.get('first_failure'),physical_acceptance=False)),flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
