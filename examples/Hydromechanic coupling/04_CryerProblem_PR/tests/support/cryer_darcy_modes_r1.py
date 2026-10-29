"""Three fixed-R Dirichlet radial modes on the retained Darcy graph; no solver."""
import os
for _name in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_name] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import TESTS, REPO, LIAN, READER, R, native, bound, batches, correction
from cryer_darcy_closed_r1 import constants
from cryer_radial_consistency_r1 import stats
from cryer_symc_step_screen_r1 import read, verify

TAG = 'cryer_darcy_modes_r1'
CHECK = TESTS/'logs'/(TAG+'.check.json')
FOLDER = TESTS/'outputs/cryer_preload_peak_r1'
CONFIG = TESTS/'configs/cryer_preload_peak_r1_Def.xml'
OPERATORS = ['receiver_C', 'symmetric_C']


def modes(radius, surface):
    numbers = np.arange(1, 4)
    phi = np.sinc(np.asarray(radius)[:, None]*numbers[None, :]/R)
    surface_roundoff = float(abs(phi[surface]).max())
    phi[surface] = 0.  # Exact prescribed p_D=0; these nodes remain neighbours.
    return phi, (numbers*np.pi/R)**2, surface_roundoff


def pair_rates(delta, vi, vj, hi, hj):
    return 2*vj[:, None]*hi[:, None]*delta, -2*vi[:, None]*hj[:, None]*delta


def apply_modes(x, pairs, h, corr, volop, ctes, phi):
    lap = np.zeros((2, len(x), 3))
    for i, j, d, g in batches(x, pairs, h):
        g = g*ctes['helper_gradient_scale']
        denominator = np.sum(d*d, axis=1)+ctes['eta2_float_m2']
        hi = np.einsum('ni,nij,nj->n', d, corr[i], g)/denominator
        hj = np.einsum('ni,nij,nj->n', d, corr[j], g)/denominator
        for op, (left_h, right_h) in enumerate([(hi, hj), (.5*(hi+hj), .5*(hi+hj))]):
            left, right = pair_rates(phi[i]-phi[j], volop[i], volop[j], left_h, right_h)
            for mode in range(3):
                lap[op, :, mode] += np.bincount(i, weights=left[:, mode], minlength=len(x))
                lap[op, :, mode] += np.bincount(j, weights=right[:, mode], minlength=len(x))
    return lap


def projection(phi, lap, volume, exact_lambda):
    norm_phi2 = float(np.dot(volume, phi*phi))
    norm_lap2 = float(np.dot(volume, lap*lap))
    assert norm_phi2 > 0 and norm_lap2 > 0
    projected = -float(np.dot(volume*phi, lap))/norm_phi2
    residual = lap+projected*phi
    error = lap+exact_lambda*phi
    cosine = float(np.clip(projected*np.sqrt(norm_phi2/norm_lap2), -1., 1.))
    rms = lambda values: float(np.sqrt(np.dot(volume, values*values)/volume.sum()))
    return dict(projected_decay_per_m2=projected, exact_decay_per_m2=float(exact_lambda),
        projected_over_exact=projected/exact_lambda,
        exact_pairing_relative_rhs_error=float(np.sqrt(np.dot(volume, error*error)/(exact_lambda**2*norm_phi2))),
        projected_residual_relative_to_rhs=float(np.sqrt(np.dot(volume, residual*residual)/norm_lap2)),
        projected_residual_rms_per_m2=rms(residual), continuum_rhs_error_rms_per_m2=rms(error),
        cosine_with_exact_rhs=cosine, angle_with_exact_rhs_degrees=float(np.degrees(np.arccos(cosine))),
        weighted_phi_squared_m3=norm_phi2, weighted_rhs_squared_per_m=float(norm_lap2)), residual, error


def selftest():
    phi, eigenvalues, roundoff = modes(np.array([0., .013, R]), np.array([False, False, True]))
    assert np.array_equal(phi[0], np.ones(3)) and np.array_equal(phi[-1], np.zeros(3))
    assert roundoff < 1e-15 and np.all(np.diff(eigenvalues) > 0)
    volume = np.array([.2, .7, .4]); values = np.array([1., -.3, .2]); exact = 17.
    result, residual, error = projection(values, -exact*values, volume, exact)
    assert abs(result['projected_decay_per_m2']-exact) < 1e-13
    assert abs(residual).max() < 1e-13 and abs(error).max() == 0
    perturbation = np.array([.2, .4, -.1])
    perturbation -= values*np.dot(volume*values, perturbation)/np.dot(volume, values*values)
    mixed, _, _ = projection(values, -exact*values+perturbation, volume, exact)
    assert abs(mixed['projected_decay_per_m2']-exact) < 1e-13
    assert mixed['projected_residual_relative_to_rhs'] > 0 and mixed['angle_with_exact_rhs_degrees'] > 0
    vi, vj, delta = np.array([.6]), np.array([.4]), np.array([[1.5, -.7, 0.]])
    left, right = pair_rates(delta, vi, vj, np.array([-4.]), np.array([-4.]))
    assert left[0, 0] < 0 and right[0, 0] > 0
    assert abs(vi[:, None]*left+vj[:, None]*right).max() < 1e-14
    return dict(passed=True, checks=['sinc origin and exact Dirichlet prescription',
        'weighted projection of an exact mode and an orthogonal perturbation',
        'factor-two pair signs and shared-H weighted cancellation'],
        native_reader_executed=False, files_written=False, solver_executed=False)


def prerequisites():
    paths = {name: TESTS/'logs'/(name+'.check.json') for name in
        ['cryer_darcy_open_screen_r1', 'cryer_radial_consistency_r1', 'cryer_symc_cpu_r1']}
    old = {name: read(path) for name, path in paths.items()}
    assert all(item['analysis_checks_passed'] for item in old.values())
    assert old['cryer_symc_cpu_r1']['integrated_steps'] == 0
    files = [Path(__file__), TESTS/'notes'/(TAG+'.json'), CONFIG, FOLDER/'data/Part_0000.bi4',
        READER, LIAN/'lian_release_r1.py', LIAN/'read_hydro_native.cpp']
    files += [Path(__file__).with_name(name) for name in ['cryer_load_pair_r1.py',
        'cryer_darcy_closed_r1.py', 'cryer_radial_consistency_r1.py', 'cryer_symc_step_screen_r1.py']]
    files += [REPO/'src/source'/name for name in ['JSphCpu.cpp', 'JSphGpu_ker.cu', 'JSph.cpp', 'FunSphKernel.h']]
    links = [bound(path) for path in list(paths.values())+files]
    for item in old.values():
        links += item['inputs']+item.get('artifacts', [])
    return old['cryer_radial_consistency_r1'], verify(links)


def main():
    assert not CHECK.exists(), 'Never overwrite or rerun this retained analysis label'
    started = time.perf_counter()
    result = dict(analysis_checks_passed=False, solver_executed=False, integrated_steps=0,
        production_implemented=False, physical_acceptance=False, automatic_dynamic_run_admitted=False)
    try:
        prior, inputs = prerequisites(); result['inputs'] = inputs
        result['pure_selftest'] = selftest()
        a = native(FOLDER, 0)
        assert len(a) == 37173 and a.id.nunique() == len(a) and np.array_equal(a.id, np.arange(8, 37181))
        assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.time_s.eq(0).all() and a.nout.eq(0).all()
        assert a.position_double.eq(1).all() and a.rho.eq(2100).all() and a.mass.eq(a.mass.iloc[0]).all()
        x = a[['x', 'y', 'z']].to_numpy(); radius = np.linalg.norm(x, axis=1)
        surface = a.fstype.isin([2, 3]).to_numpy(); active = ~surface
        assert surface.sum() == 5153 and active.sum() == 32020
        assert abs(radius[surface]-R).max() < 1e-14 and radius[active].max() <= .0475+1e-14
        with np.load(TESTS/'figures/cryer_radial_consistency_r1.npz') as saved:
            assert np.array_equal(a.id, saved['id']) and np.array_equal(radius, saved['radius_m'])
            assert np.array_equal(surface, saved['surface'])
        mass, rho, h = a.mass.to_numpy(), a.rho.to_numpy(), float(a.h.iloc[0])
        volume = mass/rho; volop = (mass.astype(np.float32)/rho.astype(np.float32)).astype(float)
        scale = float(volop[0]/volume[0]); assert np.all(volop/volume == scale)
        ctes = constants(CONFIG, h); assert ctes == prior['constants']
        pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
        corr, affine = correction(x, mass, rho, h, pairs)
        corr /= ctes['helper_gradient_scale']*scale
        assert np.linalg.eigvalsh(corr).min() > 0
        phi, exact_lambda, surface_roundoff = modes(radius, surface)
        lap = apply_modes(x, pairs, h, corr, volop, ctes, phi)
        assert np.isfinite(lap).all() and np.array_equal(phi[surface], np.zeros((5153, 3)))
        # L_h includes factor 2. The pressure-only Darcy coefficient is D/2,
        # not the coupled Cryer consolidation coefficient cv.
        prefactors = {name: values['diffusion_factor_m2_s']/2 for name, values in ctes['backends'].items()}
        rows, shells = [], []; edges = np.linspace(0., R, 21)
        masks = [(radius >= edges[k])&(radius < edges[k+1])&active for k in range(20)]
        assert sum(int(mask.sum()) for mask in masks) == int(active.sum())
        for op, name in enumerate(OPERATORS):
            for mode in range(3):
                metrics, _, _ = projection(
                    phi[active, mode], lap[op, active, mode], volume[active], exact_lambda[mode])
                row = dict(operator=name, mode=mode+1, receiver_count=int(active.sum()), **metrics)
                row['physical_scalar_decay_per_s'] = {backend: dict(
                    projected=alpha*metrics['projected_decay_per_m2'], exact=alpha*float(exact_lambda[mode]))
                    for backend, alpha in prefactors.items()}
                rows.append(row)
                for band, mask in enumerate(masks):
                    if not mask.any():
                        shells.append(dict(operator=name, mode=mode+1, band=band,
                            r_min_m=float(edges[band]), r_max_m=float(edges[band+1]), count=0))
                        continue
                    shell = dict(operator=name, mode=mode+1, band=band,
                        r_min_m=float(edges[band]), r_max_m=float(edges[band+1]), count=int(mask.sum()))
                    for key, value in [('laplacian_per_m2', lap[op, :, mode]),
                            ('continuum_rhs_error_per_m2', lap[op, :, mode]+exact_lambda[mode]*phi[:, mode]),
                            ('global_projection_residual_per_m2', lap[op, :, mode]+metrics['projected_decay_per_m2']*phi[:, mode])]:
                        shell[key] = stats(value, mask, volume)
                    shells.append(shell)
        verify(inputs)
        result.update(analysis_checks_passed=True, before_after_hashes_verified=True, native_reader_executed=True,
            constants=ctes, scalar_Darcy_prefactor_m2_s=prefactors, projection_rows=rows, radial_shells=shells,
            correction_affine_selfcheck=affine,
            geometry=dict(native_soil_count=len(a), dirichlet_count=int(surface.sum()), nondrained_count=int(active.sum()),
                native_ids_sha256=hashlib.sha256(a.id.to_numpy(dtype='<u4').tobytes()).hexdigest(),
                pair_count=len(pairs), actual_boundary_radius_m=R, nondrained_radius_max_m=float(radius[active].max()),
                native_volume_m3=float(volume.sum()), native_over_geometric_volume=float(volume.sum()/(4*np.pi*R**3/3)),
                operator_over_native_volume=scale, correction_matrices_sha256=hashlib.sha256(corr.astype('<f8').tobytes()).hexdigest()),
            surface_values=dict(analytic_sinc_roundoff_before_exact_prescription=surface_roundoff,
                prescribed_phi_absmax=float(abs(phi[surface]).max()), raw_surface_rhs_not_evolved=True),
            formulas=dict(mode='phi_n(r)=sinc(n*pi*r/R), sinc(z)=sin(z)/z; n=1,2,3; R=.05m',
                exact_pairing='Laplacian(phi_n)=-(n*pi/R)^2*phi_n on the actual sphere, including its smooth origin limit',
                discrete='Lh_i=2 sum_j Vop_j*(phi_i-phi_j)*[dij dot Ci*gij]/(rij^2+Eta2); symmetric uses (Ci+Cj)/2',
                projection='lambda_hat=-<phi,Lh phi>_V/<phi,phi>_V; inner product and all RHS norms use nondrained rows only',
                physical='pdot_D=alpha_D*Lh p; alpha_D=(Kw/n)*k/(rho_w*g)=stored_diffusion_factor/2; CPU/GPU scalar constants only',
                angle='angle(Lh phi,-lambda_exact phi) in the same native-volume weighted nondrained inner product'),
            artifacts=[])
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    result.update(wall_seconds=time.perf_counter()-started, limitations=[
        'Pressure-only frozen Darcy mode projections, not computed eigenvectors/eigenvalues of the coupled Cryer system.',
        'The receiver-C projection is not a variational eigenvalue bound; projected decay and shape residual must be read together.',
        'All 5153 Dirichlet nodes remain exact-zero neighbours; their raw receiver rows never enter RHS norms or projections.',
        'Uses existing native geometry/correction definitions and float scalar constants with offline double sums; not backend bit replay.',
        'No radius, mass, volume, permeability, boundary, denominator, theory clock or physical guard is adjusted.',
        'No solver, integration, source/formal change, physical acceptance or automatic follow-on run.'])
    with CHECK.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'], error=result.get('error'),
        check=str(CHECK))), flush=True)
    if not result['analysis_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    for name in ['selftest', 'run']:
        action.add_argument('--'+name, action='store_true')
    args = parser.parse_args()
    if args.selftest:
        print(json.dumps(selftest(), indent=2))
    elif args.run:
        main()
    else:
        parser.print_help()
