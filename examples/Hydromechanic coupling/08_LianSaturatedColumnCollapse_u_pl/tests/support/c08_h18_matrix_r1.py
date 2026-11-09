"""Prepare/run only three admitted H1.8 psi0 windows; root selects physics after one terminal notification."""
import argparse, csv, json, os, re, struct, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base

T,C,L=base.T,base.C,base.L
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='c08_h18_matrix_r1'; NOTE=T/'notes'/(TAG+'.md'); MANIFEST=T/'configs'/(TAG+'.jobs.json')
PROFILES=T/'configs/c08_h18_profiles_r2.json'; AD=L/(TAG+'.admission.json'); RUN=L/(TAG+'.run.json')
ROOT=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml'; RUNTIME=C/'support/runtime_r6'
SOURCE=T/'outputs/c08_h18_pre_r2'; PRE=SOURCE/'data/Part_1000.bi4'; SOURCE_RUN=L/'c08_h18_pre_r2.run.json'
NATIVE_BUILD=L/'c08_h18_native_r1.build.json'; NATIVE=T/'outputs/c08_h18_native_r1_build/C08H18Native_win64.exe'
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'; CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
JOBS=[('c08_h18_a03_w09_r1',.3),('c08_h18_a05_w09_r1',.5),('c08_h18_a07_w09_r1',.7)]
MATERIAL_KEYS=('DPCtes','phi','phi_r','n_phi','coh','coh_r','n_coh','dlt','DilationDecay','SoilTriggerFos','fresh_trigger_active')


def verify(entries):need(all(stat(e['path'])==e for e in entries),'Consumed closed input/program/source changed')
def f32(value):return struct.pack('<f',float(value))
def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def signature(n):return n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k!='comment' and not k.endswith('_comment'))),(n.text or '').strip(),tuple(signature(q) for q in n)


def profiles():
    p=read(PROFILES); need(p['schema']==1 and p['source_job']=='c08_h18_pre_r2' and p['kernel']=='Cubic' and p['kernel_id']==1 and p['hdp']==1.8 and p['Dp']==.04 and p['H_nominal_m']==.072 and p['fixed_dt_s']==.000005 and p['preload_completed_step']==2000000 and p['preload_samples']==1001 and p['preload_damping_coefficient']==.03 and not p['release_damping'] and not p['release_Shepard'] and not p['residual_viscosity'],'Closed H1.8 source/release profile differs')
    need(p['AS_coefficients_first']==[.3,.5,.7] and p['AS_exponent_first']==3.825 and p['selection_requires_physical_review'],'Only three epsilon windows at n3.825 are admitted here')
    rows=[q for q in p['receiver'] if q['duration_s']==.9]; need(len(rows)==1,'One explicit .90 receiver profile required'); w=rows[0]; plan=Path(w['plan']); steps=table(plan)
    need(w['end_completed_step']==2180000 and w['samples']==91 and len(steps)==91 and int(steps[0]['completed_step'])==2000001 and int(steps[-1]['completed_step'])==2180000 and float(steps[0]['time_s'])==w['first_actual_time_s'] and float(steps[-1]['time_s'])==w['actual_end_s'],'Original scalar-time91-state window plan differs')
    need(list(steps[0])==['part','completed_step','saved_step','time_s','dt_s'] and all(int(q['part'])==i and int(q['saved_step'])==int(q['completed_step'])-1 and float(q['dt_s'])==p['fixed_dt_s'] for i,q in enumerate(steps)),'Original plan columns/indices/dt differ')
    return p,w,plan


def expected(coefficient):
    x=ET.parse(ROOT).getroot(); x.find('casedef/constantsdef/hdp').set('value','1.8'); event=x.find('execution/special/gravitypreload'); event.set('statefile',str(PRE.resolve())); event.set('keep_bed_overlap','true')
    values={'DtIni':'0.000005','DtFixed':'0.000005','SoilDampingCoef':'0.03','TimeMax':'10.90','TimeOut':'0.01','ArtificialStressCoef':str(coefficient),'ArtificialStressExp':'3.825'}
    for key,value in values.items():
        rows=x.findall("execution/parameters/parameter[@key='"+key+"']"); need(len(rows)==1,'Unique retained template parameter required: '+key); rows[0].set('value',value)
    return x


def check_input(path,coefficient,generated=False):
    actual=ET.parse(path).getroot(); want=expected(coefficient)
    if generated:
        need(all(signature(actual.find(q))==signature(want.find(q)) for q in ('execution/special','execution/parameters')),'Generated physical source sections differ'); ct=actual.find('execution/constants'); need(float(ct.find('h').get('value'))==.072 and float(ct.find('dp').get('value'))==.04,'Generated Cubic H/dp differs')
    else:need(signature(actual)==signature(want),'Only explicit H/dt/damping/AS/end/source changes and comments may differ from r6')
    return actual


def prepare():
    p,w,plan=profiles(); bat=T/'configs'/('x'+TAG+'_win64_GPU.bat'); need(not MANIFEST.exists() and not bat.exists(),'Prepared manifest/BAT protected'); jobs=[]
    for tag,coefficient in JOBS:
        config=T/'configs'/(tag+'_Def.xml'); need(not config.exists(),'Existing complete/partial prepared job protected')
    for tag,coefficient in JOBS:
        config=T/'configs'/(tag+'_Def.xml')
        payload=ET.tostring(expected(coefficient),encoding='utf-8',xml_declaration=True)
        with config.open('xb') as f:f.write(b'\n'.join(line.rstrip() for line in payload.splitlines())+b'\n')
        check_input(config,coefficient)
        jobs.append(dict(tag=tag,group='psi0',AS_coefficient=coefficient,AS_exponent=3.825,configuration=stat(config),plan=stat(plan),end_completed_step=w['end_completed_step'],samples=w['samples'],output=str(T/'outputs'/tag)))
    text='\r\n'.join(('@echo off','setlocal','cd /d "%~dp0..\\.."','set "c08python=D:\\anaconda3\\python.exe"','if not exist "%c08python%" set "c08python=python"','"%c08python%" -X utf8 -B "tests\\support\\c08_h18_matrix_r1.py" run --execution-authorized --notify','set "EC=%ERRORLEVEL%"','if not "%~1"=="--unattended" pause','exit /b %EC%',''))
    with bat.open('x',encoding='ascii',newline='') as f:f.write(text)
    save(MANIFEST,dict(stage=TAG+'.prepare',prepared_only=True,profiles=stat(PROFILES),template=stat(ROOT),BAT=stat(bat),source_pre_path=str(PRE),source_job='c08_h18_pre_r2',jobs=jobs,source_qualification_not_claimed=True,admission_written=False,solver_invocations=0,GenCase_invocations=0,native_invocations=0,physical_acceptance=False))
    print(json.dumps(dict(prepared=True,manifest=stat(MANIFEST),jobs=[q['tag'] for q in jobs],physical_invocations=0)),flush=True)


def idle(reader=False):
    for proc in psutil.process_iter(['exe','cmdline']):
        try:
            exe=proc.info['exe']; args=proc.info['cmdline'] or []
            need(not(exe and Path(exe).name.lower().startswith('dualsphysics') and any(q.lower().startswith('-gpu') for q in args[1:])),'GPU physical target active; nothing stopped')
            if reader:need(not(exe and Path(exe).name.lower().startswith('c08') and 'native' in Path(exe).name.lower()),'C08 native reader active; nothing stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass


def context(notify):
    p,w,plan=profiles(); a=read(AD); need(a['passed'] and a['allowed_plan']==TAG and a['profiles']==stat(PROFILES) and a['source_equilibrium_reviewed'] and isinstance(a['native_auto_authorized'],bool),'Root admission after source equilibrium review for this exact manifest/native policy required')
    thread=os.environ.get('CODEX_THREAD_ID'); need(not notify or (a['root_thread_id']==THREAD and thread==THREAD and CODEX.is_file()),'Only actual root thread may queue once')
    m=read(MANIFEST); need(m['prepared_only'] and m['profiles']==stat(PROFILES) and m['template']==stat(ROOT) and m['source_pre_path']==str(PRE) and len(m['jobs'])==3,'Prepared manifest differs')
    for row,(tag,coefficient) in zip(m['jobs'],JOBS):
        need(row['tag']==tag and row['group']=='psi0' and row['AS_coefficient']==coefficient and row['AS_exponent']==3.825 and row['plan']==stat(plan) and row['samples']==91 and row['end_completed_step']==2180000 and Path(row['output'])==T/'outputs'/tag,'Prepared parameter window differs'); check_input(bind(row['configuration'])['path'],coefficient)
    source_path=Path(bind(a['source_run'])['path']); need(source_path.samefile(SOURCE_RUN),'Only the corrected actual source r2 is allowed'); sr=read(source_path)
    need(sr['passed'] and sr['solver_completed'] and sr['actual_exit']==sr['actual_Win32_exit']==0 and sr['actual_steps']==2000000 and sr['saved_frames']==1001 and sr['consumed_stats_unchanged'] and sr['source_pre_file']==stat(PRE),'Genuine completed H1.8 source required before matrix')
    sd=read(bind(a['source_native'])['path']); sc=read(bind(a['source_native_call'])['path']); nb=read(bind(a['native_build'])['path'])
    need(sd['passed'] and sd['stage']=='c08_h18_native_r1.source' and sd['certified_PRE'] and not sd['partial'] and sd['samples']==1001 and sd['completed_steps']==2000000 and not sd['runtime_success_claimed'] and not sd['physical_acceptance'],'Actual full new-PRE qualification required; partials are ineligible')
    need(sc['actual_Popen_wait_exit']==sc['actual_Win32_exit']==0 and sc['ownership_failure'] is None and Path(sc['program'])==NATIVE and len(sc['arguments'])==6 and sc['arguments'][:2]==['--source','full'] and Path(sc['arguments'][2])==SOURCE/'data' and Path(sc['arguments'][4])==Path(p['preload_plan']) and Path(sc['arguments'][5])==Path(a['source_native']['path']).parent,'Actual unique full-source native call binding differs')
    need(nb['passed'] and nb['consumed_stats_unchanged'] and nb['profiles']==stat(PROFILES) and nb['program']==stat(NATIVE) and nb['actual_link_objects']==7 and len(nb['objects'])==6 and not nb['JSph_objects_linked'],'Reviewed shared six-utility reader build required')
    bp=L/'upl_c08_bedkeep_Release_r1.build.json'; b=read(bp); program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe'; need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and sr['source_build']==stat(bp) and sr['program']==stat(program) and (stat(program)['bytes'],stat(program)['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'Original macro-off runtime_r6 source/program required')
    install=L/'upl_c08_formal_r6_runtime_r1.json'; ri=read(install); need(ri['passed'],'Closed runtime installation required'); dest={Path(q['destination']['path']).name:q['destination'] for q in ri['files']}
    before=[stat(q) for q in (Path(__file__),NOTE,PROFILES,MANIFEST,ROOT,AD,bp,install,plan,Path(p['preload_plan']),Path(base.__file__),Path(base.evidence.__file__),source_path,PRE,PRE.parent/'Part_Head.ibi4')]+[bind(a[k]) for k in ('source_native','source_native_call','native_build')]+[bind(nb[k]) for k in ('program','source','core_derivation')]+[bind(q) for q in nb['calls']]+[bind(sr[k]) for k in ('actual_call','input_xml')]+[bind(b[k]) for k in ('source_capture','source_archive')]
    before.extend(bind(dest[k]) for k in ('DualSPHysics5.2_GEO_win64.exe','GenCase_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'))
    before.append(bind(m['BAT'])); before.extend(bind(row[k]) for row in m['jobs'] for k in ('configuration','plan')); verify(before); idle(True)
    return a,p,w,m,b,bp,program,before,thread


def summary(path,coefficient):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines(); need(len(lines)==2,'One Run.csv header/data row required'); match=re.match(r'^#?RunName([;,])',lines[0]); need(match,'Unsupported Run.csv delimiter'); sep=match[1]; keys=lines[0].lstrip('#').split(sep); values=lines[1].split(sep); need(len(set(keys))==len(keys) and keys.count('Configuration')==1,'Unique actual Run.csv keys required'); at=keys.index('Configuration')
    if len(values)==len(keys)+1 and sep==';':values=values[:at]+[values[at]+';'+values[at+1]]+values[at+2:]
    else:need(len(values)==len(keys),'Only known one embedded AS Configuration separator is allowed')
    number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'; text=values[at]; hits=list(re.finditer(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',text))
    need(len(hits)==1 and text.count(';')==text.count('AS_Bui2008')==1 and f32(hits[0][1])==f32(coefficient) and f32(hits[0][2])==f32(3.825),'Actual complete AS token differs'); return dict(zip(keys,values))


def output_checks(out,coefficient,w,p):
    r=summary(out/'Run.csv',coefficient); text=(out/'Run.out').read_text(encoding='utf-8-sig'); parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==w['end_completed_step'] and int(r['PartFiles'])==w['samples'] and int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'] and float(r['H'])==.072 and float(r['Dp'])==.04,'Actual H1.8/91-state/registry/no-exclusion summary differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids=1800,1852,1904,1956,2008;'
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text and text.count('GravityPreload: phase=released ')==text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual release/NoPen/AS flags differ')
    for key,value in [('ArtificialStressCoef',coefficient),('ArtificialStressExp',3.825)]:
        hits=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M); need(len(hits)==1 and f32(hits[0])==f32(value),'Actual AS log differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text); need(len(imported)==1 and int(imported[0][1])==2000000 and float(imported[0][0])==p['preload_actual_end_s'],'Actual imported source clock/event differs')
    need([q.name for q in parts]==['Part_%04d.bi4'%i for i in range(w['samples'])] and not any((out/q).exists() for q in ('C08StageTrace.csv','C08CausalTrace.csv','C08ResidualViscosity.csv','C08ReleaseShepard.csv')),'Actual complete macro-off PART sequence differs')
    return dict(actual_steps=w['end_completed_step'],saved_frames=w['samples'],summary=r,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(q) for q in parts])


def profile_csv(path,root,coefficient):
    pars={q.get('key'):q.get('value') for q in root.findall('execution/parameters/parameter')}; soil=root.find('execution/special/soils')
    def value(key,default=None):
        rows=soil.findall(key); need(len(rows)==1 or not rows and default is not None,'Unique material/profile field required: '+key); return rows[0].get('value') if rows else default
    entries={'group':'psi0','ArtificialStressCoef':pars['ArtificialStressCoef'],'ArtificialStressExp':pars['ArtificialStressExp'],'DPCtes':pars['DPCtes'],**{k:value(k) for k in ('phi','phi_r','n_phi','coh','coh_r','n_coh','dlt','DilationDecay')},'SoilTriggerFos':value('SoilTriggerFos','1.65'),'fresh_trigger_active':'0'}
    need(f32(entries['ArtificialStressCoef'])==f32(coefficient) and f32(entries['ArtificialStressExp'])==f32(3.825) and len(entries)==14,'Actual XML profile differs')
    with path.open('x',encoding='utf-8',newline='') as f:w=csv.writer(f); w.writerow(('key','value')); w.writerows(entries.items())


def native(tag,out,run_entry,profile,plan,coefficient,w,ad,before):
    dest=out/'native_r1'; check=L/(tag+'.native_r1.json'); need(not dest.exists() and not check.exists(),'Existing/partial native protected; do not decode again'); idle(True)
    argv=[str(NATIVE),'--receiver','window','psi0',str(out/'data'),str(PRE),str(plan),str(profile),str(dest)]; call=invoke(tag+'.native',argv,C)
    d=read(dest/'completion.json'); m=read(dest/'bedkeep_metadata.json'); samples=w['samples']
    need(d['passed'] and d['stage']=='c08_h18_native_r1.receiver' and d['group']=='psi0' and d['samples']==samples and d['completed_steps']==2180000 and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['actual_native_IDs_per_frame']==6805 and d['soil_IDs']==5000 and d['actual_fixed_IDs']==1805 and d['kept_bed_IDs']==list(base.BED_IDS) and d['actual_retired_count']==255 and d['ledger_checks']==d['rho_cache_bits_checks']==d['kappa_nondecreasing_from_PRE_checks']==5000*samples and d['fixed_marker_checks']==1805*samples and d['P0_bits_checks']==6805*samples and d['nonempty_signed_intervals']==samples and d['plane_gap_checks']==10000*samples and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original full22/IDs/P0/J/FS/kappa/clock/signed/plane guard coverage differs')
    need(m['passed'] and m['stage']=='c08_h18_native_r1.metadata' and m['profile']=='window' and m['group']=='psi0' and m['samples']==m['AS_active_true_headers']==m['metadata_header_scans']==m['ponding_policy_keys_absent_headers']==samples and m['completed_steps']==2180000 and m['first_post_completed_step']==2000001 and m['first_post_time_s']==w['first_actual_time_s'] and f32(m['AS_coefficient_float_reference'])==f32(coefficient) and f32(m['AS_exponent_float_reference'])==f32(3.825) and m['expected_ponding_policy']=='CompletedOnly' and m['core_array_decode_passes']==1,'Actual per-header AS/keep/CompletedOnly metadata differs')
    verify(before); files=[stat(q) for q in dest.iterdir() if q.is_file()]
    save(check,dict(stage=TAG+'.native',passed=True,source_run=run_entry,actual_call=call,utility_build=ad['native_build'],profiles=stat(PROFILES),plan=stat(plan),input_profile=stat(profile),source_pre=stat(PRE),completion=stat(dest/'completion.json'),metadata=stat(dest/'bedkeep_metadata.json'),original_native_guards_passed=True,decoder_invocations=1,physical_acceptance=False,outputs=files,consumed=before+[run_entry,stat(profile)],consumed_stats_unchanged=True))
    return stat(check)


def run_job(row,a,p,w,b,bp,program,shared):
    tag=row['tag']; coefficient=row['AS_coefficient']; out=T/'outputs'/tag; path=L/(tag+'.run.json'); need(not out.exists() and not any(L.glob(tag+'.*')),'Existing job/owner/output/partial protected'); before=list(shared); stage='preflight'; result=dict(stage=tag,passed=False,solver_completed=False,physical_acceptance=False,native_review_pending=True,configuration='Release',AS_coefficient=coefficient,AS_exponent=3.825,hdp=1.8,fixed_dt_s=.000005,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,SHA_scans=0)
    try:
        idle(True); verify(before); out.mkdir(); prefix=out/tag; stage='GenCase'; result['GenCase_invocations']=1; result['GenCase_call']=invoke(tag+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(Path(row['configuration']['path']).with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml'); actual=check_input(seed,coefficient,True); seed_entries=[stat(Path(str(prefix)+q)) for q in ('.xml','.bi4','_Normals.nbi4')]; before+=seed_entries; profile=out/'native_profile.csv'; profile_csv(profile,actual,coefficient); before.append(stat(profile)); verify(before)
        argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(w['end_completed_step'])]; ownerad=L/(tag+'.owner_admission.json')
        save(ownerad,dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(AD),matrix_manifest=stat(MANIFEST),program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,planned_steps=row['plan'],planned_new_updates=180000,planned_global_end=2180000,expected_saved_frames=91,argv=argv,solver_argv=argv,consumed=before)); before.append(stat(ownerad))
        result.update(program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,planned_steps=row['plan'],native_profile=stat(profile),owner_admission=stat(ownerad),argv=argv)
        stage='solver'; result['solver_invocations']=1; result['actual_call']=base.owned(tag,argv,program,False,stat(ownerad)); result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0); stage='solver_output_review'; result.update(output_checks(out,coefficient,w,p)); verify(before); result['passed']=True
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage); cp=L/(tag+'.call.json')
        if cp.exists():
            call=read(cp); result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
        raw=out/'Run.out'
        if raw.exists():
            text=raw.read_text(encoding='utf-8-sig',errors='replace'); hit=re.search(r'^Text: (.+)$',text,re.M); result.update(Run_out=stat(raw),first_engine_exception_text=hit[1] if hit else None)
    result.update(consumed=before,consumed_stats_unchanged=bool(before) and all(Path(e['path']).is_file() and stat(e['path'])==e for e in before),last_original_console_line=base.last_part(out),unsaved_failure_time_reconstructed=False); save(path,result)
    base.publish(tag,out,None,None,'completed_pending_native' if result['passed'] else 'failed_preserved_no_next_job'); need(result['passed'],'Matrix stops at first failed/unsafe window; preserve the actual failure')
    if not a['native_auto_authorized']:return stat(path),None
    return stat(path),native(tag,out,stat(path),profile,Path(row['plan']['path']),coefficient,w,a,before)


def notify_once():
    attempt=L/(TAG+'.queue_attempt.json'); reply=L/(TAG+'.queue_result.json'); need(not attempt.exists() and not reply.exists(),'Terminal queue already attempted; never resend')
    message=('The admitted C08 H1.8 matrix owner is terminal: '+str(RUN)+'. Verify each original owned start/call/run/status, program/source/PRE/input/plan stat and real Popen/Win32/solver exits first. The plan is only three psi0 windows epsilon.3/.5/.7 at exponent3.825, Cubic hdp1.8,5us,original total-AS/AV.1/keep5/fixedplane/CompletedOnly, Shepard/damping OFF after the new certified source. Scalar plans include firstpost+1update and91states through.90s. No automatic best choice/formal/otherpsi or further exponent trial was started. If all three run/native passed, perform independent raw-state pressure/NN/kappa/J/motion/arrest analysis and visual review before choosing a parameter, then continue the user-authorized work with reviewed tools. Lower speed/peak pressure alone is not physical acceptance. If any job/native failed or native authorization was absent, preserve all outputs and stop the remaining jobs; repair derived data only after a genuine completed solver, never rerun that solver. The old r1 zero-PART source failure and corrected r2 source are retained. Never invent unsaved failure time, remove safety guards, rearm this owner or repeat decoder calls. One45s same-thread queue attempt only; uncertain delivery must not be resent or watched.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message]; save(attempt,dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(RUN),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True)); r=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW); r.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:r.update(status='delivery_uncertain',error=str(error))
    except Exception as error:r.update(status='queue_failed',error=str(error))
    save(reply,r)


def run(notify):
    need(not RUN.exists() and not any(p.name!=AD.name for p in L.glob(TAG+'.*')),'Existing matrix owner/terminal/partial protected'); result=dict(stage=TAG,passed=False,physical_acceptance=False,selection_made=False,formal_jobs_started=0,completed_jobs=[],native_checks=[],solver_invocations=0,queue_invocations_at_seal=0,SHA_scans=0); before=[]
    try:
        a,p,w,m,b,bp,program,before,thread=context(notify); save(L/(TAG+'.claim.json'),dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True,admission=stat(AD)))
        for row in m['jobs']:
            rp,np=run_job(row,a,p,w,b,bp,program,before); result['completed_jobs'].append(rp); result['solver_invocations']+=1
            if np is None:result['halted_pending_native_review']=True; break
            result['native_checks'].append(np)
        result['passed']=len(result['completed_jobs'])==len(result['native_checks'])==3; result['physical_comparison_pending']=True
    except Exception as error:result['first_failure']=str(error)
    runs=[stat(L/(tag+'.run.json')) for tag,_ in JOBS if (L/(tag+'.run.json')).exists()]; result['job_runs']=runs; result['completed_jobs']=[e for e in runs if read(e['path'])['passed']]; result['solver_invocations']=sum(read(e['path'])['solver_invocations'] for e in runs)
    result['actual_native_calls']=[stat(L/(tag+'.native.call.json')) for tag,_ in JOBS if (L/(tag+'.native.call.json')).exists()]
    result.update(consumed=before,consumed_stats_unchanged=bool(before) and all(Path(e['path']).is_file() and stat(e['path'])==e for e in before)); save(RUN,result)
    if notify and (result['completed_jobs'] or any((L/(tag+'.call.json')).exists() for tag,_ in JOBS)):notify_once()
    print(json.dumps(dict(passed=result['passed'],run=str(RUN),completed_jobs=len(result['completed_jobs']),native_checks=len(result['native_checks']),first_failure=result.get('first_failure'))),flush=True); return 0 if result['passed'] else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('action',choices=('prepare','run')); ap.add_argument('--execution-authorized',action='store_true'); ap.add_argument('--notify',action='store_true'); args=ap.parse_args(); need(args.execution_authorized,'Author-only until root full-read'); need(args.action=='run' or not args.notify,'Prepare never queues'); prepare() if args.action=='prepare' else exit(run(args.notify))
