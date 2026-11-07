"""Separate a05 GPU old/new comparison; explicit single actions, frozen programs, no GenCase."""
import argparse,csv,json,os,re,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'10_StaticDrySoilColumn/tests/support'))
from basic_material_r1 import R,H,need,read,stat,save,invoke,xml_time,psutil
C=Path(__file__).resolve().parents[2];T=C/'tests';STEM='CaseGranularColumnCollapse2D_a05';SOIL=20000;FIXED=4028
MP=T/'logs/basic_a05_r1.inputs.json';END={'short':.1,'full':1.};NAMES=('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')
def tag(window,mode):return 'basic_a05_'+window+'_'+mode+'_GPU_r1'
def record(window,mode,suffix):return T/'logs'/(tag(window,mode)+suffix)
def output(window,mode):return T/'outputs'/tag(window,mode)
def table(p):
    with Path(p).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def prepare():
    seed=T/'outputs/basic_a05_r1_seed';need(not MP.exists() and not seed.exists(),'Fresh a05 preparation required');source=C/(STEM+'_GPU_out');original=C/(STEM+'_Def.xml');src=[source/(STEM+s) for s in ('.xml','.bi4','_Normals.nbi4')];protected=[stat(original),*[stat(p) for p in src]]
    d,g=ET.parse(original),ET.parse(src[0]);values=lambda e:{x.get('key'):x.get('value') for x in e.findall('.//parameters/parameter')};soils=lambda e:{x.tag:x.get('value') for x in e.findall('.//special/soils/*')};need(values(d)==values(g) and soils(d)==soils(g),'Retained a05 generated settings differ from formal Def');p=g.find('.//particles');need(int(p.get('np'))==SOIL+FIXED and int(p.get('nb'))==int(p.get('nbf'))==FIXED,'Actual a05 native registry differs');need(float(g.find('.//constants/dp').get('value'))==.001,'Original a05 dp required')
    folders=[T/'outputs'/('basic_a05_r1_runtime_'+mode) for mode in ('old','new')];cfg=[T/'configs'/(STEM+s) for s in ('_basic_a05_Def.xml','_basic_a05_short.xml','_basic_a05_full.xml')];need(not any(p.exists() for p in folders+cfg),'Existing a05 artifacts protected');programs={}
    for mode,buildtag in [('old','upl_preload_handoff_Release_r2'),('new','upl_material_release_Release_r3')]:
        bp=H/'logs'/(buildtag+'.build.json');b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and stat(b['program']['path'])==b['program'],'Closed unchanged GPU Release build required');capture=b['source_capture'];need(stat(capture['path'])==capture,'Frozen source capture changed');archive=read(capture['path'])['archive'];need(stat(archive['path'])==archive,'Frozen source archive changed');runtime=[stat(Path(b['program']['path']).parent/n) for n in NAMES]
        programs[mode]=dict(frozen_program=b['program'],build=stat(bp),source_capture=capture,source_archive=archive,runtime_sources=runtime)
    seed.mkdir();shutil.copy2(original,cfg[0])
    for p in src:shutil.copy2(p,seed/p.name)
    for window,path in zip(('short','full'),cfg[1:]):xml_time(seed/(STEM+'.xml'),path,END[window])
    for mode,folder in zip(('old','new'),folders):
        folder.mkdir();p=programs[mode];shutil.copy2(p['frozen_program']['path'],folder/Path(p['frozen_program']['path']).name)
        for e in p['runtime_sources']:shutil.copy2(e['path'],folder/Path(e['path']).name)
        p.update(program=stat(folder/Path(p['frozen_program']['path']).name),runtime=[stat(folder/n) for n in NAMES])
    need(all(stat(e['path'])==e for e in protected),'Formal/retained seed changed');save(MP,dict(stage='basic_a05_r1.prepare',passed=True,soil=SOIL,fixed=FIXED,seed=[stat(seed/(STEM+s)) for s in ('.xml','.bi4','_Normals.nbi4')],configs={k:stat(p) for k,p in zip(('short','full'),cfg[1:])},programs=programs,protected=protected,GenCase_invocations=0,SHA_scans=0));print('PREPARED a05',SOIL,FIXED,flush=True)
def run(window,mode):
    m=read(MP);need(m['passed'],'Prepared a05 inputs required');out=output(window,mode);rp=record(window,mode,'.run.json');seed=T/'outputs'/(tag(window,mode)+'_seed');need(not any(p.exists() for p in (out,rp,seed)),'Fresh single run required')
    if window=='full':need(read(T/'logs/basic_a05_short_r1.review.json')['passed'],'Review both short runs before an explicit full run')
    p=m['programs'][mode];consumed=[stat(MP),stat(__file__),p['program'],p['frozen_program'],p['build'],p['source_capture'],p['source_archive'],*p['runtime'],*p['runtime_sources'],*m['seed'],m['configs'][window],*m['protected']];need(all(stat(e['path'])==e for e in consumed),'Frozen a05 dependency changed')
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and 'dualsphysics' in Path(q.info['exe']).name.lower() and any(str(x).lower().startswith('-gpu') for x in (q.info['cmdline'] or []))),'Another GPU solver is active')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    seed.mkdir();shutil.copy2(m['configs'][window]['path'],seed/(STEM+'.xml'))
    for suffix in ('.bi4','_Normals.nbi4'):shutil.copy2(Path(m['seed'][0]['path']).parent/(STEM+suffix),seed/(STEM+suffix))
    argv=[p['program']['path'],'-gpu:0','-stable','-mdbc_noslip',str(seed/STEM),str(out),'-dirdataout','data','-svres'];result=dict(stage=tag(window,mode)+'.run',passed=False,window=window,mode=mode,consumed=consumed,input_manifest=stat(MP),physical_acceptance=False)
    try:
        call=invoke(T,tag(window,mode),argv,C);result['actual_call']=call
        with (out/'Run.csv').open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f,delimiter=';'))
        need(len(rows)==1,'One actual Run.csv row required');r=rows[0];text=(out/'Run.out').read_text(encoding='utf-8',errors='replace');need('[Simulation finished' in text and int(r['Np'])==SOIL+FIXED and int(r['Nfixed'])==int(r['Nbound'])==FIXED and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Normal completion/count/no-exclusion failed');need(all(k in r['Configuration'] for k in ('Symplectic','Wendland','No-slip')) and 'GPU' in r['RunMode'] and float(r['Dp'])==.001 and float(r['H'])==.0018,'Actual a05 backend/formulation differs');n=int(r['PartFiles']);parts=list((out/'data').glob('Part_*.bi4'));need(len(parts)==n and all((out/'data'/f'Part_{i:04d}.bi4').is_file() for i in range(n)),'Native PART membership differs');need(all(stat(e['path'])==e for e in consumed),'Frozen a05 dependency changed');result.update(passed=True,actual_steps=int(r['Steps']),saved_frames=n,RunCSV=r,hardware=r['Hardware'],main_loop_seconds=float(r['TSimul']),last_console_PART_line=next((x for x in reversed(text.splitlines()) if re.match(r'^Part_\d+\s',x)),None),consumed_stats_unchanged=True,native_review_pending=True)
    except Exception as e:result['first_failure']=str(e)
    save(rp,result);print(json.dumps({k:v for k,v in result.items() if k not in ('consumed','RunCSV')},indent=2),flush=True);need(result['passed'],'Run failed; no automatic retry')
def native(window,mode):
    rp=record(window,mode,'.run.json');r=read(rp);need(r['passed'] and r['consumed_stats_unchanged'],'Closed safe solver run required');bp=R/'examples/Elastoplastic_basic/10_StaticDrySoilColumn/tests/logs/basic_native_r2.build.json';b=read(bp);need(b['passed'] and stat(b['program']['path'])==b['program'],'Closed unchanged generic native reader required');out=T/'outputs'/(tag(window,mode)+'_native_r2');cp=record(window,mode,'.native_r2.check.json');need(not out.exists() and not cp.exists(),'Fresh sole native read required');before=[stat(rp),stat(bp),b['program']];v=dict(passed=False,source_run=stat(rp),reader_build=stat(bp),physical_acceptance=False)
    try:
        call=invoke(T,tag(window,mode)+'.native_r2',[b['program']['path'],str(output(window,mode)/'data'),str(SOIL),str(FIXED),str(r['saved_frames']),str(out)],C);d=read(out/'completion.json');clock=table(out/'clocks.csv');need(d['passed'] and d['soil']==SOIL and d['fixed']==FIXED and d['samples']==r['saved_frames'] and d['no_exclusions'] and int(clock[-1]['completed_steps'])==r['actual_steps'] and d['native_end_s']>=END[window],'Native counts/finite/fixed/end guards failed');need(all(stat(e['path'])==e for e in before),'Reader/run binding changed');v.update(passed=True,actual_call=call,completion=d,consumed_stats_unchanged=True,files=[stat(p) for p in out.iterdir() if p.is_file()])
    except Exception as e:v['first_failure']=str(e)
    save(cp,v);print(json.dumps({k:x for k,x in v.items() if k not in ('actual_call','files')},indent=2));need(v['passed'],'Native read failed; preserve first evidence')
def review(window):
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from basic_material_review_r1 import write
    prefix='basic_a05_'+window+'_r1';png=T/'figures'/(prefix+'.png');cp=T/'logs'/(prefix+'.review.json');csvs=[T/'figures'/(prefix+x) for x in ('_history.csv','_final.csv','_differences.csv')];need(not any(p.exists() for p in [png,cp,*csvs]),'Fresh offline review required');sets=[];consumed=[]
    for mode in ('old','new'):
        ncp=record(window,mode,'.native_r2.check.json');n=read(ncp);need(n['passed'] and n['consumed_stats_unchanged'],'Both native reads must pass');folder=T/'outputs'/(tag(window,mode)+'_native_r2');b=folder/'states.bin';h=np.fromfile(b,dtype='<u4',count=4);need(tuple(map(int,h[[0,1,3]]))==(SOIL,FIXED,14),'Native a05 registry changed');frames=int(h[2]);dt=np.dtype([('time','<f8'),('state','<f8',(SOIL,14))]);need(b.stat().st_size==16+frames*dt.itemsize,'Native binary length differs');a=np.fromfile(b,dtype=dt,offset=16);hh=table(folder/'history.csv');clock=table(folder/'clocks.csv');need(len(a)==len(hh)==len(clock) and np.array_equal(a['time'],[float(x['time_s']) for x in clock]),'Actual native clock coverage differs');sets.append(dict(mode=mode,a=a,history=hh,completion=n['completion']));consumed += [stat(ncp),stat(b),stat(folder/'history.csv'),stat(folder/'clocks.csv')]
    old,new=sets;initial=int(np.count_nonzero(old['a']['state'][0].view('<u8')!=new['a']['state'][0].view('<u8')));need(initial==0,'Common initial14 native fields differ');hist=[];final=[];diff=[];summary={};labels=('x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s','native_rho_kg_m3','kappa','sigma_xx_Pa','sigma_yy_Pa','sigma_zz_Pa','sigma_xy_Pa','sigma_yz_Pa','sigma_xz_Pa')
    for d in sets:
        mode=d['mode'];hist += [dict(mode=mode,**r) for r in d['history']];a=d['a']['state'];v=a[-1]
        for i,row in enumerate(v):final.append(dict(mode=mode,id=FIXED+i,x0_m=float(a[0,i,0]),z0_m=float(a[0,i,2]),**dict(zip(labels,map(float,row))),settlement_m=float(a[0,i,2]-row[2])))
        runinfo=read(record(window,mode,'.run.json'));summary[mode]=dict(native=d['completion'],last_history=d['history'][-1],hardware=runinfo['hardware'],main_loop_seconds=runinfo['main_loop_seconds'],actual_steps=runinfo['actual_steps'],elapsed_seconds=runinfo['actual_call']['elapsed_s'])
    for part,(tm,v) in enumerate(zip(old['a']['time'],old['a']['state'])):
        j=int(np.argmin(abs(new['a']['time']-tm)));gap=float(new['a']['time'][j]-tm);e=new['a']['state'][j]-v;s=e[:,8:14];diff.append(dict(old_part=part,new_nearest_part=j,old_actual_time_s=float(tm),new_actual_time_s=float(new['a']['time'][j]),time_gap_s=gap,comparison='matched_actual_time' if abs(gap)<=1e-14 else 'nearest_actual_time_descriptive_only',position_XYZ_RMS_m=float(np.sqrt(np.mean(np.sum(e[:,:3]**2,axis=1)))),velocity_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(e[:,3:6]**2,axis=1)))),rho_RMS_kg_m3=float(np.sqrt(np.mean(e[:,6]**2))),kappa_RMS=float(np.sqrt(np.mean(e[:,7]**2))),sigma_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(s[:,:3]**2,axis=1)+2*np.sum(s[:,3:]**2,axis=1)))),sigma_component_max_abs_Pa=float(np.max(abs(s)))))
    for p,rs in zip(csvs,(hist,final,diff)):write(p,rs)
    fig,ax=plt.subplots(2,2,figsize=(11,8),layout='constrained')
    for d in sets:
        tm=d['a']['time'];v=d['a']['state'][-1];hh=d['history'];mode=d['mode'];line=lambda k:[float(r[k]) for r in hh];ax[0,0].scatter(v[:,0],v[:,2],s=2,alpha=.4,label=mode+' @ '+format(tm[-1],'.9g')+' s');ax[0,1].plot(tm,line('sigma_Frobenius_RMS_Pa'),label=mode);ax[1,0].plot(tm,line('kappa_max'),label=mode);ax[1,1].plot(tm,line('velocity_RMS_m_s'),label=mode)
    ax[0,0].set(xlabel='x (m)',ylabel='z (m)',title='All20,000 original soil IDs');ax[0,0].set_aspect('equal',adjustable='datalim');ax[0,1].set(xlabel='actual time (s)',ylabel='dry stress Frobenius RMS (Pa)');ax[1,0].set(xlabel='actual time (s)',ylabel='maximum saved kappa');ax[1,1].set(xlabel='actual time (s)',ylabel='velocity XYZ RMS (m/s)')
    for a in ax.flat:a.grid(alpha=.25);a.legend(fontsize=8)
    fig.suptitle('Granular column a=0.5 | original dp=.001 | old basic fast vs unified return | GPU\nSame input/adaptive dt; unequal-time differences are descriptive');fig.savefig(png,dpi=160);plt.close(fig);need(all(stat(e['path'])==e for e in consumed),'Consumed export changed');r=dict(stage=prefix+'.review',passed=True,initial_common_14_different_scalar_bitpatterns=initial,summary=summary,maximum_nearest_actual_time_gap_s=max(abs(x['time_gap_s']) for x in diff),maximum_descriptive_sigma_Frobenius_RMS_gap_Pa=max(x['sigma_Frobenius_RMS_Pa'] for x in diff),maximum_descriptive_position_XYZ_RMS_gap_m=max(x['position_XYZ_RMS_m'] for x in diff),position_precision='native float32 expanded exactly',stress_precision='See native completion float64_stress_frames; SigmaState preferred',interpolation=False,new_physical_error_gate=False,physical_acceptance=False,timing_is_controlled_benchmark=False,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(png),*[stat(p) for p in csvs]],SHA_scans=0);save(cp,r);print(json.dumps({k:v for k,v in r.items() if k not in ('consumed','files')},indent=2))
def particles(window):
    runpath=record(window,'new','.run.json');nativepath=record(window,'new','.native_r2.check.json');r,n=read(runpath),read(nativepath);need(r['passed'] and n['passed'],'Closed completed new a05 run/native required');out=output(window,'new');target=out/'particles';cp=record(window,'new','.particles_r1.check.json');need(not target.exists() and not cp.exists(),'Fresh official PartVTK output required');program=R/'bin/windows/PartVTK_win64.exe';xml=T/'outputs'/(tag(window,'new')+'_seed')/(STEM+'.xml');consumed=[stat(runpath),stat(nativepath),stat(program),stat(R/'bin/windows/DsphConfig.xml'),stat(xml),*[stat(out/'data'/f'Part_{i:04d}.bi4') for i in range(r['saved_frames'])]];argv=[str(program),'-dirin',str(out/'data'),'-filexml',str(xml),'-savevtk',str(target/'PartFluid'),'-onlytype:-all,fluid','-vars:-all,+idp,+mk,+vel,+rhop,+press,+SigmaState_kk,+SigmaState_ij,+Sigma_kk,+Sigma_ij,+Kplastic','-threads:1'];v=dict(passed=False,window=window,solver_invocations=0,physical_acceptance=False)
    try:
        call=invoke(T,tag(window,'new')+'.particles_r1',argv,C);files=sorted(target.glob('PartFluid_*.vtk'));need(len(files)==r['saved_frames'],'Every actual saved frame required');head=files[0].read_bytes();need(b'POINTS 20000 ' in head,'All20,000soil VTK points required');types={}
        for field in ('SigmaState_kk','SigmaState_ij','Sigma_kk','Sigma_ij','Kplastic','Vel','Rhop','Press'):
            at=head.find(field.encode());need(at>=0,'Requested VTK field missing: '+field);types[field]=head[at:head.find(b'\n',at)].decode('ascii',errors='replace')
        need(all(stat(e['path'])==e for e in consumed),'PartVTK modified a consumed input');text='# New a05 granular collapse particles\n\n'+str(END[window])+' s '+window+' run, original dp=.001 and20,000soil. All '+str(len(files))+' actual saved frames exported once by official PartVTK. This is '+('not the full1s result' if window=='short' else 'the complete1s result')+'. Pos is native float32; stress/field declarations below are actual. Offdiagonal order xy,yz,xz. `Press` is dry WCSPH EOS pressure, NOT pore-water pressure. Original BI4/native data unchanged; no new solver or interpolation.\n\n```text\n'+'\n'.join(types.values())+'\n```\n'
        with (target/'README.md').open('x',encoding='utf-8') as f:f.write(text)
        v.update(passed=True,actual_call=call,frames=len(files),soil_points_per_frame=SOIL,VTK_field_declarations=types,consumed=consumed,consumed_stats_unchanged=True,files=[stat(p) for p in files],README=stat(target/'README.md'))
    except Exception as e:v['first_failure']=str(e)
    save(cp,v);print(json.dumps({k:x for k,x in v.items() if k not in ('files','consumed','actual_call')},indent=2));need(v['passed'],'PartVTK failed; preserve first evidence')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','native','review','particles']);p.add_argument('window',nargs='?',choices=['short','full']);p.add_argument('mode',nargs='?',choices=['old','new']);a=p.parse_args()
    if a.action=='prepare':need(a.window is None and a.mode is None,'Use prepare only');prepare()
    elif a.action in ('run','native'):need(a.window is not None and a.mode is not None,'Use ACTION WINDOW MODE');(run if a.action=='run' else native)(a.window,a.mode)
    else:need(a.window is not None and a.mode is None,'Use ACTION WINDOW');(review if a.action=='review' else particles)(a.window)
