"""Own actual root psi0 r4 GPU BAT once; retain existing handles/status/postcheck/one queue flow."""
import argparse,ctypes,datetime,json,os,re,subprocess,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import psutil
import upl_c08_resume_r1 as short
stat,read,summary=short.stat,short.read,short.summary
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_formal_psi0_r4_r1';CASE='CaseLianSaturatedColumnCollapse_psi0_shared_r4'
OUT=C/(CASE+'_GPU_out');BAT=C/('x'+CASE+'_win64_GPU.bat');RUNTIME=C/'support/runtime_r4';EXE=RUNTIME/'DualSPHysics5.2_GEO_win64.exe';GEN=RUNTIME/'GenCase_win64.exe'
SOURCE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out';PRE=SOURCE/'data/Part_1000.bi4';REG=L/'upl_c08_nopen_public_reg_r1.run.json';REVIEW=L/'upl_c08_nopen_public_review_r1.check.json';BUILD=L/'upl_c08_nopen_public_Release_r1.build.json'
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

def context(review_path,notify):
    global THREAD
    need(not OUT.exists() and not any(p.exists() for p in P.values()),'Existing formal output/owner/partial receipts are protected')
    admission=read(review_path);r=read(REG);cp=L/'upl_c08_nopen_public_reg_r1.call.json';call=read(cp);b=read(BUILD)
    need(admission['passed'] and admission['all15_time_and22_arrays_byte_exact'] and admission['all_signed_clocks_byte_exact'] and admission['consumed_stats_unchanged'],'Closed actual15-frame production NoPen review required')
    need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_GlobalStep']==4060000 and r['saved_frames']==15 and r['consumed_stats_unchanged'],'Actual public0.15 solver did not pass')
    need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_errors']==[] and Path(call['child']['exe']).samefile(EXE) and call['child']['argv']==call['argv'] and call['child']['parent_pid']==call['owner']['pid'],'Actual regression owned exit/program/argv differs')
    need(Path(r['actual_program']['path']).samefile(EXE) and Path(r['actual_PRE']['path']).samefile(PRE),'Actual regression source/program differs')
    need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Closed formal NoPen GPU Release build required')
    need((stat(EXE)['bytes'],stat(EXE)['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'runtime_r4 solver differs from its build')
    native=read(admission['native_completion']['path']);need(native['passed'] and native['stage']=='c08_post_native_r4' and native['samples']==15 and native['completed_steps']==4060000 and native['typed_arrays']==22 and native['actual_native_IDs_per_frame']==6800 and native['DynamicNoPenetrationPolicy']=='LegacyOperatorSplitReleaseOnly' and native['DynamicNoPenetrationActive'] and not native['DynamicNoPenetrationReactionClosed'],'Actual public native15 scope/policy differs')
    post=read(admission['postprocess']['path']);need(post['passed'] and post['global_steps']==4060000 and post['native_completed'] and post['PartFluid'] and post['PartBound'],'Actual0.15 native/Fluid/Bound/PNG/CSV postprocessing required')
    postcall=read(admission['actual_postprocess_call']['path']);need(postcall['actual_Popen_wait_exit']==postcall['actual_Win32_exit']==0 and postcall['ownership_failure'] is None,'Actual postprocessor tool exit/ownership differs')
    rows=[stat(p) for p in (review_path,REG,cp,BUILD,Path(__file__),T/'notes'/(TAG+'.md'),Path(short.__file__),BAT,C/(CASE+'_Def.xml'),C/'support/run_lian_collapse_shared_r4_win64.bat',C/'support/check_lian_preload_schedule_r1.ps1',C/'support/postprocess_lian_collapse_r4.py',C/'README_server_r4.md',SOURCE/'Run.csv',SOURCE/'Run.out',SOURCE/'data/Part_Head.ibi4',PRE)]
    rows += admission['consumed']+r['consumed']+[admission['actual_postprocess_call'],admission['native_completion'],admission['postprocess'],r['actual_program'],r['actual_input'],r['actual_PRE'],b['source_capture'],b['source_archive'],b['program'],post['script'],post['source_pre'],post['native_completion'],*post['figure_files'],*post['VTK_calls']]
    for name in ('native','PartFluid','PartBound'):
        path=Path(admission['postprocess']['path']).parent/'logs'/(name+'.call.json');tool=read(path);need(tool['passed'] and tool['actual_exit']==tool['actual_Win32_exit']==0,'Actual short post-tool failed: '+name);rows += [stat(path),*tool['inputs'],*tool['outputs']]
    rows += [stat(p) for p in RUNTIME.iterdir() if p.is_file()];rows=list({e['path']:e for e in rows}.values());verify(rows)
    need('C08_PRELOAD_SOURCE=CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out' in BAT.read_text(encoding='utf8'),'Root BAT lacks the same original r2 GPU source binding')
    x=ET.parse(C/(CASE+'_Def.xml')).getroot();p={e.get('key'):e.get('value') for e in x.findall('./execution/parameters/parameter')};need(float(p['TimeMax'])==13 and float(p['DtFixed'])==.0000025 and float(p['TimeOut'])==.01 and float(p['NoPenetration'])==1 and float(p['ArtificialStress'])==0,'Formal root clock/NoPen1/AS0 changed');need(x.find('./execution/special/gravitypreload').get('statefile')=='__GRAVITY_PRELOAD_STATE__','Formal root PRE marker differs')
    need(not any(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(a.lower().startswith('-gpu') for a in (q.info['cmdline'] or [])[1:]) for q in psutil.process_iter(['exe','cmdline'])),'Another GPU physical solver is active; no process is stopped')
    THREAD=os.environ.get('CODEX_THREAD_ID');need(not notify or (THREAD==ROOT_THREAD and CODEX.is_file()),'Launch must inherit the verified root thread, not a subagent UUID; no queue is attempted')
    return rows,stat(BUILD)

def output_checks():
    text=(OUT/'Run.out').read_text(encoding='utf-8-sig');r=summary(OUT/'Run.csv')
    need('Finished execution (code=0).' in text and int(r['Steps'])==5200000,'Actual formal global end differs')
    need('No Penetration=True' in text and 'Dynamic NoPen: LegacyOperatorSplitReleaseOnly; elastic PRE uses NoPen off, collapse uses the existing corrector velocity/displacement projection; same-stage Darcy reaction is not included.' in text and 'ArtificialStress="None"' in text,'Actual formal NoPen1/AS0 policy differs')
    need(int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Original registry/no-exclusion summary differs')
    imports=[x for x in text.splitlines() if 'GravityPreload: state imported file=' in x];release=[x for x in text.splitlines() if 'GravityPreload: phase=released' in x]
    need(len(imports)==len(release)==1 and 'GravityPreload: source material law=legacy MR1 ElasticV1;' in text,'Actual legacy import/unique release differs')
    need('retired=260; damping=OFF Shepard=OFF FreeSeepage=ON.' in release[0],'Actual release/stage flags differ')
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
    path=OUT/'postprocess_r4.json';post=read(path)
    need(post['passed'] and post['group']=='psi0' and post['backend_from_Run_csv']=='GPU' and post['global_steps']==5200000 and post['native_completed'] and post['PartFluid'] and post['PartBound'] and not post['raw_BI4_rewritten'] and not post['physical_acceptance'],'Formal postprocessing completion failed or has a different scope')
    completion=OUT/'native/completion.json';d=read(completion);need(d['passed'] and d['group']=='psi0' and d['completed_steps']==5200000 and d['typed_arrays']==22 and d['source_material_law_version']==1 and d['target_material_law_version']==2,'Completed native review differs')
    need(d['stage']=='c08_post_native_r4' and d['DynamicNoPenetrationPolicy']=='LegacyOperatorSplitReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and not d['reaction_J_Darcy_closed'] and not d['same_operator_PRE_contract_claimed'],'Completed NoPen policy/scope differs')
    calls=[]
    for name in ('native','PartFluid','PartBound'):
        call=OUT/'logs'/(name+'.call.json');r=read(call);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0,'Post-tool failed: '+name);verify(r['inputs']);verify(r['outputs']);calls.append(stat(call))
    verify([post['source_pre'],post['native_completion'],*post['figure_files'],*post['VTK_calls']]);need(Path(post['source_pre']['path']).samefile(PRE) and Path(post['native_completion']['path']).samefile(completion),'Postprocess PRE/native binding differs')
    fig=Path(post['figure_directory']);required=['history.png','history.csv']+[('fields_tau_%.1f'%t)+suffix for t in (.1,.5,1.,2.,3.) for suffix in ('.png','.csv')]
    need(all((fig/n).is_file() for n in required),'Full-duration figure/CSV set incomplete')
    return dict(postprocess_completed=True,postprocess_check=stat(path),native_completion=stat(completion),postprocess_calls=calls,figure_files=post['figure_files'],**post_state())

def queue_once(result):
    event='formal_postprocessing_completed_pending_physical_plot_review' if result['passed'] else ('formal_solver_completed_postprocess_failed' if result.get('solver_completed') else 'formal_run_or_owned_process_failed')
    message=('同线程已授权C08正式ψ0 r4 GPU继续：'+TAG+'，事件='+event+'。先读'+str(P['run'])+'及同标签.start.json/.call.json/.status.json与所绑定新的15帧NoPen实际回归审查、原始r2 Part1000、实际root r4 BAT/程序。NoPen为LegacyOperatorSplitReleaseOnly，ReactionClosed=false，退出0不等于完整塌陷物理验收。若run通过，真实BAT已自动完成一次C08Native、独立PartFluid/PartBound全帧VTK、历史/形态PNG及CSV；先核现有postprocess_r4.json、native/completion.json、logs三份post-tool call与绑定图CSV，直接做物理/论文图审核，禁止重复解码或VTK。若solver_completed而postprocess失败，只离线诊断/修复派生，绝不重跑已完成solver。失败保留真实wrapper/solver句柄退出、最后原样console PART行及首因，不虚构未保存时间，不重跑10s、不重启/覆盖/放宽门。完成本组审查后按原用户授权决定其余ψ阶段，不因本提醒直接启动它们。通知仅一次45s，超时可能已送达，禁止重发/重新布防/连通性自测。')
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
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--review-check',type=Path,default=REVIEW);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full read and explicit execution authorization required')
    frozen,build=context(args.review_check.resolve(),args.notify);owner=short.psutil.Process();ownerid=dict(pid=owner.pid,created_epoch=owner.create_time());cmd=Path(os.environ.get('COMSPEC','C:/Windows/System32/cmd.exe'))
    command='"'+str(cmd)+'" /d /s /c ""'+str(BAT)+'" --unattended"';expected={'GenCase':[str(Path(OUT.name)/(CASE+'_Def')),str(Path(OUT.name)/CASE),'-save:all'],'solver':['-gpu:0','-stable','-mdbc_freeslip:1',str(Path(OUT.name)/CASE),OUT.name,'-dirdataout','data','-svres']}
    result=dict(stage=TAG,passed=False,backend='GPU',output=str(OUT),program=stat(EXE),source_build=build,source_pre_file=stat(PRE),BAT_executed=True,GenCase_invocations=0,solver_invocations=0,BAT_postprocess_owned=True,native_decoder_invocations=0,native_review_pending=True,physical_plot_review_pending=True,solver_completed=False,postprocess_completed=False,physical_acceptance=False,NoPen_policy='LegacyOperatorSplitReleaseOnly',NoPen_reaction_J_Darcy_closed=False,same_operator_PRE_contract_claimed=False,SHA_scans=0)
    tracked=[];errors=[];wrapper=None;wrapperid=None;started=utc();wall=time.monotonic();next_status=0.;wrapper_early=False
    def publish(state):
        save(P['status'],dict(stage=TAG+'.status',utc=utc(),owner=ownerid,wrapper=wrapperid,owned_wrapper_alive=bool(wrapper and alive(int(wrapper._handle))),children=[dict(role=e['role'],identity=e['identity'],owned_alive=alive(e['handle']),actual_Win32_exit=None if alive(e['handle']) else exit_code(e['handle'])) for e in tracked],state=state,last_console_report=last_part(),ownership_errors=errors,progress_is_console_observation_not_native_clock=True,physical_acceptance=False),True)
    try:
        with P['log'].open('xb') as log:
            wrapper=subprocess.Popen(command,cwd=C,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
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
