"""Own one root psi0 r5 GPU3s diagnostic BAT; preserve failed solver/postprocess evidence separately."""
import argparse,ctypes,datetime,json,os,re,struct,subprocess,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import psutil
import upl_c08_resume_r1 as short
stat,read=short.stat,short.read
from upl_c08_asplane_summary_r1 import summary
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_formal_psi0_r5_r1';CASE='CaseLianSaturatedColumnCollapse_psi0_shared_r5'
OUT=C/(CASE+'_GPU_out');BAT=C/('x'+CASE+'_win64_GPU.bat');RUNTIME=C/'support/runtime_r5';EXE=RUNTIME/'DualSPHysics5.2_GEO_win64.exe';GEN=RUNTIME/'GenCase_win64.exe'
SOURCE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out';PRE=SOURCE/'data/Part_1000.bi4';ADMISSION=L/'upl_c08_formal_r5_r1.admission.json';DECISION=L/'upl_c08_bedkeep_window_decision_r1.json';BUILD=L/'upl_c08_bedkeep_Release_r1.build.json';BED=(1800,1852,1904,1956,2008)
ROOT_THREAD='01a07683-bc64-7463-8db7-9ee6243967d8';THREAD=None;CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
P={k:L/(TAG+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',status='.status.json',tmp='.status.tmp',log='.log',attempt='.queue_attempt.json',queue='.queue_result.json').items()}
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
K.CloseHandle.argtypes=[w.HANDLE];K.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];K.WaitForSingleObject.restype=w.DWORD
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];K.QueryFullProcessImageNameW.restype=w.BOOL
K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];K.GetProcessTimes.restype=w.BOOL

def need(ok,text):
    if not ok:raise RuntimeError(text)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,d,atomic=False):
    q=P['tmp'] if atomic else p
    with q.open('w' if atomic else 'x',encoding='utf-8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    if atomic:os.replace(q,p)
def verify(rows):
    for e in rows:need(stat(e['path'])==e,'Frozen binding changed: '+e['path'])
def norm(p):return os.path.normcase(os.path.abspath(p))
def ident(h,pid):
    ft=[w.FILETIME() for _ in range(4)];n=w.DWORD(32768);buf=ctypes.create_unicode_buffer(n.value)
    need(K.GetProcessTimes(h,*[ctypes.byref(x) for x in ft]) and K.QueryFullProcessImageNameW(h,0,buf,ctypes.byref(n)),'Actual owned process identity unavailable')
    q=psutil.Process(pid)
    return dict(pid=pid,creation_filetime_100ns=(ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime,created_epoch=q.create_time(),exe=buf.value,argv=q.cmdline(),parent_pid=q.ppid())
def alive(h):
    value=K.WaitForSingleObject(h,0);need(value in (0,258),'Owned handle wait failed');return value==258
def exit_code(h):
    need(not alive(h),'Process is still active; no terminal exit is asserted');v=w.DWORD();need(K.GetExitCodeProcess(h,ctypes.byref(v)),'Actual native exit capture failed');return v.value

def last_part():
    p=OUT/'Run.out'
    if not p.exists():return None
    with p.open('rb') as f:f.seek(max(0,p.stat().st_size-65536));lines=f.read().splitlines(keepends=True)
    for line in reversed(lines):
        if re.match(rb'^Part_\d+\s+[0-9.eE+-]+\s+\d+\s+',line) and line.endswith(b'\n'):
            return dict(raw_complete_line=line.decode('utf-8','replace'),not_decoded_native_clock=True)
    return None

def context(admission_path,notify):
    global THREAD
    need(not OUT.exists() and not any(p.exists() for p in P.values()),'Existing formal output/owner/partial receipts are protected')
    ad=read(admission_path);decision=read(DECISION);b=read(BUILD)
    need(ad['passed'] and ad['allowed_job']==TAG and not ad['physical_acceptance'] and not ad['other_psi_admitted'] and ad['decision']==stat(DECISION),'Fresh exact psi0-only prepared admission required')
    need(decision['passed'] and decision['allowed_job']==TAG and decision['decision']=='admit_one_fresh_root_psi0_3s_diagnostic_only' and decision['root_3s_admitted'] and not decision['other_psi_admitted'] and not decision['physical_acceptance'],'Root decision admits only this fresh3s diagnostic, not physics or other groups')
    verify([decision[k] for k in ('source_run','source_native','review','visual')]);r,native,review=(read(decision[k]['path']) for k in ('source_run','source_native','review'))
    need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4240000 and r['saved_frames']==60 and r['consumed_stats_unchanged'],'Closed normal .6s source run required')
    need(native['passed'] and native['original_native_guards_passed'] and native['consumed_stats_unchanged'] and review['passed'] and review['new_normal_frames']==60 and review['three_way_actual_common_steps']==53,'Closed60 native and reviewed figures required')
    d=read(native['completion']['path']);need(d['passed'] and d['samples']==60 and d['completed_steps']==4240000 and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6805 and d['actual_fixed_IDs']==1805 and d['kept_bed_IDs']==list(BED),'Closed60 native registry/release scope differs')
    need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['release_geometry_policy']=='KeepBedOverlapReleaseOnly' and len(b['project_objects'])==113,'Closed matched GPU Release build required')
    need(Path(ad['program']['path']).samefile(EXE) and (stat(EXE)['bytes'],stat(EXE)['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']) and ad['source_build']==stat(BUILD),'runtime_r5 program/build binding differs')
    rows=[stat(p) for p in (admission_path,DECISION,BUILD,Path(__file__),T/'notes/upl_c08_formal_r5_r1.md',Path(short.__file__),Path(summary.__code__.co_filename),SOURCE/'Run.csv',SOURCE/'Run.out',SOURCE/'data/Part_Head.ibi4',PRE)]
    rows += ad['inputs']+ad['consumed']+ad['runtime']+[ad['program'],ad['source_capture'],ad['source_archive'],ad['native_build']]+[decision[k] for k in ('source_run','source_native','review','visual')];rows=list({e['path']:e for e in rows}.values());verify(rows)
    need('C08_PRELOAD_SOURCE=CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out' in BAT.read_text(encoding='utf8'),'Root GPU BAT must bind the original r2 source')
    x=ET.parse(C/(CASE+'_Def.xml')).getroot();p={e.get('key'):e.get('value') for e in x.findall('./execution/parameters/parameter')};need(all(float(p[k])==v for k,v in dict(TimeMax=13,TimeOut=.01,DtFixed=.0000025,DtMin=1e-8,NoPenetration=1,ArtificialStress=1,ArtificialStressCoef=.2,ArtificialStressExp=2.55).items()),'Formal root clock/AS/NoPen parameters differ')
    event=x.find('./execution/special/gravitypreload');need(event.get('statefile')=='__GRAVITY_PRELOAD_STATE__' and event.get('keep_bed_overlap')=='true' and float(event.get('time'))==10 and int(event.get('release_mkbound'))==2,'Formal PRE marker/event/keep scope differs')
    soil=x.find('./execution/special/soils');need(all(float(soil.find(k).get('value'))==v for k,v in dict(phi=25,phi_r=25,n_phi=0,coh=5000,coh_r=1000,n_coh=5,dlt=0,DilationDecay=0).items()),'This owner admits only the unchanged psi0 material')
    need(not any(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(a.lower().startswith('-gpu') for a in (q.info['cmdline'] or [])[1:]) for q in psutil.process_iter(['exe','cmdline'])),'Another GPU physical solver is active; no process is stopped')
    THREAD=os.environ.get('CODEX_THREAD_ID');need(not notify or (THREAD==ROOT_THREAD and CODEX.is_file()),'Launch must inherit the verified root thread; no queue is attempted')
    return rows,stat(BUILD)

def output_checks():
    text=(OUT/'Run.out').read_text(encoding='utf-8-sig');r=summary(OUT/'Run.csv')
    need('Finished execution (code=0).' in text and int(r['Steps'])==5200000 and int(r['PartFiles'])==300,'Actual formal global end/frame count differs')
    need('No Penetration=True' in text and 'Dynamic NoPen: FixedPlaneStageProjectionReleaseOnly' in text and 'ArtificialStress="Bui2008"' in text,'Actual formal fixed-plane/AS1 policy differs')
    for key,expected in (('ArtificialStressCoef',.2),('ArtificialStressExp',2.55)):
        values=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(values)==1 and struct.pack('<f',float(values[0]))==struct.pack('<f',expected),'Actual explicit AS coefficient/exponent log differs')
    need(int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Original registry/no-exclusion summary differs')
    imports=[x for x in text.splitlines() if 'GravityPreload: state imported file=' in x];release=[x for x in text.splitlines() if 'GravityPreload: phase=released' in x]
    need(len(imports)==len(release)==1 and 'GravityPreload: source material law=legacy MR1 ElasticV1;' in text,'Actual legacy import/unique release differs')
    need('retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in release[0],'Actual release/stage flags differ')
    marker='GravityPreload: release policy=KeepBedOverlap ';expected=marker+'original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,BED))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.'
    need(text.count(marker)==1 and expected in text,'Actual five kept original bed IDs/roles differ')
    scalar=0.
    for _ in range(4000000):scalar+=.0000025
    for line in (imports[0],release[0]):
        m=re.search(r'actual=([^ ]+) completed_step=(\d+)',line);need(m and float(m[1])==scalar and int(m[2])==4000000,'Actual source clock/global completed count was reset or changed')
    files=sorted((OUT/'data').glob('Part_*.bi4'));need([p.name for p in files]==['Part_%04d.bi4'%i for i in range(int(r['PartFiles']))],'Actual native file sequence differs')
    return dict(actual_steps=int(r['Steps']),saved_frames=int(r['PartFiles']),actual_new_updates=int(r['Steps'])-4000000,actual_source_time_from_loader=scalar,summary=r,input_xml=stat(OUT/(CASE+'.xml')),actual_import_line=imports[0],actual_release_line=release[0],Run_out=stat(OUT/'Run.out'),Run_csv=stat(OUT/'Run.csv'))

def post_state():
    state=dict(BAT_postprocess_owned=True,native_decoder_invocations=0,VTK_tool_invocations=0,native_review_pending=True,physical_plot_review_pending=True)
    try:
        for name in ('native','PartFluid','PartBound'):
            path=OUT/'logs'/(name+'.call.json')
            if path.exists():
                r=read(path)
                if isinstance(r.get('actual_exit'),int):state['native_decoder_invocations' if name=='native' else 'VTK_tool_invocations']+=1
        completion=OUT/'native/completion.json'
        state['native_review_pending']=not(completion.exists() and read(completion).get('passed') and (OUT/'logs/native.call.json').exists() and read(OUT/'logs/native.call.json').get('passed'))
    except Exception as e:state['postprocess_observation_failure']=str(e)
    return state

def post_checks():
    path=OUT/'postprocess_r5.json';post=read(path)
    need(post['passed'] and post['group']=='psi0' and post['backend_from_Run_csv']=='GPU' and post['global_steps']==5200000 and post['native_completed'] and post['PartFluid'] and post['PartBound'] and not post['raw_BI4_rewritten'] and not post['physical_acceptance'],'Formal postprocessing completion failed or has a different scope')
    completion=OUT/'native/completion.json';d=read(completion);need(d['passed'] and d['group']=='psi0' and d['completed_steps']==5200000 and d['typed_arrays']==22 and d['source_material_law_version']==1 and d['target_material_law_version']==2,'Completed native review differs')
    need(d['stage']=='upl_c08_bedkeep_formal_native_r1' and d['samples']==300 and d['actual_native_IDs_per_frame']==6805 and d['actual_fixed_IDs']==1805 and d['kept_bed_IDs']==list(BED) and d['actual_retired_count']==255 and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and not d['reaction_J_Darcy_closed'] and not d['same_operator_PRE_contract_claimed'],'Completed keep/NoPen native scope differs')
    metadata=OUT/'native/bedkeep_metadata.json';m=read(metadata);need(m['passed'] and m['stage']=='upl_c08_bedkeep_formal_native_r1.metadata' and m['keep_bed_overlap'] and m['kept_bed_IDs']==list(BED) and m['actual_retired_count']==255 and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==300 and m['AS_policy']=='ReleaseOnly','Completed formal keep/AS metadata differs')
    calls=[]
    for name in ('native','PartFluid','PartBound'):
        call=OUT/'logs'/(name+'.call.json');r=read(call);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0,'Post-tool failed: '+name);verify(r['inputs']);verify(r['outputs']);calls.append(stat(call))
    verify([post['source_pre'],post['native_completion'],*post['figure_files'],*post['VTK_calls']]);need(Path(post['source_pre']['path']).samefile(PRE) and Path(post['native_completion']['path']).samefile(completion),'Postprocess PRE/native binding differs')
    fig=Path(post['figure_directory']);required=['history.png','history.csv']+[('fields_tau_%.1f'%t)+suffix for t in (.1,.5,1.,2.,3.) for suffix in ('.png','.csv')]
    need(all((fig/n).is_file() for n in required),'Full-duration figure/CSV set incomplete')
    return dict(postprocess_completed=True,postprocess_check=stat(path),native_completion=stat(completion),bedkeep_metadata=stat(metadata),postprocess_calls=calls,figure_files=post['figure_files'],**post_state())

def queue_once(result):
    event='formal_postprocessing_completed_pending_physical_plot_review' if result['passed'] else ('formal_solver_completed_postprocess_failed' if result.get('solver_completed') else 'formal_run_or_owned_process_failed')
    message=('The authorized single C08 root psi0 r5 GPU 3 s diagnostic '+TAG+' is terminal: '+event+'. Read '+str(P['run'])+' and its actual start/call/status plus the bound preparation/admission/decision. Keep original r2 GPU PRE, all prior r3/r4/plane/AS failures and old runtimes unchanged. This is KeepBedOverlap (five original bed IDs kept, 255 retired, native 6805=5000 soil+1805 fixed), fixed-plane NoPen release-only, AS1 .2/2.55 ReleaseOnly; same-stage Darcy reaction is not closed. Normal exit is not physics/paper acceptance. If completed, the real root BAT already performed one formal native read, separate PartFluid/PartBound series and PNG/CSV; inspect postprocess_r5.json, native completion/bedkeep_metadata, three tool calls and bound figures first. Never duplicate a successful decode/VTK. If solver_completed but postprocessing failed, repair derived outputs only via --postprocess; do not rerun the physical solver. On solver failure preserve the actual Win32 exits, first error and last raw saved console line, without inferring unsaved native time or restarting/relaxing guards. Review all original soil pressure/stress/velocity/plastic history/J and contact/geometry, negative-pressure transients, actual source clock and saved output. Other psi groups remain locked and require separate root admission; do not auto-start them, half chains, another source preload or another solver. This queue is attempted only once with a 45 s timeout; timeout may have delivered, never resend, rearm or add a watcher/connectivity test.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message]
    save(P['attempt'],dict(stage=TAG+'.queue_attempt',utc=utc(),thread=THREAD,argv=argv,run=stat(P['run']),attempts=1,timeout_s=45,do_not_resend=True))
    out=dict(stage=TAG+'.queue_result',attempts=1,thread=THREAD,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,env=os.environ.copy(),creationflags=subprocess.CREATE_NO_WINDOW)
        out.update(status='queued' if q.returncode==0 else 'queue_failed',actual_exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as e:out.update(status='queue_delivery_uncertain',error=str(e),stdout=e.stdout.decode('utf-8','replace') if isinstance(e.stdout,bytes) else e.stdout,stderr=e.stderr.decode('utf-8','replace') if isinstance(e.stderr,bytes) else e.stderr)
    except Exception as e:out.update(status='queue_failed',error=str(e))
    out['ended_utc']=utc();save(P['queue'],out)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--admission',type=Path,default=ADMISSION);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full read and explicit execution authorization required')
    frozen,build=context(args.admission.resolve(),args.notify);owner=short.psutil.Process();ownerid=dict(pid=owner.pid,created_epoch=owner.create_time());cmd=Path(os.environ.get('COMSPEC','C:/Windows/System32/cmd.exe'))
    command='"'+str(cmd)+'" /d /s /c ""'+str(BAT)+'" --unattended"';expected={'GenCase':[str(Path(OUT.name)/(CASE+'_Def')),str(Path(OUT.name)/CASE),'-save:all'],'solver':['-gpu:0','-stable','-mdbc_freeslip:1',str(Path(OUT.name)/CASE),OUT.name,'-dirdataout','data','-svres']}
    result=dict(stage=TAG,passed=False,backend='GPU',output=str(OUT),program=stat(EXE),source_build=build,source_pre_file=stat(PRE),admission=stat(args.admission),decision=stat(DECISION),BAT_executed=False,GenCase_invocations=0,solver_invocations=0,BAT_postprocess_owned=True,native_decoder_invocations=0,native_review_pending=True,physical_plot_review_pending=True,solver_completed=False,postprocess_completed=False,physical_acceptance=False,NoPen_policy='FixedPlaneStageProjectionReleaseOnly',keep_bed_overlap=True,AS_policy='ReleaseOnly',AS_coef=.2,AS_exp=2.55,NoPen_reaction_J_Darcy_closed=False,same_operator_PRE_contract_claimed=False,SHA_scans=0)
    tracked=[];errors=[];wrapper=None;wrapperid=None;started=utc();wall=time.monotonic();next_status=0.;wrapper_early=False
    def publish(state):
        save(P['status'],dict(stage=TAG+'.status',utc=utc(),owner=ownerid,wrapper=wrapperid,owned_wrapper_alive=bool(wrapper and alive(int(wrapper._handle))),children=[dict(role=e['role'],identity=e['identity'],owned_alive=alive(e['handle']),actual_Win32_exit=None if alive(e['handle']) else exit_code(e['handle'])) for e in tracked],state=state,last_console_report=last_part(),ownership_errors=errors,progress_is_console_observation_not_native_clock=True,physical_acceptance=False),True)
    try:
        with P['log'].open('xb') as log:
            wrapper=subprocess.Popen(command,cwd=C,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            result['BAT_executed']=True
            wrapperid=ident(int(wrapper._handle),wrapper.pid);save(P['start'],dict(stage=TAG+'.start',utc=utc(),owner=ownerid,wrapper=wrapperid,wrapper_command_line=command,root_BAT=stat(BAT),notification_thread_from_launch_environment=THREAD,expected_root_thread=ROOT_THREAD,consumed=frozen));print('ROOT_BAT_STARTED',wrapper.pid,flush=True)
            while True:
                if wrapper.poll() is None:
                    try:descendants=psutil.Process(wrapper.pid).children(recursive=True)
                    except psutil.NoSuchProcess:
                        need(not alive(int(wrapper._handle)),'Wrapper identity lost while its native handle is live');descendants=[]
                    for q in descendants:
                        try:
                            exe=q.exe();role='solver' if norm(exe)==norm(EXE) else 'GenCase' if norm(exe)==norm(GEN) else None
                            if role is None or any(e['identity']['pid']==q.pid and e['identity']['created_epoch']==q.create_time() for e in tracked):continue
                            h=K.OpenProcess(0x100000|0x1000,False,q.pid);need(h,'Owned descendant handle acquisition failed')
                            try:identity=ident(h,q.pid)
                            except Exception:K.CloseHandle(h);raise
                            tracked.append(dict(role=role,handle=h,identity=identity));need(identity['parent_pid']==wrapper.pid and identity['argv'][1:]==expected[role],'Actual BAT descendant parent/exact argv differs')
                            need(sum(e['role']==role for e in tracked)==1,'More than one actual '+role+' process observed');print('OBSERVED',role,identity['pid'],flush=True)
                        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                        except Exception as e:errors.append(str(e))
                wrapper_done=wrapper.poll() is not None;live_targets=any(alive(e['handle']) for e in tracked)
                if wrapper_done and live_targets and not wrapper_early:
                    wrapper_early=True;errors.append('Wrapper exited while an owned target remained live; keep observing, never launch another solver');print(errors[-1],flush=True)
                if time.monotonic()>=next_status:
                    publish('wrapper_exited_target_alive' if wrapper_early else 'solver_completed_postprocessing' if any(e['role']=='solver' and not alive(e['handle']) for e in tracked) else 'running');next_status=time.monotonic()+30
                if wrapper_done and not live_targets:break
                time.sleep(.01 if not any(e['role']=='solver' for e in tracked) else .25)
            rc=wrapper.wait();wx=exit_code(int(wrapper._handle));children=[dict(role=e['role'],identity=e['identity'],actual_Win32_exit=exit_code(e['handle'])) for e in tracked]
            save(P['call'],dict(stage=TAG+'.call',started_utc=started,ended_utc=utc(),wrapper=wrapperid,wrapper_command_line=command,actual_wrapper_Popen_wait_exit=rc,actual_wrapper_Win32_exit=wx,children=children,ownership_errors=errors,elapsed_s=time.monotonic()-wall,log=stat(P['log'])))
        gens=[x for x in children if x['role']=='GenCase'];solvers=[x for x in children if x['role']=='solver'];result.update(actual_call=stat(P['call']),GenCase_invocations=len(gens),solver_invocations=len(solvers),wrapper=wrapperid,actual_wrapper_exit=rc,actual_wrapper_Win32_exit=wx,owned_children=children)
        if len(solvers)==1:result.update(actual_exit=solvers[0]['actual_Win32_exit'],actual_Win32_exit=solvers[0]['actual_Win32_exit'],actual_exit_source='owned_solver_Win32_handle')
        need(len(gens)==len(solvers)==1 and gens[0]['actual_Win32_exit']==solvers[0]['actual_Win32_exit']==0 and not errors,'Actual GenCase/solver ownership or exit failed')
        result.update(output_checks());result['solver_completed']=True;need(rc==wx==0,'BAT postprocessing failed after a completed solver; repair post only')
        result.update(post_checks());verify(frozen);result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as e:
        result['first_failure']=str(e)
        # A bookkeeping failure must not abandon or stop an owned still-running wrapper/target.
        if wrapper is not None:
            while alive(int(wrapper._handle)) or any(alive(e['handle']) for e in tracked):
                try:publish('running_after_observation_failure')
                except Exception:pass
                time.sleep(30)
            if not P['call'].exists():save(P['call'],dict(stage=TAG+'.call',wrapper=wrapperid,wrapper_command_line=command,actual_wrapper_Popen_wait_exit=wrapper.wait(),actual_wrapper_Win32_exit=exit_code(int(wrapper._handle)),children=[dict(role=x['role'],identity=x['identity'],actual_Win32_exit=exit_code(x['handle'])) for x in tracked],owner_exception=str(e),last_console_report=last_part()))
            call=read(P['call']);result.update(actual_call=stat(P['call']),actual_wrapper_exit=call['actual_wrapper_Popen_wait_exit'],actual_wrapper_Win32_exit=call['actual_wrapper_Win32_exit'],owned_children=call['children'],GenCase_invocations=sum(x['role']=='GenCase' for x in call['children']),solver_invocations=sum(x['role']=='solver' for x in call['children']))
            target=[x for x in call['children'] if x['role']=='solver']
            if len(target)==1:result.update(actual_exit=target[0]['actual_Win32_exit'],actual_Win32_exit=target[0]['actual_Win32_exit'],actual_exit_source='owned_solver_Win32_handle')
            if len(target)==1 and target[0]['actual_Win32_exit']==0:
                try:result.update(output_checks());result['solver_completed']=True
                except Exception as review_error:result['solver_metadata_failure']=str(review_error)
        result['failed_stage']='postprocess' if result.get('solver_completed') else 'solver_or_ownership'
    result.update(post_state())
    try:verify(frozen);result['consumed_stats_unchanged']=True
    except Exception as e:result.update(passed=False,consumed_stats_unchanged=False,first_failure=result.get('first_failure','')+'; '+str(e))
    result.update(consumed=frozen,last_console_report=last_part(),elapsed_s=time.monotonic()-wall)
    try:publish('terminal_pending_physical_plot_review' if result['passed'] else 'terminal_postprocess_failure' if result.get('solver_completed') else 'terminal_failure')
    except Exception as e:result.update(passed=False,first_failure=result.get('first_failure','')+'; terminal status: '+str(e))
    save(P['run'],result)
    for e in tracked:K.CloseHandle(e['handle'])
    if args.notify and wrapper is not None:queue_once(result)
    print(json.dumps(dict(passed=result['passed'],run=str(P['run']),native_review_pending=result['native_review_pending'],physical_plot_review_pending=True,first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
