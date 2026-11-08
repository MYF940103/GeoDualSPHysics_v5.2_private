"""One admitted fresh h/dp1.5 elastic PRE and selected Fluid/Bound exports; no receiver."""
import argparse,json,os,re,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base
T,C,L=base.T,base.C,base.L
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='upl_c08_hdp15_preload_GPU_r1';OUT=T/'outputs'/TAG;CONFIG=T/'configs'/(TAG+'_Def.xml');BAT=T/'configs'/('x'+TAG+'_win64_GPU.bat')
NOTE=T/'notes/upl_c08_hdp15_preload_r1.md';ROOT=C/'CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml';RUNTIME=C/'support/runtime_r6'
AD=L/(TAG+'.admission.json');RUN=L/(TAG+'.run.json');THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
PS=Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe');SCHEDULE=C/'support/check_lian_preload_schedule_r1.ps1';SELECTED=(100,500,1000)
VARS='-vars:-all,+idp,+mk,+vel,+rhop,+PorePress,+PorePress0,+ExcessPorePress,+SigmaState_kk,+SigmaState_ij,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PoroVolumeRatio,+PoroPorosity,+PoroThetaLastStage,+PoroCurrentVolume,+PoroMixtureDensity,+PoroHydraulicConductivity,+PosDiv,+HydroMechLoadAce'

def verify(entries):need(all(stat(q['path'])==q for q in entries),'Consumed input/program/runtime/source binding changed')

def signature(n):return n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k!='comment' and not k.endswith('_comment'))),(n.text or '').strip(),tuple(signature(q) for q in n)

def check_input(path,generated=False):
    expected=ET.parse(ROOT).getroot();h=expected.find('casedef/constantsdef/hdp');need(h.get('value')=='1.2','Retained source template changed');h.set('value','1.5');actual=ET.parse(path).getroot()
    if generated:
        need(all(signature(actual.find(q))==signature(expected.find(q)) for q in ('execution/special','execution/parameters')),'GenCase changed the actual physical source input')
        constants=actual.find('execution/constants');need(float(constants.find('h').get('value'))==.06 and float(constants.find('dp').get('value'))==.04,'Actual generated h/dp differs')
    else:need(signature(actual)==signature(expected),'Only declared hdp1.2->1.5/comments may differ from the retained source template')
    p={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};event=actual.find('execution/special/gravitypreload')
    need(float(p.get('NoPenetration','0'))==float(p.get('ArtificialStress','0'))==0 and event.get('elastic_source')=='true' and not event.get('statefile') and event.get('keep_bed_overlap','false')=='false','Fresh elastic source must have NoPen/AS/bedkeep off and no imported state')

def context(notify):
    a=read(AD);need(a['passed'] and a['allowed_job']==TAG and a['hdp']==1.5 and a['planned_global_end']==4000000 and a['expected_saved_frames']==1001,'Explicit root admission for this exact fresh10s source required')
    thread=os.environ.get('CODEX_THREAD_ID');need(not notify or (a['root_thread_id']==THREAD and thread in (None,'',THREAD) and CODEX.is_file()),'Only the admitted same root thread may receive one terminal queue')
    rp=L/'upl_c08_formal_psi0_r6_r1.run.json';r=read(rp);need(r['passed'] and r['solver_completed'] and r['postprocess_completed'],'Closed official runtime_r6 provenance required');bp=Path(bind(r['source_build'])['path']);b=read(bp)
    need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Closed Release source build required');program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe';need(bind(r['program'])==stat(program) and (stat(program)['bytes'],stat(program)['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'Actual official runtime_r6 program differs')
    install=L/'upl_c08_formal_r6_runtime_r1.json';ri=read(install);need(ri['passed'],'Closed official runtime_r6 installation required');dest={Path(q['destination']['path']).name:q['destination'] for q in ri['files']}
    runtime=[bind(dest[k]) for k in ('DualSPHysics5.2_GEO_win64.exe','GenCase_win64.exe','PartVTK_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')]
    before=[stat(q) for q in (Path(__file__),NOTE,CONFIG,BAT,ROOT,AD,rp,bp,install,SCHEDULE,PS,Path(base.__file__),Path(base.evidence.__file__),Path(base.summary.__code__.co_filename))]+runtime+[bind(b[k]) for k in ('source_capture','source_archive')]
    check_input(CONFIG);verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),'GPU physical target active; no process stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return a,b,bp,program,before,thread

def output_checks():
    r=base.summary(OUT/'Run.csv');text=(OUT/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((OUT/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==4000000 and int(r['PartFiles'])==1001 and int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'] and float(r['Dp'])==.04 and float(r['H'])==.06,'Actual GPU source schedule/registry/h/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'GravityPreload: requested=10 event_completed_step=4000000 release_mkbound=2;' in text and 'GravityPreload: phase=released' not in text and 'GravityPreload: state imported' not in text,'Source must finish at PRE before any release/import')
    need('No Penetration=False' in text and 'ArtificialStress="None"' in text and 'SoilDamping="BuiFukagawa2013"' in text and 'SoilDampingCoef=0.02' in text and 'PoreShepardRegularization="Enabled"' in text and 'PoreShepardInterval: 40' in text,'Actual source NoPen/AS/damping/Shepard log differs')
    need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(1001)],'Actual1001 contiguous native source PART files required')
    return dict(actual_steps=4000000,saved_frames=1001,Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),PARTs=[stat(p) for p in parts],source_pre_file=stat(OUT/'data/Part_1000.bi4'),source_head=stat(OUT/'data/Part_Head.ibi4'),physical_time_Run_csv_rounded_text=r['PhysicalTime'],Hardware=r['Hardware'])

def export_selected(seed,result):
    particles=OUT/'particles';particles.mkdir();calls=[];files=[]
    for label,kind,npoints in (('PartFluid','fluid',5000),('PartBound','fixed',2060)):
        for part in SELECTED:
            argv=[str(RUNTIME/'PartVTK_win64.exe'),'-dirin',str(OUT/'data'),'-filexml',str(seed),'-first:'+str(part),'-last:'+str(part),'-savevtk',str(particles/label),'-onlytype:-all,'+kind,VARS,'-threads:1'];result['PartVTK_invocations']+=1;calls.append(invoke(TAG+'.vtk_'+label+'_%04d'%part,argv,C));p=particles/(label+'_%04d.vtk'%part)
            with p.open('rb') as f:m=re.search(rb'\bPOINTS\s+(\d+)\s+',f.read(4096))
            need(m and int(m[1])==npoints,'Selected '+label+' point count differs');files.append(stat(p))
    need({p.name for p in particles.iterdir()}=={Path(q['path']).name for q in files},'Unexpected/partial selected particle export');return calls,files

def queue_once(thread):
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists(),'Existing terminal queue protected; never resend')
    message=('同线程已授权 hdp1.5 fresh PRE终态：'+TAG+'。先读 '+str(RUN)+' 与原始start/call/status/owner_admission/root admission，核真实创建时间/exe/argv/parent/Win32出口及程序输入stat。它仅用runtime_r6 law2从零重力加载10s/4M步/1001帧；AS/NoPen/keepbed均off，dp.04/dt2.5us/阻尼.02/Shepard40/Model1Ck2原样，不是撤墙或平衡验收。若solver完成但VTK后处理失败，只修派生，绝不重算source。所有BI4保留，selected1/5/10s PartFluid/PartBound仅供审阅；真实保存clock/22数组/κ0/P0/ledger/FS/必要时步仍待原认证loader及同H新窄资格审查。原h1.2 server PRE为旧law1、来源程序不同，不能称单独h-only 0ULP控制。失败保留真实rc/首因及最后原始PART行，不虚构未保存状态。root审物理与认证后决定同h ψ0接收；本owner不启动接收/其他ψ/half/native/新PRE。只queue一次45s，超时可能已投递，不重发/不重新布防。')
    argv=[str(CODEX),'queue','--thread',thread,'--message',message];save(attempt,dict(stage=TAG,utc=base.utc(),thread=thread,run=stat(RUN),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        p=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=p.returncode,status='queued' if p.returncode==0 else 'queue_failed',stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');args=ap.parse_args();need(args.execution_authorized and AD.is_file(),'Root full-read and explicit admission are required before this test can start')
    need(not OUT.exists() and not any(p.name!=AD.name for p in L.glob(TAG+'.*')),'Existing owner/output/partial protected; no retry');claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));before=[];stage='preflight';result=dict(stage=TAG,passed=False,solver_completed=False,postprocess_completed=False,physical_acceptance=False,equilibrium_acceptance=False,native_review_pending=True,source_material_law_version_expected=2,source_material_law_version_native_observed=False,retained_hdp12_source_law_version=1,independent_h_only_control_claimed=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        a,b,bp,program,before,environment_thread=context(args.notify);before.append(stat(claim));OUT.mkdir();prefix=OUT/TAG;stage='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,True);seed_entries=[stat(Path(str(prefix)+q)) for q in ('.xml','.bi4','_Normals.nbi4')];before+=seed_entries;verify(before)
        argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:4000000'];ad=L/(TAG+'.owner_admission.json');save(ad,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(AD),actual_environment_thread=environment_thread,notification_thread=THREAD if args.notify else None,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],input_xml=stat(seed),seed=seed_entries,planned_global_end=4000000,expected_saved_frames=1001,argv=argv,solver_argv=argv,consumed=before));before.append(stat(ad))
        stage='solver';result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(ad));result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],input_xml=stat(seed),seed=seed_entries,hdp=1.5,expected_native_H=float(struct.unpack('<f',struct.pack('<f',.06))[0]))
        stage='solver_output_review';result.update(output_checks())
        stage='postprocess';base.publish(TAG,OUT,None,None,'source_completed_selected_exports_running');result['schedule_call']=invoke(TAG+'.schedule',[str(PS),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(SCHEDULE),'-SourceOut',str(OUT)],C);calls,files=export_selected(seed,result);verify(before);result.update(passed=True,postprocess_completed=True,PartVTK_calls=calls,particle_files=files,selected_part_numbers=list(SELECTED),selected_nominal_physical_times_s=[1,5,10],VTK_positions_are_float=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage);cp=L/(TAG+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    result.update(consumed=before,last_original_console_line=base.last_part(OUT))
    try:base.publish(TAG,OUT,None,None,'completed_pending_PRE_and_physical_review' if result['passed'] else 'failed_preserved_pending_diagnosis')
    except Exception as error:result['terminal_status_error']=str(error)
    save(RUN,result)
    if args.notify and (L/(TAG+'.call.json')).exists():queue_once(THREAD)
    print(json.dumps(dict(passed=result['passed'],run=str(RUN),solver_completed=result['solver_completed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
