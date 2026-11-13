"""One explicitly admitted Wendland H1.8 psi0 plastic source; no receiver/native/next job."""
import argparse,json,os,re,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base
import c08_h18_bedroles_pre_r1 as prior

T,C,L=base.T,base.C,base.L
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
ROOT=C/'CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml';NOTE=T/'notes/c08_h18_wend_pre_r1.md';ORIGINAL=T/'support/c08_h18_plastic_pre_r1.py'
BUILD=L/'c08_preload_schema2_Release_r1.build.json';RUNTIME=T/'outputs/c08_preload_schema2_Release_r1'
GROUPS={'psi0':('5000','0','0')}
END=2000000;FRAMES=1001;DT=.000005;THREAD=prior.THREAD;CODEX=prior.CODEX
SELECTED=prior.SELECTED;VARS=prior.VARS;signature=prior.signature

def paths(group):
    tag='c08_h18_wend_'+group+'_pre_r1'
    return tag,T/'outputs'/tag,T/'configs'/(tag+'_Def.xml'),T/'configs'/(tag+'_GPU.bat'),L/(tag+'.prepare.json'),L/(tag+'.admission.json'),L/(tag+'.run.json')
def verify(entries):need(all(stat(q['path'])==q for q in entries),'Consumed source/input/program/runtime changed')
def material(group):return dict(zip(('coh','dlt','DilationDecay'),map(float,GROUPS[group])))
def input_tree(group):
    root=ET.parse(ROOT).getroot();root.find('casedef/constantsdef/hdp').set('value','1.8');root.find('casedef/constantsdef/hdp').set('comment','Candidate h/dp=1.8 for Wendland; support remains 2H, unlike the Lian cubic kernel weights')
    main=root.find('casedef/geometry/commands/mainlist');commands=list(main);marks=[i for i,q in enumerate(commands) if q.tag=='setmkbound'];fluid=next(i for i,q in enumerate(commands) if q.tag=='setmkfluid')
    need([commands[i].get('mk') for i in marks]==['0','1','2'] and all(commands[i+1].tag=='drawbox' for i in marks),'Original left/bed/right command pairs differ');left,bed,right=marks;need(bed==left+2 and right==bed+2 and fluid==right+2,'Original geometry pairing differs')
    main[:]=commands[:left]+commands[left:bed]+commands[right:fluid]+commands[bed:right]+commands[fluid:]
    p={q.get('key'):q for q in root.findall('execution/parameters/parameter')}
    for key,value in (('Kernel','2'),('DtIni','0.000005'),('DtFixed','0.000005'),('SoilDampingCoef','0.03'),('TimeMax','13.0')):need(key in p,'Original parameter missing');p[key].set('value',value)
    p['Kernel'].set('comment','Wendland kernel; same H/dp, changed weights and gradients versus retained Cubic source');p['DtFixed'].set('comment','Fixed 5 microsecond source step; original necessary stability guards remain')
    g=root.find('execution/special/gravitypreload');need(g is not None and not g.get('statefile'),'Fresh template must not import');g.set('elastic_source','false');g.set('keep_bed_overlap','false');g.set('comment','Same-material plastic source; preserve native stress/kappa/J/p history; event certificate and equilibrium require independent review')
    soil=root.find('execution/special/soils')
    for key,value in zip(('coh','dlt','DilationDecay'),GROUPS[group]):
        nodes=soil.findall(key);need(len(nodes)==1,'Unique original material key required: '+key);nodes[0].set('value',value);nodes[0].set('comment','Same-material '+group+' source and future receiver must match exactly')
    return root
def check_input(path,group,generated=False):
    actual=ET.parse(path).getroot();expected=input_tree(group)
    if generated:
        need(all(signature(actual.find(q))==signature(expected.find(q)) for q in ('execution/special','execution/parameters')),'GenCase changed source material/physics')
        c=actual.find('execution/constants');need(c is not None and float(c.find('h').get('value'))==.072 and float(c.find('dp').get('value'))==.04,'Generated H/dp differs')
        p=actual.find('execution/particles');need(p is not None and [p.get(k) for k in ('np','nb','nbf')]==['7060','2060','2060'],'Generated source registry differs')
        need([(q.get('mkbound'),q.get('begin'),q.get('count')) for q in p.findall('fixed')]==[('0','0','255'),('1','255','1550'),('2','1805','255')] and [(q.get('begin'),q.get('count')) for q in p.findall('fluid')]==[('2060','5000')],'Generated bed-last roles/IDs differ')
    else:need(signature(actual)==signature(expected),'Only declared Wendland/H/dt/damping/bed-last/plastic-source/group changes allowed')
    pairs=[(q.get('key'),q.get('value')) for q in actual.findall('execution/parameters/parameter')];p=dict(pairs);need(len(p)==len(pairs),'Duplicate actual parameter')
    for key,value in dict(Kernel=2,DPCtes=3,DtIni=DT,DtFixed=DT,DtMin=1e-8,TimeMax=13,TimeOut=.01,SoilDamping=1,SoilDampingCoef=.03,SavePosDouble=1,PartsOutMax=0).items():need(float(p.get(key,'nan'))==value,'Source parameter differs: '+key)
    g=actual.find('execution/special/gravitypreload');need(float(g.get('time'))==10 and g.get('release_mkbound')=='2' and g.get('elastic_source')==g.get('keep_bed_overlap')=='false' and not g.get('statefile'),'Fresh plastic source flags/event differ')
    need(float(p.get('NoPenetration','0'))==float(p.get('ArtificialStress','0'))==0,'Source NoPen/AS must remain OFF')
def build_context():
    b=read(BUILD);need(b['passed'] and b['configuration']=='Release' and b['consumed_stats_unchanged'],'Passed frozen schema2 Release build required')
    program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe';need(bind(b['program'])==stat(program),'Actual new program differs');call=read(bind(b['actual_call'])['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual MSBuild exits failed')
    runtime=[bind(q['destination']) for q in b['runtime']];need({Path(q['path']).name for q in runtime}=={'GenCase_win64.exe','PartVTK_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'} and all(Path(q['path']).parent.samefile(RUNTIME) for q in runtime),'Actual copied new-program runtime differs')
    before=[stat(q) for q in (Path(__file__),NOTE,ORIGINAL,ROOT,BUILD,Path(base.__file__),Path(base.evidence.__file__),Path(base.summary.__code__.co_filename),Path(prior.__file__))]+[bind(b[k]) for k in ('program','actual_call','source_capture','source_archive')]+runtime
    return b,program,before,runtime
def prepare(group):
    tag,out,config,bat,prep,ad,rp=paths(group);need(not any(p.exists() for p in (out,config,bat,prep)),'Existing or partial preparation/source protected');before=[];result=dict(stage=tag+'.prepare',passed=False,group=group,GenCase_invocations=0,solver_invocations=0,reader_invocations=0,physical_acceptance=False)
    try:
        b,program,before,runtime=build_context()
        with config.open('xb') as f:f.write(ET.tostring(input_tree(group),encoding='utf-8',xml_declaration=True)+b'\n')
        check_input(config,group)
        body='@echo off\r\nsetlocal\r\nset "PYTHON=D:\\anaconda3\\python.exe"\r\nif not exist "%PYTHON%" set "PYTHON=python"\r\n"%PYTHON%" -X utf8 -B "%~dp0..\\support\\c08_h18_wend_pre_r1.py" run --group '+group+' --execution-authorized --notify\r\nset "EC=%ERRORLEVEL%"\r\nif not "%~1"=="--unattended" pause\r\nexit /b %EC%\r\n'
        with bat.open('xb') as f:f.write(body.encode('ascii'))
        verify(before);result.update(passed=True,input_xml=stat(config),test_BAT=stat(bat),program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],material=material(group),kernel=2,kernel_name='Wendland',outputs=[stat(config),stat(bat)],consumed_stats_unchanged=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=before;save(prep,result);need(result['passed'],result.get('first_failure','Preparation failed'));print('WENDLAND_SOURCE_PREPARED',tag,flush=True)
def context(group,notify):
    tag,out,config,bat,prep,ad,rp=paths(group);a=read(ad);p=read(prep);b,program,before,runtime=build_context()
    need(a['passed'] and a['allowed_job']==tag and a['group']==group and a['hdp']==1.8 and a['fixed_dt_s']==DT and a['damping_coefficient']==.03 and a['planned_global_end']==END and a['expected_saved_frames']==FRAMES and a['material']==material(group) and a['kernel']==2 and a['kernel_name']=='Wendland','Exact root Wendland/group/material/schedule admission required')
    for key,entry in dict(program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],input_xml=stat(config),preparation=stat(prep)).items():need(bind(a[key])==entry,'Root admission actual binding differs: '+key)
    need(p['passed'] and p['group']==group and p['GenCase_invocations']==p['solver_invocations']==p['reader_invocations']==0 and p['consumed_stats_unchanged'],'Explicit prepare-only receipt required');before += [stat(prep),stat(ad)]+[bind(q) for q in p['outputs']]+[bind(q) for q in p['consumed']]
    thread=os.environ.get('CODEX_THREAD_ID');need(not notify or (a['root_thread_id']==thread==THREAD and CODEX.is_file()),'Only the admitted actual root thread may queue once');check_input(config,group);verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),'GPU physical target active; nothing stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return b,program,before,runtime,thread
def output_checks(out):
    r=base.summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(all(int(r[k])==v for k,v in dict(Steps=END,PartFiles=FRAMES,Np=7060,Nbound=2060,Nfixed=2060,PartsOut=0,PartsOutRhop=0,PartsOutVel=0).items()) and 'Gpu_' in r['Hardware'] and float(r['Dp'])==.04 and float(r['H'])==.072,'Actual GPU source schedule/registry/H/exclusions differ')
    need('Wendland' in r['Configuration'] and '[Simulation INTERRUPTED' not in text,'Actual Wendland source was interrupted or uses a different kernel')
    need('Finished execution (code=0).' in text and 'GravityPreload: requested=10 event_completed_step=2000000 release_mkbound=2;' in text and 'GravityPreload: phase=released' not in text and 'GravityPreload: state imported' not in text and 'GravityPreload: validated native right-wall range=[1805,2060), count=255.' in text,'Must finish original bed-last PRE before any release/import')
    need('No Penetration=False' in text and 'ArtificialStress="None"' in text and 'SoilDamping="BuiFukagawa2013"' in text and 'SoilDampingCoef=0.03' in text and 'PoreShepardRegularization="Enabled"' in text and 'PoreShepardInterval: 40' in text,'Actual AS/NoPen/damping/Shepard source modes differ')
    need([q.name for q in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual1001 contiguous source saves required')
    return dict(actual_steps=END,saved_frames=FRAMES,summary=r,Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(q) for q in parts],source_pre_file=stat(out/'data/Part_1000.bi4'),source_head=stat(out/'data/Part_Head.ibi4'))
def export_selected(tag,out,seed,result):
    particles=out/'particles';particles.mkdir();calls=[];files=[];result['PartVTK_calls']=calls;result['particle_files']=files
    for label,kind,count in (('PartFluid','fluid',5000),('PartBound','fixed',2060)):
        for part in SELECTED:
            argv=[str(RUNTIME/'PartVTK_win64.exe'),'-dirin',str(out/'data'),'-filexml',str(seed),'-first:'+str(part),'-last:'+str(part),'-savevtk',str(particles/label),'-onlytype:-all,'+kind,VARS,'-threads:1'];result['PartVTK_invocations']+=1;calls.append(invoke(tag+'.vtk_'+label+'_%04d'%part,argv,C));path=particles/(label+'_%04d.vtk'%part)
            with path.open('rb') as f:m=re.search(rb'\bPOINTS\s+(\d+)\s+',f.read(4096))
            need(m and int(m[1])==count,'Selected Fluid/Bound point count differs');files.append(stat(path))
    need({q.name for q in particles.iterdir()}=={Path(q['path']).name for q in files},'Unexpected/partial selected export');return calls,files
def queue_once(tag,rp,group):
    attempt=L/(tag+'.queue_attempt.json');reply=L/(tag+'.queue_result.json');need(not attempt.exists() and not reply.exists(),'Existing terminal notification protected; never resend')
    message=('The single admitted C08 Wendland same-material plastic source '+group+' is terminal: '+str(rp)+'. Read original run/start/call/status/owner_admission/root admission first; verify actual owned creation/exe/argv/parent, Popen/Win32/solver exits and new schema2 Release program/full_source capture/archive/input stats. This is Wendland(Kernel2) hdp1.8/H=.072, fixed5us/damping.03/Shepard40, event10 with TimeMax13 and nsteps2M,1001 saves, bed-last fixed MK0[0,255),MK1[255,1805),MK2[1805,2060),5000soil. Source AS/NoPen/keepfalse and elastic_source=false: valid Smooth/Apex/TensionRepair may commit under original guards; stress/kappa/J/p histories are not reset. Wendland and Cubic retain support2H but change kernel weights/gradients, so this is not an h-only or no-feedback comparison. This run does not itself certify a PRE or equilibrium. Only genuine completed source gets selected nominal0/1/5/10s Fluid5000/Bound2060 VTK; actual scalar times remain unchanged. If export fails after solver0, repair derived files only, never rerun this source. A separately reviewed Wendland native qualification is required; Cubic-only profiles cannot be silently reused or relabelled. The source and future target kernel/H contracts must match. A schema2 same-material native qualification must verify exact group cp/psi/sf and complete material/trigger/tension contract; old schema1 kappa0/keep5 readers are incompatible. No automatic decoder, receiver, other group, AS selection or next solver is launched. Preserve actual failure first cause/partials/last console; never invent unsaved failure time. Root independently reviews source equilibrium and parameter choice before further work under user authorization. This same-thread queue is attempted once with45s timeout; timeout delivery is uncertain, never resend/rearm or start a watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=tag,utc=base.utc(),thread=THREAD,run=stat(rp),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=tag,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)
def run(group,notify):
    tag,out,config,bat,prep,ad,rp=paths(group);need(ad.is_file() and prep.is_file(),'Root admission and preparation required');allowed={ad.name,prep.name};need(not out.exists() and not any(q.name not in allowed for q in L.glob(tag+'.*')),'Existing owner/source/partial protected; no retry')
    claim=L/(tag+'.claim.json');save(claim,dict(stage=tag,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));before=[];stage='preflight'
    result=dict(stage=tag,group=group,passed=False,solver_completed=False,postprocess_completed=False,physical_acceptance=False,equilibrium_acceptance=False,native_review_pending=True,source_certificate_verified_by_owner=False,elastic_source=False,keep_bed_overlap=False,ArtificialStress=False,NoPenetration=False,source_material_law_version_expected=2,material=material(group),kernel=2,kernel_name='Wendland',hdp=1.8,expected_native_H=struct.unpack('<f',struct.pack('<f',.072))[0],fixed_dt_s=DT,damping_coefficient=.03,planned_global_end=END,expected_saved_frames=FRAMES,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        b,program,before,runtime,thread=context(group,notify);before.append(stat(claim));out.mkdir();prefix=out/tag;stage='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(tag+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(config.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,group,True);entries=[stat(Path(str(prefix)+q)) for q in ('.xml','.bi4','_Normals.nbi4')];before+=entries;verify(before)
        argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(END)];ownerad=L/(tag+'.owner_admission.json');save(ownerad,dict(stage=tag,group=group,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(ad),preparation=stat(prep),actual_environment_thread=thread,notification_thread=THREAD if notify else None,program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=runtime,input_xml=stat(seed),seed=entries,material=material(group),kernel=2,kernel_name='Wendland',elastic_source=False,planned_global_end=END,expected_saved_frames=FRAMES,fixed_dt_s=DT,argv=argv,solver_argv=argv,consumed=before));before.append(stat(ownerad));result.update(program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=runtime,input_xml=stat(seed),seed=entries,preparation=stat(prep),argv=argv,owner_admission=stat(ownerad))
        stage='solver';result['solver_invocations']=1;result['actual_call']=base.owned(tag,argv,program,False,stat(ownerad));result.update(solver_returned_zero=True,actual_exit=0,actual_Win32_exit=0);stage='solver_output_review';result.update(output_checks(out));result['solver_completed']=True;stage='postprocess';base.publish(tag,out,None,None,'source_completed_selected_exports_running');calls,files=export_selected(tag,out,seed,result);verify(before);result.update(passed=True,postprocess_completed=True,PartVTK_calls=calls,particle_files=files,selected_part_numbers=list(SELECTED),selected_nominal_physical_times_s=[0,1,5,10],VTK_positions_are_float=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage);cp=L/(tag+'.call.json')
        if cp.exists():a=read(cp);result.update(actual_call=stat(cp),actual_exit=a['actual_solver_Win32_exit'],actual_Win32_exit=a['actual_solver_Win32_exit'],actual_tool_exit=a['actual_Popen_wait_exit'],ownership_errors=a['ownership_errors'])
        path=out/'Run.out'
        if path.exists():
            result['Run_out']=stat(path);lines=path.read_text(encoding='utf-8-sig',errors='replace').splitlines();first=next((i for i,line in enumerate(lines) if line.startswith('*** Exception')),None);result['first_engine_exception_lines']=lines[first:first+6] if first is not None else []
    result.update(consumed=before,last_original_console_line=base.last_part(out),unsaved_failure_time_reconstructed=False)
    try:base.publish(tag,out,None,None,'completed_pending_native_and_equilibrium_review' if result['passed'] else 'failed_preserved_pending_diagnosis')
    except Exception as error:result['terminal_status_error']=str(error)
    save(rp,result)
    if notify and (L/(tag+'.call.json')).exists():queue_once(tag,rp,group)
    print(json.dumps(dict(passed=result['passed'],run=str(rp),solver_completed=result['solver_completed'],postprocess_completed=result['postprocess_completed'],first_failure=result.get('first_failure'))),flush=True);return result['passed']

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'));p.add_argument('--group',choices=GROUPS,required=True);p.add_argument('--execution-authorized',action='store_true');p.add_argument('--notify',action='store_true');a=p.parse_args();need(a.execution_authorized and not(a.action=='prepare' and a.notify),'Root review and explicit single action required')
    if a.action=='prepare':prepare(a.group)
    else:raise SystemExit(0 if run(a.group,a.notify) else 1)
