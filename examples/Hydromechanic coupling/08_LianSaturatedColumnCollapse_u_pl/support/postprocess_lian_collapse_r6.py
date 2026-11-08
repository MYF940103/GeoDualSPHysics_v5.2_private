"""C08 r6 psi0 full diagnostic: one native decode, separate300-frame VTK and raw-state figures."""
import argparse,csv,ctypes,json,re,struct,subprocess,sys,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
C=Path(__file__).resolve().parents[1];RUNTIME=C/'support/runtime_r6'
GROUPS={'psi0':(5000.,0.,0.)};BED=(1800,1852,1904,1956,2008);POLICY='FixedPlaneStageProjectionReleaseOnly'
NATIVE_STAGE='upl_c08_n3_formal_native_r1';FRAMES=300;GLOBAL_END=5200000
VARS='-vars:-all,+idp,+mk,+vel,+rhop,+PorePress,+PorePress0,+ExcessPorePress,+SigmaState_kk,+SigmaState_ij,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PoroVolumeRatio,+PoroPorosity,+PoroThetaLastStage,+PoroCurrentVolume,+PoroMixtureDensity,+PoroHydraulicConductivity,+PosDiv,+HydroMechLoadAce'
def need(ok,text):
    if not ok:raise RuntimeError(text)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v,replace=False):
    with Path(p).open('w' if replace else 'x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def verify(rows):
    for e in rows:need(stat(e['path'])==e,'Source/tool/output changed: '+e['path'])
def summary(path):
    # Same strict AS parser as the verified bounded owner: only its one Configuration semicolon is repairable.
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines();need(len(lines)==2,'Exactly one Run.csv header and data row required');match=re.match(r'^#?RunName([;,])',lines[0]);need(match,'Unsupported Run.csv header');sep=match[1]
    keys=(lines[0][1:] if lines[0].startswith('#') else lines[0]).split(sep);values=lines[1].split(sep);need(len(set(keys))==len(keys) and all(keys) and keys.count('Configuration')==1,'Unique nonempty keys and one Configuration required');index=keys.index('Configuration');extra=len(values)-len(keys)
    if extra==1 and sep==';':values=values[:index]+[values[index]+';'+values[index+1]]+values[index+2:]
    else:need(extra==0,'Only the known one embedded AS Configuration semicolon is repairable')
    need(len(values)==len(keys),'Run.csv reconstructed width differs');configuration=values[index];number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?';matches=list(re.finditer(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',configuration))
    need(len(matches)==1 and configuration.count(';')==1 and configuration.count('AS_Bui2008')==1,'Unique complete AS_Bui2008 token required')
    need(all(struct.pack('<f',float(matches[0][j+1]))==struct.pack('<f',v) for j,v in enumerate((.2,3.0))),'Actual AS coefficient/exponent differs from0.2f/3.0f')
    return dict(zip(keys,values)) # No other field is normalized or rewritten.
def check_tools():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    for name in ('C08Native_win64.exe','PartVTK_win64.exe'):need((RUNTIME/name).is_file(),'Missing runtime_r6/'+name)
    return dict(numpy=np.__version__,matplotlib=matplotlib.__version__,tools=[stat(RUNTIME/n) for n in ('C08Native_win64.exe','PartVTK_win64.exe')],auto_install=False)
def invoke(label,exe,args,inputs,logs,complete):
    call=logs/(label+'.call.json');log=logs/(label+'.log');argv=[str(exe),*map(str,args)]
    if call.exists():
        r=read(call);need(r['passed'] and r['inputs']==inputs and r['argv']==argv,'Existing failed/different postprocessing call; inspect it, do not rerun blindly');verify(r['inputs']);verify(r['outputs']);complete();print('REUSE',label,flush=True);return r
    need(not log.exists(),'Partial postprocessing log protected');verify(inputs);start=time.monotonic();rc=wx=None;failure=None;outputs=[]
    try:
        with log.open('xb') as f:
            p=subprocess.Popen(argv,cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try:rc=p.wait()
            finally:
                rc=p.wait();k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];code=w.DWORD();need(k.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Post-tool actual Win32 exit unavailable');wx=code.value
        need(rc==wx==0,'Post-tool failed; preserve partial output and inspect '+str(log));outputs=complete();verify(inputs)
    except Exception as e:failure=str(e)
    result=dict(passed=failure is None,argv=argv,inputs=inputs,outputs=outputs,actual_exit=rc,actual_Popen_wait_exit=rc,actual_Win32_exit=wx,typed_returncode_captured_before_postchecks=(rc is not None and wx is not None),elapsed_s=time.monotonic()-start,first_failure=failure,log=stat(log),solver_invocations=0,SHA_scans=0)
    save(call,result);need(result['passed'],failure);return result

def validate_input(group,out,pre):
    need(group=='psi0','Only the psi0 r6 diagnostic is admitted; other materials/preload use their retained workflows')
    r=summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');need('Finished execution (code=0).' in text,'Solver not completed normally')
    steps=int(r['Steps']);need(steps==GLOBAL_END and int(r['PartFiles'])==FRAMES,'Only normal full3s/global5.2M/300 actual states are admitted')
    need(int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Original registry/no-exclusion checks failed')
    xml=out/(r['RunName']+'.xml');root=ET.parse(xml).getroot();soil=root.find('execution/special/soils');hydro=root.find('execution/special/hydromechanics');event=root.find('execution/special/gravitypreload');p={e.get('key'):e.get('value') for e in root.findall('execution/parameters/parameter')}
    def value(parent,key):
        nodes=parent.findall(key);need(len(nodes)==1,'Missing/duplicate input field '+key);return float(nodes[0].get('value'))
    for key,v in dict(DtFixed=.0000025,DtIni=.0000025,DtMin=1e-8,TimeMax=13,TimeOut=.01,NoPenetration=1,ArtificialStress=1,ArtificialStressCoef=.2,ArtificialStressExp=3.0,Kernel=1,DPCtes=3,SavePosDouble=1,PartsOutMax=0,SoilStressRateGradCorr=1).items():need(key in p and float(p[key])==v,'Actual r6 parameter differs: '+key)
    for key,v in dict(HydroMech=1,HydroMechDynamicSeepage=1,HydroMechConductivityModel=1,HydroMechConductivityCk=2,HydroMechFreeSeepage=1,HydroMechDrainage=0,PoreCompressionGradCorr=1,PoreWaterRho=1000,PoreWaterBulkModulus=1e9,Porosity=.35,HydraulicConductivity=.0002).items():need(value(hydro,key)==v,'Actual hydromechanics differs: '+key)
    cp,psi,sf=GROUPS[group]
    for key,v in dict(phi=25,phi_r=25,n_phi=0,coh=cp,coh_r=1000,n_coh=5,dlt=psi,DilationDecay=sf).items():need(value(soil,key)==v,'Actual group material differs: '+key)
    need(event is not None and event.get('keep_bed_overlap')=='true' and event.get('elastic_source','false').lower() in ('false','0'),'Explicit receiving KeepBedOverlap event required')
    source=Path(event.get('statefile',''));source=source if source.is_absolute() else xml.parent/source;need(source.samefile(pre) and float(event.get('time'))==10 and int(event.get('release_mkbound'))==2,'Actual PRE/event binding differs')
    need('Dynamic NoPen: '+POLICY in text and text.count('GravityPreload: phase=released ')==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual fixed-plane/single release policy differs')
    need('GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids=1800,1852,1904,1956,2008;' in text,'Actual retained bed identity/roles differ')
    parts=sorted((out/'data').glob('Part_*.bi4'));need([x.name for x in parts]==['Part_%04d.bi4'%i for i in range(int(r['PartFiles']))],'Saved native sequence incomplete')
    return r,xml,[stat(out/'Run.csv'),stat(out/'Run.out'),stat(xml),stat(out/'data/Part_Head.ibi4'),*[stat(p) for p in parts]]
def native(group,backend,out,pre,steps,inputs,logs):
    dest=out/'native';completion=dest/'completion.json';exe=RUNTIME/'C08Native_win64.exe'
    def done():
        d=read(completion);need(d['passed'] and d['group']==group and d['samples']==FRAMES and d['completed_steps']==steps==GLOBAL_END and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['actual_native_IDs_per_frame']==6805 and d['backend_argument']==backend and not d['backend_proven_by_reader'] and d['stage']==NATIVE_STAGE and d['DynamicNoPenetrationPolicy']==POLICY and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and not d['reaction_J_Darcy_closed'] and not d['same_operator_PRE_contract_claimed'] and d['completed_runtime_Run_csv_checked'],'Native completion/window/schema/NoPen policy failed')
        need(d['original_ID_domain']==7060 and d['soil_IDs']==5000 and d['source_material_law_version'] in (1,2) and d['target_material_law_version']==2 and d['release_target_ID_begin']==1800 and d['release_target_ID_count']==260 and d['actual_retired_count']==255 and not d['actual_retired_IDs_contiguous'] and d['kept_bed_IDs']==list(BED) and d['kept_bed_count']==5 and d['actual_fixed_IDs']==1805 and d['kept_bed_source_geometry_checks']==5,'Actual6805/1805/5000 noncontiguous retirement differs')
        counts=dict(ledger_checks=1500000,fixed_marker_checks=541500,P0_bits_checks=2041500,rho_cache_bits_checks=1500000,kappa_nondecreasing_from_PRE_checks=1500000,nonempty_signed_intervals=300,plane_gap_checks=3000000)
        need(all(d[k]==v for k,v in counts.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['min_soil_x_m']>=-4e-8 and d['min_soil_z_m']>=-4e-8,'Original full native safety/coverage gates failed')
        need(d['saved_steps_checked_against_formal_profile'] and d['formal_save_cadence_steps']==4000 and d['formal_saved_samples']==300 and d['formal_material_groups_admitted']==['psi0'] and d['full_3s_diagnostic_only'],'Original explicit formal save profile differs')
        m=read(dest/'bedkeep_metadata.json');need(m['passed'] and m['stage']==NATIVE_STAGE+'.metadata' and m['keep_bed_overlap'] and m['original_target_count']==260 and m['actual_retired_count']==255 and m['kept_bed_IDs']==list(BED) and m['kept_bed_count']==5 and m['samples']==m['keep_policy_headers']==m['metadata_header_scans']==m['AS_active_true_headers']==300 and m['completed_steps']==GLOBAL_END and m['expected_AS'] and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==struct.unpack('<f',struct.pack('<f',.2))[0] and m['AS_exponent_float_reference']==struct.unpack('<f',struct.pack('<f',3.0))[0] and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and not m['core_original_numerical_budgets_changed'],'Typed KeepBedOverlap/AS per-header metadata differs')
        need(m['expected_ponding_policy']=='CompletedOnly' and m['ponding_policy_keys_absent_headers']==FRAMES,'All300 headers must retain legacy CompletedOnly: both ponding-policy keys absent')
        return [stat(p) for p in sorted(dest.iterdir()) if p.is_file()]
    need(not dest.exists() or (logs/'native.call.json').exists(),'Unbound/partial native output protected')
    invoke('native',exe,['--read',group,backend,out/'data',pre,steps,dest],inputs+[stat(pre),stat(pre.parent/'Part_Head.ibi4'),stat(exe)],logs,done)
    return dest

def vtk(out,group,count,xml,inputs,logs):
    dest=out/'particles';dest.mkdir(exist_ok=True);exe=RUNTIME/'PartVTK_win64.exe'
    for label,kind,npoints in [('PartFluid','fluid',5000),('PartBound','fixed',1805)]:
        def done():
            files=sorted(dest.glob(label+'_*.vtk'));need([p.name for p in files]==[label+'_%04d.vtk'%i for i in range(count)],'Incomplete '+label+' series')
            for p in files:
                with p.open('rb') as f:h=f.read(2048)
                m=re.search(rb'\bPOINTS\s+(\d+)\s+',h);need(m and int(m[1])==npoints,'VTK point count/type differs: '+p.name)
            return [stat(p) for p in files]
        need(not list(dest.glob(label+'*')) or (logs/(label+'.call.json')).exists(),'Existing unbound/partial '+label+' protected')
        invoke(label,exe,['-dirin',out/'data','-filexml',xml,'-savevtk',dest/label,'-onlytype:-all,'+kind,VARS,'-threads:1'],inputs+[stat(exe)],logs,done)

def bundle(folder):
    import numpy as np
    d=read(folder/'completion.json');need(d['passed'] and d['actual_native_IDs_per_frame']==6805 and d['samples']==300 and d['typed_arrays']==22,'Only the admitted6805/300/22 payload is plotted');layout=list(csv.DictReader((folder/'typed22_layout.csv').open(encoding='utf-8')));n=6805;samples=300;types={'uint32':'<u4','float32':'<f4','float64':'<f8'};fields=[('time','<f8')]
    schema=(('Idp','uint32',1),('Posd','float64',3),('Vel','float32',3),('Sigma_kk','float32',3),('Sigma_ij','float32',3),('FSNormal','float32',3),('HydroMechLoadAce','float32',3),('native_Rhop','float32',1),('Kplastic','float32',1),('PorePress','float32',1),('PorePress0','float32',1),('ExcessPorePress','float32',1),('SigmaState_kk','float64',3),('SigmaState_ij','float64',3),('FSType','uint32',1),('PoroVolumeRatio','float64',1),('PoroPorosity','float64',1),('PoroThetaLastStage','float64',1),('PoroCurrentVolume','float64',1),('PoroMixtureDensity','float64',1),('PoroHydraulicConductivity','float64',1),('PosDiv','float32',1))
    need(len(layout)==len(schema)==22,'Exactly22 original layout fields required')
    for row,(name,kind,comp) in zip(layout,schema):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,comp,np.dtype(types[kind]).itemsize*comp),'Original typed22 schema differs');fields.append((name,types[kind],(n,) if comp==1 else (n,comp)))
    dtype=np.dtype(fields,align=False);head=np.fromfile(folder/'typed22.bin',dtype='<u4',count=3);need(np.array_equal(head,[n,22,samples]) and (folder/'typed22.bin').stat().st_size==12+samples*dtype.itemsize,'Typed22 payload size/layout differs')
    need(dtype.itemsize==8+n*212,'Original record byte stride differs');a=np.memmap(folder/'typed22.bin',dtype=dtype,mode='r',offset=12,shape=(samples,));ids=a[0]['Idp'];expected=np.sort(np.r_[np.arange(1800),BED,np.arange(2060,7060)]);soil=ids>=2060;need(np.array_equal(ids,expected) and soil.sum()==5000 and np.all(a['Idp']==ids),'Original noncontiguous fixed/soil material IDs differ')
    h=np.atleast_1d(np.genfromtxt(folder/'history.csv',delimiter=',',names=True));need(len(h)==samples and np.array_equal(h['time_s'],a['time']),'History/raw actual clocks differ')
    extra={'front_x_m':a['Posd'][:,soil,0].max(axis=1),'maximum_height_m':a['Posd'][:,soil,2].max(axis=1),'mean_material_settlement_from_PRE_mm':-1000*h['mean_dz_from_PRE_m'],'mean_kappa':a['Kplastic'][:,soil].mean(axis=1,dtype=np.float64),'mean_n':a['PoroPorosity'][:,soil].mean(axis=1),'mean_k_m_s':a['PoroHydraulicConductivity'][:,soil].mean(axis=1)}
    names=list(h.dtype.names)+list(extra);rows=np.column_stack([h[k] for k in h.dtype.names]+list(extra.values()));return d,a,soil,names,rows

def history_plot(fig,names,rows,label):
    import numpy as np
    import matplotlib.pyplot as plt
    q={k:rows[:,i] for i,k in enumerate(names)};tau=q['tau_s'];f,axs=plt.subplots(3,3,figsize=(14,10),constrained_layout=True)
    panels=[('Total pore pressure / native excess [kPa]',['p_mean_Pa','p_min_Pa','p_max_Pa','native_excess_mean_Pa'],.001),('PRE material movement [mm]',['mean_material_settlement_from_PRE_mm','displacement_RMS_from_PRE_mm','max_displacement_from_PRE_mm'],1),('Absolute geometry [m]',['front_x_m','maximum_height_m'],1),('Plastic strain history',['mean_kappa','max_kappa'],1),('Porosity',['min_n','mean_n','max_n'],1),('Conductivity [m/s]',['min_k_m_s','mean_k_m_s','max_k_m_s'],1),('Speed [m/s]',['velocity_RMS_m_s','max_speed_m_s'],1),('Total stress Frobenius RMS [kPa]',['total_stress_Frobenius_RMS_Pa'],.001),('Volume ratio J',['min_J','max_J'],1)]
    for ax,(title,keys,scale) in zip(axs.flat,panels):
        for key in keys:ax.plot(tau,q[key]*scale,label=key)
        ax.set(title=title,xlabel='Actual time since release [s]');ax.grid(alpha=.25);ax.legend(fontsize=7)
    f.suptitle(label+' r6 diagnostic; true PRE reference, no inserted t=0');f.savefig(fig/'history.png',dpi=180);plt.close(f);np.savetxt(fig/'history.csv',rows,delimiter=',',header=','.join(names),comments='',fmt='%.17g')

def field_plot(path,sets,limits=None):
    import numpy as np
    import matplotlib.pyplot as plt
    fields=['PorePress','ExcessPorePress','Kplastic','PoroPorosity','PoroHydraulicConductivity'];f,axs=plt.subplots(len(sets),len(fields),figsize=(18.5,4*len(sets)),squeeze=False,constrained_layout=True);csvrows=[]
    if limits is None:limits={key:(min(float(s[2][key].min()) for s in sets),max(float(s[2][key].max()) for s in sets)) for key in fields}
    xmin=min(float(s[2]['Posd'][:,0].min()) for s in sets);xmax=max(float(s[2]['Posd'][:,0].max()) for s in sets);zmin=min(float(s[2]['Posd'][:,2].min()) for s in sets);zmax=max(float(s[2]['Posd'][:,2].max()) for s in sets)
    for line,(label,tau,rec,ids) in enumerate(sets):
        x,z=rec['Posd'][:,0],rec['Posd'][:,2]
        for col,key in enumerate(fields):
            ax=axs[line,col];lo,hi=limits[key]
            if lo==hi:ax.scatter(x,z,s=4,color='tab:blue',linewidths=0);ax.set_title(key+' constant='+format(lo,'.7g'))
            else:im=ax.scatter(x,z,c=rec[key],s=4,cmap='viridis',vmin=lo,vmax=hi,linewidths=0);f.colorbar(im,ax=ax);ax.set_title(key)
            ax.set(xlabel='x [m]',ylabel='z [m]',xlim=(xmin,xmax),ylim=(zmin,zmax));ax.set_aspect('equal',adjustable='box')
        axs[line,0].set_ylabel(label+' actual tau='+format(tau,'.9g')+' s\nz [m]')
        csvrows.extend((label,tau,int(i),xx,zz,p,e,k,n,h) for i,xx,zz,p,e,k,n,h in zip(ids,x,z,rec['PorePress'],rec['ExcessPorePress'],rec['Kplastic'],rec['PoroPorosity'],rec['PoroHydraulicConductivity']))
    f.suptitle('Total pore pressure and native excess p - fixed material P0 are separate raw fields\nPaper-times panels match saved times only; native excess is not a unique paper reference, inferred current hydrostatic field or pure plastic component',fontsize=10)
    f.savefig(path.parent/(path.name+'.png'),dpi=180);plt.close(f)
    with (path.parent/(path.name+'.csv')).open('w',encoding='utf-8',newline='') as o:wri=csv.writer(o);wri.writerow(['group','actual_tau_s','native_id','x_m','z_m','PorePress_Pa','NativeExcessPorePress_Pa','Kplastic','Porosity','HydraulicConductivity_m_s']);wri.writerows(csvrows)

def plots(group,folder,fig):
    import numpy as np
    d,a,soil,names,rows=bundle(folder);fig.mkdir(parents=True,exist_ok=True);history_plot(fig,names,rows,group);tau=a['time']-d['source_actual_time_s'];fields=['PorePress','ExcessPorePress','Kplastic','PoroPorosity','PoroHydraulicConductivity'];limits={k:(float(a[k][:,soil].min()),float(a[k][:,soil].max())) for k in fields};ids=a[0]['Idp'][soil]
    paper=[]
    # Existing visually checked Fig14 time record: psi0 tau=.3,.6,1.2; no paper image is resampled.
    for requested in (.1,.3,.5,.6,1.,1.2,2.,3.):
        j=int(np.argmin(abs(tau-requested)))
        if abs(tau[j]-requested)>.0050000001:continue
        rec={key:a[j][key][soil] for key in ['Posd',*fields]};field_plot(fig/('fields_tau_'+format(requested,'.1f')),[(group,float(tau[j]),rec,ids)],limits)
        if requested in (.3,.6,1.2):paper.append((group,float(tau[j]),rec,ids))
    need(len(paper)==3,'All three psi0 paper-comparison saved states must exist');field_plot(fig/'paper_times_psi0_fields',paper,limits)
    return d

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check-tools',action='store_true');ap.add_argument('--group',choices=tuple(GROUPS));ap.add_argument('--outdir',type=Path);ap.add_argument('--source-pre',type=Path);ap.add_argument('--figdir',type=Path);args=ap.parse_args()
    if args.check_tools:print(json.dumps(dict(passed=True,**check_tools())));return 0
    need(args.group=='psi0' and args.outdir and args.source_pre,'Only --group psi0 --outdir OUT --source-pre PRE is admitted');out=args.outdir.resolve();pre=args.source_pre.resolve();solver_completed=False
    try:
        need(out.is_dir(),'Missing existing solver output; postprocessing never launches it');solver_completed=(out/'Run.out').is_file() and 'Finished execution (code=0).' in (out/'Run.out').read_text(encoding='utf-8-sig');tools=check_tools()
        r,xml,inputs=validate_input(args.group,out,pre);hardware=r['Hardware'];backend='CPU' if hardware=='CPU' else 'GPU' if re.match(r'^Gpu_[0-9]+=',hardware,re.I) else None;need(backend,'Unknown actual Hardware backend: '+hardware);logs=out/'logs';logs.mkdir(exist_ok=True)
        folder=native(args.group,backend,out,pre,int(r['Steps']),inputs,logs);vtk(out,args.group,FRAMES,xml,inputs,logs)
        fig=args.figdir.resolve() if args.figdir else C/('figures/collapse_psi0_r6' if backend=='GPU' else 'figures/collapse_psi0_CPU_r6');manifest=fig/'figures_r6.json';source=dict(group='psi0',backend=backend,output=str(out),native_payload=stat(folder/'typed22.bin'),native_completion=stat(folder/'completion.json'),bedkeep_metadata=stat(folder/'bedkeep_metadata.json'),NoPen_policy=POLICY,KeepBedOverlap=True,kept_bed_IDs=list(BED),actual_retired_count=255,AS_policy='ReleaseOnly',AS_coefficient_float=struct.unpack('<f',struct.pack('<f',.2))[0],AS_exponent_float=struct.unpack('<f',struct.pack('<f',3.0))[0],free_seepage_ponding_policy='CompletedOnly',ponding_policy_keys_absent=True,NoPen_reaction_J_Darcy_closed=False,same_operator_PRE_contract_claimed=False)
        if manifest.exists():
            m=read(manifest);need(m['passed'] and m['source']==source,'Existing figure manifest belongs to different data');verify(m['files']);print('REUSE figures',fig,flush=True)
        else:
            need(not fig.exists() or not any(fig.iterdir()),'Existing partial/different figures protected; choose a fresh --figdir, never rerun the solver');fig.mkdir(parents=True,exist_ok=True);save(fig/'source.json',source);plots(args.group,folder,fig);save(manifest,dict(passed=True,source=source,files=[stat(p) for p in sorted(fig.iterdir()) if p.is_file()],all300_raw_field_color_ranges=True,paper_comparison_requested_tau_s=[.3,.6,1.2],physical_acceptance=False))
        verify(inputs);final=out/'postprocess_r6.json';result=dict(passed=True,group='psi0',solver_completed=solver_completed,postprocess_completed=True,NoPen_policy=POLICY,NoPen_active=True,NoPen_reaction_J_Darcy_closed=False,same_operator_PRE_contract_claimed=False,KeepBedOverlap=True,actual_native_IDs=6805,actual_fixed_IDs=1805,soil_IDs=5000,release_target_count=260,actual_retired_count=255,kept_bed_IDs=list(BED),AS_policy='ReleaseOnly',AS_coefficient=.2,AS_exponent=3.0,free_seepage_ponding_policy='CompletedOnly',ponding_policy_keys_absent_headers=FRAMES,backend_from_Run_csv=backend,actual_Hardware=hardware,global_steps=GLOBAL_END,saved_frames=FRAMES,native_completed=True,native_completion=stat(folder/'completion.json'),bedkeep_metadata=stat(folder/'bedkeep_metadata.json'),native_call=stat(logs/'native.call.json'),figure_directory=str(fig),figure_files=[stat(p) for p in sorted(fig.iterdir()) if p.is_file()],VTK_calls=[stat(logs/(x+'.call.json')) for x in ('PartFluid','PartBound')],PartFluid=True,PartBound=True,PartFluid_frames=300,PartBound_frames=300,script=stat(__file__),tools=tools,source_pre=stat(pre),inputs=inputs,physical_acceptance=False,raw_BI4_rewritten=False,solver_invocations=0)
        if final.exists():
            previous=read(final);need(previous['passed'] and previous['native_completion']==result['native_completion'] and previous['figure_directory']==str(fig),'Existing final post receipt differs; preserve it');verify(previous['figure_files'])
        else:save(final,result)
        print('POSTPROCESS_COMPLETED',out,flush=True);return 0
    except Exception as error:
        failure=out/'postprocess_r6.failed.json'
        if out.is_dir() and not failure.exists():save(failure,dict(passed=False,group='psi0',solver_completed=solver_completed,postprocess_completed=False,first_failure=str(error),solver_invocations=0,raw_BI4_rewritten=False,source_pre=str(pre),script=stat(__file__),physical_acceptance=False))
        raise
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:print('POSTPROCESS_FAILED:',e,file=sys.stderr);raise SystemExit(1)
