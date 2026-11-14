"""Fixed linear Fourier compatibility counterexample, not an SPH solver or release."""
import argparse, cmath, csv, itertools, json, math
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = 'c08_tpi_coupled_r1'
OUT, CHECK = T / 'outputs' / TAG, T / 'logs' / (TAG + '.check.json')
H, RHO, RHOW, K, GAMMA, ALPHA = 29632906.0, 2072.5, 1000.0, .0002, 9806.65, .5
EPS, TINY = np.finfo(float).eps, float(np.nextafter(0., 1.))
CS = math.sqrt(H / RHO)

def need(ok, message):
    if not ok: raise ValueError(message)

def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)

def x0(state, q, mu, dt, beta):
    """Proposed X0 only: physical state (sigma[Pa],v[m/s],p[Pa],p_previous[Pa])."""
    sn, vn, pn, pm = state; iq = 1j * q
    an = iq * (sn - pn) / RHO
    vh, sh = vn + dt * .5 * an, sn + dt * .5 * H * iq * vn
    ph = pn + .5 * (pn - pm)
    ah = iq * (sh - ph) / RHO
    sf, vf = sn + dt * H * iq * vh, vn + dt * ah
    guess = pn + ALPHA * (pn - pm)
    ae = iq * (sf - guess) / RHO
    S = K * q*q / (1 - mu)
    B = -GAMMA * iq * vf + RHOW * K * iq * ae
    pf = (B + S * mu * guess + (beta / dt) * guess) / (S + beta / dt)
    return np.array((sf, vf, pf, pn), dtype=complex)

def eigenvalues(matrix, scales):
    # Fixed physical-unit similarity, not fitted/eigenvalue-dependent rescaling.
    d = np.asarray(scales); balanced = matrix * d[None, :] / d[:, None]
    values, vectors = np.linalg.eig(balanced)
    error = np.max(np.abs(balanced @ vectors - vectors * values[None, :]), axis=0)
    scale = (np.linalg.norm(balanced, np.inf) + np.abs(values)) * np.max(np.abs(vectors), axis=0)
    budget = 1024 * EPS * scale + 1024 * TINY
    need(np.all(error <= budget), 'Small-matrix eigensystem backward-error check failed')
    return values[np.lexsort((values.imag, values.real))], float(np.max(error / budget))

def reference(q, mass):
    iq = 1j * q; drho = RHO - RHOW
    if mass == 0:
        a = np.array(((0, H*iq), (iq/drho, -GAMMA/(K*drho))), dtype=complex)
        values, ratio = eigenvalues(a, (H, CS))
        terms = np.array((values**2, GAMMA/(K*drho)*values, np.full(2, H*q*q/drho)))
    else:
        a = np.array(((0, H*iq, 0), (iq/RHO, 0, -iq/RHO),
            (-RHOW*K*q*q/(RHO*mass), -GAMMA*iq/mass, -K*q*q*(1-RHOW/RHO)/mass)), dtype=complex)
        values, ratio = eigenvalues(a, (H, CS, H))
        terms = np.array((mass*RHO*values**3, K*drho*q*q*values**2,
                          (mass*H+GAMMA)*q*q*values, np.full(3, K*H*q**4)))
    residual = np.abs(np.sum(terms, axis=0)); budget = 1024*EPS*np.sum(np.abs(terms), axis=0)+1024*TINY
    need(np.all(residual <= budget), 'Independent continuous characteristic polynomial differs')
    return values, ratio, float(np.max(residual/budget))

def calculations():
    cases, modes = [], []; count = 0
    vector = np.array((1+.2j, .3-.1j, -.4+.7j, .2+.5j))
    critical = GAMMA * (RHO-RHOW) / (H*RHOW)
    for qname, q in (('pi_over_2', math.pi/2), ('pi_over_dp', math.pi/.04)):
      for mu, dt, beta in itertools.product((.2, .8), (.000005, .000010, .000020), (0.0, .04)):
        count += 1; matrix = np.column_stack([x0(e, q, mu, dt, beta) for e in np.eye(4, dtype=complex)])
        direct = x0(vector, q, mu, dt, beta); error = np.abs(matrix@vector-direct)
        budget = 128*EPS*(np.abs(matrix)@np.abs(vector)+np.abs(direct))+128*TINY
        need(np.all(error <= budget) and np.all(x0(np.zeros(4), q, mu, dt, beta) == 0), 'X0 is not the declared linear map')
        z, eig_ratio = eigenvalues(matrix, (H, CS, H, H))
        mass = beta*(1-ALPHA); lam, ref_ratio, poly_ratio = reference(q, mass)
        exact = np.exp(lam*dt); n = len(lam)
        order = min(itertools.permutations(range(4)), key=lambda p: sum(abs(z[p[i]]-exact[i])**2 for i in range(n)))
        assignments = {order[i]:i for i in range(n)}; zerrors, gerrors = [], []
        for j, value in enumerate(z):
            defined = value != 0; generator = cmath.log(value)/dt if defined else None
            row = dict(case=count, q_name=qname, q_m_inv=q, mu=mu, dt_s=dt, beta_capacity_m_inv=beta,
                reference_capacity_m_inv=mass, mode=j, z_real=value.real, z_imag=value.imag, abs_z=abs(value),
                principal_generator_defined=defined, generator_real_s_inv=generator.real if defined else '',
                generator_imag_s_inv=generator.imag if defined else '', role='unmatched_history', reference_mode='',
                reference_lambda_real_s_inv='', reference_lambda_imag_s_inv='', reference_exp_real='', reference_exp_imag='',
                amplification_error='', generator_error_s_inv='', relative_generator_error='')
            if j in assignments:
                i = assignments[j]; ze = abs(value-exact[i]); zerrors.append(ze)
                ge = abs(generator-lam[i]) if defined else None
                if ge is not None: gerrors.append(ge)
                row.update(role='matched_reference', reference_mode=i, reference_lambda_real_s_inv=lam[i].real,
                    reference_lambda_imag_s_inv=lam[i].imag, reference_exp_real=exact[i].real, reference_exp_imag=exact[i].imag,
                    amplification_error=ze, generator_error_s_inv=ge if defined else '',
                    relative_generator_error=ge/abs(lam[i]) if defined and lam[i] != 0 else '')
            modes.append(row)
        cases.append(dict(case=count,q_name=qname,q_m_inv=q,mu=mu,dt_s=dt,beta_capacity_m_inv=beta,
            reference_capacity_m_inv=mass,reference_dimension=n,critical_capacity_m_inv=critical,
            capacity_over_critical=mass/critical,normalized_continuous_margin=1-mass/critical,
            continuous_decay_domain=(mass<critical),reference_max_real_lambda_s_inv=float(max(lam.real)),
            reference_max_abs_exp=float(max(abs(exact))),X0_spectral_radius=float(max(abs(z))),
            matched_max_amplification_error=max(zerrors),matched_max_generator_error_s_inv=max(gerrors) if gerrors else '',
            matched_undefined_generators=n-len(gerrors),linearity_max_arithmetic_ratio=float(max(error/budget)),
            X0_eigen_arithmetic_ratio=eig_ratio,reference_eigen_arithmetic_ratio=ref_ratio,
            reference_polynomial_arithmetic_ratio=poly_ratio,elastic_fixed_negative_branch_counterexample=(beta>0)))
    need(len(cases)==24 and len(modes)==96, 'Prescribed24/96 coverage differs')
    return cases, modes

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    need(p.parse_args().execution_authorized,'Root algebra-only execution admission required')
    need(not OUT.exists() and not CHECK.exists(),'Existing complete/failed evidence is immutable')
    before=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md'))];OUT.mkdir()
    result=dict(stage=TAG,passed=False,consumed=before,force_calls=0,solver_invocations=0,native_decodes=0,
                build_invocations=0,physical_steps=0,SHA_scans=0,physical_acceptance=False,X0_selected=False)
    try:
        cases,modes=calculations()
        for name,rows in (('cases',cases),('modes',modes)):
            with (OUT/(name+'.csv')).open('x',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        need(all(stat(q['path'])==q for q in before),'Author files changed during algebra component')
        result.update(passed=True,consumed_stats_unchanged=True,cases=24,modes=96,alpha=ALPHA,
            H_Pa=H,rho_kg_m3=RHO,rhow_kg_m3=RHOW,k_m_s=K,gamma_Pa_m=GAMMA,
            parameters_fitted=False,reference_independent_of_mu=True,matching_permutations=24,
            generator_uses_principal_log=True,full_four_mode_spectrum_retained=True,
            beta_positive_is_elastic_fixed_branch_counterexample_not_plastic_paper_disproof=True,
            spatial_boundary_AV_plasticity_not_tested=True,files=[stat(OUT/(q+'.csv')) for q in ('cases','modes')])
    except Exception as e:
        result.update(first_failure=str(e),partial_outputs_preserved=True);raise
    finally:
        with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)

if __name__=='__main__':main()
