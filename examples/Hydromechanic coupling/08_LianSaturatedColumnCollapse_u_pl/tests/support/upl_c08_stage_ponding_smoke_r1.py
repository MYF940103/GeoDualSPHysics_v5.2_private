"""One root-selected ReleasedSubstages 2 ms smoke; no reader, queue or next-stage launch."""
import argparse,csv,json,os,re,shutil,struct
from pathlib import Path
import xml.etree.ElementTree as ET
import psutil
import upl_c08_bedkeep_run_r1 as base
import upl_c08_asn3_window_r1 as n3

T,C,L,PRE=base.T,base.C,base.L,base.PRE
SOURCE=4000000;UPDATES=800;CADENCE=400;FRAMES=2;END='10.002';TOUT='0.001'
OLD='upl_c08_asn3_window_GPU_r1';DEF=T/'configs'/(OLD+'_Def.xml');SEED=T/'outputs'/OLD/(OLD+'.xml')
SPECS={'CPUdebug':('DebugCPU','CPU',False),'GPUdebug':('Debug','GPU',True),'Release':('Release','GPU',False)}
need,read,stat,bind,save=base.need,base.read,base.stat,base.bind,base.save

def verify(entries):need(all(stat(e['path'])==e for e in entries),'Consumed closed input changed')
def clocks(root):
    p=root.find('execution/parameters')
    for key,value in (('TimeMax',END),('TimeOut',TOUT)):
        nodes=[q for q in p if q.get('key')==key];need(len(nodes)==1,'Unique time parameter required');nodes[0].set('value',value)
    return root

def check_input(path,tag,generated=False):
    actual=ET.parse(path).getroot();expected=clocks(ET.parse(SEED if generated else DEF).getroot())
    if generated:
        rename={OLD+'_hdp_Actual.vtk':tag+'_hdp_Actual.vtk',OLD+'__Actual.vtk':tag+'__Actual.vtk'};nodes=expected.findall('execution/vtkout/vtkfile')
        need(len(nodes)==2 and {q.get('name') for q in nodes}==set(rename),'Exactly two known generated VTK labels required')
        for q in nodes:q.set('name',rename[q.get('name')])
        actual.attrib.pop('date',None);expected.attrib.pop('date',None)
    need(n3.signature(actual)==n3.signature(expected),'Only the two declared clock values / generated labels may differ from n3 input')
    params={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')}
    for key,value in (('DtFixed',.0000025),('DtIni',.0000025),('TimeMax',float(END)),('TimeOut',float(TOUT)),('ArtificialStress',1),('ArtificialStressCoef',.2),('ArtificialStressExp',3),('NoPenetration',1)):
        need(float(params[key])==value,'Locked original input differs: '+key)
    event=actual.find('execution/special/gravitypreload');need(Path(event.get('statefile','')).is_absolute() and Path(event.get('statefile')).samefile(PRE) and event.get('keep_bed_overlap')=='true','Original r2 PRE / kept bed source required')

def normal_output(out,backend):
    r=n3.summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==SOURCE+UPDATES and int(r['PartFiles'])==FRAMES and int(r['Np'])==7060 and int(r['Nbound'])==int(r['Nfixed'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual steps / registry / two saves / exclusions differ')
    need(('Gpu_' in r['Hardware'])==(backend=='GPU'),'Actual Run.csv backend differs')
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text and 'FreeSeepagePolicy: candidate ReleasedSubstages;' in text,'Actual new boundary / ponding policy missing')
    for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',3.)):
        values=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(values)==1 and struct.pack('<f',float(values[0]))==struct.pack('<f',value),'Actual AS log differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,base.BED_IDS))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.'
    need(text.count('GravityPreload: phase=released ')==text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Original one-time release differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==SOURCE,'True source scalar clock / step missing')
    need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual two native filenames differ')
    result=dict(actual_steps=SOURCE+UPDATES,saved_frames=FRAMES,summary=r,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(p) for p in parts])
    trace=out/'C08StageTrace.csv'
    if backend=='GPU':need(trace.is_file() and trace.stat().st_size>0,'Macro-enabled GPU trace missing');result.update(trace_file=stat(trace),trace_algebra_review_pending=True)
    else:need(not trace.exists(),'CPU Debug was built without the GPU-only trace macro')
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('configuration',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read and explicit one-stage selection required')
    conf,backend,memcheck=SPECS[a.configuration];tag='upl_c08_stage_ponding_smoke_'+a.configuration+'_r1';out=T/'outputs'/tag;config=T/'configs'/(tag+'_Def.xml');rp=L/(tag+'.run.json');rootad=L/(tag+'.admission.json');bp=L/('upl_c08_stage_ponding_'+conf+'_r2.build.json')
    need(not out.exists() and not config.exists() and not any(p.name!=rootad.name for p in L.glob(tag+'.*')),'Existing complete or partial invocation protected; no retry')
    before=[];result=dict(stage=tag,passed=False,configuration=conf,source_backend='GPU',target_backend=backend,cross_backend_handoff=(backend=='CPU'),physical_acceptance=False,solver_invocations=0,reader_invocations=0,queue_invocations=0,PartVTK_invocations=0,SHA_scans=0,native_review_pending=True,policy=base.POLICY,free_seepage_policy='ReleasedSubstages',keep_bed_overlap=True,expected_active_native_IDs=6805,ArtificialStress=True,ArtificialStressCoef=.2,ArtificialStressExp=3.,expected_saved_completed_steps=[4000400,4000800])
    try:
        b=read(bp);gpu=backend=='GPU';need(b['passed'] and b['configuration']==conf and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_runtime_PRE_unchanged'] and len(b['project_objects'])==(113 if gpu else 87),'Passed corresponding new r2 isolated build required')
        need(b['trace_macro']=='C08_STAGE_TRACE' and b['trace_macro_enabled']==gpu and b['environment_macro']['appended']==({'CL':'/DC08_STAGE_TRACE','NVCC_PREPEND_FLAGS':'-DC08_STAGE_TRACE'} if gpu else {}) and Path(b['source_capture']['path']).samefile(T/'outputs/upl_c08_stage_ponding_source_r2/source.json'),'Current new r2 source / CPU-off GPU-on trace build required')
        program=Path(bind(b['program'])['path']);before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_stage_ponding_smoke_r1.md',Path(base.__file__),Path(base.evidence.__file__),Path(n3.__file__),bp,DEF,SEED,PRE,PRE.parent/'Part_Head.ibi4')]+[bind(b[k]) for k in ('program','source_capture','source_archive')];runtime=[]
        if rootad.exists():before.append(stat(rootad))
        for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'):
            origin=C/'support/runtime_r5'/leaf;e=stat(origin);dest=program.parent/leaf
            if not dest.exists():shutil.copy2(origin,dest)
            d=stat(dest);need((d['bytes'],d['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Runtime dependency copy differs');before.extend((e,d));runtime.append(d)
        for q in psutil.process_iter(['exe','cmdline']):
            try:
                exe=q.info['exe'];argv=q.info['cmdline'] or [];need(not(exe and Path(exe).name.lower().startswith('dualsphysics') and (Path(exe).samefile(program) or gpu and any(x.lower().startswith('-gpu') for x in argv[1:]))),'Conflicting actual solver active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        text=DEF.read_text(encoding='utf-8')
        for key,value in (('TimeMax',END),('TimeOut',TOUT)):
            text,count=re.subn(r'(<parameter key="'+key+r'" value=")[^"]+("[^>]*>)',lambda m:m[1]+value+m[2],text);need(count==1,'Unique literal clock substitution required')
        with config.open('x',encoding='utf-8',newline='') as f:f.write(text)
        check_input(config,tag);before.append(stat(config));gen=C/'support/runtime_r5/GenCase_win64.exe';before.append(stat(gen));prefix=out/tag
        result['GenCase_call']=base.invoke(tag+'.gencase',[str(gen),str(config.with_suffix('')),str(prefix),'-save:all'],C);seed=Path(str(prefix)+'.xml');check_input(seed,tag,True);before.extend(stat(Path(str(prefix)+suffix)) for suffix in ('.xml','.bi4','_Normals.nbi4'))
        plan=out/'planned_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(('part','completed_step'));writer.writerows(((0,4000400),(1,4000800)))
        before.append(stat(plan));solverargv=[str(program),*(['-cpu','-ompthreads:8'] if not gpu else ['-gpu:0']),'-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:4000800'];argv=solverargv;sanlog=L/(tag+'.memcheck.log')
        if memcheck:before.append(stat(base.evidence.SAN));argv=[str(base.evidence.SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*solverargv]
        admission=L/(tag+('.owner_admission.json' if rootad.exists() else '.admission.json'));save(admission,dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),program=stat(program),source_build=stat(bp),source_pre_file=stat(PRE),planned_steps=stat(plan),planned_global_end=SOURCE+UPDATES,expected_saved_frames=FRAMES,argv=argv,solver_argv=solverargv,consumed=before))
        result['solver_invocations']=1;result['actual_call']=base.owned(tag,argv,program,memcheck,stat(admission));result.update(normal_output(out,backend))
        if memcheck:
            text=sanlog.read_text(encoding='utf-8');errors=re.findall(r'ERROR SUMMARY: ([0-9,]+) errors',text);leaks=re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations',text);need(errors and leaks and all(int(v.replace(',',''))==0 for v in errors) and all(int(v.replace(',',''))==int(w.replace(',',''))==0 for v,w in leaks),'Original zero memcheck errors / leaks gate failed');result.update(memcheck_zero_errors_and_leaks=True,memcheck_log=stat(sanlog))
        verify(before);result.update(passed=True,actual_exit=0,actual_Win32_exit=0,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],input_xml=stat(seed),source_pre_file=stat(PRE),planned_steps=stat(plan),runtime=runtime,consumed_stats_unchanged=True)
    except Exception as error:
        result['first_failure']=str(error);cp=L/(tag+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    result.update(consumed=before,last_original_console_line=base.last_part(out));save(rp,result);print(json.dumps(dict(passed=result['passed'],receipt=str(rp),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
