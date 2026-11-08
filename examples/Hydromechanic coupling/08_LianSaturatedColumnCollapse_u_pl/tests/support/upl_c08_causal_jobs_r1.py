"""Explicit prepare/smoke/window actions for one causal observer; no automatic physical sequence."""
import argparse,csv,json,os,shutil,struct,subprocess
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base
from upl_c08_asn3_window_r1 import summary,signature

T,C,L,PRE=base.T,base.C,base.L,base.PRE
need,read,stat,bind,save=base.need,base.read,base.stat,base.bind,base.save
SOURCE=4000000;IDS=(7017,5944,6814);STEM='CaseLianSaturatedColumnCollapse_psi0_shared_r6'
ROOTXML=C/(STEM+'_Def.xml');ROOTSEED=C/(STEM+'_GPU_out')/(STEM+'.xml')
SPECS={'smoke':('Debug',10,10,'10.000025','0.000025',1,True),'window':('Release',360000,4000,'10.90','0.01',90,False)}
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8';CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
MACROS={'CL':'/DC08_STAGE_TRACE /DC08_CAUSAL_TRACE','NVCC_PREPEND_FLAGS':'-DC08_STAGE_TRACE -DC08_CAUSAL_TRACE'}

def verify(entries):need(all(stat(e['path'])==e for e in entries),'Consumed closed dependency changed')
def paths(profile):
    tag='upl_c08_causal_'+profile+'_GPU_r1';return tag,T/'outputs'/tag,T/'configs'/(tag+'_Def.xml'),T/'configs'/('xCaseLianSaturatedColumnCollapse_causal_'+profile+'_r1_win64_GPU.bat')

def gates(profile):
    tag,_,_,_=paths(profile);adpath=L/(tag+'.admission.json');ad=read(adpath)
    need(ad['passed'] and ad['allowed_job']==tag and ad['ArtificialStressCoef']==.2 and ad['ArtificialStressExp']==3 and ad['FreeSeepagePondingPolicy']=='CompletedOnly','Explicit root admission for this exact AS.2/n3 CompletedOnly job required')
    entries=[stat(adpath)];builds={};capture=None
    for conf,count in (('DebugCPU',87),('Debug',113),('Release',113)):
        p=L/('upl_c08_causal_'+conf+'_r1.build.json');b=read(p);gpu=conf!='DebugCPU'
        need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_runtime_PRE_unchanged'] and len(b['project_objects'])==count,'All three closed isolated causal builds required')
        need(b['trace_macro']=='C08_STAGE_TRACE' and b['causal_macro']=='C08_CAUSAL_TRACE' and b['trace_macro_enabled']==gpu and b['causal_macro_enabled']==gpu and b['environment_macro']['appended']==(MACROS if gpu else {}),'CPU macros off/GPU dual macros required')
        se,archive=bind(b['source_capture']),bind(b['source_archive']);need(Path(se['path']).resolve()==(T/'outputs/upl_c08_causal_source_r1/source.json').resolve() and (capture is None or se==capture),'One frozen causal source capture required')
        if capture is None:entries.extend((se,archive));capture=se
        entries.extend((stat(p),bind(b['program'])));builds[conf]=b
    rb=L/'upl_c08_causal_native_r1.build.json';reader=read(rb);need(reader['passed'],'Reviewed causal reader must already be built; this owner never invokes it');entries.extend((stat(rb),bind(reader['program'])))
    return adpath,ad,entries,builds[SPECS[profile][0]]

def input_tree(profile,generated=False):
    tag,_,_,_=paths(profile);conf,updates,cadence,end,tout,frames,memcheck=SPECS[profile]
    root=base.ET.parse(ROOTSEED if generated else ROOTXML).getroot();event=root.find('execution/special/gravitypreload');event.set('statefile',str(PRE.resolve()));params=root.find('execution/parameters')
    for key,value in (('TimeMax',end),('TimeOut',tout)):
        nodes=[q for q in params if q.get('key')==key];need(len(nodes)==1,'Unique existing clock parameter required');nodes[0].set('value',value);nodes[0].set('comment','Causal observer '+profile+': imported PRE plus '+('0.000025' if profile=='smoke' else '0.90')+' s; no new PRE or formal acceptance' if key=='TimeMax' else 'Causal observer '+profile+' output interval '+tout+' s; retain actual scalar clocks')
    if generated:
        labels={STEM+'_hdp_Actual.vtk':tag+'_hdp_Actual.vtk',STEM+'__Actual.vtk':tag+'__Actual.vtk'};nodes=root.findall('execution/vtkout/vtkfile');need(len(nodes)==2 and {q.get('name') for q in nodes}==set(labels),'Exactly two retained generated VTK labels required')
        for q in nodes:q.set('name',labels[q.get('name')])
        root.attrib.pop('date',None)
    return root

def check_input(path,profile,generated=False):
    root=base.ET.parse(path).getroot()
    if generated:root.attrib.pop('date',None)
    need(signature(root)==signature(input_tree(profile,generated)),'Only declared TimeMax/TimeOut comments, absolute original PRE and exact generated VTK labels/date may differ from r6')

def prepare(profile):
    tag,out,config,bat=paths(profile);receipt=L/(tag+'.prepare.json');need(not out.exists() and not config.exists() and not bat.exists() and not receipt.exists(),'Existing complete/partial preparation protected')
    before=[];result=dict(stage=tag+'.prepare',passed=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,physical_acceptance=False)
    try:
        _,_,entries,b=gates(profile);before=entries+[stat(p) for p in (Path(__file__),T/'notes/upl_c08_causal_jobs_r1.md',Path(base.__file__),Path(base.evidence.__file__),Path(summary.__code__.co_filename),ROOTXML,ROOTSEED,PRE,PRE.parent/'Part_Head.ibi4')]
        with config.open('xb') as f:f.write(base.ET.tostring(input_tree(profile),encoding='utf-8',xml_declaration=True)+b'\n')
        check_input(config,profile);out.mkdir();plan=out/'planned_steps.csv';_,updates,cadence,_,_,frames,_=SPECS[profile]
        with plan.open('x',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(('part','completed_step'));w.writerows((i,SOURCE+(i+1)*cadence) for i in range(frames))
        body='@echo off\r\nsetlocal\r\nset "PYTHON=D:\\anaconda3\\python.exe"\r\nif not exist "%PYTHON%" set "PYTHON=python"\r\n"%PYTHON%" -X utf8 -B "%~dp0..\\support\\upl_c08_causal_jobs_r1.py" '+profile+' --execution-authorized\r\nset "EC=%ERRORLEVEL%"\r\nif not "%~1"=="--unattended" pause\r\nexit /b %EC%\r\n'
        with bat.open('xb') as f:f.write(body.encode('ascii'))
        verify(before);result.update(passed=True,configuration=SPECS[profile][0],program=b['program'],source_build=stat(L/('upl_c08_causal_'+SPECS[profile][0]+'_r1.build.json')),input_xml=stat(config),planned_steps=stat(plan),test_BAT=stat(bat),outputs=[stat(p) for p in (config,plan,bat)],consumed_stats_unchanged=True,actual_seed_pending_single_GenCase=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=before;save(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True);return result['passed']

def smoke_gate(ad):
    tag,out,_,_=paths('smoke');rp=L/(tag+'.run.json');np=L/(tag+'.native_r1.json');r,n=read(rp),read(np)
    need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4000010 and r['saved_frames']==1 and r['memcheck_zero_errors_and_leaks'] and r['cumulative_counters_checked'] and r['consumed_stats_unchanged'],'Sealed ten-update final-only Debug memcheck smoke required')
    need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1 and bind(n['source_run'])==stat(rp),'Unique original smoke native guards required')
    ce,me=bind(n['completion']),bind(n['metadata']);d,m=read(ce['path']),read(me['path'])
    need(d['passed'] and d['stage']=='upl_c08_causal_native_r1' and d['samples']==1 and d['completed_steps']==4000010 and d['actual_native_IDs_per_frame']==6805 and d['typed_arrays']==22 and m['passed'] and m['profile']=='smoke' and m['smoke_final_only'] and m['expected_ponding_policy']=='CompletedOnly' and m['ponding_policy_keys_absent_headers']==1 and m['AS_exponent_float_reference']==3.,'Actual final-only smoke arrays/CompletedOnly metadata required')
    qe=bind(ad['smoke_trace']);q=read(qe['path']);need(q['passed'],'Root must bind the separately reviewed new causal smoke trace/cumulative-ten check')
    need(bind(q['trace'])==bind(r['trace_file']) and bind(q['totals'])==bind(r['totals_file']),'Smoke review must bind both actual causal CSVs')
    return [stat(rp),stat(np),ce,me,qe,bind(r['trace_file']),bind(r['totals_file'])]

def normal_output(out,profile):
    _,updates,cadence,_,_,frames,_=SPECS[profile];r=summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==SOURCE+updates and int(r['PartFiles'])==frames and int(r['Np'])==7060 and int(r['Nbound'])==int(r['Nfixed'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'],'Actual GPU registry/steps/frames/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text,'Actual normal AS1/fixed-plane execution differs')
    for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',3.)):
        values=base.re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,base.re.M);need(len(values)==1 and struct.pack('<f',float(values[0]))==struct.pack('<f',value),'Actual AS coefficient/exponent log differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,base.BED_IDS))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.'
    need(text.count('GravityPreload: phase=released ')==text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'One actual255/five-kept release required')
    imported=base.re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==SOURCE,'Original source clock/import missing')
    need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(frames)],'Actual contiguous native sequence differs')
    trace,totals=out/'C08CausalTrace.csv',out/'C08CausalTotals.csv';need(trace.is_file() and trace.stat().st_size>0,'Actual causal RHS/material/contact trace missing');seen={i:set() for i in IDS};rows=0
    with totals.open(encoding='utf-8-sig',newline='') as f:
        for q in csv.DictReader(f):
            i,step=int(q['native_id']),int(q['completed_step']);count=step-SOURCE;need(i in seen and count in range(cadence,updates+1,cadence) and step not in seen[i] and int(q['errors'])==0 and all(int(q[k])==count for k in ('material_pre_count','material_cor_count','plane_pre_count','plane_cor_count')),'Actual saved cumulative material/contact counters differ');seen[i].add(step);rows+=1
    expected=set(range(SOURCE+cadence,SOURCE+updates+1,cadence));need(all(v==expected for v in seen.values()) and rows==3*frames,'Saved cumulative counter/ID coverage differs')
    return dict(actual_steps=SOURCE+updates,saved_frames=frames,summary=r,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(p) for p in parts],trace_file=stat(trace),totals_file=stat(totals),cumulative_counters_checked=True,cumulative_final_updates_per_ID=updates,causal_trace_scientific_review_pending=True)

def notify_once(receipt):
    tag,_,_,_=paths('window');need(not any((L/(tag+s)).exists() for s in ('.queue_attempt.json','.queue_result.json')),'Existing terminal queue attempt protected; never resend')
    message=('The single admitted C08 causal GPU .90s window is terminal. Read '+str(receipt)+' and original start/call/status/owner_admission/root admission; verify actual owned creation/exe/argv/parent and Popen/Win32 tool/solver exits, frozen dual-macro Release program, original r2GPU10s PRE and input bindings first. This is360000 new updates/global4360000 with90 planned saves, AS.2/n3/CompletedOnly/keep5/fixed-plane, not physical acceptance. C08CausalTrace.csv and C08CausalTotals.csv are output-only observations of IDs7017/5944/6814; do not confuse their new sampling/schema with the old57-column checker. Before any separate unique causal-native invocation, check existing/active readers; retain original22/P0/J/ledger/FS/AS/keep/plane/clock/signed guards and untouched launch plan. Full90-frame no-feedback prefix comparison with the actual r6 body follows native review, not a prior rerun/reference. Preserve failure first cause/partials and the last original console line; never invent unsaved native time, rearm this owner or resend its notification. This owner starts no further solver/native/VTK/PRE/other psi/half chain; root independently decides later development under the continuing user authorization. One45s same-thread terminal queue attempt only; timeout delivery is uncertain, never resend or add a watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(L/(tag+'.queue_attempt.json'),dict(stage=tag,utc=base.utc(),thread=THREAD,run=stat(receipt),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=tag,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(L/(tag+'.queue_result.json'),result)

def run(profile,notify):
    tag,out,config,bat=paths(profile);conf,updates,cadence,_,_,frames,memcheck=SPECS[profile];rp=L/(tag+'.run.json');prep=L/(tag+'.prepare.json');rootad=L/(tag+'.admission.json');allowed={prep.name,rootad.name}
    need(not any(p.name not in allowed for p in L.glob(tag+'.*')) and out.is_dir() and {p.name for p in out.iterdir()}=={'planned_steps.csv'},'Existing physical/GenCase/reader/partial job protected; no retry')
    need(not notify or (profile=='window' and os.environ.get('CODEX_THREAD_ID')==THREAD and CODEX.is_file()),'Only explicitly root-started window may queue once to the same thread')
    before=[];result=dict(stage=tag,passed=False,configuration=conf,source_backend='GPU',target_backend='GPU',physical_acceptance=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,postprocessor_invocations=0,terminal_queue_requested=notify,queue_invocations_at_run_seal=0,SHA_scans=0,native_review_pending=True,free_seepage_policy='CompletedOnly',keep_bed_overlap=True,expected_active_native_IDs=6805,ArtificialStress=True,ArtificialStressCoef=.2,ArtificialStressExp=3.,policy=base.POLICY)
    try:
        _,ad,entries,b=gates(profile);p=read(prep);need(p['passed'] and p['consumed_stats_unchanged'] and p['GenCase_invocations']==p['solver_invocations']==0,'Closed prepare-only record required');before=entries+[stat(prep)]+[bind(e) for e in p['consumed']]+[bind(e) for e in p['outputs']]
        if profile=='window':before+=smoke_gate(ad)
        program=Path(bind(b['program'])['path']);runtime=[]
        for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'):
            origin=C/'support/runtime_r6'/leaf;e=stat(origin);dest=program.parent/leaf
            if not dest.exists():shutil.copy2(origin,dest)
            d=stat(dest);need((d['bytes'],d['mtime_ns'])==(e['bytes'],e['mtime_ns']) and dest.read_bytes()==origin.read_bytes(),'Existing/new known runtime copy differs; never overwrite');before.extend((e,d));runtime.append(d)
        for q in psutil.process_iter(['exe','cmdline']):
            try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(x.lower().startswith('-gpu') for x in (q.info['cmdline'] or [])[1:])),'GPU physical target active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        check_input(config,profile);gen=C/'support/runtime_r6/GenCase_win64.exe';before.append(stat(gen));prefix=out/tag;result['GenCase_invocations']=1;result['GenCase_call']=base.invoke(tag+'.gencase',[str(gen),str(config.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,profile,True);seed_entries=[stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];before+=seed_entries;plan=out/'planned_steps.csv';solverargv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(SOURCE+updates)];argv=solverargv;sanlog=L/(tag+'.memcheck.log')
        if memcheck:before.append(stat(base.evidence.SAN));argv=[str(base.evidence.SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*solverargv]
        ap=L/(tag+'.owner_admission.json');save(ap,dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(rootad),preparation=stat(prep),program=stat(program),source_build=stat(L/('upl_c08_causal_'+conf+'_r1.build.json')),source_capture=b['source_capture'],source_pre_file=stat(PRE),seed=seed_entries,planned_steps=stat(plan),planned_new_updates=updates,planned_global_end=SOURCE+updates,expected_saved_frames=frames,argv=argv,solver_argv=solverargv,consumed=before))
        result['solver_invocations']=1;result['actual_call']=base.owned(tag,argv,program,memcheck,stat(ap));result.update(normal_output(out,profile))
        if memcheck:
            s=sanlog.read_text(encoding='utf-8',errors='replace');need('ERROR SUMMARY: 0 errors' in s and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in s,'Actual memcheck zero errors/leaks required');result.update(memcheck_zero_errors_and_leaks=True,memcheck_log=stat(sanlog))
        verify(before);result.update(passed=True,actual_exit=0,actual_Win32_exit=0,program=stat(program),source_build=stat(L/('upl_c08_causal_'+conf+'_r1.build.json')),source_capture=b['source_capture'],source_archive=b['source_archive'],source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,planned_steps=stat(plan),runtime=runtime,preparation=stat(prep),consumed_stats_unchanged=True)
    except Exception as error:
        result['first_failure']=str(error);cp=L/(tag+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    result.update(consumed=before,last_original_console_line=base.last_part(out));save(rp,result);base.publish(tag,out,None,None,'completed_pending_native' if result['passed'] else 'failed_preserved_pending_diagnosis')
    if notify and result['solver_invocations']:notify_once(rp)
    print(json.dumps(dict(passed=result['passed'],receipt=str(rp),first_failure=result.get('first_failure'))),flush=True);return result['passed']

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('prepare','smoke','window'));ap.add_argument('profile',nargs='?',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized and (a.action=='prepare')==(a.profile is not None) and not(a.action=='prepare' and a.notify),'Root full-read and one explicit action required; prepare additionally names its profile');raise SystemExit(0 if (prepare(a.profile) if a.action=='prepare' else run(a.action,a.notify)) else 1)
