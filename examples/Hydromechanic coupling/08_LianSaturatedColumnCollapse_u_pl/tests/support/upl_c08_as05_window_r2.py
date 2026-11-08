"""Adopt the genuine r1 epsilon.5 seed after its zero-solver VTK-label gate failure; one target only."""
import argparse,csv,ctypes,json,os,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
from copy import deepcopy
import psutil
import upl_c08_as05_window_r1 as original
T,C,L,PRE,SOURCE,base=original.T,original.C,original.L,original.PRE,original.SOURCE,original.base
need,read,stat,bind,save,verify=original.need,original.read,original.stat,original.bind,original.save,original.verify
THREAD,CODEX=original.THREAD,original.CODEX
TAG='upl_c08_as05_window_GPU_r2';OLD='upl_c08_as05_window_GPU_r1'
OUT=T/'outputs'/OLD;CONFIG=T/'configs'/(OLD+'_Def.xml');PREFIX=OUT/OLD
UPDATES=264000;FRAMES=66;CADENCE=4000
FAILURE='Only TimeMax/TimeOut/epsilon/source binding and their declared comments may differ; geometry/full body/SPR/HG/filter/FOS remain literal'

def prepared():
    rp=L/(OLD+'.run.json');ap=L/'upl_c08_as05_preparation_audit_r1.json';r,a=read(rp),read(ap)
    need(not r['passed'] and r['solver_invocations']==r['reader_invocations']==0 and r['first_failure']==FAILURE,'Only the original known zero-solver r1 gate failure is adoptable')
    need(a['passed'] and a['r1_solver_invocations']==0 and a['whole_generated_tree_exact_after_two_filename_labels_and_date'] and a['old_failure_preserved'] and not a['physical_parameters_changed_by_audit'] and bind(a['r1_run'])==stat(rp),'Closed independent preparation audit required')
    gp=Path(bind(r['GenCase_call'])['path']);g=read(gp);need(bind(a['actual_GenCase_call'])==stat(gp) and g['actual_Popen_wait_exit']==g['actual_Win32_exit']==0 and g['ownership_failure'] is None,'Original actual GenCase ownership/exit differs')
    need(g['arguments']==[str(CONFIG.with_suffix('')),str(PREFIX),'-save:all'] and g['child']['argv']==[g['program'],*g['arguments']] and g['child']['parent_pid']==g['owner']['pid'] and Path(g['child']['exe']).samefile(g['program']),'Original GenCase inputs/child identity differ')
    need(not any((OUT/x).exists() for x in ('Run.out','Run.csv','C08StageTrace.csv','planned_steps.csv','data','native')) and not any((L/(OLD+s)).exists() for s in ('.start.json','.call.json','.solver.log')),'Any existing actual solver/native/plan work prevents adoption')
    original.check_input(CONFIG);actual=base.ET.parse(str(PREFIX)+'.xml').getroot();expected=base.ET.parse(original.BASE_SEED).getroot();execution=expected.find('execution');target=original.make_input()
    for section in ('special','parameters'):
        old=execution.find(section);index=list(execution).index(old);execution.remove(old);execution.insert(index,deepcopy(target.find('execution/'+section)))
    expected_names={original.BASELINE+'_hdp_Actual.vtk':OLD+'_hdp_Actual.vtk',original.BASELINE+'__Actual.vtk':OLD+'__Actual.vtk'}
    nodes=expected.findall('execution/vtkout/vtkfile');need(len(nodes)==2 and {n.get('name') for n in nodes}==set(expected_names),'Only the two known generated VTK labels are admitted')
    for node in nodes:node.set('name',expected_names[node.get('name')])
    actual.attrib.pop('date',None);expected.attrib.pop('date',None);need(original.signature(actual)==original.signature(expected),'Full generated tree differs beyond the exact two labels and date')
    seeds=[stat(Path(str(PREFIX)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];need([bind(e) for e in a['prepared_files']]==seeds,'Prepared seed identities differ from independent audit')
    verify(r['consumed']);return [stat(p) for p in (rp,ap,gp,CONFIG)]+[bind(e) for e in r['consumed']]+seeds

def owned(argv,program,admission):
    # Exact direct-target subset of the original handle owner; actual output stays r1, receipt tag is r2.
    log=L/(TAG+'.solver.log');start=L/(TAG+'.start.json');call=L/(TAG+'.call.json');outer=None;errors=[];rc=wx=None;begin=base.utc();wall=time.monotonic();next_status=0.
    with log.open('xb') as f:
        p=subprocess.Popen(argv,cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        try:
            outer=base.evidence.ident(int(p._handle),p.pid);need(Path(outer['exe']).samefile(program) and outer['argv']==argv and outer['parent_pid']==os.getpid(),'Actual owned target argv/creation/exe/parent differs')
            save(start,dict(stage=TAG,started_utc=begin,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),actual_outer=outer,actual_solver=outer,admission=admission,actual_output_directory=str(OUT)));print('AS05_R2_SOLVER_STARTED',p.pid,flush=True)
            while p.poll() is None:
                if time.monotonic()>=next_status:base.publish(TAG,OUT,outer,outer,'running');next_status=time.monotonic()+30
                time.sleep(.02)
        except BaseException as error:errors.append(repr(error))
        finally:
            rc=p.wait();code=w.DWORD();wx=code.value if base.K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)) else None
    record=dict(stage=TAG,actual_outer=outer,actual_solver=outer,arguments=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=wx,actual_solver_Win32_exit=wx,ownership_errors=errors,started_utc=begin,ended_utc=base.utc(),elapsed_s=time.monotonic()-wall,log=stat(log),admission=admission,actual_output_directory=str(OUT))
    save(call,record);need(rc==wx==0 and not errors and outer is not None,'Actual solver/owner failed; preserve partial, no retry');return stat(call)

def notify_once(check):
    need(not any((L/(TAG+s)).exists() for s in ('.queue_attempt.json','.queue_result.json')),'A terminal queue attempt already exists; never resend')
    message=('The explicitly admitted C08 epsilon.5 single-factor complete-body .66 s GPU window is terminal. Read '+str(check)+' and original start/call/status/owner_admission/root admission; verify owned creation/exe/argv/parent, real Win32/Popen exits and program/PRE/input stats first. This is only tau .66 s,264000 new updates,66 planned saves, AS1 epsilon.5 exponent2.55/fixed-plane/keep5, not physical acceptance. The original r2 GPU10 s PRE was reused, not rerun. Prepared r1 seed/output were adopted after the zero-solver generated-label preflight failure; GenCase was not rerun. Actual run files are in outputs/upl_c08_as05_window_GPU_r1 while this owner/call/run tag is r2. C08StageTrace.csv observes IDs5809/4956/4959 every40 steps before tau .60 and every step from .60 to .66. Do not rearm this owner or launch another solver. On failure preserve the first real error and partials, without inventing unsaved native time. Before any reader invocation check existing/active readers; only a separately reviewed66-frame6805-ID reader and window CSV review may be authorized. Keep all original22/P0/J/ledger/FS/keep/clock/signed guards and scalar clocks; a separately reviewed native adapter must expect epsilon.5, not the old epsilon.2 AS metadata. This is one prescribed Bui2008 parameter comparison, not proof of repair. No new SPR/HG/filter/FOS action is admitted. No automatic native/VTK, other psi, half-step chain or source restart. This terminal queue is attempted once with45 s timeout; delivery may be uncertain after timeout, so never resend or add a watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message]
    save(L/(TAG+'.queue_attempt.json'),dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(check),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True))
    result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(L/(TAG+'.queue_result.json'),result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read and explicit r2 adoption admission required')
    need(not args.notify or (os.environ.get('CODEX_THREAD_ID')==THREAD and CODEX.is_file()),'Only exact-thread one terminal queue is allowed')
    root_ad=L/(TAG+'.admission.json');rp=L/(TAG+'.run.json');need(not any(p.name!=root_ad.name for p in L.glob(TAG+'.*')),'Existing r2 work preserved; no retry')
    before=[];result=dict(stage=TAG,passed=False,configuration='Release',physical_acceptance=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,queue_invocations_at_run_seal=0,terminal_queue_requested=args.notify,SHA_scans=0,native_review_pending=True,keep_bed_overlap=True,expected_active_native_IDs=6805,ArtificialStress=True,ArtificialStressCoef=.5,ArtificialStressExp=2.55,policy=base.POLICY,actual_output_directory=str(OUT),prepared_r1_adopted=True)
    try:
        ad=read(root_ad);need(ad['passed'] and ad['allowed_job']==TAG and ad['ArtificialStressCoef']==.5,'Independent root r2 epsilon.5 admission required')
        before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_as05_window_r2.md',Path(original.__file__),Path(base.__file__),root_ad)]+prepared()+original.baseline_gates()
        bp=L/'upl_c08_stage_trace_Release_r1.build.json';b=read(bp);need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['trace_macro_enabled'] and b['trace_macro']=='C08_STAGE_TRACE' and b['environment_macro']['appended']=={'CL':'/DC08_STAGE_TRACE','NVCC_PREPEND_FLAGS':'-DC08_STAGE_TRACE'} and len(b['project_objects'])==113,'Closed same trace Release program required');program=Path(bind(b['program'])['path']);before.extend([stat(bp)]+[bind(b[k]) for k in ('program','source_capture','source_archive')])
        need(Path(b['source_capture']['path']).samefile(T/'outputs/upl_c08_stage_trace_source_r1/source.json') and bind(read(L/(original.BASELINE+'.run.json'))['program'])==stat(program),'Actual baseline program/capture differs')
        for q in psutil.process_iter(['exe','cmdline']):
            try:
                exe=q.info['exe'];argv=q.info['cmdline'] or [];need(not(exe and Path(exe).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in argv[1:])),'GPU solver active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        plan=OUT/'planned_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(('part','completed_step'));writer.writerows((i,SOURCE+(i+1)*CADENCE) for i in range(FRAMES))
        before.append(stat(plan));argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(PREFIX),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(SOURCE+UPDATES)]
        admission=L/(TAG+'.owner_admission.json');save(admission,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(root_ad),program=stat(program),source_build=stat(bp),source_pre_file=stat(PRE),planned_steps=stat(plan),planned_new_updates=UPDATES,planned_global_end=SOURCE+UPDATES,expected_saved_frames=FRAMES,argv=argv,solver_argv=argv,actual_output_directory=str(OUT),consumed=before))
        result['solver_invocations']=1;result['actual_call']=owned(argv,program,stat(admission));result.update(original.normal_output(OUT));verify(before);result.update(passed=True,actual_exit=0,actual_Win32_exit=0,program=stat(program),source_build=stat(bp),input_xml=stat(str(PREFIX)+'.xml'),source_pre_file=stat(PRE),original_run=stat(L/(OLD+'.run.json')),preparation_audit=stat(L/'upl_c08_as05_preparation_audit_r1.json'),prepared_GenCase_call=stat(L/(OLD+'.gencase.call.json')),consumed_stats_unchanged=True)
    except Exception as error:
        result['first_failure']=str(error);cp=L/(TAG+'.call.json')
        if cp.exists():
            c=read(cp);result.update(actual_call=stat(cp),actual_exit=c['actual_solver_Win32_exit'],actual_Win32_exit=c['actual_solver_Win32_exit'],actual_tool_exit=c['actual_Popen_wait_exit'],ownership_errors=c['ownership_errors'])
    result.update(consumed=before,last_original_console_line=base.last_part(OUT));save(rp,result);base.publish(TAG,OUT,None,None,'completed_pending_native' if result['passed'] else 'failed_preserved_pending_diagnosis')
    if args.notify and result['solver_invocations']:notify_once(rp)
    print(json.dumps(dict(passed=result['passed'],receipt=str(rp),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
