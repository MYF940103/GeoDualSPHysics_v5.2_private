"""Explicit trace run/native/review actions; no automatic sequence, queue or long physical job."""
import argparse,csv,json,os,shutil,struct
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base

T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';PREFIX='upl_c08_stage_trace_smoke';SOURCE=4000000
ROOTXML=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r5_Def.xml';PRE=base.PRE
SPECS={'Debug':(40,40,'10.0001','0.0001',True),'Release':(12000,4000,'10.03','0.01',False)}
need,read,stat,bind,save=base.need,base.read,base.stat,base.bind,base.save

def table(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def verify(entries):need(all(stat(e['path'])==e for e in entries),'Consumed closed input changed')
def locations(conf):
    tag=PREFIX+'_'+conf+'_r1';return tag,T/'outputs'/tag,L/(tag+'.run.json'),L/(tag+'.native.json'),L/(tag+'.review.json')

def normal_output(out,updates,frames):
    r=base.summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==SOURCE+updates and int(r['PartFiles'])==frames and int(r['Np'])==7060 and int(r['Nbound'])==int(r['Nfixed'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual registry/steps/frames/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text,'Actual normal AS1/fixed-plane mode differs')
    for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',2.55)):
        values=base.re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,base.re.M);need(len(values)==1 and struct.pack('<f',float(values[0]))==struct.pack('<f',value),'Actual AS log differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,base.BED_IDS))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.'
    need(text.count('GravityPreload: phase=released ')==1 and text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual one255/five-kept release differs')
    imported=base.re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==SOURCE,'Original actual source clock/import missing')
    need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(frames)],'Actual native sequence differs')
    trace=out/'C08StageTrace.csv';rows=table(trace);need(rows and {int(q['native_id']) for q in rows}=={5809,4956,4959} and all(int(q['hits'])==1 and SOURCE<=int(q['nstep'])<=SOURCE+updates for q in rows),'Actual nonempty three-ID trace missing or outside window')
    return dict(actual_steps=SOURCE+updates,saved_frames=frames,summary=r,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(p) for p in parts],trace_file=stat(trace),trace_rows=len(rows),trace_events=sorted({int(q['event']) for q in rows}))

def run(conf):
    tag,out,rp,npth,review=locations(conf);updates,cadence,end,tout,memcheck=SPECS[conf];frames=updates//cadence;config=T/'configs'/(tag+'_Def.xml');root_ad=L/(tag+'.admission.json')
    need(not out.exists() and not config.exists() and not any(p.name!=tag+'.admission.json' for p in L.glob(tag+'.*')),'Existing output/config/invocation preserved')
    if conf=='Release':need(read(locations('Debug')[4])['passed'],'Root must first review closed Debug memcheck/native/control comparison; no automatic next run')
    before=[];result=dict(stage=tag,passed=False,configuration=conf,physical_acceptance=False,solver_invocations=0,reader_invocations=0,queue_invocations=0,SHA_scans=0,native_review_pending=True,keep_bed_overlap=True,expected_active_native_IDs=6805,ArtificialStress=True,policy=base.POLICY)
    try:
        bp=L/('upl_c08_stage_trace_'+conf+'_r1.build.json');b=read(bp);need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['trace_macro_enabled'] and b['trace_macro']=='C08_STAGE_TRACE' and b['environment_macro']['appended']=={'CL':'/DC08_STAGE_TRACE','NVCC_PREPEND_FLAGS':'-DC08_STAGE_TRACE'} and len(b['project_objects'])==113,'Closed macro-enabled corresponding GPU build required')
        need(Path(b['source_capture']['path']).samefile(T/'outputs/upl_c08_stage_trace_source_r1/source.json'),'Current isolated trace source capture required');program=Path(bind(b['program'])['path'])
        before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_stage_trace_smoke_r1.md',Path(base.__file__),Path(base.summary.__code__.co_filename),T/'support/mdbc_partition_components_r3.py',ROOTXML,bp,PRE,PRE.parent/'Part_Head.ibi4')]+[bind(b[k]) for k in ('program','source_capture','source_archive')];runtime=[]
        if conf=='Release':before.append(stat(locations('Debug')[4]))
        if root_ad.exists():before.append(stat(root_ad))
        for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'):
            origin=C/'support/runtime_r5'/leaf;old=stat(origin);dest=program.parent/leaf
            if not dest.exists():shutil.copy2(origin,dest)
            copied=stat(dest);need((copied['bytes'],copied['mtime_ns'])==(old['bytes'],old['mtime_ns']),'Existing/new runtime copy differs');before.extend((old,copied));runtime.append(copied)
        for q in psutil.process_iter(['exe','cmdline']):
            try:
                exe=q.info['exe'];argv=q.info['cmdline'] or [];need(not(exe and Path(exe).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in argv[1:])),'A GPU physical target is active; no process is stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        root=base.ET.parse(ROOTXML).getroot();root.find('execution/special/gravitypreload').set('statefile',str(PRE.resolve()));params=root.find('execution/parameters')
        for key,value in (('TimeMax',end),('TimeOut',tout)):
            entries=[q for q in params if q.get('key')==key];need(len(entries)==1,'Unique existing clock parameter required');entries[0].set('value',value)
            entries[0].set('comment',('Implementation regression: actual imported PRE plus '+('0.0001' if conf=='Debug' else '0.03')+' s; not the formal3 s trajectory') if key=='TimeMax' else 'Implementation regression save interval '+tout+' s; keep actual saved scalar clocks')
        with config.open('xb') as f:f.write(base.ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n')
        base.check_input(config,end,tout,True,True,True);before.append(stat(config));gen=C/'support/runtime_r5/GenCase_win64.exe';before.append(stat(gen));prefix=out/tag
        result['GenCase_call']=base.invoke(tag+'.gencase',[str(gen),str(config.with_suffix('')),str(prefix),'-save:all'],C);seed=Path(str(prefix)+'.xml');base.check_input(seed,end,tout,True,True,True)
        before += [stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];plan=out/'planned_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(('part','completed_step'));writer.writerows((i,SOURCE+(i+1)*cadence) for i in range(frames))
        before.append(stat(plan));solverargv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(SOURCE+updates)];argv=solverargv;sanlog=L/(tag+'.memcheck.log')
        if memcheck:before.append(stat(base.evidence.SAN));argv=[str(base.evidence.SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*solverargv]
        admission=L/(tag+('.owner_admission.json' if root_ad.exists() else '.admission.json'));save(admission,dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),program=stat(program),source_build=stat(bp),source_pre_file=stat(PRE),planned_steps=stat(plan),planned_global_end=SOURCE+updates,expected_saved_frames=frames,argv=argv,solver_argv=solverargv,consumed=before))
        result['solver_invocations']=1;result['actual_call']=base.owned(tag,argv,program,memcheck,stat(admission));result.update(normal_output(out,updates,frames))
        if memcheck:
            text=sanlog.read_text(encoding='utf-8');errors=base.re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',text);leaks=base.re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',text);need(errors and leaks and all(int(v.replace(',',''))==0 for v in errors) and all(int(v.replace(',',''))==int(w.replace(',',''))==0 for v,w in leaks),'Original memcheck zero-error/leak guard failed');result.update(memcheck_zero_errors_and_leaks=True,memcheck_log=stat(sanlog))
        verify(before);result.update(passed=True,actual_exit=0,actual_Win32_exit=0,program=stat(program),source_build=stat(bp),input_xml=stat(seed),source_pre_file=stat(PRE),runtime=runtime,consumed_stats_unchanged=True)
    except Exception as error:
        result['first_failure']=str(error);cp=L/(tag+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    result.update(consumed=before,last_original_console_line=base.last_part(out));save(rp,result);print(json.dumps(dict(passed=result['passed'],receipt=str(rp),first_failure=result.get('first_failure'))),flush=True);return result['passed']

def native(conf):
    tag,out,rp,npth,review=locations(conf);updates,cadence,end,tout,memcheck=SPECS[conf];samples=updates//cadence;folder=out/'native';need(not folder.exists() and not npth.exists() and not any((L/(tag+s)).exists() for s in ('.native.call.json','.native.log')),'Existing/partial native work preserved')
    before=[];actual=None;result=dict(stage=tag+'.native',passed=False,solver_invocations=0,decoder_invocations=0,physical_acceptance=False,SHA_scans=0)
    try:
        r=read(rp);cp=L/(tag+'.call.json');sp=L/(tag+'.start.json');c,s=read(cp),read(sp);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==SOURCE+updates and r['saved_frames']==samples and r['consumed_stats_unchanged'],'Closed actual normal trace run required')
        need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and not c['ownership_errors'] and c['actual_outer']==s['actual_outer'],'Actual original solver/tool ownership differs')
        adpath=Path(bind(c['admission'])['path']);ad=read(adpath);need(c['admission']==s['admission'] and c['arguments']==ad['argv'] and c['actual_solver']['argv']==ad['solver_argv'] and ad['owner']==s['owner'],'Actual original admission/argv differs')
        if memcheck:need(r['memcheck_zero_errors_and_leaks'] and read(L/(tag+'.target.json'))['actual_solver']==c['actual_solver'],'Actual memcheck closure missing')
        else:need(s['actual_solver']==c['actual_solver']==c['actual_outer'],'Direct target identity differs')
        base.check_input(Path(r['input_xml']['path']),end,tout,True,True,True);plan=out/'planned_steps.csv';need(bind(ad['planned_steps'])==stat(plan),'Original planned saves changed')
        bp=L/'upl_c08_bedkeep_native_r1.build.json';b=read(bp);need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and not b['JSph_objects_linked'],'Existing closed six-utility reader required');program=Path(bind(b['program'])['path'])
        for q in psutil.process_iter(['exe']):
            try:
                if q.info['exe']:need(not Path(q.info['exe']).samefile(program) and not Path(q.info['exe']).samefile(r['program']['path']),'Exact reader/solver still active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_stage_trace_smoke_r1.md',Path(base.__file__),rp,cp,sp,adpath,bp,plan)]+[bind(e) for e in r['consumed']]+[bind(r[k]) for k in ('Run_out','Run_csv','program','source_build','input_xml','source_pre_file','trace_file')]+[bind(b['program'])]+[bind(e) for e in b['consumed']]
        result['decoder_invocations']=1;actual=base.invoke(tag+'.native',[str(program),'--read','psi0','GPU',str(out/'data'),str(PRE),str(SOURCE+updates),str(samples),'1',str(plan),str(folder)],C)
        d=read(folder/'completion.json');m=read(folder/'bedkeep_metadata.json');counts=dict(samples=samples,completed_steps=SOURCE+updates,typed_arrays=22,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=5000*samples,fixed_marker_checks=1805*samples,P0_bits_checks=6805*samples,rho_cache_bits_checks=5000*samples,kappa_nondecreasing_from_PRE_checks=5000*samples,nonempty_signed_intervals=samples,plane_gap_checks=10000*samples)
        need(d['passed'] and d['stage']=='upl_c08_bedkeep_native_r1' and all(d[k]==v for k,v in counts.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_launch_plan'] and d['DynamicNoPenetrationPolicy']==base.POLICY and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['min_soil_x_m']>=-4e-8 and d['min_soil_z_m']>=-4e-8 and d['kept_bed_IDs']==list(base.BED_IDS) and d['actual_retired_count']==255 and d['kept_bed_source_geometry_checks']==5,'Original22/6805/ledger/P0/FS/kappa/clock/plane guards differ')
        need(m['passed'] and m['stage']=='upl_c08_bedkeep_native_r1.metadata' and m['keep_bed_overlap'] and m['expected_AS'] and m['kept_bed_IDs']==list(base.BED_IDS) and m['actual_retired_count']==255 and m['samples']==m['metadata_header_scans']==m['keep_policy_headers']==m['AS_active_true_headers']==samples and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==struct.unpack('<f',struct.pack('<f',.2))[0] and m['AS_exponent_float_reference']==struct.unpack('<f',struct.pack('<f',2.55))[0] and m['core_array_decode_passes']==1 and not m['core_original_numerical_budgets_changed'],'Original keep/AS metadata differs')
        verify(before);result.update(passed=True,original_native_guards_passed=True,source_run=stat(rp),actual_call=actual,completion=stat(folder/'completion.json'),bedkeep_metadata=stat(folder/'bedkeep_metadata.json'),outputs=[stat(p) for p in sorted(folder.iterdir()) if p.is_file()],consumed_stats_unchanged=True)
    except Exception as error:
        cp=L/(tag+'.native.call.json');result.update(first_failure=str(error),actual_call=stat(cp) if cp.exists() else actual)
    result['consumed']=before;save(npth,result);print(json.dumps(dict(passed=result['passed'],receipt=str(npth),first_failure=result.get('first_failure'))),flush=True);return result['passed']

def review(conf):
    tag,out,rp,npth,check=locations(conf);frames=1 if conf=='Debug' else 3;need(not check.exists(),'Existing review preserved');before=[];result=dict(stage=tag+'.review',passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,SHA_scans=0)
    try:
        n=read(npth);need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'],'Closed new native required');before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_stage_trace_smoke_r1.md',npth)]+[bind(e) for e in n['outputs']];new=out/'native'
        if conf=='Debug':
            old=T/'outputs/upl_c08_bedkeep_smoke_GPU_r1/native';cp=L/'upl_c08_bedkeep_smoke_GPU_r1.native.json';c=read(cp);need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'],'Retained same-dt GPU Debug native control required');before.append(stat(cp));before.extend(bind(e) for e in c['outputs']);control_samples=1
        else:
            old=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out/native';cp=old.parent/'postprocess_r5.json';c=read(cp);need(c['passed'] and c['global_steps']==5200000 and c['saved_frames']==300 and c['KeepBedOverlap'] and c['AS_policy']=='ReleaseOnly','Retained normal root r5 control required');nativecall=old.parent/'logs/native.call.json';rc=read(nativecall);need(rc['passed'] and rc['actual_exit']==rc['actual_Win32_exit']==0,'Actual old root native exit differs');before.extend((stat(cp),stat(nativecall)));before.extend(bind(next(e for e in rc['outputs'] if Path(e['path']).samefile(old/leaf))) for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv'));control_samples=300
        d=read(old/'completion.json');need(d['passed'] and d['samples']==control_samples and d['actual_native_IDs_per_frame']==6805 and d['typed_arrays']==22,'Actual control coverage differs');stride=8+6805*212
        with (new/'typed22.bin').open('rb') as a,(old/'typed22.bin').open('rb') as b:
            hnew=struct.unpack('<III',a.read(12));hold=struct.unpack('<III',b.read(12));need(hnew==(6805,22,frames) and hold==(6805,22,control_samples),'Original unequal-sample headers must remain real');left=a.read(frames*stride);right=b.read(frames*stride)
        need(len(left)==len(right)==frames*stride,'Actual prefix payload size differs');equal=left==right;result.update(typed22_time_payload_byte_exact=equal,first_different_payload_byte=None if equal else next(i for i,(x,y) in enumerate(zip(left,right)) if x!=y),new_header=list(hnew),control_header=list(hold),headers_rewritten=False)
        nclock=(new/'clocks.csv').read_bytes().splitlines(keepends=True);oclock=(old/'clocks.csv').read_bytes().splitlines(keepends=True);need(len(nclock)==frames+1 and len(oclock)==control_samples+1,'Actual raw clock row counts differ');clocks=nclock==oclock[:frames+1];layout=(new/'typed22_layout.csv').read_bytes()==(old/'typed22_layout.csv').read_bytes();result.update(actual_common_saved_frames=frames,typed_layout_byte_exact=layout,signed_clock_header_and_rows_byte_exact=clocks,control_directory=str(old),comparison='same-backend actual saved fields, not half-step error')
        need(equal and clocks and layout,'Trace changed original22/time/signed-clock bytes; preserve and diagnose, no retry');verify(before);result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=before;save(check,result);print(json.dumps(dict(passed=result['passed'],receipt=str(check),first_failure=result.get('first_failure'))),flush=True);return result['passed']

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('run','native','review'));ap.add_argument('configuration',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read and explicit one-action execution required');raise SystemExit(0 if {'run':run,'native':native,'review':review}[args.action](args.configuration) else 1)
