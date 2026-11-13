"""Two explicit 2ms candidate Debug jobs, then one offline aggregate; never Release/native/VTK."""
import argparse,json,re,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_centroid_a07_r1 as owner

matrix=owner.matrix
T,C,L=owner.T,owner.C,owner.L
need,read,stat,bind,save,invoke=owner.need,owner.read,owner.stat,owner.bind,owner.save,owner.invoke
TAG='c08_h18_centroid_debug_regression_r1';NOTE=T/'notes'/(TAG+'.md')
PREP=L/(TAG+'.prepare.json');CHECK=L/(TAG+'.check.json')
SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
CAP=2000400
SPECS={'cpu':('DebugCPU','CPU','DualSPHysics5.2CPU_win64_debug.exe'),'gpu_memcheck':('Debug','GPU_memcheck','DualSPHysics5.2_win64_debug.exe')}


def paths(action):
    configuration,suffix,leaf=SPECS[action];tag=TAG+'_'+suffix
    return configuration,tag,T/'configs'/(tag+'_Def.xml'),T/'outputs'/tag,L/(tag+'.check.json'),leaf


def prepare():
    need(not PREP.exists() and not CHECK.exists(),'Existing Debug preparation/aggregate protected')
    original,prior,config,window,preload,material,gen,consumed=owner.original_context()
    consumed.extend(stat(q) for q in (Path(__file__),NOTE,Path(owner.__file__)))
    jobs=[]
    for action in SPECS:
        configuration,tag,destination,out,check,leaf=paths(action)
        need(not destination.exists() and not out.exists() and not any(L.glob(tag+'.*')),'Existing short Debug job or partial protected')
    for action in SPECS:
        configuration,tag,destination,out,check,leaf=paths(action)
        with destination.open('xb') as handle:handle.write(config.read_bytes())
        matrix.check_input(destination,.7)
        need(matrix.signature(ET.parse(destination).getroot())==matrix.signature(ET.parse(config).getroot()),'Short Debug XML must retain the actual full AS.7 numerical input')
        jobs.append(dict(action=action,tag=tag,configuration=configuration,input_xml=stat(destination),output=str(out),CLI_completed_step_cap=CAP,expected_saved_frames=2))
    matrix.verify(consumed)
    save(PREP,dict(stage=TAG+'.prepare',prepared_only=True,intervention=owner.INTERVENTION,original_run=stat(owner.previous.ORIGINAL_RUN),original_full91_plan=stat(matrix.PLAN),source_pre_file=stat(matrix.PRE),source_actual_time_s=preload['preload_actual_end_s'],jobs=jobs,consumed=consumed,consumed_stats_unchanged=True,solver_invocations=0,GenCase_invocations=0,native_decodes=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False))


def output_checks(out,configuration,preload):
    summary=matrix.old.old.summary(out/'Run.csv',.7);text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(summary['Steps'])==CAP and int(summary['PartFiles'])==2 and int(summary['Np'])==7060 and int(summary['Nfixed'])==int(summary['Nbound'])==2060 and all(int(summary[key])==0 for key in ('PartsOut','PartsOutRhop','PartsOutVel')) and float(summary['Dp'])==.04 and float(summary['H'])==.072,'Actual short Debug summary/cap/2frame/no-loss registry differs')
    need((summary['Hardware']=='CPU' and 'OpenMP(Threads:8)' in summary['RunMode']) if configuration=='DebugCPU' else 'Gpu_' in summary['Hardware'],'Actual CPU8/GPU hardware differs from the selected Debug job')
    need('Kernel="Wendland"' in text and 'Wendland' in summary['Configuration'] and 'Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text and 'DynamicPoreWall rejected:' not in text,'Actual short Debug kernel/normal completion differs')
    need(text.count('GravityPreload: phase=released ')==1 and text.count('GravityPreload: state imported file=')==1 and text.count('GravityPreload: validated native right-wall range=[1805,2060), count=255.')==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text and 'No Penetration=True' in text and 'Dynamic NoPen: FixedPlaneStageProjectionReleaseOnly' in text,'Actual short import/release/retirement/contact differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text)
    need(len(imported)==1 and int(imported[0][1])==2000000 and float(imported[0][0])==preload['preload_actual_end_s'],'Actual certified PRE import clock differs')
    saved=re.findall(r'^Part_(\d+)\s+([0-9.eE+-]+)\s+(\d+)\s+',text,re.M)
    need(len(saved)==2 and [int(q[0]) for q in saved]==[0,1] and [int(q[2]) for q in saved]==[2000001,CAP] and [q.name for q in parts]==['Part_0000.bi4','Part_0001.bi4'],'Actual two short saves must be PRE+1 and the genuine CLI cap')
    for key,value in (('ArtificialStressCoef',.7),('ArtificialStressExp',3.825)):
        hits=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(hits)==1 and matrix.f32(hits[0])==matrix.f32(value),'Actual AS.7/n3.825 log differs')
    return dict(summary=summary,Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(q) for q in parts],actual_steps=CAP,saved_frames=2,actual_source_time_from_loader=float(imported[0][0]))


def run_job(action):
    configuration,tag,config,out,check,leaf=paths(action);build_path=L/('c08_h18_centroid_'+configuration+'_r1.build.json')
    need(not out.exists() and not check.exists() and not any(L.glob(tag+'.*')),'Existing Debug invocation or partial protected; external launch prefix must differ')
    consumed=[];phase='preflight';result=dict(stage=tag,passed=False,configuration=configuration,intervention=owner.INTERVENTION,physical_acceptance=False,centroid_retry_exercised_proven=False,CPU_GPU_bitwise_agreement_claimed=False,solver_invocations=0,GenCase_invocations=0,native_decodes=0,VTK_invocations=0,SHA_scans=0)
    try:
        prepared=read(PREP);row=next(q for q in prepared['jobs'] if q['action']==action);build=read(build_path)
        original,prior,original_config,window,preload,material,gen,consumed=owner.original_context()
        need(prepared['prepared_only'] and prepared['consumed_stats_unchanged'] and prepared['source_pre_file']==stat(matrix.PRE) and row['input_xml']==stat(config) and row['CLI_completed_step_cap']==CAP and row['expected_saved_frames']==2,'Exact prepared short job required')
        need(build['stage']=='c08_h18_centroid_'+configuration+'_r1.build' and build['passed'] and build['configuration']==configuration and build['intervention']==owner.INTERVENTION and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and build['source_stats_unchanged'] and build['consumed_stats_unchanged'] and len(build['project_objects'])==(87 if action=='cpu' else 113),'Passed authoritative candidate Debug build required')
        program=Path(bind(build['program'])['path']);need(program==T/'outputs'/('c08_h18_centroid_'+configuration+'_r1')/leaf,'Only the isolated corresponding Debug executable is allowed')
        consumed.extend(stat(q) for q in (Path(__file__),NOTE,Path(owner.__file__),PREP,config,build_path))
        consumed.extend(bind(q) for q in prepared['consumed'])
        consumed.extend(bind(build[key]) for key in ('program','source_capture','source_archive','actual_call'))
        consumed.extend(bind(q) for q in build['runtime']);matrix.check_input(config,.7)
        matrix.verify(consumed);matrix.old.old.idle(True);out.mkdir();prefix=out/tag
        phase='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(tag+'.gencase',[gen['path'],str(config.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');matrix.check_input(seed,.7,True);consumed.extend(stat(Path(str(prefix)+suffix)) for suffix in ('.xml','.bi4','_Normals.nbi4'))
        solver=[str(program),*(['-cpu','-ompthreads:8'] if action=='cpu' else ['-gpu:0']),'-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(CAP)]
        sanlog=L/(tag+'.memcheck.log');argv=solver
        if action=='gpu_memcheck':
            consumed.append(stat(SAN));need(not sanlog.exists(),'Existing memcheck log protected');argv=[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','99','--log-file',str(sanlog),*solver]
        matrix.verify(consumed);phase='solver';result['solver_invocations']=1
        actual=invoke(tag+'.solver',argv,C,target=program if action=='gpu_memcheck' else None);call=read(bind(actual)['path'])
        target=call['actual_target'] if action=='gpu_memcheck' else call['child'];solver_exit=call['actual_target_Win32_exit'] if action=='gpu_memcheck' else call['actual_Win32_exit']
        need(target is not None and Path(target['exe']).samefile(program) and target['argv']==solver and solver_exit==call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual owned Debug target/tool identity and exits differ')
        result.update(actual_call=actual,actual_exit=solver_exit,actual_Win32_exit=solver_exit,actual_tool_exit=call['actual_Popen_wait_exit'],program=stat(program),source_build=stat(build_path),source_capture=build['source_capture'],source_archive=build['source_archive'],source_pre_file=stat(matrix.PRE),input_xml=stat(seed),solver_argv=solver,argv=argv)
        phase='runtime_review';result.update(output_checks(out,configuration,preload))
        if action=='gpu_memcheck':
            text=sanlog.read_text(encoding='utf-8');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',text);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',text)
            need(errors and leaks and all(int(v.replace(',',''))==0 for v in errors) and all(int(v.replace(',',''))==int(w.replace(',',''))==0 for v,w in leaks),'Actual memcheck ERROR/leak summaries must both be present and zero')
            result.update(memcheck_log=stat(sanlog),memcheck_zero_errors_and_leaks=True)
        matrix.verify(consumed);result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=phase);call_path=L/(tag+'.solver.call.json')
        if call_path.exists():
            actual=read(call_path);solver_exit=actual['actual_target_Win32_exit'] if action=='gpu_memcheck' else actual['actual_Win32_exit'];result.update(actual_call=stat(call_path),actual_exit=solver_exit,actual_tool_exit=actual['actual_Popen_wait_exit'],actual_Win32_exit=solver_exit,ownership_failure=actual['ownership_failure'])
    result.update(consumed=consumed,last_original_console_line=owner.base.last_part(out),CLI_completed_step_cap=CAP,original_full91_plan=stat(matrix.PLAN),no_automatic_next_job=True)
    save(check,result);print(json.dumps(dict(check=str(check),passed=result['passed'])),flush=True)
    return 0 if result['passed'] else 1


def review():
    need(not CHECK.exists(),'Existing Debug aggregate protected');consumed=[stat(q) for q in (PREP,Path(__file__),NOTE,Path(owner.__file__))];receipts={}
    for action in SPECS:
        configuration,tag,config,out,check,leaf=paths(action);result=read(check)
        need(result['passed'] and result['consumed_stats_unchanged'] and result['configuration']==configuration and result['actual_exit']==result['actual_Win32_exit']==result['actual_tool_exit']==0 and result['actual_steps']==CAP and result['saved_frames']==2,'Both genuine short Debug jobs must pass before aggregation')
        receipts[action]=(stat(check),result);consumed.append(stat(check));consumed.extend(bind(q) for q in result['consumed'])
        consumed.extend(bind(result[key]) for key in ('actual_call','Run_csv','Run_out','program','source_build','source_capture','source_archive'))
        consumed.extend(bind(q) for q in result['PARTs'])
    cpu_entry,cpu=receipts['cpu'];gpu_entry,gpu=receipts['gpu_memcheck']
    need(cpu['source_capture']==gpu['source_capture'] and cpu['source_archive']==gpu['source_archive'] and gpu['memcheck_zero_errors_and_leaks'],'Accepted CPU/GPU source and actual memcheck scope differ')
    consumed.append(bind(gpu['memcheck_log']));matrix.verify(consumed)
    save(CHECK,dict(stage=TAG,passed=True,intervention=owner.INTERVENTION,source_stats_unchanged=True,consumed_stats_unchanged=True,source_capture=cpu['source_capture'],source_archive=cpu['source_archive'],CPU_Debug_smoke_passed=True,GPU_Debug_smoke_passed=True,GPU_Debug_memcheck_zero_errors_and_leaks=True,cpu_build=cpu['source_build'],gpu_build=gpu['source_build'],cpu_smoke=cpu_entry,gpu_smoke=gpu_entry,gpu_memcheck=gpu_entry,physical_acceptance=False,centroid_retry_exercised_proven=False,CPU_GPU_bitwise_agreement_claimed=False,Release_validation_claimed=False,actual_jobs=2,completed_step_cap=CAP,consumed=consumed,solver_invocations=0,native_decodes=0,VTK_invocations=0,SHA_scans=0,no_automatic_next_job=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','cpu','gpu_memcheck','review'));parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Author-only until root full-read and one explicitly authorized action')
    if args.action=='prepare':prepare()
    elif args.action=='review':review()
    else:exit(run_job(args.action))
