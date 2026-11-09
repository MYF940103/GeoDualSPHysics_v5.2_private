"""Author-only fresh-process, two-geometry/eight-case CUDA math comparison."""
import argparse,csv,ctypes,json,math,os,sys
from pathlib import Path
import numpy as np
import upl_c08_residual_visc_gpu_math_r1_build as b
T,L,TAG=b.T,b.L,b.TAG;OUT=T/'outputs'/(TAG+'_result');CHECK=L/(TAG+'.check.json')
need,read,stat,bind,save,invoke=b.need,b.read,b.stat,b.bind,b.save,b.invoke
E64=np.finfo(np.float64).eps;E32=np.finfo(np.float32).eps;H=float(np.float32(.048));ALPHA=.1
SAN=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')

def gamma(n):
    x=float(n)*E64;need(x<1,'Invalid arithmetic gamma');return x/(1-x)
def table(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def bound_output(j,key,leaf):
    return bind(next(e for e in j[key] if Path(e['path']).name==leaf))
def sources():
    bp=L/(TAG+'.build.json');build=read(bp);cp=L/'upl_c08_cubic_residual_rate_r1.check.json';c=read(cp);pp=L/'upl_c08_pair_force_cpu_r1.check.json';p=read(pp)
    need(build['passed'] and build['configuration']=='Debug' and build['actual_NVCC_calls']==build['link_invocations']==build['actual_link_objects']==1 and build['physical_objects']==0 and build['CUDA_debug_G'] and build['consumed_stats_unchanged'],'Closed standalone Debug DLL required')
    need(c['passed'] and c['consumed_stats_unchanged'] and c['source_parts']==[13,14] and c['soil_IDs']==5000 and c['complete_soil_pair_graph'] and not c['regularization'],'Closed actual two-state particle CSV required')
    need(p['passed'] and p['consumed_stats_unchanged'] and p['source_parts']==[13,14] and p['force_evaluations']==6 and p['actual_physical_steps']==0 and c['source_native']==p['source_native'],'Closed same-native actual CPU baseline required')
    particles=bound_output(c,'outputs','upl_c08_cubic_residual_rate_r1_particles.csv');soil=bound_output(p,'files','soil_force.csv')
    refs=[stat(x) for x in (Path(__file__),Path(b.__file__),bp,cp,pp,b.NOTE)]+[bind(build[k]) for k in ('program','source','module_definition')]+[particles,soil]
    return build,c,Path(particles['path']),Path(soil['path']),refs

def graph(x,V,rho,G):
    n=len(x);ii=[];jj=[];dd=[]
    for i in range(n-1):
        d=x[i]-x[i+1:];r2=np.sum(d*d,axis=1);need(np.all(r2>0),'Coincident nodes are not dropped')
        # Exclude unresolved double support decisions, not a physical cutoff.
        roundscale=np.sum((np.abs(x[i])+np.abs(x[i+1:]))**2,axis=1)
        need(np.all(np.abs(r2-4*H*H)>16*E64*(roundscale+4*H*H)),'Support decision is within declared double roundoff; no silent graph change')
        use=np.flatnonzero(r2<4*H*H)
        ii.extend([i]*len(use));jj.extend(i+1+use);dd.extend(d[use])
    I=np.asarray(ii,dtype=np.int64);J=np.asarray(jj,dtype=np.int64);d=np.asarray(dd,dtype=np.float64);r2=np.sum(d*d,axis=1).astype(np.float32)
    rad=np.sqrt(r2,dtype=np.float32);q=np.divide(rad,np.float32(H),dtype=np.float32)
    aa=(10./(math.pi*7.))/(H*H*H);c1=np.float32(-3*aa);d1=np.float32(9*aa/4);c2=np.float32(-3*aa/4)
    inner=rad<=np.float32(H);fac=np.empty(len(I),dtype=np.float32)
    q2=np.multiply(q,q,dtype=np.float32);term=np.add(np.multiply(c1,q,dtype=np.float32),np.multiply(d1,q2,dtype=np.float32),dtype=np.float32)
    fac[inner]=np.divide(term[inner],rad[inner],dtype=np.float32)
    tail=np.subtract(np.float32(2),q,dtype=np.float32);tail2=np.multiply(tail,tail,dtype=np.float32)
    fac[~inner]=np.divide(np.multiply(c2,tail2[~inner],dtype=np.float32),rad[~inner],dtype=np.float32)
    w=-fac.astype(np.float64);keep=w!=0;need(np.all(w[keep]>0) and np.all(np.isfinite(w)),'Positive finite Cubic graph required')
    I,J,d,w,q,rad,inner=I[keep],J[keep],d[keep],w[keep],q[keep].astype(float),rad[keep].astype(float),inner[keep]
    # Predeclared absolute float-kernel envelope, including cancellation and
    # CUDA fast reciprocal/sqrt/FMA versus NumPy's separate float32 operations.
    wscale=np.where(inner,(abs(float(c1))*q+abs(float(d1))*q*q)/rad,abs(float(c2))*(2+q)**2/rad)
    we=64*E32*wscale
    tau=H/np.sqrt(G/rho);eta=.5*G*(tau[I]+tau[J]);beta=eta*V[I]*V[J]*w;be=eta*V[I]*V[J]*we+64*E64*np.abs(beta)
    mass=rho*V;degree=np.zeros(n);degree_e=np.zeros(n);count=np.zeros(n,dtype=int)
    for ix in (I,J):np.add.at(degree,ix,beta);np.add.at(degree_e,ix,be);np.add.at(count,ix,1)
    M=np.zeros((n,2,2));Me=np.zeros_like(M);Mabs=np.zeros_like(M);dd=np.einsum('ei,ej->eij',d,d)
    for ix,other in ((I,J),(J,I)):
        weight=eta*V[other]*w;err=eta*V[other]*we+64*E64*np.abs(weight)
        np.add.at(M,ix,weight[:,None,None]*dd);np.add.at(Mabs,ix,np.abs(weight[:,None,None]*dd));np.add.at(Me,ix,err[:,None,None]*np.abs(dd))
    gam=np.array([gamma(64*(int(k)+1)) for k in count]);Me+=gam[:,None,None]*Mabs
    scale=np.max(np.abs(M),axis=(1,2));need(np.all(scale>0),'Empty LS node');a=M[:,0,0]/scale;b0=M[:,0,1]/scale;c0=M[:,1,1]/scale;det=a*c0-b0*b0
    need(np.all((a>0)&(c0>0)&(det>128*E64*(a*c0+b0*b0))),'Unregularized scaled LS rank failure')
    inv=np.empty_like(M);den=scale*det;inv[:,0,0]=c0/den;inv[:,0,1]=inv[:,1,0]=-b0/den;inv[:,1,1]=a/den
    invnorm=np.linalg.norm(inv,ord=2,axis=(1,2));em=np.linalg.norm(Me,axis=(1,2));qM=invnorm*em;need(np.all(qM<1),'Declared LS floating uncertainty reaches singularity; no tolerance enlargement')
    lam=2*ALPHA*degree/mass;le=2*ALPHA*(degree_e+gam*degree)/mass+64*E64*np.abs(lam)
    return dict(I=I,J=J,d=d,w=w,we=we,eta=eta,beta=beta,be=be,M=M,Me=Me,inv=inv,invnorm=invnorm,qM=qM,em=em,gam=gam,lam=lam,le=le,mass=mass,V=V,rho=rho,x=x,count=count)

def reference(g,v,target):
    I,J,d=g['I'],g['J'],g['d'];n=len(v);dv=v[I]-v[J];outer=np.einsum('ei,ej->eij',dv,d);N=np.zeros((n,2,2));Ne=np.zeros_like(N);Nabs=np.zeros_like(N)
    for ix,other in ((I,J),(J,I)):
        w=g['eta']*g['V'][other]*g['w'];we=g['eta']*g['V'][other]*g['we']+64*E64*np.abs(w)
        np.add.at(N,ix,w[:,None,None]*outer);np.add.at(Nabs,ix,np.abs(w[:,None,None]*outer));np.add.at(Ne,ix,we[:,None,None]*np.abs(outer))
    Ne+=g['gam'][:,None,None]*Nabs;fit=np.einsum('nij,njk->nik',N,g['inv'])
    # Normwise inverse perturbation bound; no fitted tolerance or 5-Pa gate.
    lb=g['invnorm']/(1-g['qM'])*(np.linalg.norm(Ne,axis=(1,2))+np.linalg.norm(fit,axis=(1,2))*g['em'])+g['gam']*np.linalg.norm(N,axis=(1,2))*g['invnorm']
    mb=None
    if target is not None:
        residual=dv-d@target.T;R=np.zeros((n,2,2));Ra=np.zeros_like(R)
        for ix,other in ((I,J),(J,I)):
            ww=g['eta']*g['V'][other]*(g['w']+g['we']);rr=np.abs(np.einsum('ei,ej->eij',residual,d));np.add.at(R,ix,ww[:,None,None]*rr)
        Ra=g['gam'][:,None,None]*(Nabs+np.linalg.norm(target)*np.abs(g['M']))
        manufacture_lb=g['invnorm']/(1-g['qM'])*np.linalg.norm(R+Ra,axis=(1,2))
        # Both are valid algebraic envelopes; the affine correlated bound avoids
        # pretending independent weight errors destroy exact affine reproduction.
        mb=manufacture_lb+g['gam']*(1+np.linalg.norm(target))
        lb=np.minimum(lb,2*mb)
    ri=dv-np.einsum('eij,ej->ei',fit[I],d);rj=dv-np.einsum('eij,ej->ei',fit[J],d)
    f=-.5*ALPHA*g['beta'][:,None]*(ri+rj);F=np.zeros((n,2));np.add.at(F,I,f);np.add.at(F,J,-f)
    de=4*E64*(np.abs(g['x'][I])+np.abs(g['x'][J]));ve=4*E64*(np.abs(v[I])+np.abs(v[J]));dn=np.linalg.norm(d,axis=1);den=np.linalg.norm(de,axis=1);ven=np.linalg.norm(ve,axis=1);vn=np.linalg.norm(dv,axis=1)
    rie=lb[I]*(dn+den)+np.linalg.norm(fit[I],axis=(1,2))*den+ven+g['gam'][I]*(vn+np.linalg.norm(fit[I],axis=(1,2))*dn)
    rje=lb[J]*(dn+den)+np.linalg.norm(fit[J],axis=(1,2))*den+ven+g['gam'][J]*(vn+np.linalg.norm(fit[J],axis=(1,2))*dn)
    fe=.5*ALPHA*(g['be']*(np.linalg.norm(ri,axis=1)+np.linalg.norm(rj,axis=1))+(g['beta']+g['be'])*(rie+rje));fb=np.zeros(n);fa=np.zeros(n)
    for ix in (I,J):np.add.at(fb,ix,fe);np.add.at(fa,ix,np.linalg.norm(f,axis=1))
    fb+=g['gam']*fa;acc=F/g['mass'][:,None];ab=fb/g['mass']+64*E64*np.linalg.norm(acc,axis=1)
    nullab=None
    if target is not None:
        residual=np.linalg.norm(dv-d@target.T,axis=1)
        nfe=.5*ALPHA*(g['beta']+g['be'])*(2*residual+(mb[I]+mb[J])*(dn+den)+2*ven+(g['gam'][I]+g['gam'][J])*(vn+np.linalg.norm(target)*dn))
        nb=np.zeros(n)
        for ix in (I,J):np.add.at(nb,ix,nfe)
        nullab=(nb+g['gam']*fa)/g['mass']
    return fit,lb,acc,ab,mb,nullab

def guarded(shape,dtype):
    a=np.full((shape[0]+2,*shape[1:]),137.125,dtype=dtype);return a,a[1:-1]
def ratio(err,budget):
    return float(np.max(np.divide(err,budget,out=np.zeros_like(np.asarray(err,dtype=float)),where=budget>0)))

def worker():
    build,c,particles,soil,refs=sources();need(OUT.is_dir() and not (OUT/'completion.json').exists(),'Fresh parent-created result directory required')
    rows=table(particles);old=[q for q in table(soil) if q['mode']=='baseline'];need(len(rows)==len(old)==10000,'Exactly two full5000 states required');G=float(np.float32(c['G_from_actual_Run_Pa']));need(G==7518796.5,'Actual material G differs')
    dll=ctypes.CDLL(str(bind(build['program'])['path']));fun=dll.C08ResidualViscGpuMathR1;ptr=ctypes.c_void_p
    fun.argtypes=[ptr,ptr,ptr,ptr,ptr,ctypes.c_uint,ctypes.c_float,ctypes.c_float,ctypes.c_double,ptr,ptr,ptr,ptr,ptr];fun.restype=ctypes.c_int
    need(ctypes.sizeof(ctypes.c_double)*2==16 and ctypes.sizeof(ctypes.c_float)*2==8 and ctypes.sizeof(ctypes.c_void_p)==8,'64-bit ctypes double2/float2 ABI required')
    nodefile=OUT/'nodes.csv';casefile=OUT/'cases.csv';summary=[]
    with nodefile.open('x',encoding='utf-8',newline='') as nf,casefile.open('x',encoding='utf-8',newline='') as cf:
        fields=['part','case','native_id','Lxx_gpu','Lxz_gpu','Lzx_gpu','Lzz_gpu','Lxx_ref','Lxz_ref','Lzx_ref','Lzz_ref','L_error_F','L_budget_F','dax_gpu','daz_gpu','dax_ref','daz_ref','da_error_norm','da_budget_norm','lambda_gpu_s_1','lambda_ref_s_1','lambda_budget_s_1','added_ax_float','added_az_float','commit_error_norm','commit_budget_norm','node_error'];nw=csv.DictWriter(nf,fieldnames=fields);nw.writeheader();cw=None
        for part in (13,14):
            rr=sorted((q for q in rows if int(q['part'])==part),key=lambda q:int(q['native_id']));oo=sorted((q for q in old if int(q['part'])==part),key=lambda q:int(q['native_id']));ids=np.array([int(q['native_id']) for q in rr]);need(len(rr)==len(oo)==5000 and np.array_equal(ids,np.arange(2060,7060)) and [int(q['native_id']) for q in oo]==ids.tolist(),'Complete matching native ID order required')
            x=np.array([[float(q['x_m']),float(q['z_m'])] for q in rr]);v0=np.array([[float(q['vx_m_s']),float(q['vz_m_s'])] for q in rr]);V=np.array([float(q['V_area_m2']) for q in rr]);rho=np.array([float(q['rho_kg_m3']) for q in rr]);base=np.array([[float(q['Ace_x_m_s2']),float(q['Ace_z_m_s2'])] for q in oo]);need(np.array_equal(base,base.astype(np.float32).astype(float)),'Actual baseline CPU float Ace must be promoted exactly')
            for q,z in zip(rr,oo):need(float(q['time_s'])==float(z['time_s']) and float(q['x_m'])==float(z['x_m']) and float(q['z_m'])==float(z['z_m']),'Actual source clock/positions differ across derived inputs')
            g=graph(x,V,rho,G)
            for name in ('native','constant','affine','rigid_rotation'):
                target=None
                if name=='native':v=v0.copy()
                elif name=='constant':target=np.zeros((2,2));v=np.tile([.125,-.25],(5000,1))
                elif name=='affine':target=np.array([[1.25,-.5],[.75,.25]]);v=x@target.T+np.array([.125,-.25])
                else:target=np.array([[0.,-.75],[.75,0.]]);v=x@target.T+np.array([.125,-.25])
                fit,lb,acc,ab,mb,nullab=reference(g,v,target);inputs=[np.ascontiguousarray(z,dtype=np.float64) for z in (x,v,V,rho,base)];before=[z.tobytes() for z in inputs]
                arrays=[guarded(shape,dtype) for shape,dtype in [((5000,9),np.float64),((5000,2),np.float64),((5000,2),np.float32),((5000,),np.float64),((5000,),np.uint32)]];canaries=[(a[0].tobytes(),a[-1].tobytes()) for a,z in arrays];outs=[z for a,z in arrays]
                rc=fun(*[ptr(z.ctypes.data) for z in inputs],5000,H,G,ALPHA,*[ptr(z.ctypes.data) for z in outs]);need(rc==0,'CUDA host function returned '+str(rc));need(all(z.tobytes()==q for z,q in zip(inputs,before)),'Host input bytes changed');need(all((a[0].tobytes(),a[-1].tobytes())==q for (a,z),q in zip(arrays,canaries)),'Output head/tail canary changed')
                L9,da,added,lam,errors=outs;need(np.all(errors==0) and all(np.all(np.isfinite(z)) for z in outs[:-1]),'GPU math node error/nonfinite output');need(np.all(L9[:,[1,3,4,5,7]]==0),'Out-of-plane LS entries differ')
                Lgpu=L9[:,[0,2,6,8]].reshape(5000,2,2);le=np.linalg.norm(Lgpu-fit,axis=(1,2));ae=np.linalg.norm(da-acc,axis=1);lambdae=np.abs(lam-g['lam']);predicted=(base+da).astype(np.float32);need(np.array_equal(added.view(np.uint32),predicted.view(np.uint32)),'Actual final float commit is not float(double(base)+returned delta)')
                refcommit=(base+acc).astype(np.float32).astype(float);ce=np.linalg.norm(added.astype(float)-refcommit,axis=1);cb=ab+E32*(np.linalg.norm(base+acc,axis=1)+np.linalg.norm(base+da,axis=1))+2*np.finfo(np.float32).smallest_subnormal
                need(np.all(le<=lb) and np.all(ae<=ab) and np.all(lambdae<=g['le']) and np.all(ce<=cb),'Declared L/acceleration/lambda/float-commit floating envelope exceeded')
                F=da*g['mass'][:,None];pn=float(np.sum(v*F));net=np.sum(F,axis=0);torque=float(np.sum(x[:,1]*F[:,0]-x[:,0]*F[:,1]));globalgamma=gamma(64*(5000+len(g['I'])+1));fb=g['mass']*ab
                powerbudget=float(np.sum(np.linalg.norm(v,axis=1)*fb)+globalgamma*np.sum(np.abs(v*F)));netbudget=float(np.sum(fb)+globalgamma*np.sum(np.linalg.norm(F,axis=1)));torquebudget=float(np.sum(np.linalg.norm(x,axis=1)*fb)+globalgamma*np.sum(np.linalg.norm(x,axis=1)*np.linalg.norm(F,axis=1)))
                need(pn<=powerbudget and np.linalg.norm(net)<=netbudget and abs(torque)<=torquebudget,'Frozen mechanical power/netforce/torque envelope failed')
                committed=(added.astype(float)-base)*g['mass'][:,None];commitfb=g['mass']*(E32*np.linalg.norm(base+da,axis=1)+2*np.finfo(np.float32).smallest_subnormal)
                cwork=float(np.sum(v*committed));cnet=float(np.linalg.norm(np.sum(committed,axis=0)));ctorque=float(np.sum(x[:,1]*committed[:,0]-x[:,0]*committed[:,1]));cpb=powerbudget+float(np.sum(np.linalg.norm(v,axis=1)*commitfb));cnb=netbudget+float(np.sum(commitfb));ctb=torquebudget+float(np.sum(np.linalg.norm(x,axis=1)*commitfb))
                need(cwork<=cpb and cnet<=cnb and abs(ctorque)<=ctb,'Final-float committed power/netforce/torque envelope failed')
                manufacture_error=manufacture_budget=0.
                if target is not None:
                    manufacture_error=float(np.max(np.linalg.norm(Lgpu-target,axis=(1,2))));manufacture_budget=float(np.max(mb));need(np.all(np.linalg.norm(Lgpu-target,axis=(1,2))<=mb) and np.all(np.linalg.norm(da,axis=1)<=nullab),'Analytic manufactured LS/residual-force null envelope failed')
                s=dict(part=part,case=name,nodes=5000,edges=len(g['I']),alpha=ALPHA,max_L_budget_fraction=ratio(le,lb),max_da_budget_fraction=ratio(ae,ab),max_lambda_budget_fraction=ratio(lambdae,g['le']),max_float_commit_budget_fraction=ratio(ce,cb),max_delta_a_m_s2=float(np.max(np.linalg.norm(da,axis=1))),max_lambda_bound_s_1=float(np.max(lam)),power_W_per_depth=pn,power_budget=powerbudget,net_force_norm=float(np.linalg.norm(net)),net_force_budget=netbudget,torque_y=torque,torque_budget=torquebudget,committed_power_W_per_depth=cwork,committed_power_budget=cpb,committed_net_force_norm=cnet,committed_net_force_budget=cnb,committed_torque_y=ctorque,committed_torque_budget=ctb,manufacture_L_error=manufacture_error,manufacture_L_budget=manufacture_budget,input_bytes_unchanged=True,output_canaries_unchanged=True,node_errors=0)
                need(all(not isinstance(z,(int,float)) or math.isfinite(z) for z in s.values()),'Nonfinite case metric/budget')
                if cw is None:cw=csv.DictWriter(cf,fieldnames=list(s));cw.writeheader()
                cw.writerow(s);summary.append(s)
                for k,identity in enumerate(ids):nw.writerow(dict(zip(fields,[part,name,int(identity),*Lgpu[k].ravel(),*fit[k].ravel(),le[k],lb[k],*da[k],*acc[k],ae[k],ab[k],lam[k],g['lam'][k],g['le'][k],*added[k],ce[k],cb[k],int(errors[k])])))
                nf.flush();cf.flush();print('GPU_MATH_CASE_COMPLETE',part,name,flush=True)
    need(len(summary)==8 and all(stat(e['path'])==e for e in refs),'Eight-case coverage or source stat closure differs')
    save(OUT/'completion.json',dict(stage=TAG,passed=True,host_function_calls=8,kernel_launches=16,node_checks=40000,parts=[13,14],cases=['native','constant','affine','rigid_rotation'],alpha=ALPHA,G_Pa=G,KernelH_float=H,numpy_no_FMA_reference=True,baseline_Ace='actual CPU float field promoted to double; not a GPU force stage',float_kernel_absolute_envelope_factor=64,coupled_or_continuum_accuracy_claimed=False,solver_integration_admitted=False,physical_acceptance=False,cases_summary=summary,consumed=refs,consumed_stats_unchanged=True))

def run(memcheck):
    need(not OUT.exists() and not CHECK.exists(),'Existing complete/partial component protected');refs=[];call=None
    try:
        build,c,p,s,refs=sources();refs.append(stat(sys.executable));OUT.mkdir();argv=[sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--worker','--execution-authorized'];sanlog=L/(TAG+'.memcheck.log')
        if memcheck:
            need(not sanlog.exists(),'Existing memcheck protected');refs.append(stat(SAN));argv=[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(sanlog),*argv]
        call=invoke(TAG+'.run',argv,OUT,target=Path(sys.executable) if memcheck else None);done=read(OUT/'completion.json');need(done['passed'] and done['host_function_calls']==8 and done['kernel_launches']==16 and done['node_checks']==40000,'Actual DLL math coverage incomplete')
        if memcheck:
            text=sanlog.read_text(encoding='utf-8-sig');need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Missing/nonzero sanitizer summaries')
        need(all(stat(e['path'])==e for e in refs),'Closed component inputs changed');save(CHECK,dict(stage=TAG,passed=True,component_build=stat(L/(TAG+'.build.json')),actual_call=call,component_completion=stat(OUT/'completion.json'),source_particle_check=stat(L/'upl_c08_cubic_residual_rate_r1.check.json'),source_CPU_baseline_check=stat(L/'upl_c08_pair_force_cpu_r1.check.json'),memcheck_zero_errors_and_leaks=True if memcheck else None,memcheck=stat(sanlog) if memcheck else None,host_function_calls=8,kernel_launches=16,baseline_is_actual_CPU_float_Ace=True,solver_force_or_Darcy_comparison=False,solver_invocations=0,native_decodes=0,physical_acceptance=False,consumed=refs,consumed_stats_unchanged=True,files=[stat(OUT/q) for q in ('completion.json','cases.csv','nodes.csv')],SHA_scans=0))
    except Exception as error:
        if not CHECK.exists():save(CHECK,dict(stage=TAG,passed=False,first_failure=str(error),actual_call=stat(L/(TAG+'.run.call.json')) if (L/(TAG+'.run.call.json')).exists() else call,partial_outputs_preserved=True,consumed=refs,solver_invocations=0,native_decodes=0,physical_acceptance=False,SHA_scans=0))
        raise
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');p.add_argument('--memcheck',action='store_true');p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS);a=p.parse_args();need(a.execution_authorized,'Author-only until root full-read and explicit one-shot execution');worker() if a.worker else run(a.memcheck)
