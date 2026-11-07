"""One explicit AS/fixed-plane C08 receiver job; no sequence, postprocessing, decoding or retry."""
import argparse,csv,ctypes,datetime,json,os,re,shutil,struct,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
import xml.etree.ElementTree as ET
import psutil
import mdbc_partition_components_r3 as evidence
from upl_c08_resume_r1 import summary
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';RUNTIME=C/'support/runtime_r4'
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
BASE=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r4_Def.xml'
POLICY='FixedPlaneStageProjectionReleaseOnly';SOURCE_STEP=4000000;DT=.0000025
SPECS={
    'CPUdebug':('smoke_CPU','DebugCPU','CPU',True,True,40,40,'10.0001','0.0001',False),
    'GPUdebug':('smoke_GPU','Debug','GPU',True,True,40,40,'10.0001','0.0001',True),
    'OFF':('off_GPU','Release','GPU',True,False,8000,4000,'10.02','0.01',False),
    'SHORT':('short_GPU','Release','GPU',True,True,12000,4000,'10.03','0.01',False),
    'WINDOW':('window_GPU','Release','GPU',True,True,240000,4000,'10.6','0.01',False)}
need,read,stat,bind,save,invoke=evidence.need,evidence.read,evidence.stat,evidence.bind,evidence.save,evidence.invoke
K=evidence.K;K.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];K.WaitForSingleObject.restype=w.DWORD

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def last_part(out):
    path=out/'Run.out'
    if not path.exists():return None
    with path.open('rb') as f:f.seek(max(0,path.stat().st_size-65536));lines=f.read().splitlines(keepends=True)
    return next((x.decode('utf-8','replace') for x in reversed(lines) if re.match(rb'^Part_\d+\s+[0-9.eE+-]+\s+\d+\s+',x) and x.endswith(b'\n')),None)

def publish(tag,out,outer,target,state):
    path=L/(tag+'.status.json');tmp=path.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8') as f:json.dump(dict(stage=tag,utc=utc(),owner_pid=os.getpid(),outer=outer,target=target,state=state,last_original_console_line=last_part(out),native_review_pending=True,physical_acceptance=False),f,indent=2)
    os.replace(tmp,path)

def notify_once(tag,check):
    thread=os.environ['CODEX_THREAD_ID'];codex=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
    r=read(check);event='bounded_run_completed_pending_native_review' if r['passed'] else 'bounded_failed_preserved_pending_diagnosis'
    message=('同线程已授权C08 AS+固定平面单窗候选'+tag+'，事件='+event+'。先读'+str(check)+'和同tag start/call/status/实际admission；核真实owner和tool/solver退出、输入/程序/PRE stat。原r2 GPU认证PRE不改名、不重算10秒，旧r4/plane失败及旧分析全部保留。此窗AS1 epsilon=.2 exp2.55，AS ReleaseOnly；NoPen为FixedPlaneStageProjectionReleaseOnly，ReactionClosed=false，dt2.5us，最多tau.6s/60帧，不是正式3秒/物理验收。成功后先查已有/活动reader，再由根明确选择最多一次已审upl_c08_as_plane_native_r1适配器，按原planned_steps.csv和EXPECT_AS1审22数组/6800IDs/P0/J/ledger/FS/时钟/signed以及逐帧AS Policy/Active/系数；本owner没有自动解码或VTK。失败保留真实首因、最后原始console行和partial，不伪造停止native时间，不重跑/重解码。离线核全材料孔压/应力/速度/塑性/J及极端ID轨迹，不拟合/half/调整原必要dt或阈值。后续按用户原目标继续，但不能据正常退出自动启动下一物理算例或验收。本owner仅终态queue一次45秒，timeout可能已投递，禁止重发/重挂watcher/连通自测。')
    argv=[str(codex),'queue','--thread',thread,'--message',message]
    save(L/(tag+'.queue_attempt.json'),dict(stage=tag,utc=utc(),thread=thread,run=stat(check),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True))
    result=dict(stage=tag,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as e:result.update(status='delivery_uncertain',error=str(e))
    except Exception as e:result.update(status='queue_failed',error=str(e))
    save(L/(tag+'.queue_result.json'),result)

def check_input(path,end,tout,nopen,ason):
    root=ET.parse(path).getroot();params=root.find('execution/parameters');event=root.find('execution/special/gravitypreload')
    need(params is not None and event is not None,'Actual input sections missing')
    pairs=[(x.get('key'),x.get('value')) for x in params.findall('parameter')];p=dict(pairs);need(len(p)==len(pairs),'Duplicate parameters')
    for key,value in dict(DtFixed=DT,DtIni=DT,DtMin=1e-8,TimeMax=float(end),TimeOut=float(tout),NoPenetration=int(nopen),ArtificialStress=int(ason),ArtificialStressCoef=.2,ArtificialStressExp=2.55,SoilStressRateGradCorr=1,SavePosDouble=1,DPCtes=3,Kernel=1,PartsOutMax=0).items():
        need(key in p and float(p[key])==value,'Locked input differs: '+key)
    for section,expected in (('soils',dict(phi=25,phi_r=25,n_phi=0,coh=5000,coh_r=1000,n_coh=5,dlt=0,DilationDecay=0,ModulusE=20e6,PRvs=.33)),('hydromechanics',dict(HydroMech=1,HydroMechDynamicSeepage=1,HydroMechConductivityModel=1,HydroMechConductivityCk=2,HydroMechFreeSeepage=1,HydroMechDrainage=0,PoreCompressionGradCorr=1,PoreWaterRho=1000,PoreWaterBulkModulus=1e9,Porosity=.35,HydraulicConductivity=.0002))):
        node=root.find('execution/special/'+section);need(node is not None,'Missing '+section)
        for key,value in expected.items():
            entries=node.findall(key);need(len(entries)==1 and float(entries[0].get('value'))==value,'Locked '+section+' differs: '+key)
    source=Path(event.get('statefile',''));source=source if source.is_absolute() else path.parent/source
    need(source.is_file() and source.samefile(PRE) and float(event.get('time'))==10 and int(event.get('release_mkbound'))==2 and event.get('elastic_source','false').lower() in ('false','0'),'Actual PRE/event differs')

def owned(tag,argv,solver,memcheck,admission):
    """Acquire real handles before exits; always wait/capture even if observation fails."""
    log=L/(tag+'.solver.log');start=L/(tag+'.start.json');call=L/(tag+'.call.json')
    p=None;targeth=None;outer=None;target=None;rc=wx=tx=None;errors=[];begin=utc();wall=time.monotonic();next_status=0.;out=Path(admission['path']).parent.parent/'outputs'/tag
    with log.open('xb') as f:
        p=subprocess.Popen(argv,cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        try:
            outer=evidence.ident(int(p._handle),p.pid)
            need(Path(outer['exe']).samefile(argv[0]) and outer['argv']==argv and outer['parent_pid']==os.getpid(),'Actual owned argv/identity differs')
            if not memcheck:target=outer
            save(start,dict(stage=tag,started_utc=begin,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),actual_outer=outer,actual_solver=target,admission=admission))
            print('ASPLANE_JOB_STARTED',tag,'outer_PID',p.pid,flush=True)
            while p.poll() is None:
                if time.monotonic()>=next_status:publish(tag,out,outer,target,'running');next_status=time.monotonic()+30
                if memcheck and targeth is None:
                    for q in psutil.Process(p.pid).children(recursive=True):
                        try:
                            if Path(q.exe()).samefile(solver):
                                targeth=K.OpenProcess(0x100000|0x1000,False,q.pid);need(targeth,'Solver handle unavailable');target=evidence.ident(targeth,q.pid)
                                need(target['argv']==argv[argv.index(str(solver)):],'Actual sanitizer solver argv differs')
                                save(L/(tag+'.target.json'),dict(stage=tag,owner_pid=os.getpid(),actual_solver=target));print('ASPLANE_SOLVER_PID',q.pid,flush=True);break
                        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                time.sleep(.02)
        except BaseException as e:errors.append(repr(e))
        finally:
            # No observer failure abandons or restarts an already owned calculation.
            rc=p.wait();code=w.DWORD();wx=code.value if K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)) else None
            if memcheck and targeth:
                waited=K.WaitForSingleObject(targeth,0xffffffff);code=w.DWORD();tx=code.value if waited==0 and K.GetExitCodeProcess(targeth,ctypes.byref(code)) else None
                K.CloseHandle(targeth)
            elif not memcheck:tx=wx
    record=dict(stage=tag,actual_outer=outer,actual_solver=target,arguments=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=wx,actual_solver_Win32_exit=tx,ownership_errors=errors,started_utc=begin,ended_utc=utc(),elapsed_s=time.monotonic()-wall,log=stat(log),admission=admission)
    save(call,record);need(rc==wx==tx==0 and not errors and target is not None,'Actual solver/tool/owner failed; preserve partial, no retry')
    return stat(call)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Explicit reviewed single-job execution required')
    need(not a.notify or (a.action=='WINDOW' and os.environ.get('CODEX_THREAD_ID')=='01a07683-bc64-7463-8db7-9ee6243967d8' and Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe').is_file()),'Only the genuinely new bounded root job may notify once')
    stem,conf,backend,nopen,ason,updates,cadence,end,tout,memcheck=SPECS[a.action];tag='upl_c08_asplane_'+stem+'_r1';out=T/'outputs'/tag;config=T/'configs'/(tag+'_Def.xml');bp=L/('upl_c08_asplane_'+conf+'_r1.build.json');check=L/(tag+'.run.json')
    need(not out.exists() and not config.exists() and not any(p.name!=tag+'.admission.json' for p in L.glob(tag+'.*')),'Existing job/output/owner protected; root admission alone is not an invocation')
    result=dict(stage=tag,passed=False,source_backend='GPU',target_backend=backend,cross_backend_handoff=(backend=='CPU'),physical_acceptance=False,policy=POLICY,ArtificialStress=ason,AS_phase_policy='ReleaseOnly',AS_coef_expected=.2,AS_exp_expected=2.55,AS_active_metadata_review_pending=True,reaction_Darcy_J_closure_claimed=False,same_PRE_operator_claimed=False,solver_invocations=0,reader_invocations=0,postprocessor_invocations=0,PartVTK_invocations=0,SHA_scans=0)
    consumed=[];call=None;program=None
    try:
        b=read(bp);need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['policy']==POLICY and b['artificial_stress_policy']=='ReleaseOnly' and len(b['project_objects'])==(87 if backend=='CPU' else 113),'Closed corresponding current build required')
        need(Path(b['source_capture']['path']).samefile(T/'outputs/upl_c08_asplane_source_r1/source.json'),'Current common plane source capture required')
        consumed=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_asplane_run_r1.md',Path(evidence.__file__),T/'support/upl_c08_resume_r1.py',bp,BASE,PRE,PRE.parent/'Part_Head.ibi4')]+[bind(b[k]) for k in ('program','source_capture','source_archive')]
        program=Path(b['program']['path']);runtime=[]
        root_admission=L/(tag+'.admission.json')
        if root_admission.exists():consumed.append(stat(root_admission))
        for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'):
            origin=RUNTIME/leaf;before=stat(origin);dest=program.parent/leaf
            if not dest.exists():shutil.copy2(origin,dest)
            after=stat(dest);need((before['bytes'],before['mtime_ns'])==(after['bytes'],after['mtime_ns']),'Existing/new local runtime dependency differs: '+leaf);consumed += [before,after];runtime.append(after)
        for q in psutil.process_iter(['exe','cmdline']):
            try:
                exe=q.info['exe'];args=q.info['cmdline'] or []
                need(not(exe and Path(exe).name.lower().startswith('dualsphysics') and (Path(exe).samefile(program) or backend=='GPU' and any(x.lower().startswith('-gpu') for x in args[1:]))),'Conflicting actual solver active; no process is stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        root=ET.parse(BASE).getroot();root.find('execution/special/gravitypreload').set('statefile',str(PRE.resolve()));params=root.find('execution/parameters')
        for key,value in (('TimeMax',end),('TimeOut',tout),('NoPenetration','1'),('ArtificialStress',str(int(ason))),('ArtificialStressCoef','0.2'),('ArtificialStressExp','2.55')):
            nodes=[x for x in params if x.get('key')==key];need(len(nodes)<=1,'Duplicate template parameter: '+key)
            if not nodes:
                need(key in ('ArtificialStressCoef','ArtificialStressExp'),'Missing template parameter: '+key)
                nodes=[ET.SubElement(params,'parameter',key=key,comment='Explicit existing artificial-stress default for this bounded AS comparison')]
            nodes[0].set('value',value)
        with config.open('xb') as f:f.write(ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n')
        check_input(config,end,tout,nopen,ason);consumed.append(stat(config));gen=RUNTIME/'GenCase_win64.exe';consumed.append(stat(gen));prefix=out/tag
        result['GenCase_call']=invoke(tag+'.gencase',[str(gen),str(config.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,end,tout,nopen,ason);consumed += [stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        plan=out/'planned_steps.csv'
        with plan.open('x',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(('part','completed_step'))
            for frame,step in enumerate(range(SOURCE_STEP+cadence,SOURCE_STEP+updates+1,cadence)):
                writer.writerow((frame,step))
        consumed.append(stat(plan));solverargv=[str(program),*(['-cpu','-ompthreads:8'] if backend=='CPU' else ['-gpu:0']),'-stable','-mdbc_freeslip:'+str(int(nopen)),str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(SOURCE_STEP+updates)]
        sanlog=L/(tag+'.memcheck.log');argv=solverargv
        if memcheck:
            consumed.append(stat(evidence.SAN));argv=[str(evidence.SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*solverargv]
        admission=L/(tag+('.owner_admission.json' if root_admission.exists() else '.admission.json'));save(admission,dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),source_backend='GPU',target_backend=backend,source_PRE_certification_required_from_native_loader=True,source_PRE_certified_by_this_owner=False,source_pre_file=stat(PRE),source_build=stat(bp),program=stat(program),policy=result['policy'],ArtificialStress=ason,AS_phase_policy='ReleaseOnly',AS_coef=.2,AS_exp=2.55,planned_steps=stat(plan),planned_new_updates=updates,planned_global_end=SOURCE_STEP+updates,expected_saved_frames=updates//cadence,argv=argv,solver_argv=solverargv,consumed=consumed));result['solver_invocations']=1
        call=owned(tag,argv,program,memcheck,stat(admission));result['actual_call']=call
        r=summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'));frames=updates//cadence
        need(int(r['Steps'])==SOURCE_STEP+updates and int(r['PartFiles'])==frames and int(r['PartsOut'])==0 and int(r['Np'])==7060 and int(r['Nbound'])==int(r['Nfixed'])==2060,'Actual Run/global original registry/count/exclusions differ')
        need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(frames)],'Actual native sequence differs')
        need('No Penetration=True' in text and ('ArtificialStress="Bui2008"' if ason else 'ArtificialStress="None"') in text and 'Dynamic NoPen: '+POLICY in text,'Executed NoPen/AS mode differs')
        if ason:
            for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',2.55)):
                matches=re.findall(r'^\s*'+key+r':\s*([0-9.eE+-]+)\s*$',text,re.M)
                need(len(matches)==1 and struct.pack('<f',float(matches[0]))==struct.pack('<f',value),'Actual AS coefficient/exponent log differs: '+key)
        need(text.count('GravityPreload: phase=released ')==1 and 'retired=260; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'One genuine260 release/phase required')
        imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==SOURCE_STEP,'Actual loader clock/import line missing')
        if memcheck:
            st=sanlog.read_text(encoding='utf-8');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',st);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',st)
            need(errors and leaks and all(int(x.replace(',',''))==0 for x in errors) and all(int(x.replace(',',''))==int(y.replace(',',''))==0 for x,y in leaks),'Actual memcheck summaries missing/nonzero')
        need(all(stat(e['path'])==e for e in consumed),'Consumed source/program/runtime/PRE/input changed')
        result.update(passed=True,actual_exit=0,actual_Win32_exit=0,actual_steps=SOURCE_STEP+updates,saved_frames=frames,actual_source_time_from_loader=float(imported[0][0]),summary=r,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_pre_file=stat(PRE),input_xml=stat(seed),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(p) for p in parts],runtime=runtime,memcheck_zero_errors_and_leaks=True if memcheck else None,memcheck_log=stat(sanlog) if memcheck else None,consumed_stats_unchanged=True,native_review_pending=True)
    except Exception as e:
        result.update(first_failure=str(e));cp=L/(tag+'.call.json')
        if cp.exists():
            q=read(cp);result.update(actual_call=stat(cp),actual_exit=q['actual_solver_Win32_exit'] if memcheck else q['actual_Popen_wait_exit'],actual_Win32_exit=q['actual_solver_Win32_exit'],actual_tool_exit=q['actual_Popen_wait_exit'],ownership_errors=q['ownership_errors'])
    result.update(consumed=consumed,last_original_console_line=last_part(out));save(check,result)
    publish(tag,out,None,None,'completed_pending_native' if result['passed'] else 'failed_preserved_pending_diagnosis')
    if a.notify and result['solver_invocations']:notify_once(tag,check)
    print(json.dumps(dict(passed=result['passed'],receipt=str(check),first_failure=result.get('first_failure'),native_review_pending=result.get('native_review_pending',False))),flush=True)
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
