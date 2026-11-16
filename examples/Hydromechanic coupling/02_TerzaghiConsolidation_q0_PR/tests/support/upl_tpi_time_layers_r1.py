"""Author-only fixed-mode time-layer analysis; no SPH solve, force, reader or build."""
import argparse, cmath, csv, importlib.util, itertools, json, math
from pathlib import Path
import numpy as np

T=Path(__file__).resolve().parents[1]
COUPLING=T.parents[1]
OLD=COUPLING/'08_LianSaturatedColumnCollapse_u_pl/tests/support/c08_tpi_coupled_r1.py'
TAG='upl_tpi_time_layers_r1'
OUT=T/'outputs'/TAG
CHECK=T/'logs'/(TAG+'.check.json')
NOTE=T/'notes'/(TAG+'.md')
# Reused fixed Fourier-example parameters, not the case02 physical A input.
H,RHO,RHOW,K,GAMMA=29632906.,2072.5,1000.,.0002,9806.65
CS=math.sqrt(H/RHO)
EPS,TINY=np.finfo(float).eps,float(np.nextafter(0.,1.))
METHODS=(('B_TPI',.5,.5),('C_PPE_t',0.,0.))
STEPS=(1e-8,2e-8,4e-8,8e-8)  # Algebraic asymptotic probes, not proposed SPH dt.


def need(ok,message):
    if not ok:raise ValueError(message)


def stat(p):
    p=Path(p);s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def save_csv(p,rows):
    with p.open('x',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def reference(q):
    dr=RHO-RHOW;r=RHOW/RHO;iq=1j*q
    P=np.array((-r/(1-r),-GAMMA*iq/(K*q*q*(1-r))),dtype=complex)
    L=np.array(((0,H*iq),(iq/dr,-GAMMA/(K*dr))),dtype=complex)
    tr=-GAMMA/(K*dr);det=H*q*q/dr
    root=cmath.sqrt(tr*tr-4*det)
    fast=(tr-root)/2
    slow=det/fast  # Avoid subtraction in the slow real eigenvalue.
    return P,L,np.array((slow,fast),dtype=complex)


def step(y,q,mu,h,alpha,half):
    """State=(sigma,v,p,p_previous); h=0 is only a closed-map identity probe."""
    sn,vn,pn,previous=y;iq=1j*q
    an=iq*(sn-pn)/RHO
    vh,sh=vn+h*.5*an,sn+h*.5*H*iq*vn
    ph=pn if half==0 else pn+half*(pn-previous)
    ah=iq*(sh-ph)/RHO
    sf,vf=sn+h*H*iq*vh,vn+h*ah
    guess=pn if alpha==0 else pn+alpha*(pn-previous)
    ae=iq*(sf-guess)/RHO
    S=K*q*q/(1-mu)
    B=-GAMMA*iq*vf+RHOW*K*iq*ae
    pf=(B+S*mu*guess)/S
    return np.array((sf,vf,pf,pn),dtype=complex)


def eigen(matrix):
    d=np.array((H,CS,H,H));a=matrix*d[None,:]/d[:,None]
    z,v=np.linalg.eig(a)
    err=np.max(np.abs(a@v-v*z[None,:]),axis=0)
    scale=(np.linalg.norm(a,np.inf)+np.abs(z))*np.max(np.abs(v),axis=0)
    budget=4096*EPS*scale+4096*TINY
    need(np.all(err<=budget),'Small-matrix eigensystem arithmetic failed')
    return z,float(np.max(err/budget))


def calculations(legacy):
    identities=[];fastrows=[];matrices=[];modes=[]
    test=np.array((1+.2j,.3-.1j,-.4+.7j,.2+.5j))
    r=RHOW/RHO
    for mu in (.2,.8):
      m=r+(1-r)*mu
      for method,alpha,half in METHODS:
        disc=cmath.sqrt((m*(1+alpha))**2-4*m*alpha)
        roots=((m*(1+alpha)+disc)/2,(m*(1+alpha)-disc)/2)
        polynomial=max(abs(z*z-m*(1+alpha)*z+m*alpha) for z in roots)
        budget=256*EPS*max(abs(z*z)+abs(m*(1+alpha)*z)+abs(m*alpha) for z in roots)+256*TINY
        need(polynomial<=budget,'Independent fast quadratic arithmetic differs')
        jury=(1-m>0 and 1+m*(1+2*alpha)>0 and 1-m*alpha>0)
        need(jury and max(map(abs,roots))<1,'Selected real fast block must be Schur')
        c=m*(1-alpha)/(1-m)
        fastrows.append(dict(method=method,alpha_neighbor=alpha,half_predictor=half,mu=mu,rhow_over_rho=r,m_density_shifted=m,
            root1_real=roots[0].real,root1_imag=roots[0].imag,root2_real=roots[1].real,root2_imag=roots[1].imag,
            fast_spectral_radius=max(map(abs,roots)),Jury_real_scalar=True,pressure_lag_coefficient=c,
            mechanical_modified_coefficient=half-.5-c,quadratic_arithmetic_ratio=polynomial/budget))
    for qname,q in (('pi_over_2',math.pi/2),('pi_over_dp',math.pi/.04)):
      P,L,lam=reference(q)
      iq=1j*q
      for mu in (.2,.8):
        m=r+(1-r)*mu
        for method,alpha,half in METHODS:
          zero=step(test,q,mu,0.,alpha,half)
          g=test[2]+alpha*(test[2]-test[3])
          expected=(1-m)*(P@test[:2])+m*g
          scale=abs(zero[2])+abs((1-m)*(P@test[:2]))+abs(m*g)
          budget=256*EPS*scale+256*TINY
          need(abs(zero[2]-expected)<=budget and np.array_equal(zero[[0,1,3]],test[[0,1,2]]),'h0 closed constraint map differs')
          pp=P@test[:2];acc=iq*(test[0]-pp)/RHO
          residual=-GAMMA*iq*test[1]-K*q*q*pp+RHOW*K*iq*acc
          rb=256*EPS*(abs(GAMMA*iq*test[1])+abs(K*q*q*pp)+abs(RHOW*K*iq*acc))+256*TINY
          need(abs(residual)<=rb,'Independent M0 pressure constraint differs')
          identities.append(dict(q_name=qname,q_m_inv=q,mu=mu,method=method,alpha_neighbor=alpha,half_predictor=half,
              h0_identity_error=abs(zero[2]-expected),h0_arithmetic_budget=budget,reference_constraint_error=abs(residual),reference_constraint_budget=rb))
          c=m*(1-alpha)/(1-m)
          b=np.array((0,-iq/RHO),dtype=complex)
          L1=(half-.5-c)*np.outer(b,P@L)
          trace1=np.trace(L1)
          det1=L1[0,0]*L[1,1]+L[0,0]*L1[1,1]-L1[0,1]*L[1,0]-L[0,1]*L1[1,0]
          coefficient=(trace1*lam-det1)/(2*lam-np.trace(L))
          last_fast_error=None;last_h=None
          for h in STEPS:
            A=np.column_stack([step(e,q,mu,h,alpha,half) for e in np.eye(4,dtype=complex)])
            direct=step(test,q,mu,h,alpha,half)
            eb=256*EPS*(np.abs(A)@np.abs(test)+np.abs(direct))+256*TINY
            need(np.all(np.abs(A@test-direct)<=eb),'Declared new half scheme is not the constructed linear map')
            legacy_error=0.
            if method=='B_TPI':
                original=legacy.x0(test,q,mu,h,0.)
                legacy_error=float(np.max(np.abs(direct-original)))
                lb=256*EPS*(np.abs(direct)+np.abs(original))+256*TINY
                need(np.all(np.abs(direct-original)<=lb),'New B definition differs from retained X0 beta0')
            z,eigratio=eigen(A);exact=np.exp(lam*h)
            order=min(itertools.permutations(range(4)),key=lambda p:sum(abs(z[p[i]]-exact[i])**2 for i in range(2)))
            assignments={order[i]:i for i in range(2)}
            current_fast_error=None
            for j,value in enumerate(z):
                gen=cmath.log(value)/h if value!=0 else None
                row=dict(method=method,alpha_neighbor=alpha,half_predictor=half,q_name=qname,q_m_inv=q,mu=mu,dt_algebra_s=h,mode=j,
                    z_real=value.real,z_imag=value.imag,abs_z=abs(value),role='unmatched_history',reference_lambda_real='',reference_lambda_imag='',
                    generator_real=gen.real if gen is not None else '',generator_imag=gen.imag if gen is not None else '',generator_error='',
                    predicted_first_coefficient_real='',predicted_first_coefficient_imag='',measured_first_coefficient_real='',measured_first_coefficient_imag='',
                    first_coefficient_relative_error='')
                if j in assignments:
                    i=assignments[j]
                    row.update(role='matched_slow_physical' if i==0 else 'matched_fast_physical',reference_lambda_real=lam[i].real,reference_lambda_imag=lam[i].imag,
                        generator_error=abs(gen-lam[i]) if gen is not None else '')
                    if gen is not None:
                        measured=(gen-lam[i])/h
                        row.update(predicted_first_coefficient_real=coefficient[i].real,predicted_first_coefficient_imag=coefficient[i].imag,
                            measured_first_coefficient_real=measured.real,measured_first_coefficient_imag=measured.imag,
                            first_coefficient_relative_error=abs(measured-coefficient[i])/abs(coefficient[i]) if coefficient[i]!=0 else '')
                        if i==1:current_fast_error=abs(gen-lam[i])
                modes.append(row)
            observed=math.log(current_fast_error/last_fast_error)/math.log(h/last_h) if last_fast_error and current_fast_error else ''
            matrices.append(dict(method=method,alpha_neighbor=alpha,half_predictor=half,q_name=qname,mu=mu,dt_algebra_s=h,
                spectral_radius=float(max(abs(z))),eigensystem_arithmetic_ratio=eigratio,legacy_B_max_absolute_difference=legacy_error,
                fast_physical_generator_error=current_fast_error,observed_fast_generator_error_order=observed,
                order_and_stability_are_reported_not_physical_acceptance=True))
            last_fast_error,last_h=current_fast_error,h
    need(len(identities)==8 and len(fastrows)==4 and len(matrices)==32 and len(modes)==128,'Prescribed new coverage differs')
    return identities,fastrows,matrices,modes


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    need(p.parse_args().execution_authorized,'Root full-read and one algebra-only admission required')
    need(not OUT.exists() and not CHECK.exists(),'Existing/partial analysis is protected; never overwrite')
    before=[stat(Path(__file__)),stat(NOTE),stat(OLD)]
    spec=importlib.util.spec_from_file_location('legacy_tpi_coupled_definition',OLD);legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    OUT.mkdir();result=dict(stage=TAG,passed=False,consumed=before,physical_acceptance=False,force_calls=0,solver_invocations=0,
        native_decodes=0,build_invocations=0,physical_steps=0,SHA_scans=0,legacy_component_rerun=False)
    try:
        arrays=calculations(legacy)
        for name,rows in zip(('identities','fast_block','matrices','modes'),arrays):save_csv(OUT/(name+'.csv'),rows)
        need(all(stat(q['path'])==q for q in before),'Author/reference source changed during algebra')
        result.update(passed=True,analysis_complete=True,identity_cases=8,fast_blocks=4,new_matrices=32,new_modes=128,
            H_Pa=H,rho_kg_m3=RHO,rhow_kg_m3=RHOW,k_m_s=K,gamma_Pa_m=GAMMA,parameters_are_case02_A=False,
            methods=[dict(name=n,alpha_neighbor=a,half_predictor=b) for n,a,b in METHODS],beta=0,
            dt_family_is_algebraic_asymptotic_probe_not_SPH_recommendation=True,
            reference_M0_independent_of_mu=True,all_four_modes_retained=True,
            order_results_are_observations_not_assumed_second_order=True,no_stability_claim_for_real_SPH=True,
            files=[stat(OUT/(n+'.csv')) for n in ('identities','fast_block','matrices','modes')])
    except Exception as e:result.update(first_failure=str(e),partial_outputs_preserved=True);raise
    finally:
        with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False)


if __name__=='__main__':main()
