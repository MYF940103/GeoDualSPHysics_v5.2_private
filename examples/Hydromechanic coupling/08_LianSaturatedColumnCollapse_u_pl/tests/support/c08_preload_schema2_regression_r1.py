"""Four explicit old/new GPU compatibility jobs; one shared source GenCase, existing readers only."""
import argparse,csv,re,struct
from pathlib import Path
import xml.etree.ElementTree as ET
import psutil
import upl_c08_bedkeep_run_r1 as base
from upl_c08_asn3_window_r1 import summary as as_summary

T,C,L=base.T,base.C,base.L;need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='c08_preload_schema2_regression_r1';ROOT=C/'CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml'
SEEDOUT=T/'outputs'/(TAG+'_seed');SOURCE=SEEDOUT/(TAG+'_source');PREP=L/(TAG+'.prepare.json')
HANDOFF=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_GPU_out/CaseLianSaturatedColumnCollapse_psi0_shared_r6'
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4';RUNTIME=C/'support/runtime_r6'
NEW_BUILD=L/'c08_preload_schema2_Release_r1.build.json';OLD_BUILD=L/'upl_c08_bedkeep_Release_r1.build.json'
READERS={'source':L/'upl_c08_hdp15_preload_partial_r3.build.json','handoff':L/'upl_c08_causal_native_r1.build.json'}
RUNTIME_LEAVES=('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')

def verify(entries):need(all(stat(q['path'])==q for q in entries),'Consumed input/program/seed/PRE changed')
def rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def idle():
    for q in psutil.process_iter(['name']):
        try:
            name=(q.info['name'] or '').lower()
            need(name not in ('c08causalnative_win64.exe','c08preloadpartial_win64.exe'),'A selected native reader is active; nothing stopped')
            if name.startswith('dualsphysics'):need(not any(x.lower().startswith('-gpu') for x in q.cmdline()[1:]),'A GPU solver is active; nothing stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
def params(path):
    root=ET.parse(path).getroot();p={}
    for q in root.findall('execution/parameters/parameter'):need(q.get('key') not in p,'Duplicate parameter');p[q.get('key')]=q.get('value')
    for key,value in dict(DtFixed=.0000025,DtIni=.0000025,TimeMax=13,TimeOut=.01,Kernel=1,DPCtes=3,SavePosDouble=1,Visco=.1,SoilStressRateGradCorr=1,PartsOutMax=0).items():need(float(p[key])==value,'Old-path fixed parameter differs: '+key)
    h=root.find('casedef/constantsdef/hdp')
    if h is None:h=root.find('execution/constants/hdp')
    # GenCase emits constants under execution/constants; actual H is also checked by both readers.
    if h is not None:need(float(h.get('value'))==1.2,'Old source hdp differs')
    return root,p
def check_input(path,kind):
    root,p=params(path);g=root.find('execution/special/gravitypreload');need(g is not None and float(g.get('time'))==10 and g.get('release_mkbound')=='2','Old event differs')
    if kind=='source':need(g.get('elastic_source')=='true' and not g.get('statefile') and g.get('keep_bed_overlap','false')=='false' and float(p.get('ArtificialStress','0'))==float(p.get('NoPenetration','0'))==0 and float(p['SoilDamping'])==1,'Strict elastic AS0/NoPen0 old source required')
    else:
        need(g.get('keep_bed_overlap')=='true' and Path(g.get('statefile')).samefile(PRE) and g.get('elastic_source','false')=='false','Actual old schema1 PRE/keep5 seed required')
        for key,value in dict(ArtificialStress=1,ArtificialStressCoef=.2,ArtificialStressExp=3,NoPenetration=1).items():need(float(p[key])==value,'Old handoff AS/NoPen differs: '+key)
def prepare():
    need(not SEEDOUT.exists() and not PREP.exists(),'Existing/partial common seed protected');before=[];call=None
    try:
        idle();check_input(ROOT,'source');check_input(HANDOFF.with_suffix('.xml'),'handoff')
        before=[stat(q) for q in (Path(__file__),T/'notes'/(TAG+'.md'),ROOT,PRE,PRE.parent/'Part_Head.ibi4',RUNTIME/'GenCase_win64.exe',Path(base.__file__),Path(base.evidence.__file__),Path(as_summary.__code__.co_filename))]+[stat(Path(str(HANDOFF)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        SEEDOUT.mkdir();call=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(ROOT.with_suffix('')),str(SOURCE),'-save:all'],C);check_input(SOURCE.with_suffix('.xml'),'source')
        # CSV consumes the generated seed's actual material values, not guessed defaults.
        r=ET.parse(SOURCE.with_suffix('.xml')).getroot();p={q.get('key'):q.get('value') for q in r.findall('execution/parameters/parameter')};soil=r.find('execution/special/soils');need(p['DPCtes']=='3','DP_PS internal and XML3 required by fixed reader')
        material=SEEDOUT/'material.csv'
        with material.open('x',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow(('key','value'));w.writerow(('DPCtes','3'))
            for key in ('phi','phi_r','n_phi','coh','coh_r','n_coh','dlt','DilationDecay'):
                nodes=soil.findall(key);need(len(nodes)==1,'Actual material key missing/duplicate: '+key);w.writerow((key,nodes[0].get('value')))
            fos=soil.find('SoilTriggerFos');w.writerow(('SoilTriggerFos',fos.get('value') if fos is not None else '1.65'));w.writerow(('fresh_trigger_active','0'))
        plan=SEEDOUT/'handoff_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(('part','completed_step'));w.writerow((0,4000010))
        verify(before);outputs=[stat(Path(str(SOURCE)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]+[stat(material),stat(plan)]
        save(PREP,dict(stage=TAG+'.prepare',passed=True,GenCase_call=call,GenCase_invocations=1,source_seed=str(SOURCE),handoff_seed=str(HANDOFF),source_material=stat(material),handoff_plan=stat(plan),outputs=outputs,consumed=before,consumed_stats_unchanged=True,solver_invocations=0,reader_invocations=0,physical_acceptance=False))
    except Exception as error:
        if not PREP.exists():save(PREP,dict(stage=TAG+'.prepare',passed=False,first_failure=str(error),GenCase_call=call,consumed=before,physical_acceptance=False))
        raise
def programs(which):
    conf='Debug' if which=='debug' else 'Release';bp=OLD_BUILD if which=='old' else L/('c08_preload_schema2_'+conf+'_r1.build.json');b=read(bp);need(b['passed'] and b['configuration']==conf,'Passed matching GPU '+conf+' build required');before=[stat(bp),bind(b['program']),bind(b['source_capture']),bind(b['source_archive'])]
    if which=='old':
        need(b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Sealed old program build required');program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe';actual=stat(program);need((actual['bytes'],actual['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'Original runtime_r6 program differs');before.append(actual)
    else:
        need(b['consumed_stats_unchanged'],'Frozen schema2 build changed');call=read(bind(b['actual_call'])['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual candidate MSBuild failed');before.append(bind(b['actual_call']));program=Path(b['program']['path']);leaf='DualSPHysics5.2_win64_debug.exe' if which=='debug' else 'DualSPHysics5.2_GEO_win64.exe';need(program.samefile(T/'outputs'/('c08_preload_schema2_'+conf+'_r1')/leaf),'Unexpected candidate program')
    before += [stat(program.parent/s) for s in RUNTIME_LEAVES];return program,bp,before
def summary(path,kind):
    if kind=='handoff':return as_summary(path)
    text=Path(path).read_text(encoding='utf-8-sig').splitlines();need(len(text)==2,'Completed source two-line Run.csv required');sep=';' if ';' in text[0] else ',';keys=text[0].lstrip('#').split(sep);values=text[1].split(sep);need(len(keys)==len(values) and len(set(keys))==len(keys),'Strict ASoff source Run.csv width differs');return dict(zip(keys,values))
def native_check(out,kind):
    d=read(out/'completion.json')
    if kind=='source':
        need(d['passed'] and d['stage']=='upl_c08_hdp15_preload_partial_r3' and d['profile']=='h12_control' and d['samples']==3 and d['completed_steps']==8000 and d['typed_arrays']==22 and d['native_IDs']==7060 and d['ledger_checks']==d['rho_cache_bits_checks']==15000 and d['fixed_marker_checks']==6180 and d['P0_bits_checks']==d['kappa_zero_checks']==21180 and d['noninitial_signed_intervals']==2 and d['max_scalar_clock_error_s']<=1e-14 and d['max_noninitial_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13,'Original three-frame source guards failed')
    else:
        counts=dict(samples=1,completed_steps=4000010,new_updates=10,typed_arrays=22,actual_native_IDs_per_frame=6805,actual_fixed_IDs=1805,soil_IDs=5000,ledger_checks=5000,rho_cache_bits_checks=5000,fixed_marker_checks=1805,P0_bits_checks=6805,kappa_nondecreasing_from_PRE_checks=5000,nonempty_signed_intervals=1,plane_gap_checks=10000)
        need(d['passed'] and d['stage']=='upl_c08_causal_native_r1' and all(d[k]==v for k,v in counts.items()) and d['source_material_law_version']==1 and d['source_PREs_read']==1 and d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['saved_steps_checked_against_launch_plan'],'Original ten-update schema1 handoff guards failed')
        m=read(out/'bedkeep_metadata.json');need(m['passed'] and m['profile']=='smoke' and m['smoke_final_only'] and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==m['ponding_policy_keys_absent_headers']==1 and m['AS_exponent_float_reference']==3 and m['expected_ponding_policy']=='CompletedOnly','Original receiver metadata failed')
    return d
def run(kind,which,memcheck=False):
    tag=TAG+'_'+kind+'_'+which;out=T/'outputs'/tag;rp=L/(tag+'.run.json');need(not out.exists() and not any(L.glob(tag+'.*')),'Existing physical/native/call/partial job protected');before=[];actual=None;reader_call=None;result=dict(stage=tag,passed=False,kind=kind,program_label=which,solver_completed=False,native_completed=False,solver_invocations=0,reader_invocations=0,physical_acceptance=False)
    try:
        idle();p=read(PREP);need(p['passed'] and p['consumed_stats_unchanged'],'Common seed preparation failed');program,bp,before=programs(which);before += [stat(PREP)]+[bind(q) for q in p['consumed']+p['outputs']]
        seed=SOURCE if kind=='source' else HANDOFF;check_input(seed.with_suffix('.xml'),kind);end,frames,nopen=(8000,3,0) if kind=='source' else (4000010,1,1);out.mkdir();readerpath=READERS[kind];b=read(readerpath);need(b['passed'],'Existing qualified native utility required');before += [stat(readerpath),bind(b['program']),bind(b['source'])]
        solverargv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:'+str(nopen),str(seed),str(out),'-dirdataout','data','-svres','-nsteps:'+str(end)];argv=solverargv;sanlog=L/(tag+'.memcheck.log')
        if memcheck:
            need(which=='debug' and kind=='handoff','Memcheck only for the optional independent Debug handoff');before.append(stat(base.evidence.SAN));argv=[str(base.evidence.SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*solverargv]
        ap=L/(tag+'.owner_admission.json');save(ap,dict(stage=tag,program=stat(program),source_build=stat(bp),shared_preparation=stat(PREP),input_xml=stat(seed.with_suffix('.xml')),source_pre_file=stat(PRE) if kind=='handoff' else None,planned_global_end=end,expected_saved_frames=frames,argv=argv,solver_argv=solverargv,memcheck=memcheck,consumed=before,physical_acceptance=False));result['solver_invocations']=1;actual=base.owned(tag,argv,program,memcheck,stat(ap));r=summary(out/'Run.csv',kind);text=(out/'Run.out').read_text(encoding='utf-8-sig')
        if memcheck:
            s=sanlog.read_text(encoding='utf-8',errors='replace');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',s);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',s);need(errors and leaks and all(int(q.replace(',',''))==0 for q in errors) and all(int(x.replace(',',''))==int(y.replace(',',''))==0 for x,y in leaks),'Actual memcheck summaries missing/nonzero');result.update(memcheck_zero_errors_and_leaks=True,memcheck_log=stat(sanlog))
        need(all(int(r[k])==v for k,v in dict(Steps=end,PartFiles=frames,Np=7060,Nbound=2060,Nfixed=2060,PartsOut=0,PartsOutRhop=0,PartsOutVel=0).items()) and 'Gpu_' in r['Hardware'] and 'Finished execution (code=0).' in text,'Actual GPU steps/registry/no-exclusion/end differs')
        parts=sorted((out/'data').glob('Part_*.bi4'));need([q.name for q in parts]==['Part_%04d.bi4'%i for i in range(frames)],'Actual contiguous native saves differ')
        if kind=='source':need('GravityPreload: phase=released ' not in text and 'state imported file=' not in text,'20ms source unexpectedly imported/released')
        else:
            need(len(re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=4000000;',text))==1 and text.count('GravityPreload: phase=released ')==1 and text.count('release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5')==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual schema1 import/one old release differs')
        result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0,actual_steps=end,saved_frames=frames,program=stat(program),source_build=stat(bp),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(q) for q in parts]);verify(before);idle();native=out/'native';ra=[b['program']['path'],'--read','h12_control',str(out/'data'),p['source_material']['path'],str(native)] if kind=='source' else [b['program']['path'],'--read','psi0','GPU',str(out/'data'),str(PRE),'4000010','1','1',p['handoff_plan']['path'],str(native)]
        result['reader_invocations']=1;reader_call=invoke(tag+'.native',ra,T/'outputs');d=native_check(native,kind);clock=rows(native/'clocks.csv');need(len(clock)==frames and int(clock[-1]['completed_step'])==end and all(q['dterror_interval_empty']=='0' for q in clock[1:] if kind=='source'),'Actual native completed clock shape differs');verify(before)
        artifacts=[stat(native/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json')]+([stat(native/'bedkeep_metadata.json')] if kind=='handoff' else []);result.update(passed=True,native_completed=True,shared_preparation=stat(PREP),input_xml=stat(seed.with_suffix('.xml')),source_pre_file=stat(PRE) if kind=='handoff' else None,native_completion=stat(native/'completion.json'),native_files=artifacts,native_original_numerical_guards_passed=True,consumed_stats_unchanged=True,source_reader_is_uncertified_diagnostic=(kind=='source'),old_path_compatibility_only=True)
    except Exception as error:
        result['first_failure']=str(error);cp=L/(tag+'.call.json')
        if cp.exists():a=read(cp);actual=stat(cp);result.update(actual_exit=a['actual_solver_Win32_exit'],actual_Win32_exit=a['actual_solver_Win32_exit'],actual_tool_exit=a['actual_Popen_wait_exit'],ownership_errors=a['ownership_errors'])
        nc=L/(tag+'.native.call.json')
        if nc.exists():reader_call=stat(nc)
    result.update(actual_call=actual,native_call=reader_call,consumed=before,last_original_console_line=base.last_part(out));save(rp,result);need(result['passed'],result.get('first_failure','Compatibility job failed'));print('REGRESSION_JOB_PASS',tag,flush=True)
def compare(kind):
    cp=L/(TAG+'_'+kind+'.compare.json');need(not cp.exists(),'Existing comparison protected');before=[];result=dict(stage=TAG+'.compare',kind=kind,passed=False,physical_acceptance=False)
    try:
        roots=[]
        for which in ('old','new'):
            rp=L/(TAG+'_'+kind+'_'+which+'.run.json');r=read(rp);need(r['passed'] and r['solver_completed'] and r['native_original_numerical_guards_passed'] and r['consumed_stats_unchanged'],'Both independent real jobs/native must pass');before += [stat(rp),bind(r['actual_call']),bind(r['native_call'])]+[bind(q) for q in r['native_files']];roots.append(Path(r['native_completion']['path']).parent)
        equal={leaf:(roots[0]/leaf).read_bytes()==(roots[1]/leaf).read_bytes() for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv')};need(all(equal.values()),'All22 payload/time/layout/signed clocks differ; preserve mismatch');verify(before);result.update(passed=True,files_byte_exact=equal,genuine_headers_not_rewritten=True,all22_and_actual_time_and_signed_dterror_byte_exact=True,consumed_stats_unchanged=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=before;save(cp,result);need(result['passed'],result.get('first_failure','Comparison failed'))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run','compare','debug_handoff'));p.add_argument('--kind',choices=('source','handoff'));p.add_argument('--program',choices=('old','new'));p.add_argument('--memcheck',action='store_true');p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized and ((a.action in ('prepare','debug_handoff') and a.kind is None and a.program is None) or (a.action=='run' and a.kind and a.program) or (a.action=='compare' and a.kind and a.program is None)) and (not a.memcheck or a.action=='debug_handoff'),'Explicit single action required; memcheck only optional Debug handoff; no matrix/next/queue');{'prepare':lambda:prepare(),'run':lambda:run(a.kind,a.program),'compare':lambda:compare(a.kind),'debug_handoff':lambda:run('handoff','debug',a.memcheck)}[a.action]()
