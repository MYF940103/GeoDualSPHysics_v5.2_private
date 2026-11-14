"""Author-only offline pressure-weight attribution; no executable/native calls."""
import argparse,csv,json,math,re,struct,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_joint_eta_shadow_r1'
GATE=L/'c08_h18_joint_darcy_probe_r1.check.json';NOTE=T/'notes'/(TAG+'.md')
RAW=T/'outputs/c08_h18_joint_darcy_probe_r1';LOCAL=T/'outputs'/TAG
FIG=T/'figures';CHECK=L/(TAG+'.check.json')
PARTS=(29,30);FIELDS=('H_hydro_affine','N_normal_quadratic','X_cross_cubic')
ORACLES=('real_wall','analytic_ghost');VARIANTS=('pair_C_eta','pair_C_bare','receiver_C_eta','receiver_C_bare')
COHORTS=('all_soil','legal_flat_bed','interior_no_wall')
U=np.finfo(float).eps*.5;UF=np.finfo(np.float32).eps*.5;SF=float(np.nextafter(np.float32(0),np.float32(1)))
def need(q,s):
    if not q:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):
    with Path(p).open(encoding='utf-8-sig')as f:return json.load(f)
def bind(e):need(stat(e['path'])==e,'Bound file changed: '+e['path']);return e
def same(a,b):return Path(a).resolve()==Path(b).resolve()
def gamma(n):
    a=np.asarray(n,dtype=float)*U;need(np.all((a>=0)&(a<1)),'Invalid operation count');return a/(1-a)
def f32(x):return float(np.float32(x))
def table(p):
    with Path(p).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
def write_csv(p,rr):
    need(rr,'Empty scientific table')
    with p.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,list(rr[0]));w.writeheader();w.writerows(rr)
def entry(q,k,consumed):e=bind(q[k]);consumed.append(e);return e
def member(text,a,b):
    need(text.count(a)==1,'Frozen source start anchor differs');i=text.index(a);return text[i:text.index(b,i)]

def source_constants(consumed):
    gate=read(GATE);need(gate['passed']and gate['consumed_stats_unchanged']and gate['component']and gate['physical_steps']==0,'Passed zero-step joint component required');consumed.append(stat(GATE))
    done=read(entry(gate,'completion',consumed)['path']);call=read(entry(gate,'actual_call',consumed)['path']);build=read(entry(gate,'build',consumed)['path'])
    need(done['passed']and done['manufactured_rows']==60000 and done['wall_rows']==5700 and done['total_original_Darcy_API_calls']==8 and done['actual_rate_float_bit_rows']==30000 and done['analytic_generated_float_rows']==30000,'Actual joint scope differs')
    need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure']is None and build['passed']and build['consumed_stats_unchanged'],'Actual tool/build failed')
    need(same(call['program'],entry(build,'program',consumed)['path'])and build['physical_objects_compiled']==0 and build['actual_link_objects']==87,'Original CPU component identity differs')
    files={Path(e['path']).name:bind(e)for e in gate['files']};need(all(q in files for q in('manufactured.csv','walls.csv','summary.csv','selected_clocks.csv')),'Missing sealed joint tables');consumed.extend(files.values())
    oldrun=L/'c08_h18_as03_n255_r1.run.json';r=read(oldrun);need(r['passed']and r['solver_completed'],'Original seed run must remain complete');consumed.append(stat(oldrun));xml=entry(r,'input_xml',consumed)
    args=call['arguments'];need(args[:6]==['--check','-cpu','-ompthreads:1','-stable','-svres','-mdbc_freeslip:1']and len(args)==8 and same(str(args[6])+'.xml',xml['path'])and same(args[7],RAW),'Actual component seed/CLI differs')
    archive=entry(build,'source_archive',consumed);entry(build,'source',consumed)
    for e in build['generated_includes']:
        if Path(e['path']).name=='setup.inc':consumed.append(bind(e))
    with zipfile.ZipFile(archive['path'])as z:
        sph=z.read('src/source/JSph.cpp').decode('utf-8').replace('\r\n','\n');ker=z.read('src/source/FunSphKernel.h').decode('utf-8').replace('\r\n','\n');defs=z.read('src/source/DualSphDef.h').decode('utf-8')
    for a in('ctes.LoadXmlRun(xml,"case.execution.constants")','KernelH=(float)ctes.GetH()','MassFluid=(float)ctes.GetMassFluid()','RhopZero=(float)ctes.GetRhop0()','const double h=KernelH','KernelSize=float(kh)','KernelSize2=KernelSize*KernelSize','Eta2=float((h*0.1)*(h*0.1))','CSP.kwend         =KWend','CSP.kernelh       =KernelH'):
        need(re.sub(r'\s+','',a)in re.sub(r'\s+','',sph),'Frozen constant initialization changed: '+a)
    fac=member(ker,'inline float GetKernelWendland_Fac(const StKWendlandCte','//==============================================================================',)
    compact=lambda s:re.sub(r'\s+','',s)
    expected='inline float GetKernelWendland_Fac(const StKWendlandCte &kc,float h,float rr2){const float rad=sqrt(rr2);const float qq=rad/h;const float wqq1=1.f-0.5f*qq;return(kc.bwen*qq*wqq1*wqq1*wqq1/rad);}'
    need(compact(fac)==compact(expected)and 'kc.bwen=float(-2.7852/(h*h*h));'in ker and 'return(2.0f);'in ker and '#define ALMOSTZERO 1e-18f'in defs,'Exact 2D Wendland/ALMOSTZERO recipe differs')
    root=ET.parse(xml['path']).getroot();c=root.find('execution/constants');hy=root.find('execution/special/hydromechanics');need(c is not None and hy is not None,'Generated execution constants required')
    get=lambda node,key:float(node.find(key).get('value'))
    need(c.find('data2d').get('value')=='true'and get(c,'data2dposy')==0 and root.find("execution/parameters/parameter[@key='Kernel']").get('value')=='2','Actual 2D/Wendland constants differ')
    h=f32(get(c,'h'));size=f32(2.*h);size2=f32(size*size);eta=f32((h*.1)*(h*.1));mass=f32(get(c,'massfluid'));rho0=f32(get(c,'rhop0'))
    kw=f32(get(hy,'PoreWaterBulkModulus'));rw=f32(get(hy,'PoreWaterRho'));n0=f32(get(hy,'Porosity'));k0=f32(get(hy,'HydraulicConductivity'));ck=get(hy,'HydroMechConductivityCk')
    need(h==f32(.072)and size==f32(.144)and mass==f32(3.316)and rho0==2072.5 and kw==1e9 and rw==1000 and ck==2 and get(hy,'HydroMechConductivityModel')==1 and get(hy,'HydroMechFreeSeepage')==1 and get(hy,'HydroMechDrainage')==0,'Bound C08 material/constants differ')
    # Run text is a current post-pass cross-check, not an invented exit-time seal.
    run=RAW/'Run.out';consumed.append(stat(run));rt=run.read_text('utf-8-sig');need('Kernel="Wendland"'in rt and 'KernelH=0.072000'in rt and 'MassFluid=3.316'in rt and 'RhopZero=2072.5'in rt,'Actual component configuration text differs')
    return files,dict(h=h,size2=size2,eta2=eta,bwen=f32(-2.7852/(h*h*h)),v0=mass/rho0,rho0=rho0,rw=rw,kw=kw,n0=n0,k0=k0,ck=ck,almost=f32(1e-18),dp=get(c,'dp'),constant_source='frozen archive equations + unchanged generated execution XML; Run text only cross-check')

def load_groups(files,c):
    groups={};walls={};keys=[(p,f,o)for p in PARTS for f in FIELDS for o in ORACLES]
    common=['native_id','x_m','z_m','J','stored_p_Pa','stored_Ace_m_s2_x','stored_Ace_m_s2_y','stored_Ace_m_s2_z']+[f'C{i}{j}'for i in range(1,4)for j in range(1,4)]
    extra=['n','V_m2','rho_kg_m3','k_m_s','theta_s_1','manufactured_FS','legal_flat_bed','interior_no_wall','LP_Pa_m2','Da_s_2','source_lap_Pa_m2','source_chain_Pa_m_s','literal_rate_Pa_s','float_rate_Pa_s','Cplane_cond_inf','Cplane_cond_defined','fluid_donors','fixed_donors']+[a+'_'+b for a in('Lx_m_1','Gp_Pa_m','gradJ_m_1')for b in'xyz']
    for leaf,target,columns in(('manufactured.csv',groups,common+extra),('walls.csv',walls,common)):
        with Path(files[leaf]['path']).open(encoding='utf-8-sig',newline='')as f:
            reader=csv.DictReader(f);need(set(columns+['part','field','oracle','time_s','completed_step'])<=set(reader.fieldnames),'Missing closed joint columns')
            for q in reader:
                key=(int(q['part']),q['field'],q['oracle']);need(key in keys,'Unexpected joint group');values=[float(q[k])if q[k]!=''else math.nan for k in columns];need(all(math.isfinite(v)for k,v in zip(columns,values)if k!='Cplane_cond_inf'),'Nonfinite required input')
                a=target.setdefault(key,dict(rows=[],time=float(q['time_s']),tau=float(q['tau_s']),step=int(q['completed_step'])))
                need(a['time']==float(q['time_s'])and a['step']==int(q['completed_step']),'Group actual clock mismatch');a['rows'].append(values)
    need(set(groups)==set(walls)==set(keys),'All12 actual/oracle groups required')
    for key in keys:
        a=groups[key];w=walls[key];need(len(a['rows'])==5000 and len(w['rows'])==475 and a['time']==w['time']and a['step']==w['step'],'Original whole-material/wall coverage differs')
        a['a']=np.asarray(a.pop('rows'));w['a']=np.asarray(w.pop('rows'));a['col']={n:i for i,n in enumerate(common+extra)};w['col']={n:i for i,n in enumerate(common)}
        for x,expected in((a,np.arange(2060,7060)),(w,None)):
            order=np.argsort(x['a'][:,x['col']['native_id']]);x['a']=x['a'][order];ids=x['a'][:,x['col']['native_id']].astype(int);need(len(np.unique(ids))==len(ids),'Duplicate material owner')
            need(np.array_equal(ids,expected)if expected is not None else np.all((ids>=0)&(ids<1805)),'Original owner domain differs')
        for name,expected in(('n',1.-(1.-c['n0'])/a['a'][:,a['col']['J']]),('V_m2',c['v0']*a['a'][:,a['col']['J']]),('rho_kg_m3',c['rw']+(c['rho0']-c['rw'])/a['a'][:,a['col']['J']])):
            actual=a['a'][:,a['col'][name]];need(np.all(np.abs(actual-expected)<=gamma(8)*(np.abs(actual)+np.abs(expected))),'Current J ledger does not match source constants: '+name)
        need(np.all(a['a'][:,a['col']['J']]==1.)and np.all(a['a'][:,a['col']['k_m_s']]==c['k0']),'Manufactured soil J1/k0 differs')
    clocks={int(q['part']):(float(q['time_s']),int(q['completed_step']))for q in table(files['selected_clocks.csv']['path'])}
    need(set(clocks)==set(PARTS)and all((a['time'],a['step'])==clocks[key[0]]for key,a in groups.items()),'Sealed original selected clocks differ')
    return keys,groups,walls

def rounded_interval(lo,hi):
    e=UF*np.maximum(np.abs(lo),np.abs(hi))/(1.-UF)+SF;return lo-e,hi+e
def mul_interval(a,b):
    v=np.stack((a[0]*b[0],a[0]*b[1],a[1]*b[0],a[1]*b[1]));return rounded_interval(v.min(axis=0),v.max(axis=0))
def fac_and_bound(rr,c):
    rf=rr.astype(np.float32);rad=np.sqrt(rf);q=rad/np.float32(c['h']);t=np.float32(1)-np.float32(.5)*q
    fac=((((np.float32(c['bwen'])*q)*t)*t)*t)/rad
    need(np.all(np.isfinite(fac))and np.all(rad>0),'Invalid original Wendland float evaluation')
    # One input-float ULP envelopes the much smaller gamma8-double distance error.
    low=np.nextafter(rf,np.float32(-np.inf)).astype(float);high=np.nextafter(rf,np.float32(np.inf)).astype(float)
    need(np.all(low>0)and np.all(gamma(8)*rr<high-low),'Kernel argument envelope not justified')
    ri=rounded_interval(np.sqrt(low),np.sqrt(high));qi=rounded_interval(ri[0]/c['h'],ri[1]/c['h']);wi=rounded_interval(1.-.5*qi[1],1.-.5*qi[0]);p=(c['bwen'],c['bwen'])
    for v in(qi,wi,wi,wi):p=mul_interval(p,v)
    v=np.stack((p[0]/ri[0],p[0]/ri[1],p[1]/ri[0],p[1]/ri[1]));lo,hi=rounded_interval(v.min(axis=0),v.max(axis=0));f=fac.astype(float)
    need(np.all((f>=lo)&(f<=hi)),'Rebuilt Fac outside its source FP envelope');return f,np.maximum(np.abs(f-lo),np.abs(hi-f))
def dot(a,b):return (a[...,0]*b[...,0]+a[...,1]*b[...,1])+a[...,2]*b[...,2]
def cmul(C,g):return np.stack(((C[...,0,0]*g[...,0]+C[...,0,1]*g[...,1])+C[...,0,2]*g[...,2],(C[...,1,0]*g[...,0]+C[...,1,1]*g[...,1])+C[...,1,2]*g[...,2],(C[...,2,0]*g[...,0]+C[...,2,1]*g[...,1])+C[...,2,2]*g[...,2]),axis=-1)
def accumulated(value,error):
    n=len(value);s=np.sum(value,axis=0);a=np.sum(np.abs(value),axis=0);b=np.sum(error,axis=0)/(1.-gamma(n+1))+2.*gamma(n+1)*a;return s,b,a
def reconcile(actual,ref,budget,label):
    actual=np.asarray(actual);ref=np.asarray(ref);budget=np.asarray(budget);error=np.abs(actual-ref)
    need(np.all(np.isfinite(actual))and np.all(np.isfinite(ref))and np.all(np.isfinite(budget))and np.all(budget>=0)and np.all(error<=budget),'Source arithmetic reconciliation failed: '+label)
    return float(np.max(np.divide(error,budget,out=np.zeros_like(error),where=budget>0)))
def arrays(a):
    get=lambda k:a['a'][:,a['col'][k]]
    pos=np.column_stack((get('x_m'),np.zeros(len(a['a'])),get('z_m')));ace=np.column_stack([get('stored_Ace_m_s2_'+x)for x in'xyz']);C=np.column_stack([get(f'C{i}{j}')for i in range(1,4)for j in range(1,4)]).reshape(-1,3,3)
    return get,pos,ace,C

def geometry(a,w,c):
    _,x,_,_=arrays(a);_,wx,_,_=arrays(w);points=np.r_[x,wx];radius=math.sqrt(c['size2']);envelope=radius+16*np.finfo(float).eps*max(1.,float(np.max(np.abs(points))),radius)
    candidates=cKDTree(points[:,(0,2)]).query_ball_point(x[:,(0,2)],envelope);out=[]
    for i,jj in enumerate(candidates):
        jj=np.sort(np.asarray(jj,dtype=int));d=x[i]-points[jj];rr=dot(d,d);use=(rr<=c['size2'])&(rr>=c['almost']);jj,d,rr=jj[use],d[use],rr[use];fac,ef=fac_and_bound(rr,c);out.append((jj,d,rr,fac,ef))
    return points,out

def shadow_group(key,a,w,geom,c,rowwriter):
    get,x,ace,C=arrays(a);wg,wx,wace,wC=arrays(w);points,edges=geom;need(np.array_equal(np.r_[x,wx],points),'Geometry differs across declared same-part groups')
    J=np.r_[get('J'),wg('J')];p=np.r_[get('stored_p_Pa'),wg('stored_p_Pa')];A=np.r_[ace,wace];Cs=np.r_[C,wC];V=c['v0']*J
    vals={v:[]for v in VARIANTS};recon={k:0. for k in('LP','Lx','Gp','Da','GJ','lap','chain','rate')};delta_stats={v:[]for v in VARIANTS}
    for i,(jj,d,rr,fac,ef)in enumerate(edges):
        need(np.count_nonzero(jj<5000)==int(get('fluid_donors')[i])and np.count_nonzero(jj>=5000)==int(get('fixed_donors')[i]),'Actual support count differs')
        g=d*fac[:,None];gi=cmul(C[i],g);gj=cmul(Cs[jj],g);absi=cmul(np.abs(C[i]),np.abs(d));absj=cmul(np.abs(Cs[jj]),np.abs(d));bi=absi*ef[:,None]+gamma(64)*absi*np.abs(fac[:,None]);bj=absj*ef[:,None]+gamma(64)*absj*np.abs(fac[:,None])
        volume=V[jj];dp=p[i]-p[jj];da=A[jj]-ace[i];dj=J[jj]-J[i];den=rr+c['eta2'];num=volume*dot(d,gi+gj);basew=num/den
        bw=volume*dot(np.abs(d),bi+bj)/den+gamma(64)*volume*dot(np.abs(d),np.abs(gi)+np.abs(gj)+bi+bj)/den
        lp,blp,_=accumulated(basew*dp,np.abs(dp)*bw+gamma(8)*np.abs(basew*dp));lx,blx,_=accumulated(d*basew[:,None],np.abs(d)*bw[:,None]+gamma(8)*np.abs(d*basew[:,None]))
        gp,bgp,_=accumulated(-gi*(volume*dp)[:,None],np.abs(volume*dp)[:,None]*bi+gamma(16)*np.abs(gi*(volume*dp)[:,None]));daval,bda,_=accumulated(volume*dot(da,gi),volume*dot(np.abs(da),bi)+gamma(32)*volume*dot(np.abs(da),np.abs(gi)))
        GJ,bGJ,_=accumulated(gi*(volume*dj)[:,None],np.abs(volume*dj)[:,None]*bi+gamma(16)*np.abs(gi*(volume*dj)[:,None]))
        refgp=np.array([get('Gp_Pa_m_'+q)[i]for q in'xyz']);reflx=np.array([get('Lx_m_1_'+q)[i]for q in'xyz']);refj=np.array([get('gradJ_m_1_'+q)[i]for q in'xyz']);refLP=get('LP_Pa_m2')[i];refDa=get('Da_s_2')[i];sf=int(get('manufactured_FS')[i])in(2,3)
        for name,actual,ref,b in(('LP',lp,refLP,blp),('Lx',lx,reflx,blx),('Gp',gp,refgp,bgp),('Da',daval,refDa,bda),('GJ',GJ,refj,bGJ)):recon[name]=max(recon[name],reconcile(actual,ref,b,name+str((key,i+2060))))
        ai=ace[i];rw=c['rw'];n=get('n')[i];k=get('k_m_s')[i];B=c['kw']/n;dk=k/((1.-c['n0'])*c['ck']);scale=B*k/(rw*9.80665)
        lap=lp+rw*(dot(ai,lx)+daval)if sf else ((lp-gp[0]*lx[0])-gp[1]*lx[1])-gp[2]*lx[2]+rw*daval
        bilinear=dot(np.abs(gp),blx)+dot(np.abs(lx),bgp)+dot(bgp,blx)
        blap=blp+rw*(dot(np.abs(ai),blx)+bda)if sf else blp+bilinear+rw*bda
        blap+=gamma(64)*(abs(lp)+dot(np.abs(gp),np.abs(lx))+rw*(abs(daval)+dot(np.abs(ai),np.abs(lx))))
        drive=gp+rw*ai;chain=dk*dot(GJ,drive);bchain=abs(dk)*(dot(bGJ,np.abs(drive))+dot(np.abs(GJ)+bGJ,bgp))+gamma(64)*abs(dk)*dot(np.abs(GJ),np.abs(gp)+rw*np.abs(ai))
        rate=B*(-get('theta_s_1')[i]+k/(rw*9.80665)*lap+chain/(rw*9.80665));brate=B/(rw*9.80665)*(abs(k)*blap+bchain)+gamma(64)*B*(abs(get('theta_s_1')[i])+abs(k*lap/(rw*9.80665))+abs(chain/(rw*9.80665)))
        for name,actual,ref,b in(('lap',lap,get('source_lap_Pa_m2')[i],blap),('chain',chain,get('source_chain_Pa_m_s')[i],bchain),('rate',rate,get('literal_rate_Pa_s')[i],brate)):recon[name]=max(recon[name],reconcile(actual,ref,b,name+str((key,i+2060))))
        condition=get('Cplane_cond_inf')[i]if get('Cplane_cond_defined')[i]else None
        for v in VARIANTS:
            if v=='pair_C_eta':dlp=0.;dlx=np.zeros(3);deltalap=0.;drate=0.;budget=0.
            else:
                receiver=v.startswith('receiver');bare=v.endswith('bare');ng=gi+gi if receiver else gi+gj;bn=bi+bi if receiver else bi+bj;dvden=rr if bare else den;wv=volume*dot(d,ng)/dvden;ewv=volume*dot(np.abs(d),bn)/dvden+gamma(64)*volume*dot(np.abs(d),np.abs(ng)+bn)/dvden
                dw=wv-basew;edw=ewv+bw+gamma(4)*(np.abs(wv)+np.abs(basew));dlp,bdlp,_=accumulated(dw*dp,np.abs(dp)*edw+gamma(8)*np.abs(dw*dp));dlx,bdlx,_=accumulated(d*dw[:,None],np.abs(d)*edw[:,None]+gamma(8)*np.abs(d*dw[:,None]));bcoef=rw*ai if sf else -refgp
                deltalap=dlp+dot(bcoef,dlx);drate=scale*deltalap;budget=abs(scale)*(bdlp+dot(np.abs(bcoef),bdlx)+gamma(32)*(abs(dlp)+dot(np.abs(bcoef),np.abs(dlx))))+gamma(8)*abs(drate)
            original=get('literal_rate_Pa_s')[i];shadow=original+drate;need(all(math.isfinite(float(z))for z in(original,shadow,drate,dlp,deltalap,budget)),'Nonfinite weight shadow')
            vals[v].append(shadow);delta_stats[v].append((drate,dlp,float(np.linalg.norm(dlx)),deltalap,budget))
            rowwriter.writerow([key[0],key[1],key[2],a['time'],a['step'],i+2060,v,int(get('manufactured_FS')[i]),int(get('legal_flat_bed')[i]),int(get('interior_no_wall')[i]),get('x_m')[i],get('z_m')[i],condition,original,shadow,drate,dlp,*dlx,deltalap,budget])
    metrics=[];masks=(np.ones(5000,dtype=bool),get('legal_flat_bed')==1,get('interior_no_wall')==1);condition=get('Cplane_cond_inf');defined=get('Cplane_cond_defined')==1
    for cohort,mask in zip(COHORTS,masks):
        count=int(mask.sum());condmax=float(np.max(condition[mask&defined]))if np.any(mask&defined)else None
        for v in VARIANTS:
            orig=get('literal_rate_Pa_s')[mask];s=np.asarray(vals[v])[mask];d=np.asarray(delta_stats[v])[mask];r=dict(part=key[0],field=key[1],oracle=key[2],time_s=a['time'],completed_step=a['step'],cohort=cohort,material_IDs=count,variant=v,Cplane_max_finite_condition=condmax,Cplane_undefined_count=int(np.count_nonzero(mask&~defined)))
            for name,x in(('original_rate',orig),('shadow_rate',s),('delta_rate',d[:,0]),('deltaLP',d[:,1]),('deltaLx_norm',d[:,2]),('delta_lap',d[:,3])):r.update({name+'_mean':float(np.mean(x))if count else None,name+'_RMS':float(np.sqrt(np.mean(x*x)))if count else None,name+'_absmax':float(np.max(np.abs(x)))if count else None})
            r.update(delta_rate_arithmetic_budget_absmax=float(np.max(d[:,4]))if count else None,absolute_rate_lower_count=int(np.count_nonzero(np.abs(s)<np.abs(orig))),absolute_rate_higher_count=int(np.count_nonzero(np.abs(s)>np.abs(orig))));metrics.append(r)
    return metrics,dict(part=key[0],field=key[1],oracle=key[2],time_s=a['time'],completed_step=a['step'],material_IDs=5000,**{k+'_max_budget_ratio':v for k,v in recon.items()})

def plots(metrics):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import SymmetricalLogLocator
    paths=[];colors=('tab:blue','tab:orange','tab:green','tab:red')
    fig,axes=plt.subplots(3,3,figsize=(15,10),layout='constrained')
    for i,field in enumerate(FIELDS):
        for j,cohort in enumerate(COHORTS):
            ax=axes[i,j]
            for color,(part,oracle)in zip(colors,[(p,o)for p in PARTS for o in ORACLES]):
                rr=[next(q for q in metrics if(q['part'],q['field'],q['oracle'],q['cohort'],q['variant'])==(part,field,oracle,cohort,v))for v in VARIANTS]
                ax.plot(range(4),[q['shadow_rate_RMS']for q in rr],'.-',color=color,label=f'P{part} {oracle}')
            ax.set(title=field[:1]+' | '+cohort,ylabel='Conditional rate RMS [Pa/s]');ax.set_xticks(range(4),('pair/eta','pair/bare','recv/eta','recv/bare'),rotation=20);ax.set_yscale('symlog',linthresh=1);locator=SymmetricalLogLocator(base=10,linthresh=1);locator.set_params(numticks=9);ax.yaxis.set_major_locator(locator);ax.grid(alpha=.25)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,fontsize=9);fig.suptitle('Frozen joint fields: pressure-weight changes only; actual C/J/FS/Gp/Da/chain retained\nNot a trajectory, physical repair or operator selection')
    p=FIG/(TAG+'_rates.png');fig.savefig(p,dpi=175);plt.close(fig);paths.append(p)
    fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
    for i,field in enumerate(FIELDS):
        for j,cohort in enumerate(COHORTS[1:]):
            ax=axes[i,j]
            for color,v in zip(colors[1:],VARIANTS[1:]):
                rr=[next(q for q in metrics if(q['part'],q['field'],q['oracle'],q['cohort'],q['variant'])==(p,field,o,cohort,v))for p in PARTS for o in ORACLES]
                ax.plot(range(4),[q['delta_rate_mean']for q in rr],'.-',color=color,label=v+' signed mean');ax.plot(range(4),[q['delta_rate_RMS']for q in rr],'x--',color=color,label=v+' RMS')
            ax.axhline(0,color='.5',lw=.6);ax.set(title=field[:1]+' | '+cohort,ylabel='Variant − original rate [Pa/s]');ax.set_xticks(range(4),('29 real','29 analytic','30 real','30 analytic'),rotation=15);ax.set_yscale('symlog',linthresh=1);locator=SymmetricalLogLocator(base=10,linthresh=1);locator.set_params(numticks=9);ax.yaxis.set_major_locator(locator);ax.grid(alpha=.25)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2,fontsize=8);fig.suptitle('Signed and RMS conditional changes; all material-ID rows retained locally\nBare and receiver-C shadows are not new solver results')
    p=FIG/(TAG+'_deltas.png');fig.savefig(p,dpi=175);plt.close(fig);paths.append(p);return paths

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');need(parser.parse_args().execution_authorized,'Separate root offline admission required')
    need(not CHECK.exists()and not LOCAL.exists()and not list(FIG.glob(TAG+'_*')),'Protect prior complete/partial outputs');consumed=[];products=[]
    try:
        consumed=[stat(__file__),stat(NOTE)];files,c=source_constants(consumed);keys,groups,walls=load_groups(files,c);geometry_cache={};metrics=[];reconciliation=[];LOCAL.mkdir()
        body=LOCAL/'per_ID_weights.csv';products.append(body)
        with body.open('x',encoding='utf-8',newline='')as f:
            writer=csv.writer(f);writer.writerow(['part','field','oracle','time_s','completed_step','native_id','variant','manufactured_FS','legal_flat_bed','interior_no_wall','x_m','z_m','Cplane_cond_inf','original_literal_rate_Pa_s','shadow_rate_Pa_s','variant_minus_original_Pa_s','deltaLP_Pa_m2','deltaLx_x_m_1','deltaLx_y_m_1','deltaLx_z_m_1','delta_lap_Pa_m2','delta_rate_arithmetic_budget_Pa_s'])
            for key in keys:
                if key[0]not in geometry_cache:geometry_cache[key[0]]=geometry(groups[key],walls[key],c)
                m,r=shadow_group(key,groups[key],walls[key],geometry_cache[key[0]],c,writer);metrics.extend(m);reconciliation.append(r)
        need(len(metrics)==144 and len(reconciliation)==12,'Closed all-group/variant/cohort coverage differs');FIG.mkdir(exist_ok=True)
        for name,data in(('metrics',metrics),('reconciliation',reconciliation)):
            p=FIG/(TAG+'_'+name+'.csv');write_csv(p,data);products.append(p)
        products+=plots(metrics);[bind(q)for q in consumed]
        result=dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,source_component=stat(GATE),constants=c,actual_groups=12,soil_rows_consumed=60000,wall_rows_consumed=5700,per_ID_variant_rows=240000,metrics_rows=144,reconciliation_rows=12,variants=list(VARIANTS),baseline_reconciliation='float-kernel interval + double operation/accumulation bounds; not original order or bit proof',shadow='same actual J/C/FS; changed pressure LP+Lx weight only; Gp/Da/chain retained; anchored original literal rate plus conditional delta',receiver_bare_is_exact_paper_or_physical_acceptance=False,new_solver_invocations=0,new_API_calls=0,native_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(p)for p in products])
    except Exception as e:result=dict(stage=TAG,passed=False,first_failure=str(e),partial_outputs_preserved=True,physical_acceptance=False,solver_invocations=0,native_invocations=0,consumed=consumed);raise
    finally:
        with CHECK.open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
