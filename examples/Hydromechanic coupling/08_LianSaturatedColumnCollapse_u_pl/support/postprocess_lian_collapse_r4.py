"""Read-only C08 native validation, separate PartFluid/PartBound VTK, figures and matching CSVs."""
import argparse,csv,ctypes,json,re,subprocess,sys,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
C=Path(__file__).resolve().parents[1];RUNTIME=C/'support/runtime_r4'
GROUPS={'psi0':(5000.,0.,0.),'psi2p5':(5000.,2.5,.2),'psim5':(7500.,-5.,.2)}
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
    text=Path(path).read_text(encoding='utf-8-sig');first=text.splitlines()[0];need(re.match(r'^#?RunName[;,]',first),'Unsupported Run.csv header')
    rows=list(csv.DictReader((text[1:] if text.startswith('#') else text).splitlines(),delimiter=';' if ';' in first else ','));need(len(rows)==1,'One completed Run.csv row required');return rows[0]
def check_tools():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    for name in ('C08Native_win64.exe','PartVTK_win64.exe'):need((RUNTIME/name).is_file(),'Missing runtime_r4/'+name)
    return dict(numpy=np.__version__,matplotlib=matplotlib.__version__,tools=[stat(RUNTIME/n) for n in ('C08Native_win64.exe','PartVTK_win64.exe')],auto_install=False)
def invoke(label,exe,args,inputs,logs,complete):
    call=logs/(label+'.call.json');log=logs/(label+'.log');argv=[str(exe),*map(str,args)]
    if call.exists():
        r=read(call);need(r['passed'] and r['inputs']==inputs and r['argv']==argv,'Existing failed/different postprocessing call; inspect it, do not rerun blindly');verify(r['inputs']);verify(r['outputs']);complete();print('REUSE',label,flush=True);return r
    need(not log.exists(),'Partial postprocessing log protected');verify(inputs);start=time.monotonic();rc=wx=None;failure=None;outputs=[]
    try:
        with log.open('xb') as f:
            p=subprocess.Popen(argv,cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            rc=p.wait();k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];code=w.DWORD();need(k.GetExitCodeProcess(int(p._handle),ctypes.byref(code)),'Post-tool actual Win32 exit unavailable');wx=code.value
        need(rc==wx==0,'Post-tool failed; preserve partial output and inspect '+str(log));outputs=complete();verify(inputs)
    except Exception as e:failure=str(e)
    result=dict(passed=failure is None,argv=argv,inputs=inputs,outputs=outputs,actual_exit=rc,actual_Win32_exit=wx,elapsed_s=time.monotonic()-start,first_failure=failure,log=stat(log),solver_invocations=0,SHA_scans=0)
    save(call,result);need(result['passed'],failure);return result

def validate_input(group,out,pre):
    r=summary(out/'Run.csv');need('Finished execution (code=0).' in (out/'Run.out').read_text(encoding='utf-8-sig'),'Solver not completed normally')
    steps=int(r['Steps']);need(steps in ((4000000,) if group=='preload' else (4040000,4060000,5200000)),'Unexpected actual global endpoint')
    need(int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Original registry/no-exclusion checks failed')
    xml=out/(r['RunName']+'.xml');root=ET.parse(xml).getroot();soil=root.find('execution/special/soils');hydro=root.find('execution/special/hydromechanics');event=root.find('execution/special/gravitypreload');p={e.get('key'):e.get('value') for e in root.findall('execution/parameters/parameter')}
    def value(parent,key):
        nodes=parent.findall(key);need(len(nodes)==1,'Missing/duplicate input field '+key);return float(nodes[0].get('value'))
    need(float(p['DtFixed'])==.0000025 and float(p['TimeOut'])==.01 and value(hydro,'HydroMechConductivityModel')==1 and value(hydro,'HydroMechConductivityCk')==2,'Actual clock/conductivity input differs')
    if group!='preload':
        need('NoPenetration' in p and float(p['NoPenetration'])==1,'Actual collapse XML must explicitly select NoPenetration1')
        policy='Dynamic NoPen: LegacyOperatorSplitReleaseOnly; elastic PRE uses NoPen off, collapse uses the existing corrector velocity/displacement projection; same-stage Darcy reaction is not included.'
        need(policy in (out/'Run.out').read_text(encoding='utf-8-sig'),'Actual solver did not log the formal NoPen policy')
        cp,psi,sf=GROUPS[group]
        for key,v in dict(phi=25,phi_r=25,n_phi=0,coh=cp,coh_r=1000,n_coh=5,dlt=psi,DilationDecay=sf).items():need(value(soil,key)==v,'Actual group material differs: '+key)
        source=Path(event.get('statefile',''));source=source if source.is_absolute() else xml.parent/source;need(source.samefile(pre) and float(event.get('time'))==10 and int(event.get('release_mkbound'))==2,'Actual PRE/event binding differs')
    parts=sorted((out/'data').glob('Part_*.bi4'));need([x.name for x in parts]==['Part_%04d.bi4'%i for i in range(int(r['PartFiles']))],'Saved native sequence incomplete')
    return r,xml,[stat(out/'Run.csv'),stat(out/'Run.out'),stat(xml),stat(out/'data/Part_Head.ibi4'),*[stat(p) for p in parts]]
def native(group,backend,out,pre,steps,inputs,logs):
    dest=out/'native';completion=dest/'completion.json';exe=RUNTIME/'C08Native_win64.exe'
    def done():
        d=read(completion);need(d['passed'] and d['group']==group and d['completed_steps']==steps and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6800 and d['backend_argument']==backend and not d['backend_proven_by_reader'] and d['stage']=='c08_post_native_r4' and d['DynamicNoPenetrationPolicy']=='LegacyOperatorSplitReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and not d['reaction_J_Darcy_closed'] and not d['same_operator_PRE_contract_claimed'],'Native completion/window/schema/NoPen policy failed')
        return [stat(p) for p in sorted(dest.iterdir()) if p.is_file()]
    need(not dest.exists() or (logs/'native.call.json').exists(),'Unbound/partial native output protected')
    invoke('native',exe,['--read',group,backend,out/'data',pre,steps,dest],inputs+[stat(pre),stat(exe)],logs,done)
    return dest

def vtk(out,group,count,xml,inputs,logs):
    dest=out/'particles';dest.mkdir(exist_ok=True);exe=RUNTIME/'PartVTK_win64.exe'
    for label,kind,npoints in [('PartFluid','fluid',5000),('PartBound','fixed',2060 if group=='preload' else 1800)]:
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
    d=read(folder/'completion.json');need(d['passed'],'Native result not admitted');layout=list(csv.DictReader((folder/'typed22_layout.csv').open(encoding='utf-8')));n=d['actual_native_IDs_per_frame'];samples=d['samples'];types={'uint32':'<u4','float32':'<f4','float64':'<f8'};fields=[('time','<f8')]
    for row in layout:
        comp=int(row['components']);fields.append((row['array'],types[row['type']],(n,) if comp==1 else (n,comp)))
    dtype=np.dtype(fields,align=False);head=np.fromfile(folder/'typed22.bin',dtype='<u4',count=3);need(np.array_equal(head,[n,22,samples]) and (folder/'typed22.bin').stat().st_size==12+samples*dtype.itemsize,'Typed22 payload size/layout differs')
    a=np.memmap(folder/'typed22.bin',dtype=dtype,mode='r',offset=12,shape=(samples,));ids=a[0]['Idp'];soil=ids>=2060;need(soil.sum()==5000 and np.all(a['Idp']==ids),'Native material identity/order differs')
    h=np.atleast_1d(np.genfromtxt(folder/'history.csv',delimiter=',',names=True));need(len(h)==samples and np.array_equal(h['time_s'],a['time']),'History/raw actual clocks differ')
    extra={'front_x_m':a['Posd'][:,soil,0].max(axis=1),'maximum_height_m':a['Posd'][:,soil,2].max(axis=1),'mean_kappa':a['Kplastic'][:,soil].mean(axis=1,dtype=np.float64),'mean_n':a['PoroPorosity'][:,soil].mean(axis=1),'mean_k_m_s':a['PoroHydraulicConductivity'][:,soil].mean(axis=1)}
    names=list(h.dtype.names)+list(extra);rows=np.column_stack([h[k] for k in h.dtype.names]+list(extra.values()));return d,a,soil,names,rows

def history_plot(fig,names,rows,label):
    import numpy as np
    import matplotlib.pyplot as plt
    q={k:rows[:,i] for i,k in enumerate(names)};tau=q['tau_s'];f,axs=plt.subplots(3,3,figsize=(14,10),constrained_layout=True)
    panels=[('Pore pressure [kPa]',['p_mean_Pa','p_min_Pa','p_max_Pa'],.001),('PRE displacement [mm]',['mean_dz_from_PRE_m','displacement_RMS_from_PRE_mm','max_displacement_from_PRE_mm'],None),('Absolute geometry [m]',['front_x_m','maximum_height_m'],1),('Plastic strain history',['mean_kappa','max_kappa'],1),('Porosity',['min_n','mean_n','max_n'],1),('Conductivity [m/s]',['min_k_m_s','mean_k_m_s','max_k_m_s'],1),('Speed [m/s]',['velocity_RMS_m_s','max_speed_m_s'],1),('Total stress Frobenius RMS [kPa]',['total_stress_Frobenius_RMS_Pa'],.001),('Volume ratio J',['min_J','max_J'],1)]
    for ax,(title,keys,scale) in zip(axs.flat,panels):
        for key in keys:ax.plot(tau,q[key]*(1000 if key=='mean_dz_from_PRE_m' else (1 if scale is None else scale)),label=key)
        ax.set(title=title,xlabel='Actual time since release [s]');ax.grid(alpha=.25);ax.legend(fontsize=7)
    f.suptitle(label+'; true PRE reference, no inserted t=0');f.savefig(fig/'history.png',dpi=180);plt.close(f);np.savetxt(fig/'history.csv',rows,delimiter=',',header=','.join(names),comments='',fmt='%.17g')

def field_plot(path,sets,limits=None):
    import numpy as np
    import matplotlib.pyplot as plt
    fields=['PorePress','Kplastic','PoroPorosity','PoroHydraulicConductivity'];f,axs=plt.subplots(len(sets),4,figsize=(15,4*len(sets)),squeeze=False,constrained_layout=True);csvrows=[]
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
        csvrows.extend((label,tau,int(i),xx,zz,p,k,n,h) for i,xx,zz,p,k,n,h in zip(ids,x,z,rec['PorePress'],rec['Kplastic'],rec['PoroPorosity'],rec['PoroHydraulicConductivity']))
    f.savefig(path.parent/(path.name+'.png'),dpi=180);plt.close(f)
    with (path.parent/(path.name+'.csv')).open('w',encoding='utf-8',newline='') as o:wri=csv.writer(o);wri.writerow(['group','actual_tau_s','native_id','x_m','z_m','PorePress_Pa','Kplastic','Porosity','HydraulicConductivity_m_s']);wri.writerows(csvrows)

def plots(group,folder,fig):
    import numpy as np
    d,a,soil,names,rows=bundle(folder);fig.mkdir(parents=True,exist_ok=True);history_plot(fig,names,rows,group);tau=a['time']-d['source_actual_time_s'];fields=['PorePress','Kplastic','PoroPorosity','PoroHydraulicConductivity'];limits={k:(float(a[k][:,soil].min()),float(a[k][:,soil].max())) for k in fields};ids=a[0]['Idp'][soil]
    for requested in (.1,.5,1.,2.,3.):
        j=int(np.argmin(abs(tau-requested)))
        if abs(tau[j]-requested)>.0050000001:continue
        rec={key:a[j][key][soil] for key in ['Posd',*fields]};field_plot(fig/('fields_tau_'+format(requested,'.1f')),[(group,float(tau[j]),rec,ids)],limits)
    return d

def three_groups(backend):
    import numpy as np
    import matplotlib.pyplot as plt
    folders={g:C/('CaseLianSaturatedColumnCollapse_'+g+'_shared_r4_'+backend+'_out') for g in GROUPS}
    if not all((o/'native/completion.json').exists() and (o/'logs/native.call.json').exists() and read(o/'native/completion.json').get('passed') and read(o/'native/completion.json').get('completed_steps')==5200000 for o in folders.values()):print('SKIP three-group comparison: all three full native datasets are not complete.',flush=True);return
    fig=C/('figures/collapse_three_groups_r4' if backend=='GPU' else 'figures/collapse_three_groups_CPU_r4');fig.mkdir(parents=True,exist_ok=True);f,axs=plt.subplots(2,3,figsize=(14,8),constrained_layout=True);allrows=[];sets=[];labels=['p_mean_Pa','mean_dz_from_PRE_m','max_kappa','mean_n','mean_k_m_s','velocity_RMS_m_s']
    shared_pre=set()
    for g,o in folders.items():
        call=read(o/'logs/native.call.json');need(call['passed'],'Prior native tool call failed');verify(call['inputs']);verify(call['outputs']);shared_pre.add(str(Path(call['argv'][5]).resolve()));need(len(shared_pre)==1,'Three-group datasets use different PRE files');d,a,soil,names,rows=bundle(o/'native');q={k:rows[:,i] for i,k in enumerate(names)}
        for ax,key in zip(axs.flat,labels):ax.plot(q['tau_s'],q[key],label=g);ax.set(xlabel='Actual time since release [s]',ylabel=key);ax.grid(alpha=.25);ax.legend()
        allrows.extend([g,*r] for r in rows);rec={k:a[-1][k][soil] for k in ['Posd','PorePress','Kplastic','PoroPorosity','PoroHydraulicConductivity']};sets.append((g,float(a[-1]['time']-d['source_actual_time_s']),rec,a[-1]['Idp'][soil]))
    f.savefig(fig/'history.png',dpi=180);plt.close(f)
    with (fig/'history.csv').open('w',encoding='utf-8',newline='') as o:wri=csv.writer(o);wri.writerow(['group',*names]);wri.writerows(allrows)
    field_plot(fig/'final_fields_common_colors',sets)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check-tools',action='store_true');ap.add_argument('--group',choices=[*GROUPS,'preload']);ap.add_argument('--outdir',type=Path);ap.add_argument('--source-pre',type=Path);ap.add_argument('--figdir',type=Path);args=ap.parse_args();tools=check_tools()
    if args.check_tools:print(json.dumps(dict(passed=True,**tools)));return 0
    need(args.group and args.outdir and args.source_pre,'--group --outdir --source-pre are required');out=args.outdir.resolve();pre=args.source_pre.resolve();r,xml,inputs=validate_input(args.group,out,pre);hardware=r['Hardware'];backend='CPU' if hardware=='CPU' else 'GPU' if re.match(r'^Gpu_[0-9]+=',hardware,re.I) else None;need(backend,'Unknown actual Hardware backend: '+hardware);logs=out/'logs';logs.mkdir(exist_ok=True)
    if args.group!='preload':folder=native(args.group,backend,out,pre,int(r['Steps']),inputs,logs)
    vtk(out,args.group,int(r['PartFiles']),xml,inputs,logs)
    if args.group!='preload':
        fig=args.figdir.resolve() if args.figdir else C/('figures/collapse_'+args.group+('_r4' if backend=='GPU' else '_CPU_r4'));fig.mkdir(parents=True,exist_ok=True);source=dict(backend=backend,output=str(out),native_payload=stat(folder/'typed22.bin'),NoPen_policy='LegacyOperatorSplitReleaseOnly',NoPen_reaction_J_Darcy_closed=False,same_operator_PRE_contract_claimed=False)
        need(not (fig/'source.json').exists() or read(fig/'source.json')==source,'Figure folder belongs to different data/backend; select --figdir without overwriting it');save(fig/'source.json',source,True);d=plots(args.group,folder,fig);three_groups(backend)
    save(out/'postprocess_r4.json',dict(passed=True,group=args.group,NoPen_policy=('LegacyOperatorSplitReleaseOnly' if args.group!='preload' else None),NoPen_active=(args.group!='preload'),NoPen_reaction_J_Darcy_closed=False,same_operator_PRE_contract_claimed=False,backend_from_Run_csv=backend,actual_Hardware=hardware,global_steps=int(r['Steps']),native_completed=args.group!='preload',native_completion=stat(folder/'completion.json') if args.group!='preload' else None,figure_directory=str(fig) if args.group!='preload' else None,figure_files=[stat(p) for p in sorted(fig.iterdir()) if p.is_file()] if args.group!='preload' else [],VTK_calls=[stat(logs/(x+'.call.json')) for x in ('PartFluid','PartBound')],PartFluid=True,PartBound=True,script=stat(__file__),tools=tools,source_pre=stat(pre),physical_acceptance=False,raw_BI4_rewritten=False),True);print('POSTPROCESS_COMPLETED',out,flush=True);return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:print('POSTPROCESS_FAILED:',e,file=sys.stderr);raise SystemExit(1)
