"""Frozen compression moments and virtual work only; no solver or integration."""
import os
for _name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_name] = '1'
import argparse
import json
import time
import traceback
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import TESTS, REPO, LIAN, READER, R, Q, DP, AFFINE_L, native, bound, batches, correction, add_pair
from cryer_darcy_closed_r1 import constants
from cryer_radial_consistency_r1 import Reference, stats
from cryer_symc_step_screen_r1 import verify, read

TAG = 'cryer_compression_moments_r1'
CHECK = TESTS/'logs'/(TAG+'.check.json')
FOLDER = TESTS/'outputs/cryer_preload_peak_r1'
TAU = .0420518020252
HESS = np.array([[[4., 1., -.5], [1., -2., .3], [-.5, .3, 1.]],
    [[-1., .5, .2], [.5, 3., -.4], [.2, -.4, -2.]],
    [[2., -.3, .7], [-.3, -1., .1], [.7, .1, 4.]]])


def radial_div_prime(ref, radius):
    """Analytic d(div v)/dr from the pressure-time modal derivative."""
    wt = -ref.decay*ref.amplitude*np.exp(-ref.decay*TAU)
    result = np.empty_like(radius)
    for first in range(0, len(radius), 1024):
        sl = slice(first, first+1024); z = radius[sl, None]*ref.xi/R
        small = abs(z) < .02; derivative = np.empty_like(z); s = z[small]
        derivative[small] = -s/3+s**3/30-s**5/840+s**7/45360-s**9/3991680
        derivative[~small] = (z[~small]*np.cos(z[~small])-np.sin(z[~small]))/z[~small]**2
        result[sl] = Q/ref.H*(derivative@(ref.xi/R*wt))
    return result


def fields(x, h, ref):
    n = len(x); radius = np.linalg.norm(x, axis=1); r2 = radius**2; eye = np.eye(3)
    assert radius.min() > 0, 'This native sphere has no origin node; do not use r=0 quotients'
    field = ref.field(radius, TAU); f = field['v_over_r']; div = field['div']
    lam = (div-3*f)/r2; mu = (radius*radial_div_prime(ref, radius)-5*(div-3*f))/r2**2
    grad = f[:, None, None]*eye+lam[:, None, None]*x[:, :, None]*x[:, None, :]
    cubic = 400.; rc = R-2*h; s = r2/rc**2; inside = s < 1
    compact_f = np.where(inside, (1-s)**3, 0.)
    compact_lam = np.where(inside, -6*(1-s)**2/rc**2, 0.)
    compact_mu = np.where(inside, 24*(1-s)/rc**4, 0.)
    rotation = np.array([[0., -.2, .1], [.2, 0., -.3], [-.1, .3, 0.]])
    zero = np.zeros((n, 3, 3)); common = np.broadcast_to(AFFINE_L, zero.shape)
    result = [dict(name='affine', v=x@AFFINE_L.T, gradient=common, exact_div=np.full(n, np.trace(AFFINE_L)), kind='affine'),
        dict(name='quadratic', v=x@AFFINE_L.T+.5*np.einsum('kab,na,nb->nk', HESS, x, x),
            gradient=common+np.einsum('kab,nb->nka', HESS, x),
            exact_div=np.trace(AFFINE_L)+np.einsum('kkb,nb->n', HESS, x), kind='quadratic'),
        dict(name='radial_cubic', v=cubic*r2[:, None]*x,
            gradient=cubic*(r2[:, None, None]*eye+2*x[:, :, None]*x[:, None, :]),
            exact_div=5*cubic*r2, kind='radial', lam=np.full(n, 2*cubic), mu=np.zeros(n)),
        dict(name='finite_storage_radial_peak', v=x*f[:, None], gradient=grad,
            exact_div=div, kind='radial', lam=lam, mu=mu),
        dict(name='compact_radial_virtual', v=x*compact_f[:, None],
            gradient=compact_f[:, None, None]*eye+compact_lam[:, None, None]*x[:, :, None]*x[:, None, :],
            exact_div=3*compact_f+compact_lam*r2, kind='radial', lam=compact_lam, mu=compact_mu),
        dict(name='rigid_translation', v=np.broadcast_to([.01, -.02, .03], (n, 3)),
            gradient=zero, exact_div=np.zeros(n), kind='affine'),
        dict(name='rigid_rotation', v=x@rotation.T, gradient=np.broadcast_to(rotation, zero.shape),
            exact_div=np.zeros(n), kind='affine')]
    for item in result:
        assert np.allclose(np.trace(item['gradient'], axis1=1, axis2=2), item['exact_div'], rtol=1e-12, atol=1e-13)
    # Independent central differences check the finite radial derivative formulas.
    rr = np.linspace(.002, .048, 17); dr = 1e-7
    lo, mid, hi = [ref.field(rr+shift, TAU) for shift in [-dr, 0., dr]]
    div_fd = 3*mid['v_over_r']+rr*(hi['v_over_r']-lo['v_over_r'])/(2*dr)
    prime_fd = (hi['div']-lo['div'])/(2*dr)
    assert np.allclose(div_fd, mid['div'], rtol=1e-6, atol=1e-9)
    assert np.allclose(prime_fd, radial_div_prime(ref, rr), rtol=1e-6, atol=1e-8)
    return result, field, dict(finite_divergence_fd_absmax_per_s=float(abs(div_fd-mid['div']).max()),
        finite_divergence_radial_derivative_fd_absmax_per_m_s=float(abs(prime_fd-radial_div_prime(ref, rr)).max()),
        finite_radial_lambda='(div-3f)/r^2, v=f(r)*x',
        finite_radial_mu='[r*d(div)/dr-5*(div-3f)]/r^4; native r>0')


def quadratic_increment(item, index, delta, x):
    if item['kind'] == 'quadratic':
        return .5*np.einsum('kab,na,nb->nk', HESS, delta, delta)
    if item['kind'] == 'radial':
        xx = x[index]; xd = np.sum(xx*delta, axis=1); dd = np.sum(delta*delta, axis=1)
        return .5*item['lam'][index, None]*(2*delta*xd[:, None]+xx*dd[:, None])+\
            .5*item['mu'][index, None]*xx*xd[:, None]**2
    return np.zeros_like(delta)


def add_scalar(out, i, j, left, right):
    out += np.bincount(i, weights=left, minlength=len(out))+np.bincount(j, weights=right, minlength=len(out))


def main():
    assert not CHECK.exists() and not (TESTS/'outputs'/TAG).exists(), 'Refuse retained analysis label/output'
    started = time.perf_counter()
    result = dict(analysis_checks_passed=False, solver_executed=False, integrated_steps=0,
        production_implemented=False, physical_acceptance=False, automatic_dynamic_run_admitted=False)
    try:
        probe_path = TESTS/'logs/cryer_symc_cpu_r1.check.json'; probe = read(probe_path)
        assert probe['analysis_checks_passed'] and probe['integrated_steps'] == 0
        links = verify(probe['inputs']+probe['artifacts'])
        links = verify(links+read(TESTS/'logs/cryer_symc_cpu_r1.inputs.json')['inputs'])
        radial_path = TESTS/'logs/cryer_radial_consistency_r1.check.json'; radial = read(radial_path)
        assert radial['analysis_checks_passed']
        initial = FOLDER/'data/Part_0000.bi4'; config = TESTS/'configs/cryer_preload_peak_r1_Def.xml'
        assert any(Path(e['path']).resolve() == initial.resolve() for e in links)
        inputs = [bound(p) for p in [Path(__file__), probe_path, radial_path, initial, config, READER,
            LIAN/'lian_release_r1.py', REPO/'src/source/JSphCpu.cpp', REPO/'src/source/JSphGpu_ker.cu',
            TESTS/'support/cryer_load_pair_r1.py', TESTS/'support/cryer_darcy_closed_r1.py',
            TESTS/'support/cryer_radial_consistency_r1.py', TESTS/'support/cryer_symc_step_screen_r1.py']]
        result['inputs'] = inputs
        a = native(FOLDER, 0); n = len(a)
        assert n == 37173 and a.id.nunique() == n and np.isfinite(a.to_numpy(dtype='<f8')).all()
        assert a.nout.eq(0).all() and a.position_double.eq(1).all() and a.rho.eq(2100).all()
        assert a.mass.eq(a.mass.iloc[0]).all()
        x = a[['x', 'y', 'z']].to_numpy(); mass = a.mass.to_numpy(); rho = a.rho.to_numpy()
        volume = mass/rho; volop = (mass.astype(np.float32)/rho.astype(np.float32)).astype(float)
        scale = float(volop[0]/volume[0]); assert np.all(volop/volume == scale)
        h = float(a.h.iloc[0]); radius = np.linalg.norm(x, axis=1)
        surface = a.fstype.isin([2, 3]).to_numpy(); assert surface.sum() == 5153
        active = ~surface; center = radius <= DP+1e-12; assert center.sum() == 18
        ctes = constants(config, h); assert ctes == radial['constants']
        mf = ctes['backends']['CPU']['kwn_pa']; ref = Reference()
        fixture, exact, derivative_test = fields(x, h, ref); nf = len(fixture)
        pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
        corr, affine = correction(x, mass, rho, h, pairs); corr /= ctes['helper_gradient_scale']*scale
        assert np.linalg.eigvalsh(corr).min() > 0
        degree = np.bincount(pairs.ravel(), minlength=n); eps = np.finfo(float).eps
        gamma = (64*degree+256)*eps/(1-(64*degree+256)*eps)
        raw = np.zeros((nf, n)); corrected = np.zeros_like(raw); linear = np.zeros_like(raw)
        second = np.zeros_like(raw); higher = np.zeros_like(raw)
        pressure = np.stack([exact['p'].copy(), Q*(1-(radius/R)**2)])
        pressure[:, surface] = 0.  # The actual open Dirichlet mask, not empty or altered.
        forces = np.zeros((2, 3, n, 3)); adjoint = np.zeros((2, n, 3))
        absolute_patch_force = np.zeros((2, n)); tail_checks = {}
        for i, j, d, g in batches(x, pairs, h):
            g *= ctes['helper_gradient_scale']; gi = np.einsum('nij,nj->ni', corr[i], g)
            gj = np.einsum('nij,nj->ni', corr[j], g); delta = -d
            for k, item in enumerate(fixture):
                dv = item['v'][j]-item['v'][i]
                li = np.einsum('nij,nj->ni', item['gradient'][i], delta)
                lj = np.einsum('nij,nj->ni', item['gradient'][j], -delta)
                qi = quadratic_increment(item, i, delta, x); qj = quadratic_increment(item, j, -delta, x)
                ri, rj = dv-li-qi, -dv-lj-qj
                add_scalar(raw[k], i, j, volume[j]*np.sum(dv*g, axis=1), volume[i]*np.sum(dv*g, axis=1))
                add_scalar(corrected[k], i, j, volop[j]*np.sum(dv*gi, axis=1), volop[i]*np.sum(dv*gj, axis=1))
                for out, left, right in [(linear[k], li, lj), (second[k], qi, qj), (higher[k], ri, rj)]:
                    add_scalar(out, i, j, volop[j]*np.sum(left*gi, axis=1), volop[i]*np.sum(right*(-gj), axis=1))
                if item['name'] == 'radial_cubic':
                    wanted = 400.*np.sum(delta*delta, axis=1)[:, None]*delta
                    tail_checks['cubic_velocity_tail_absmax_m_s'] = max(tail_checks.get('cubic_velocity_tail_absmax_m_s', 0.), float(abs(ri-wanted).max()))
            for k, p in enumerate(pressure):
                vv = volume[i]*volume[j]
                pore = -(p[i]+p[j])[:, None]*vv[:, None]*g
                load = (2*Q*vv)[:, None]*g
                stress = (p[i]+p[j]-2*Q)[:, None]*vv[:, None]*g
                for target, force in zip(forces[k], [pore, load, stress]):
                    add_pair(target, i, j, force, -force)
                adj = -(volume[i]*volop[j]*p[i])[:, None]*gi-(volume[j]*volop[i]*p[j])[:, None]*gj
                add_pair(adjoint[k], i, j, adj, -adj)
                absolute = np.linalg.norm(pore, axis=1)+np.linalg.norm(load, axis=1)+np.linalg.norm(stress, axis=1)
                add_scalar(absolute_patch_force[k], i, j, absolute, absolute)
        regions = dict(center18=center, full_support_core=radius < R-2*h,
            near_surface_interior=(radius >= R-2*h)&active, nondrained=active, drained_kinematic_only=surface)
        rows = []; identities = []
        for k, item in enumerate(fixture):
            analytic = item['exact_div']; decomposition = corrected[k]-linear[k]-second[k]-higher[k]
            budget = gamma*(abs(corrected[k])+abs(linear[k])+abs(second[k])+abs(higher[k])+1.)
            assert np.all(abs(decomposition) <= budget), item['name']+' Taylor accumulation identity'
            assert abs(linear[k]-analytic).max() < 1e-10, 'Affine local Taylor closure'
            if item['name'] in ['affine', 'rigid_translation', 'rigid_rotation']:
                assert abs(corrected[k]-analytic).max() < 1e-10
            if item['name'] == 'quadratic':
                assert abs(higher[k]).max() < 1e-10
            identities.append(dict(velocity=item['name'], decomposition_absmax_per_s=float(abs(decomposition).max()),
                decomposition_budget_absmax_per_s=float(budget.max()), linear_local_closure_absmax_per_s=float(abs(linear[k]-analytic).max())))
            for name, mask in regions.items():
                row = dict(velocity=item['name'], region=name, evolved_pressure_receiver=(name != 'drained_kinematic_only'))
                for key, values in [('raw_divergence_error_per_s', raw[k]-analytic),
                        ('corrected_divergence_error_per_s', corrected[k]-analytic),
                        ('compression_error_cpu_pa_s', -mf*(corrected[k]-analytic)),
                        ('second_Taylor_compression_contribution_pa_s', -mf*second[k]),
                        ('higher_Taylor_compression_contribution_pa_s', -mf*higher[k])]:
                    row[key] = stats(values, mask, volume)
                rows.append(row)
        virtual = []; patch = []
        for pi, p in enumerate(pressure):
            pressure_name = ['finite_storage_peak_pressure', 'smooth_quadratic_pressure'][pi]
            residual = forces[pi].sum(axis=0)
            patch_budget = gamma*absolute_patch_force[pi]
            assert np.all(np.linalg.norm(residual, axis=1) <= patch_budget), 'Constant-total-stress force patch'
            patch.append(dict(pressure=pressure_name, total_stress='S=(p-q)I, hence T=-qI; uniform rho',
                raw_confinement_unchanged=True, force_residual_absmax_N=float(np.linalg.norm(residual, axis=1).max()),
                force_accumulation_budget_absmax_N=float(patch_budget.max()),
                acceleration_residual_vector_rms_m_s2=float(np.sqrt(np.average(np.sum((residual/mass[:, None])**2, axis=1), weights=volume))),
                limitation='Force-equilibrium patch only; the chosen spatial isotropic effective stress need not be compatible with a constitutive displacement.'))
            for k, item in enumerate(fixture):
                v = item['v']; pore_power = float(np.sum(v*forces[pi, 0]))
                raw_power = float(np.sum(volume*p*raw[k])); corrected_power = float(np.sum(volume*p*corrected[k]))
                transposed_power = float(np.sum(v*adjoint[pi]))
                power_scale = float(np.sum(abs(v*forces[pi, 0]))+np.sum(abs(volume*p*raw[k]))+
                    np.sum(abs(v*adjoint[pi]))+np.sum(abs(volume*p*corrected[k])))
                budget = float(gamma.max()*power_scale+np.finfo(float).tiny)
                assert abs(pore_power-raw_power) <= budget, 'Raw pair-work identity'
                assert abs(transposed_power-corrected_power) <= budget, 'Corrected weighted transpose identity'
                virtual.append(dict(pressure=pressure_name, virtual_velocity=item['name'],
                    raw_pore_force_power_W=pore_power, raw_divergence_pressure_work_W=raw_power,
                    raw_adjoint_residual_W=pore_power-raw_power, corrected_divergence_pressure_work_W=corrected_power,
                    raw_force_vs_corrected_divergence_defect_W=pore_power-corrected_power,
                    diagnostic_transpose_force_power_W=transposed_power,
                    diagnostic_transpose_identity_residual_W=transposed_power-corrected_power,
                    arithmetic_power_budget_W=budget, raw_load_virtual_power_W=float(np.sum(v*forces[pi, 1])),
                    surface_virtual_speed_max_m_s=float(np.linalg.norm(v[surface], axis=1).max())))
        finite_index = [f['name'] for f in fixture].index('finite_storage_radial_peak')
        finite_error = float(np.average(-mf*(corrected[finite_index]-exact['div'])[center], weights=volume[center]))
        actual = next(r for r in probe['rows'] if r['region'] == 'center18')
        verify(links+inputs)
        result.update(analysis_checks_passed=True, before_after_hashes_verified=True, verified_previous_links=len(links),
            geometry=dict(native_soil_count=n, surface_dirichlet_count=int(surface.sum()), nondrained_count=int(active.sum()),
                center18_count=int(center.sum()), pair_count=len(pairs), h_m=h, operator_over_native_volume=scale),
            constants=ctes, tau_s=TAU, derivative_selftest=derivative_test, correction_affine_selftest=affine,
            polynomial_fixture=dict(affine_gradient_per_s=AFFINE_L.tolist(), quadratic_velocity_Hessian_per_m_s=HESS.tolist(),
                radial_cubic_coefficient_per_m2_s=400., compact_support_radius_m=R-2*h,
                compact_velocity='x*(1-r^2/rc^2)^3 for r<rc, otherwise zero; C2 at rc'),
            formulas=dict(divergence='D_C v_i=sum Vop_j (v_j-v_i) dot (Ci*gij)',
                Taylor='dv=grad(v_i)*delta+.5*Hess(v_i):(delta delta)+remainder; delta=xj-xi',
                radial_Hessian='lambda*(delta_ka*x_b+delta_kb*x_a+delta_ab*x_k)+mu*x_k*x_a*x_b',
                raw_pair_force='Fp_i=-Vi*Vj*(pi+pj)*gij; Fp_j=-Fp_i',
                corrected_transpose_pair_force='Fstar_i=-(Vi*Vop_j*pi*Ci+Vj*Vop_i*pj*Cj)*gij; Fstar_j=-Fstar_i',
                virtual_identity='sum v.Fp=sum Vnative*p*D_I_native(v); sum v.Fstar=sum Vnative*p*D_C(v)'),
            moment_rows=rows, Taylor_identity_checks=identities, tail_selftests=tail_checks,
            constant_total_stress_raw_load_patches=patch, virtual_work_rows=virtual,
            frozen_fused_correspondence=dict(center_double_surrogate_compression_error_cpu_pa_s=finite_error,
                center_prior_actual_fused_compression_error_pa_s=actual['actual_comp_error_pa_s_mean'],
                surrogate_minus_fused_compression_error_pa_s=finite_error-actual['actual_comp_error_pa_s_mean'],
                center_double_surrogate_compression_rate_cpu_pa_s=float(np.mean(-mf*corrected[finite_index, center])),
                center_prior_actual_fused_compression_rate_pa_s=actual['actual_comp_pa_s_mean'],
                scope='Same declared finite-Kw field and frozen geometry; surrogate is not quantized-input/float-subtraction/float-accumulation kernel replay.'),
            limitations=['Only new analysis JSON; no solver, integration, source/formal change, build, prior-output overwrite or Git.',
                'Double offline distances/sums and manufactured velocities/stresses, with rounded production constants; not fused-program bit identity.',
                'Original true Dirichlet nodes are retained neighbours. Their kinematic divergence is diagnostic only; actual evolved pressure compression there is clamped/omitted.',
                'Both virtual pressures are exactly zero on Dirichlet nodes. No actual drainage flux, moving-volume storage derivative, external continuum boundary work or total elastic energy balance is inferred.',
                'Diagnostic transpose forces are never applied to an integrator or combined with unchanged raw stress/load as a proposed scheme.',
                'Affine closure constrains first moments, not nonaffine radial consistency. Taylor terms decompose this fixed field and do not assign causal percentages to dynamic peak error.',
                'Pairwise net-force cancellation is algebraic; constant-total-stress patch tests three independently accumulated raw terms, not a new native trajectory.',
                'The prior actual fused mismatch and current surrogate error do not by themselves establish the cause of peak amplitude/time error or admit another physical run.'])
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    result['wall_seconds'] = time.perf_counter()-started
    with CHECK.open('x', encoding='utf8') as output:
        json.dump(result, output, indent=2, allow_nan=False)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'], error=result.get('error'),
        frozen_fused_correspondence=result.get('frozen_fused_correspondence'), check=str(CHECK)), indent=2), flush=True)
    if not result['analysis_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if parser.parse_args().run:
        main()
    else:
        parser.print_help()
