"""Offline 3x3 linear algebra only; input symbols come from real kernel header."""
import csv, itertools, json, math, pathlib, sys
import numpy as np

source, target = map(pathlib.Path, sys.argv[1:3])
check = target.with_suffix('.json')
assert not target.exists() and not check.exists(), 'Retained analysis protected'
symbols = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(source.open())]
assert len(symbols) == 14
eps = np.finfo(float).eps
def matching(a,b):
    return min(max(abs(a[i]-p[i]) for i in range(3)) for p in itertools.permutations(b))
def require(error, scale, text):
    assert error <= 32768*eps*max(1.,scale), (text,error,scale)
rows=[]; cases=[]; maxmap=maxroots=maxeig=0.
for s in symbols:
  J,m=s['J'],int(s['m']); rho,n,M=s['rho'],s['n'],s['K']+4*s['G']/3
  B=s['Kw']/n; cu=math.sqrt((M+B)/rho); omega=cu*s['k_cont']
  Kr,Ks,Ksig,Ka,ell=[s[x] for x in ('Kr','Ks','Ksig','Ka','ell')]
  for kh in (0.,float(np.float32(.0001))):
    D=B*kh/(s['rhow']*9.80665); a=Kr/rho; b=M*Ksig; c=B*Ks; d=D*ell; t=D*s['rhow']*Ka*a
    A=np.array([[0.,-a,a],[b,0.,0.],[-c,-t,-d+t]])
    scale=np.array([1.,1/(rho*cu),1/(rho*cu)])
    N=scale[:,None]*A/scale[None,:]/omega
    coeff=np.array([1.,(d-t)/omega,a*(b+c)/omega**2,a*b*d/omega**3])
    direct=np.array([1.,-np.trace(N),.5*(np.trace(N)**2-np.trace(N@N)),-np.linalg.det(N)])
    require(np.max(abs(coeff-direct)),np.max(abs(coeff)),'matrix characteristic coefficients')
    eig=np.linalg.eigvals(N); roots=np.roots(coeff); er=matching(eig,roots); maxroots=max(maxroots,er)
    require(er,max(abs(eig)),'matrix/cubic roots')
    for z in eig:
      residual=abs(np.polyval(coeff,z)); den=sum(abs(coeff[j])*abs(z)**(3-j) for j in range(4))
      require(residual,den,'eigenvalue polynomial residual')
    for dt in (2.**-23,2.**-24):
      step=omega*dt; R=np.eye(3)+step*N+.5*step**2*(N@N)
      def rate(y):
        v,stress,p=y; acc=a*(p-stress)
        return np.array([acc,b*v,-c*v-D*ell*p+D*s['rhow']*Ka*acc])
      # Direct scalar old+dt/2*rate then old+dt*rate(mid), as read from CPU source.
      columns=[]
      for j in range(3):
        y=np.eye(3)[:,j]/scale; mid=y+.5*dt*rate(y); columns.append((y+dt*rate(mid))*scale)
      stage=np.column_stack(columns); em=np.max(abs(stage-R)); maxmap=max(maxmap,em)
      require(em,np.linalg.norm(R,np.inf),'actual frozen predictor/corrector map')
      mapped=1+step*eig+.5*(step*eig)**2; eR=np.linalg.eigvals(R); ee=matching(eR,mapped);maxeig=max(maxeig,ee)
      require(ee,max(abs(mapped)),'map eigenvalues')
      radius=float(max(abs(mapped))); maxreal=float(max(eig.real)*omega)
      acoustic=max(abs(eig.imag))*omega
      logamp=.5*math.log1p(.25*(dt*acoustic)**4) if kh==0 else math.log(radius)
      classification='k0_RK2_strict_amplification' if kh==0 else ('outside_RK2_disk' if radius>1+32*eps else 'inside_or_roundoff_boundary')
      # Physical perturbation-energy weighting; no assertion of exact model energy conservation.
      w=np.array([math.sqrt(rho),1/math.sqrt(M),math.sqrt(n/s['Kw'])])/scale
      Q=w[:,None]*R/w[None,:]
      window=2.**-15; count=round(window/dt); P=np.eye(3); vmax=omax=1.; m4v=m4o=1.
      m4count=round((2.**-17)/dt)
      for it in range(1,count+1):
        P=Q@P; ve=float(np.dot(P[:,0],P[:,0])); op=float(np.linalg.svd(P,compute_uv=False)[0]**2)
        vmax=max(vmax,ve);omax=max(omax,op)
        if it<=m4count:m4v=max(m4v,ve);m4o=max(m4o,op)
      row=dict(J=J,m=m,kHyd=kh,dt_s=dt,Kr=Kr,Ks=Ks,Ksig=Ksig,Ka=Ka,ell=ell,max_real_lambda_s=maxreal,spectral_radius_R=radius,k0_or_max_logamp_per_step=logamp,retained_window_s=window,retained_steps=count,spectral_radius_power_factor=math.exp(count*logamp),selected_v_initial_max_energy_ratio=vmax,all_state_max_energy_operator_ratio=omax,m4_preselected_window_s=2.**-17,m4_preselected_steps=m4count,m4_selected_initial_max_energy_ratio=m4v,m4_all_state_max_energy_operator_ratio=m4o,classification=classification,source_map_error=em,matrix_cubic_error=er,map_eigen_error=ee)
      rows.append(row);cases.append(dict(**row,lambda_real_s=(eig.real*omega).tolist(),lambda_imag_s=(eig.imag*omega).tolist(),A=A.tolist(),normalized_N=N.tolist()))
assert len(rows)==56
with target.open('x',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
with check.open('x') as f:
    json.dump(dict(offline_mathematical_checks_passed=True,project_solver=False,physical_acceptance=False,symbol_rows=14,matrix_cases=56,max_source_map_error=maxmap,max_matrix_cubic_error=maxroots,max_map_eigen_error=maxeig,k0_strict_asymptotic_stability_claim=False,continuous_domain_repeated=False,cases=cases),f,indent=2,allow_nan=False)
