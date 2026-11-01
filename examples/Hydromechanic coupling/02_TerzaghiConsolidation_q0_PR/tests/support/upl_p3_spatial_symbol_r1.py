"""Frozen moment/mode predictions only; no project solver or physical acceptance."""
import csv, itertools, json, math, pathlib, sys
import numpy as np

source, target = map(pathlib.Path, sys.argv[1:3])
summary = target.with_suffix('.json')
assert not target.exists() and not summary.exists(), 'Retained outputs protected'
symbols = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(source.open())]
assert [int(s['nx']) for s in symbols] == [16, 32, 64]
eps = np.finfo(float).eps
end, amp = 2.**-15, 2.**-9
times = np.arange(257)*2.**-23
kh = float(np.float32(.0001))
rows, cases = [], []
max_root_error = max_imag = 0.
def operators(s, continuum=False):
    M, B, rho = s['K']+4*s['G']/3, s['Kw']/s['n'], s['rho']
    cu = math.sqrt((M+B)/rho); k = s['k_cont']
    kr, ks, ksig, ka, ell = ((k,k,k,k,k*k) if continuum else tuple(s[x] for x in ('Kr','Ks','Ksig','Ka','ell')))
    D = B*kh/(s['rhow']*9.80665)
    a, b, c, d = kr/rho, M*ksig, B*ks, D*ell
    t = D*s['rhow']*ka*a
    A = np.array([[0.,-a,a],[b,0.,0.],[-c,-t,-d+t]])
    scales = np.array([amp, M*amp/cu, B*amp/cu])
    H = A*scales[None,:]/scales[:,None]
    omega = cu*k
    eig, evec = np.linalg.eig(H/omega)
    coeff = [1.,(d-t)/omega,a*(b+c)/omega**2,a*b*d/omega**3]
    roots = np.roots(coeff)
    er = min(max(abs(eig[i]-p[i]) for i in range(3)) for p in itertools.permutations(roots))
    assert er <= 32768*eps*max(1.,max(abs(eig))), ('cubic mismatch',er)
    return H, scales, cu, D, eig*omega, evec, er
def exact(H, scales, eig, evec):
    coef = np.linalg.solve(evec,np.array([1.,0.,0.]))
    z = np.exp(times[:,None]*eig[None,:])*coef[None,:]
    state = z@evec.T
    integ = np.expm1(times[:,None]*eig[None,:])/eig[None,:]*coef[None,:]
    u = amp*(integ@evec[0,:])
    imag = max(float(np.max(abs(state.imag))),float(np.max(abs(u.imag)))/max(amp,1e-300))
    assert imag <= 32768*eps*max(1.,float(np.max(abs(state.real)))), ('imaginary remainder',imag)
    return state.real*scales[None,:], u.real, imag
for s in symbols:
    H, scales, cu, D, eig, evec, er = operators(s)
    HC, scalesC, _, _, eigC, evecC, erC = operators(s,True)
    discrete, ud, im = exact(H,scales,eig,evec)
    continuum, uc, imC = exact(HC,scalesC,eigC,evecC)
    max_root_error=max(max_root_error,er,erC);max_imag=max(max_imag,im,imC)
    ustar=amp/(cu*s['k_cont'])
    ref_factor=int(s['nx'])//16
    for half in (False,True):
      dt=2.**(-23-int(math.log2(ref_factor))-int(half)); steps=round(end/dt)
      stride=steps//256
      R=np.eye(3)+dt*H+.5*dt*dt*(H@H)
      y=np.array([1.,0.,0.]);u=0.;states=[y*scales];us=[u]
      for it in range(steps):
        nxt=R@y;u+=.5*dt*amp*(y[0]+nxt[0]);y=nxt
        if (it+1)%stride==0:states.append(y*scales);us.append(u)
      actual=np.array(states);us=np.array(us)
      assert len(actual)==257 and len(us)==257
      norm=np.array([amp,scales[1],scales[2]])
      max_modal=np.max(abs(actual-continuum)/norm,axis=0)
      uerror=float(np.max(abs(us-uc))/ustar)
      discrete_error=np.max(abs(actual-discrete)/norm,axis=0)
      us_error=float(np.max(abs(us-ud))/ustar)
      endpoint=(actual[-1]-continuum[-1])/continuum[-1]
      row=dict(nx=int(s['nx']),nz=int(s['nz']),native=int(s['native']),half=half,dt_s=dt,steps=steps,
        max_v_modal_error_over_A=float(max_modal[0]),max_p_modal_error_over_Pstar=float(max_modal[2]),
        max_u_modal_error_over_Ustar=uerror,combined_field_RMS_normalized=float(max(max_modal[0],max_modal[2],uerror)/math.sqrt(2)),
        endpoint_p_relative_error=float(endpoint[2]),endpoint_v_relative_error=float(endpoint[0]),endpoint_u_relative_error=float((us[-1]-uc[-1])/uc[-1]),
        acoustic_frequency_ratio=float(max(abs(eig.imag))/max(abs(eigC.imag))),
        frozen_time_max_v_over_A=float(discrete_error[0]),frozen_time_max_p_over_Pstar=float(discrete_error[2]),frozen_time_max_u_over_Ustar=us_error,
        coupled_CFL=cu*dt/s['h'],Ddt_h2=D*dt/s['h']**2,necessary_wave_dt_s=.2*s['h']/cu,necessary_pore_dt_s=float(np.float32(.1))*s['h']**2/D,
        raw_first_moment=s['Mraw_xx'],corrected_first_moment_error=s['corrected_moment_max_error'],quadratic_Lstar_xx=s['Lquad_xx'],quadratic_Lstar_zz=s['Lquad_zz'])
      rows.append(row)
      cases.append(dict(**row,lambda_real_s=eig.real.tolist(),lambda_imag_s=eig.imag.tolist(),end_actual_frozen=[float(actual[-1,0]),float(actual[-1,2]),float(us[-1])],end_continuum=[float(continuum[-1,0]),float(continuum[-1,2]),float(uc[-1])],characteristic_scales=dict(A=amp,Pstar=float(scales[2]),Ustar=ustar)))
assert len(rows)==6
# These are declared predictions, not new hard physical acceptance gates.
fine=[r for r in rows if r['half']]
decline=all(fine[i+1]['combined_field_RMS_normalized']<fine[i]['combined_field_RMS_normalized'] for i in range(2))
predicted_one_percent=fine[-1]['combined_field_RMS_normalized']<=.01 and abs(fine[-1]['endpoint_p_relative_error'])<=.01
with target.open('x',newline='') as file:
    writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
with summary.open('x') as file:
    json.dump(dict(offline_mathematical_checks_passed=True,project_solver=False,physical_acceptance=False,actual_grid_or_wave_run=False,symbol_rows=3,prediction_cases=6,max_normalized_matrix_cubic_error=max_root_error,max_normalized_imaginary_remainder=max_imag,
        predicted_half_error_decreases=decline,predicted_finest_meets_proposed_one_percent=predicted_one_percent,
        interpretation='Frozen linear predictions retain actual header/mixed-gradient symbols, but not nonlinear moving positions/J/C, float write-back or actual cell-linked periodic implementation. Fixed h/dp retains quadrature and Eta2 quadratic-moment floors.',cases=cases),file,indent=2,allow_nan=False)
