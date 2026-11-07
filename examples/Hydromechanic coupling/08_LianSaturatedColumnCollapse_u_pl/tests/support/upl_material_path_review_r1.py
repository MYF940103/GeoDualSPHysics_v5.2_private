"""Independent smooth material-path reference; never launches a physical solver."""
import argparse, cmath, csv, json, math
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
T=Path(__file__).resolve().parents[1]
TAG='upl_material_path_r1'
ADMIT=T/'notes'/f'{TAG}.json'
OUT=T/'outputs'/TAG
FIT={'DP_C':1,'DP_MC':2,'DP_PS':3}
NS=(8,16,32,64)
SEG=(.006,-.001,.005)
SQ3=math.sqrt(3.)

def need(b,s):
    if not b: raise RuntimeError(s)

def write_json(p,v):
    with p.open('x',encoding='utf-8') as f: json.dump(v,f,indent=2,allow_nan=False);f.write('\n')

def smt(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def models():
    f=lambda x:float(np.float32(x))
    E=np.float32(20000000);nu=np.float32(.33)
    K=f(E/(np.float32(3)*(np.float32(1)-np.float32(2)*nu)))
    G=f(E/(np.float32(2)*(np.float32(1)+nu)))
    result=[]
    def put(name,fit,psi,soft):
        m=dict(model=name,fit=FIT[fit],K=K,G=G,phi_p=f(math.radians(25)),phi_r=f(math.radians(25)),n_p=0.,coh_p=7500.,coh_r=7500.,n_c=0.,psi0=f(math.radians(psi)),sf=0.)
        if soft in ('combined','phi'):m.update(phi_r=f(math.radians(20)),n_p=5.)
        if soft in ('combined','coh'):m.update(coh_r=1000.,n_c=5.)
        if soft in ('combined','psi'):m.update(sf=.2)
        m={k:(f(v) if k not in ('model','fit') else v) for k,v in m.items()}
        result.append(m)
    for fit in FIT:
        for psi in (0.,2.5,-5.):
            for soft in ('constant','combined'):put(f'{fit}_{psi:g}_{soft}',fit,psi,soft)
    for law in ('phi','coh','psi'):put(f'DP_PS_2.5_{law}', 'DP_PS',2.5,law)
    need(len(result)==21,'21 independent material models required')
    return result

def coeff(m,k):
    # Independent expression: complex-step differentiates the complete laws,
    # rather than using candidate's analytic coefficient derivatives.
    phi=m['phi_r']+(m['phi_p']-m['phi_r'])*cmath.exp(-m['n_p']*k)
    coh=m['coh_r']+(m['coh_p']-m['coh_r'])*cmath.exp(-m['n_c']*k)
    psi=m['psi0']*cmath.exp(-m['sf']*k)
    if m['fit']==3:
        t,u=cmath.tan(phi),cmath.tan(psi)
        d=cmath.sqrt(9+12*t*t)
        return t/d,3*coh/d,u/cmath.sqrt(9+12*u*u)
    s=-1 if m['fit']==1 else 1
    d=SQ3*(3+s*cmath.sin(phi))
    return 2*cmath.sin(phi)/d,6*coh*cmath.cos(phi)/d,2*cmath.sin(psi)/(SQ3*(3+s*cmath.sin(psi)))

def values(m,k):
    return tuple(z.real for z in coeff(m,k))

def derivs(m,k):
    return tuple(z.imag/1e-20 for z in coeff(m,k+1e-20j))

def yieldf(m,I,q,k):
    a,c,b=values(m,k);return q+a*I-c

def reference(m,tight):
    a,c,b=values(m,0.)
    # State: I,q,kappa, accumulated plastic work, external work.
    initial=np.array([-300000.,c+300000.*a,0.,0.,0.])
    y=initial.copy(); pieces=[];plastic_segments=0;minq=math.inf;mind=math.inf
    for seg,eps in enumerate(SEG):
        start=y.copy();dq=2*m['G']*eps
        f0=yieldf(m,*start[:2],start[2])
        if dq<=0 or f0+dq<=0:
            def elastic(t,start=start.copy(),dq=dq):
                z=np.repeat(start[:,None],np.size(t),axis=1);t=np.asarray(t).reshape(-1)
                z[1]+=dq*t;z[4]+=(start[1]*dq*t+.5*(dq*t)**2)/m['G'];return z
            pieces.append(elastic);y=elastic([1.])[:,0];continue
        te=max(0.,-f0/dq)
        need(te<1,'Expected nonempty plastic interval')
        at=start.copy();at[1]+=dq*te;at[4]+=(start[1]*dq*te+.5*(dq*te)**2)/m['G']
        def rhs(t,z):
            nonlocal minq,mind
            I,q,k,wp,w=z;alpha,kc,beta=values(m,k);ak,ck,bk=derivs(m,k)
            D=m['G']+9*m['K']*alpha*beta-(I*ak-ck)/SQ3
            need(q>0 and D>0 and np.isfinite(z).all(),'Reference left regular stable branch')
            minq=min(minq,q);mind=min(mind,D)
            ld=dq/D
            need(ld>=0,'Reference negative plastic loading')
            return [-9*m['K']*beta*ld,dq-m['G']*ld,ld/SQ3,ld*(q+beta*I),q*dq/m['G']]
        sol=solve_ivp(rhs,(te,1.),at,method='DOP853',rtol=2e-13 if tight else 2e-11,
          atol=np.array([1e-9,1e-9,1e-17,1e-10,1e-10]) if tight else np.array([1e-7,1e-7,1e-15,1e-8,1e-8]),dense_output=True)
        need(sol.success,'Independent reference integration failed')
        def part(t,sol=sol,te=te,start=start.copy(),dq=dq):
            t=np.asarray(t).reshape(-1);z=sol.sol(t);mask=t<te
            z[:,mask]=start[:,None];z[1,mask]+=dq*t[mask]
            z[4,mask]+=(start[1]*dq*t[mask]+.5*(dq*t[mask])**2)/m['G'];return z
        pieces.append(part);y=sol.y[:,-1];plastic_segments+=1
    need(plastic_segments==2,'Loading/unloading/reloading path coverage differs')
    return initial,pieces,dict(minimum_q_Pa=minq,minimum_consistency_denominator_Pa=mind,plastic_segments=plastic_segments)

def table_references(mm):
    refs={};summary=[]
    for m in mm:
        initial,lo,_=reference(m,False);_,hi,meta=reference(m,True)
        maxstress=maxk=maxyield=maxenergy=0.
        for N in NS:
            for seg in range(3):
                t=np.arange(1,N+1,dtype=float)/N
                l,h=lo[seg](t),hi[seg](t)
                maxstress=max(maxstress,float(np.max(np.abs(h[:2]-l[:2]))));maxk=max(maxk,float(np.max(np.abs(h[2]-l[2]))))
                for i in range(N):
                    z=h[:,i];key=(m['model'],N,seg*N+i+1);refs[key]=z
                    maxyield=max(maxyield,max(0.,yieldf(m,z[0],z[1],z[2])))
                    dWe=(z[1]**2-initial[1]**2)/(2*m['G'])+(z[0]**2-initial[0]**2)/(18*m['K'])
                    maxenergy=max(maxenergy,abs(z[4]-dWe-z[3]))
        need(maxstress<=.0001 and maxk<=1e-10 and maxyield<=.001 and maxenergy<=.0001,'Predeclared reference budgets failed')
        summary.append(dict(model=m['model'],refinement_stress_Pa=maxstress,refinement_kappa=maxk,yield_drift_Pa=maxyield,energy_balance_Pa=maxenergy,**meta))
    return refs,summary

def prepare():
    need(not OUT.exists(),'Existing path evidence protected')
    mm=models();refs,summary=table_references(mm)
    OUT.mkdir();write_json(OUT/'models.json',mm);write_json(OUT/'reference_checks.json',summary)
    with (OUT/'input.csv').open('x',newline='',encoding='utf-8') as f:
        fields=['model','method','N','step','segment','delta_diag','fit','K','G','phi_p','phi_r','n_p','coh_p','coh_r','n_c','psi0','sf','initial_I','initial_q']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for m in mm:
            a,c,b=values(m,0.)
            for method in ('candidate_general','linearized_dev','legacy_actual'):
                for N in NS:
                    for seg,de in enumerate(SEG):
                        for j in range(N):w.writerow(dict(m,method=method,N=N,step=seg*N+j+1,segment=seg,delta_diag=de/N,initial_I=-300000.,initial_q=c+300000.*a))
    with (OUT/'reference.csv').open('x',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['model','N','step','I_Pa','q_Pa','kappa','plastic_work_Pa','external_work_Pa'])
        for key,z in refs.items():w.writerow([*key,*z])
    write_json(OUT/'prepared.json',dict(stage=TAG,admission=smt(ADMIT),input=smt(OUT/'input.csv'),models=21,rows=22680,reference_checks_passed=True,SHA_scans=0,spatial_solver_invocations=0))
    print('REFERENCE_AND_INPUT_PREPARED',OUT,flush=True)

def audit_reference():
    """Audit retained reference records, including independent closed forms."""
    mm=json.loads((OUT/'models.json').read_text());by={m['model']:m for m in mm}
    states={};plastic_drift=violation=closed_stress=closed_k=0.;minimum_q=math.inf;constant_rows=plastic_rows=0
    with (OUT/'reference.csv').open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            name,N,step=r['model'],int(r['N']),int(r['step']);m=by[name]
            I,q,k=(float(r[x]) for x in ('I_Pa','q_Pa','kappa'));a,c,b=values(m,0.)
            old=states.get((name,N),(-300000.,c+300000.*a,0.))
            y=yieldf(m,I,q,k);violation=max(violation,max(y,0.));minimum_q=min(minimum_q,q)
            if k>old[2]:plastic_rows+=1;plastic_drift=max(plastic_drift,abs(y))
            if name.endswith('_constant'):
                de=SEG[(step-1)//N]/N;It,qt=old[0],old[1]+2*m['G']*de
                lam=max(0.,(qt+a*It-c)/(m['G']+9*m['K']*a*b))
                exact=(It-9*m['K']*b*lam,qt-m['G']*lam,old[2]+lam/SQ3)
                closed_stress=max(closed_stress,abs(I-exact[0]),abs(q-exact[1]));closed_k=max(closed_k,abs(k-exact[2]));constant_rows+=1
            states[(name,N)]=(I,q,k)
    need(constant_rows==3240 and plastic_rows>0,'Reference audit coverage differs')
    need(plastic_drift<=.001 and violation<=.001 and closed_stress<=.0001 and closed_k<=1e-10 and minimum_q>0,'Original independent reference audit budget failed')
    d=dict(stage=TAG+'.reference_audit',passed=True,absolute_plastic_yield_drift_Pa=plastic_drift,elastic_and_plastic_yield_violation_Pa=violation,constant_closed_form_rows=constant_rows,constant_closed_form_max_stress_Pa=closed_stress,constant_closed_form_max_kappa=closed_k,minimum_q_all_saved_Pa=minimum_q,plastic_rows=plastic_rows,source=smt(__file__),retained_reference=smt(OUT/'reference.csv'),SHA_scans=0,reference_or_solver_rerun=False)
    write_json(OUT/'reference_audit_r1.json',d);print(json.dumps(d,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['prepare','reference-audit'],required=True);a=p.parse_args()
    if a.phase=='prepare':prepare()
    else:audit_reference()
