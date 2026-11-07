"""One selected ReleaseGPU receiver or one completed native decode; no source/half/long/package launch."""
import csv,json,os,re,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
sys.path.insert(0,str(Path(__file__).parent))
from mdbc_admission_r2 import T,L,need,read,stat,save,bind,invoke
TAG='upl_c08_branches_r1';PLAN=T/'notes'/('upl_c08_branches_r1.json')
def run(group):
    need(group in('psi2p5','psim5'),'Only two prepared receiver groups');tag=TAG+'_'+group+'_GPU';out=T/'outputs'/tag;seedout=T/'outputs'/(tag+'_seed');record=L/(tag+'.run.json');need(not any(p.exists()for p in(out,seedout,record)),'Existing/partial receiver protected')
    c={};result=dict(stage=tag,passed=False,profile=group,backend='GPU',configuration='Release',solver_invocations=0,native_decoder_invocations=0,physical_acceptance=False,SHA_scans=0)
    try:
        plan=read(PLAN);scpath=Path(plan['source_native_check']);src=read(scpath);need(src['passed']and src['qualified_elastic_PRE_verified']and src['original_native_guards_passed']and src['consumed_stats_unchanged']and src['actual_completion']['source_material_law_version']==2,'Closed certified Version2 GPU Release PRE required')
        pre=Path(plan['PRE']);bind(src['certified_pre_file'],c);need(pre.samefile(src['certified_pre_file']['path']),'Prepared PRE identity differs');sr=read(src['source_run']['path']);need(sr['passed']and sr['actual_exit']==sr['actual_Win32_exit']==0 and sr['consumed_stats_unchanged']and Path(sr['source_build']['path']).name=='upl_material_release_Release_r3.build.json','Source must be the actual completed unified ReleaseGPU run')
        for e in(src['source_run'],src['native_completion']):bind(e,c)
        bp=Path(plan['target_build']);b=read(bp);need(b['passed']and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged']and b['canonical_and_package_stats_unchanged'],'Frozen new ReleaseGPU build required');program=bind(b['program'],c);exe=Path(program['path']);need(exe.samefile(plan['target_program'])and exe.parent.name=='mdbc_partition_Release_r1','Only the new isolated ReleaseGPU receiver program')
        config=Path(plan['groups'][group]['config']);root=ET.parse(config).getroot();soil=root.find('./execution/special/soils');event=root.find('./execution/special/gravitypreload');need(soil is not None and event is not None and Path(event.get('statefile','')).samefile(pre)and event.get('elastic_source','false').lower()not in('true','1'),'Actual receiver statefile/source scope differs')
        parameters={'phi':25.,'phi_r':25.,'n_phi':0.,'coh':7500. if group=='psim5'else 5000.,'coh_r':1000.,'n_coh':5.,'dlt':-5. if group=='psim5'else 2.5,'DilationDecay':.2,'MaterialReturn':1.}
        for key,value in parameters.items():need(soil.find(key)is not None and float(soil.find(key).get('value'))==value,'Actual group material differs: '+key)
        for p in(PLAN,scpath,bp,config,Path(__file__)):bind(stat(p),c)
        bind(b['source_capture'],c);original=[Path(e['path'])for e in sr['seed']];need(len(original)==3,'Certified source XML/BI4/normals geometry seed required')
        for e in sr['seed']:bind(e,c)
        runtime=T/'outputs/upl_prestress_check_GPU_r1_runtime'
        for name in('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            srcfile=bind(stat(runtime/name),c);dst=exe.parent/name
            if not dst.exists():shutil.copy2(srcfile['path'],dst)
            now=stat(dst);need((now['bytes'],now['mtime_ns'])==(srcfile['bytes'],srcfile['mtime_ns']),'Copied runtime stat differs');bind(now,c)
        active=[q.info for q in psutil.process_iter(['exe','cmdline'])if q.info['exe']and(os.path.normcase(os.path.abspath(q.info['exe']))==os.path.normcase(os.path.abspath(exe))or any(os.path.normcase(os.path.abspath(a))==os.path.normcase(os.path.abspath(out))for a in(q.info['cmdline']or[])[1:]if os.path.isabs(a)))];need(not active,'Same exact program/output already active; no process is stopped')
        seedout.mkdir();prefix=seedout/original[0].stem;shutil.copy2(config,str(prefix)+'.xml')
        for suffix,p in zip(('.bi4','_Normals.nbi4'),original[1:]):shutil.copy2(p,str(prefix)+suffix)
        seed=[stat(str(prefix)+suffix)for suffix in('.xml','.bi4','_Normals.nbi4')]
        for e in seed:bind(e,c)
        argv=[str(exe),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:800'];result.update(program=program,source_build=stat(bp),config=stat(config),seed=seed,source_pre_file=stat(pre),source_PRE_check=stat(scpath),source_pre_time_s=src['actual_completion']['source_PRE_actual_time_s'],source_continuous_run=src['source_run'],material_parameters=parameters,output=str(out),initial_completed_step=380,planned_global_completed_steps=800,planned_new_updates=420,dt_s=.0000025);result['solver_invocations']=1;rc,paths=invoke(tag,argv,c);result.update(actual_exit=rc,actual_Win32_exit=rc,start_record=stat(paths['start']),actual_call=stat(paths['call']));text=(out/'Run.out').read_text(encoding='utf-8-sig');need(rc==0 and'Finished execution (code=0).'in text,'Actual receiver did not complete safely')
        with(out/'Run.csv').open(encoding='utf-8-sig',newline='')as f:rows=list(csv.DictReader(f,delimiter=';'))
        need(len(rows)==1,'One actual receiver summary required');r=rows[0];need(int(r['Steps'])==800 and int(r['PartFiles'])==11 and int(r['Np'])==7060 and int(r['Nbound'])==int(r['Nfixed'])==2060 and all(int(r[k])==0 for k in('PartsOut','PartsOutRhop','PartsOutVel')),'Actual receiver global counters/native registry/safety differ');need([p.name for p in sorted((out/'data').glob('Part_*.bi4'))]==['Part_%04d.bi4'%i for i in range(11)],'Actual receiver frame membership differs')
        imports=[x for x in text.splitlines()if'GravityPreload: state imported file='in x];releases=[x for x in text.splitlines()if'GravityPreload: phase=released'in x];need(len(imports)==len(releases)==1 and'GravityPreload: source material law=unified2;'in text and'retired=260; damping=OFF Shepard=OFF FreeSeepage=ON.'in releases[0],'Actual Version2 import/unique wall release/stage flags differ')
        for line in(imports[0],releases[0]):
            m=re.search(r'actual=([^ ]+) completed_step=(\d+)',line);need(m and float(m[1])==result['source_pre_time_s']and int(m[2])==380,'Actual source clock/global count was reset or changed')
        result.update(passed=True,actual_steps=800,new_updates_from_completed_counters=420,saved_frames=11,summary=r,Run_out=stat(out/'Run.out'),Run_csv=stat(out/'Run.csv'),actual_import_line=imports[0],actual_release_line=releases[0],native_review_pending=True)
    except Exception as e:result['first_failure']=str(e)
    result['consumed_stats_unchanged']=bool(c)and all(stat(e['path'])==e for e in c.values());result['passed']=bool(result['passed']and result['consumed_stats_unchanged']);result['consumed']=list(c.values());save(record,result);print(json.dumps(dict(tag=tag,passed=result['passed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed']else 1

def decode(group):
    need(group in('psi2p5','psim5'),'Only two prepared receiver groups');tag=TAG+'_'+group+'_GPU';record=L/(tag+'.run.json');r=read(record);need(r['passed']and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged']and r['new_updates_from_completed_counters']==420,'Actual receiver run not closed');out=T/'outputs'/(tag+'_native');cp=L/(tag+'.native.check.json');need(not out.exists()and not cp.exists(),'Existing/partial receiver decode protected');c={};bp=L/'upl_c08_branches_native_r1.build.json';b=read(bp);need(b['passed']and b['consumed_stats_unchanged']and not b['JSph_objects_linked'],'Closed six-utility-object receiver reader required')
    for p in(record,bp,Path(__file__)):bind(stat(p),c)
    for e in r['consumed']:bind(e,c)
    for e in(b['program'],b['source']):bind(e,c)
    data=Path(r['output'])/'data'
    for p in sorted(data.glob('Part_*.bi4')):bind(stat(p),c)
    exe=Path(b['program']['path']);need(not any(q.info['exe']and os.path.normcase(os.path.abspath(q.info['exe']))==os.path.normcase(os.path.abspath(exe))for q in psutil.process_iter(['exe'])),'This exact reader is already active');argv=[str(exe),group,str(data),r['source_pre_file']['path'],str(out),'AUTHORIZED'];rc,paths=invoke(tag+'.native',argv,c);d=read(out/'completion.json')if(out/'completion.json').exists()else{};passed=rc==0 and d.get('passed')and d.get('profile')==group and d.get('samples')==11 and d.get('completed_steps')==800 and d.get('typed_arrays')==22 and d.get('ledger_checks')==55000 and d.get('fixed_checks')==19800 and d.get('qualified_Version2_elastic_PRE_read')and d.get('new_updates')==420 and d.get('noninitial_signed_intervals')==11 and d.get('receiver_part0_is_not_t0');unchanged=all(stat(e['path'])==e for e in c.values())
    save(cp,dict(passed=bool(passed and unchanged),source_run=stat(record),reader_build=stat(bp),actual_exit=rc,actual_Win32_exit=rc,actual_call=stat(paths['call']),native_completion=stat(out/'completion.json')if d else None,actual_completion=d,files=[stat(p)for p in sorted(out.iterdir())if p.is_file()]if out.exists()else[],consumed=list(c.values()),consumed_stats_unchanged=unchanged,original_native_guards_passed=bool(passed),physical_acceptance=False,SHA_scans=0));print('NATIVE_CHECK',cp,bool(passed and unchanged),flush=True);return 0 if passed and unchanged else 1
if __name__=='__main__':
    need(len(sys.argv)==4 and sys.argv[3]=='--execution-authorized','Use run|decode psi2p5|psim5 --execution-authorized')
    if sys.argv[1]=='run':raise SystemExit(run(sys.argv[2]))
    if sys.argv[1]=='decode':raise SystemExit(decode(sys.argv[2]))
    raise RuntimeError('Only explicit single run or decode supported')
