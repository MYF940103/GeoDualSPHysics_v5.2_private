"""Root-reviewed, one OFF→ON bounded GPU sequence; no half/retry/formal-package changes."""
import argparse,ctypes,csv,datetime,json,os,re,shutil,struct,subprocess,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as old
from upl_c08_resume_native_r1_run import check_input
from upl_c08_resume_r1 import summary
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_as_short_r1'
RUNTIME=T/'outputs/upl_c08_as_short_runtime_r1';FAILED=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r3_GPU_out'
SOURCE_XML=FAILED/'CaseLianSaturatedColumnCollapse_psi0_shared_r3.xml';PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
CONTROL=T/'outputs/upl_c08_partial_native_r1';CONTROL_CHECK=L/'upl_c08_partial_native_r1.check.json'
BUILD=L/'upl_c08_artstress_Release_r1.build.json';UNIT=L/'upl_c08_as_unit_r1.check.json'
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8';CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke
K=old.K

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def config(mode):return T/'configs'/(TAG+'_'+mode+'_Def.xml')
def outdir(mode):return T/'outputs'/(TAG+'_'+mode)
def last_part(out):
    path=out/'Run.out'
    if not path.exists():return None
    with path.open('rb') as f:f.seek(max(0,path.stat().st_size-65536));lines=f.read().splitlines(keepends=True)
    for line in reversed(lines):
        if re.match(rb'^Part_\d+\s+[0-9.eE+-]+\s+\d+\s+',line) and line.endswith(b'\n'):return dict(raw_complete_line=line.decode('utf8','replace'),not_decoded_native_clock=True)
    return None

def active_gpu():
    active=[]
    for q in psutil.process_iter(['pid','exe','cmdline']):
        if q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(x.lower().startswith('-gpu') for x in (q.info['cmdline'] or [])[1:]):active.append(q.info)
    need(not active,'Another GPU physical target is active; no process is stopped')

def status(mode,state,owner,child=None,identity=None):
    path=L/(TAG+'.status.json');tmp=L/(TAG+'.status.tmp')
    data=dict(stage=TAG+'.status',utc=utc(),mode=mode,state=state,owner=owner,child=identity,owned_child_alive=(child is not None and child.poll() is None),last_console_report=last_part(outdir(mode)),physical_acceptance=False)
    with tmp.open('w',encoding='utf8') as f:json.dump(data,f,indent=2);f.write('\n')
    os.replace(tmp,path)

def solver(mode,argv):
    tag=TAG+'_'+mode;call=L/(tag+'.solver.call.json');log=L/(tag+'.solver.log');need(not call.exists() and not log.exists(),'Existing target invocation protected');owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time())
    # Popen retains the native target handle until the actual typed wait and Win32 exit are sealed.
    identity=None;errors=[];started=utc();wall=time.monotonic()
    with log.open('xb') as stream:
        child=subprocess.Popen(argv,cwd=C,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            identity=old.ident(int(child._handle),child.pid);need(Path(identity['exe']).samefile(argv[0]) and identity['argv'][1:]==argv[1:] and identity['parent_pid']==os.getpid(),'Actual solver identity/argv/parent differs')
            save(L/(tag+'.solver.start.json'),dict(stage=tag+'.solver.start',utc=utc(),owner=owner,child=identity,argv=argv,program=stat(argv[0])))
            status(mode,'solver_running',owner,child,identity)
        except Exception as e:errors.append(str(e))
        while True:
            try:rc=child.wait(timeout=30);break
            except subprocess.TimeoutExpired:
                try:status(mode,'solver_running' if not errors else 'solver_running_after_observation_error',owner,child,identity)
                except Exception as e:errors.append(str(e))
        code=w.DWORD();got=bool(K.GetExitCodeProcess(int(child._handle),ctypes.byref(code)))
    rec=dict(stage=tag+'.solver.call',owner=owner,child=identity,argv=argv,started_utc=started,ended_utc=utc(),actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,ownership_errors=errors,elapsed_s=time.monotonic()-wall,last_console_report=last_part(outdir(mode)),log=stat(log));save(call,rec)
    status(mode,'solver_exited' if got and rc==code.value==0 and not errors else 'solver_failed_or_observer_failed',owner,child,identity)
    need(got and rc==code.value==0 and not errors,'Actual bounded solver exit/ownership failed; preserve partial output, no reader/retry')
    return stat(call),rec

def pair_off(native):
    stride=8+6800*212;records=[]
    with (native/'typed22.bin').open('rb') as a,(CONTROL/'typed22.bin').open('rb') as b:
        ha=a.read(12);hb=b.read(12);need(ha==hb==struct.pack('<III',6800,22,11),'Actual OFF/control 11-frame headers differ')
        for part in range(11):
            x,y=a.read(stride),b.read(stride);need(len(x)==len(y)==stride,'Incomplete actual OFF/control record');records.append(x==y)
        need(a.read(1)==b.read(1)==b'','Extra native record; no header/count rewrite permitted')
    clocks=(native/'clocks.csv').read_bytes()==(CONTROL/'clocks.csv').read_bytes();layout=(native/'typed22_layout.csv').read_bytes()==(CONTROL/'typed22_layout.csv').read_bytes()
    result=dict(passed=all(records) and clocks and layout,records=11,typed_arrays=22,all22_and_actual_time_bit_equal_by_record=records,full_signed_clock_CSV_byte_equal=clocks,typed_layout_byte_equal=layout,headers_rewritten=False,old_failed_runtime_relabelled_success=False)
    save(native/'off_control_pair.json',result);need(result['passed'],'New AS-OFF differs from retained eleven saved states; no ON launch')
    return result

def native(mode,output,consumed):
    name='upl_c08_partial_native_r1' if mode=='off' else 'upl_c08_as_bounded_native_r1';bp=L/(name+'.build.json');b=read(bp)
    need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Passed six-utility native reader required');exe=Path(bind(b['program'])['path']);consumed += [stat(bp),bind(b['program']),bind(b['source'])]
    need(not any(q.info['exe'] and os.path.normcase(os.path.abspath(q.info['exe']))==os.path.normcase(str(exe)) for q in psutil.process_iter(['exe'])),'Exact native reader is already active')
    dest=T/'outputs'/(TAG+'_'+mode+'_native');cap=4044000 if mode=='off' else 4120000
    call=invoke(TAG+'_'+mode+'.reader',[str(exe),'--read','psi0','GPU',str(output/'data'),str(PRE),str(cap),str(dest)],T)
    d=read(dest/'completion.json');samples=11 if mode=='off' else 30
    counts=dict(samples=samples,completed_steps=cap,last_saved_zero_based_step=cap-1,typed_arrays=22,actual_native_IDs_per_frame=6800,soil_IDs=5000,ledger_checks=5000*samples,fixed_marker_checks=1800*samples,P0_bits_checks=6800*samples,rho_cache_bits_checks=5000*samples,kappa_nondecreasing_from_PRE_checks=5000*samples,nonempty_signed_intervals=samples)
    need(d['passed'] and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original full native coverage/safety failed')
    if mode=='on':need(d['stage']=='upl_c08_as_bounded_native_r1' and d['ArtificialStress'] and d['AS_policy']=='ReleaseOnly' and not d['same_operator_PRE_contract_claimed'],'Bounded AS-on native policy differs')
    pair=pair_off(dest) if mode=='off' else None
    check=dict(stage=TAG+'_'+mode+'.native',passed=True,actual_call=call,native_completion=stat(dest/'completion.json'),completion=d,pair=pair,files=[stat(q) for q in sorted(dest.iterdir()) if q.is_file()],physical_acceptance=False);save(L/(TAG+'_'+mode+'.native.check.json'),check)
    return check

def runtime_checks(mode,output,cap):
    text=(output/'Run.out').read_text(encoding='utf-8-sig');r=summary(output/'Run.csv');samples=11 if mode=='off' else 30
    need('Finished execution (code=0).' in text and int(r['Steps'])==cap and int(r['PartFiles'])==samples and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual normal finish/global cap/frames/no-exclusion failed')
    need(r['Hardware']!='CPU' and int(r['Np'])==7060,'Actual backend/registry differs')
    for marker in ('source material law=legacy MR1 ElasticV1','state imported file=','actual=10.000000000374257 completed_step=4000000','phase=released actual=10.000000000374257 completed_step=4000000 retired=260; damping=OFF Shepard=OFF FreeSeepage=ON.'):
        need(marker in text,'Actual source/import/release marker missing: '+marker)
    need(text.count('GravityPreload: phase=released ')==1,'One genuine 260-marker retirement required')
    need('ArtificialStress="None"' in text if mode=='off' else 'ArtificialStress="Bui2008"' in text,'Actual AS mode log differs')
    files=sorted((output/'data').glob('Part_*.bi4'));need([p.name for p in files]==['Part_%04d.bi4'%i for i in range(samples)],'Actual native PART names/count differ')
    return dict(actual_steps=cap,saved_frames=samples,Run_csv=stat(output/'Run.csv'),Run_out=stat(output/'Run.out'),PARTs=[stat(p) for p in files],last_console_report=last_part(output))

def job(mode,program,consumed):
    tag=TAG+'_'+mode;output=outdir(mode);prefix=output/tag;cap=4044000 if mode=='off' else 4120000
    result=dict(stage=tag,passed=False,physical_acceptance=False,ArtificialStress=(mode=='on'),AS_phase_policy='ReleaseOnly',same_operator_PRE_contract_claimed=False,global_cap=cap,solver_invocations=0,GenCase_invocations=0,reader_invocations=0)
    try:
        active_gpu();check_input(config(mode),PRE);gargv=[str(RUNTIME/'GenCase_win64.exe'),str(config(mode).with_suffix('')),str(prefix),'-save:all']
        result['GenCase_invocations']=1;result['GenCase_call']=invoke(tag+'.gencase',gargv,C);seed=[stat(str(prefix)+s) for s in ('.xml','.bi4','_Normals.nbi4')];consumed += seed;check_input(Path(seed[0]['path']),PRE)
        argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(output),'-dirdataout','data','-svres','-nsteps:'+str(cap)]
        result['solver_invocations']=1;call,actual=solver(mode,argv);result.update(solver_call=call,actual_exit=actual['actual_Popen_wait_exit'],actual_Win32_exit=actual['actual_Win32_exit'],program=stat(program),source_pre_file=stat(PRE),input_xml=seed[0]);result.update(runtime_checks(mode,output,cap));result['runtime_completed']=True
        result['reader_invocations']=1;result['native']=native(mode,output,consumed);need(all(stat(e['path'])==e for e in consumed),'Consumed bindings changed during sequence');result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as e:
        result.update(first_failure=str(e),last_console_report=last_part(output));cp=L/(tag+'.solver.call.json')
        if cp.exists():actual=read(cp);result.update(solver_call=stat(cp),actual_exit=actual['actual_Popen_wait_exit'],actual_Win32_exit=actual['actual_Win32_exit'])
    save(L/(tag+'.run.json'),result);need(result['passed'],mode.upper()+' bounded stage failed: '+result.get('first_failure','unknown'));return result

def queue_once(result):
    envthread=os.environ.get('CODEX_THREAD_ID');need(envthread==THREAD,'One-shot notification requires this original root thread')
    event='off_exact_and_on_bounded_native_passed_pending_physical_review' if result['passed'] else 'bounded_sequence_failed_preserved_pending_diagnosis'
    message=('同线程已授权C08人工应力短序列 '+TAG+'，事件='+event+'。先读tests/logs/'+TAG+'.run.json及off/on原始start/call/run/native收据，核真实owner、退出、stat绑定和原生22/IDs/clock/signeddterror/ledger。OFF仅在11帧相对原失败保存prefix逐byte一致后才准入ON；ON只到tau.30且AS ReleaseOnly ε.2/exp2.55为既有默认，不是论文调参或全程物理验收。失败保留真实partial、最后已保存console行及首因，不推断未保存故障时刻，不重跑/重解码/重布防。成功时读取已有native结果离线绘图审查，再继续原授权诊断；本提醒不自动新solver/half/full。此owner只queue一次45秒，timeout可能已送达，禁止重发。')
    argv=[str(CODEX),'queue','--thread',envthread,'--message',message];save(L/(TAG+'.queue_attempt.json'),dict(stage=TAG+'.queue_attempt',utc=utc(),thread=envthread,argv=argv,terminal_run=stat(L/(TAG+'.run.json')),attempts=1,timeout_s=45,do_not_resend=True))
    rec=dict(stage=TAG+'.queue_result',attempts=1,do_not_resend=True)
    try:
        p=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);rec.update(status='queued' if p.returncode==0 else 'queue_failed',actual_exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired as e:rec.update(status='delivery_uncertain',first_failure=str(e))
    except Exception as e:rec.update(status='queue_failed',first_failure=str(e))
    save(L/(TAG+'.queue_result.json'),rec)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build-check',type=Path,default=BUILD);ap.add_argument('--unit-check',type=Path,default=UNIT);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Author-only until root fully reviews and explicitly invokes this one sequence')
    protected=[RUNTIME,*[outdir(m) for m in ('off','on')],*[T/'outputs'/(TAG+'_'+m+'_native') for m in ('off','on')]]
    need(not any(p.exists() for p in protected) and not list(L.glob(TAG+'*')),'Existing/partial sequence evidence protected; no restart')
    result=dict(stage=TAG,passed=False,physical_acceptance=False,extra_half_or_full_admitted=False,SHA_scans=0,automatic_next_solver=False,jobs=[]);consumed=[]
    try:
        b=read(a.build_check);u=read(a.unit_check);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Passed new AS GPU Release build required');need(u['passed'] is True,'Passed separately root-reviewed AS CPU/GPU unit checks required')
        need(Path(a.build_check).name=='upl_c08_artstress_Release_r1.build.json','Wrong AS Release build receipt');need(read(CONTROL_CHECK)['passed'] and read(CONTROL_CHECK)['original_saved_native_guards_passed'],'Retained failed-run eleven-state native control not closed')
        need(config('off').read_bytes()==SOURCE_XML.read_bytes(),'OFF must bytecopy the actual failed-run XML');onroot=ET.parse(config('on')).getroot();params={q.get('key'):q.get('value') for q in onroot.findall('execution/parameters/parameter')};need(all(float(params[k])==v for k,v in (('ArtificialStress',1),('ArtificialStressCoef',.2),('ArtificialStressExp',2.55))),'ON AS settings differ')
        on=onroot.find('execution/parameters');[on.remove(q) for q in list(on) if q.get('key') in ('ArtificialStress','ArtificialStressCoef','ArtificialStressExp')];offroot=ET.parse(config('off')).getroot();need(ET.tostring(onroot)==ET.tostring(offroot),'ON may only add three AS parameters')
        for m in ('off','on'):check_input(config(m),PRE)
        active_gpu();need(not a.notify or (CODEX.is_file() and os.environ.get('CODEX_THREAD_ID')==THREAD),'Original same-thread single notification CLI required')
        consumed=[stat(p) for p in (a.build_check,a.unit_check,CONTROL_CHECK,SOURCE_XML,PRE,PRE.parent/'Part_Head.ibi4',config('off'),config('on'),Path(__file__),Path(old.__file__),T/'support/upl_c08_resume_native_r1_run.py',T/'support/upl_c08_resume_r1.py',T/'notes'/(TAG+'.md'))]+[bind(b['program']),bind(b['source_capture']),bind(b['source_archive'])]+[stat(CONTROL/n) for n in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json')]
        for reader in ('upl_c08_partial_native_r1','upl_c08_as_bounded_native_r1'):
            rp=L/(reader+'.build.json');rb=read(rp);need(rb['passed'] and rb['consumed_stats_unchanged'] and len(rb['objects'])==6 and not rb['JSph_objects_linked'],'Both approved native readers must be closed before any solver');consumed += [stat(rp),bind(rb['program']),bind(rb['source'])]
        RUNTIME.mkdir();program=Path(b['program']['path'])
        for origin in [program,*[C/'support/runtime_r3'/x for x in ('GenCase_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')]]:
            source=stat(origin);dest=RUNTIME/origin.name;shutil.copy2(origin,dest);copy=stat(dest);need((source['bytes'],source['mtime_ns'])==(copy['bytes'],copy['mtime_ns']),'New isolated runtime copy differs');consumed += [source,copy]
        save(L/(TAG+'.start.json'),dict(stage=TAG+'.start',utc=utc(),owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),source_build=stat(a.build_check),unit_check=stat(a.unit_check),consumed=consumed,plan=['OFF4044000→11-frame exact native gate','ON4120000→30-frame original native gates'],formal_inputs_or_runtime_changed=False,PRE_recomputed=False))
        for mode in ('off','on'):result['jobs'].append(job(mode,RUNTIME/program.name,consumed))
        need(all(stat(e['path'])==e for e in consumed),'Final sequence consumed bindings changed');result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as e:result.update(first_failure=str(e),consumed_stats_unchanged=bool(consumed) and all(Path(e['path']).is_file() and stat(e['path'])==e for e in consumed))
    result['job_run_records']=[stat(L/(TAG+'_'+m+'.run.json')) for m in ('off','on') if (L/(TAG+'_'+m+'.run.json')).exists()];result['consumed']=consumed;save(L/(TAG+'.run.json'),result)
    owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time());mode='on' if (L/(TAG+'_on.solver.call.json')).exists() else 'off';status(mode,'terminal_passed_pending_physical_review' if result['passed'] else 'terminal_failure',owner)
    if a.notify and (L/(TAG+'.start.json')).exists():queue_once(result)
    print(json.dumps(dict(passed=result['passed'],run=str(L/(TAG+'.run.json')),first_failure=result.get('first_failure'),physical_acceptance=False)),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
