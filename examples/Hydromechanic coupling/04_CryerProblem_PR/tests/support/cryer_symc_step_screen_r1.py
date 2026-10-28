"""Frozen CPU-scalar Darcy row bounds only; default help, no integration."""
import argparse
import json
import time
import traceback
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import TESTS, READER, LIAN, native, bound, batches, correction
from cryer_darcy_closed_r1 import constants

TAG = 'cryer_symc_step_screen_r1'
CHECK = TESTS/'logs'/(TAG+'.check.json')
PROBE = TESTS/'logs/cryer_symc_cpu_r1.check.json'
MANIFEST = TESTS/'logs/cryer_symc_cpu_r1.inputs.json'
COMPLETE = TESTS/'logs/cryer_symc_cpu_r1.completion.json'
FOLDER = TESTS/'outputs/cryer_preload_peak_r1'
CONFIG = TESTS/'configs/cryer_preload_peak_r1_Def.xml'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify(entries):
    unique = {}
    for entry in entries:
        key = str(Path(entry['path']).resolve()).casefold()
        assert key not in unique or unique[key]['sha256'].casefold() == entry['sha256'].casefold()
        unique[key] = entry
    for entry in unique.values():
        actual = bound(Path(entry['path']))
        assert actual['sha256'].casefold() == entry['sha256'].casefold(), entry['path']
        if 'bytes' in entry:
            assert actual['bytes'] == entry['bytes'], entry['path']
    return list(unique.values())


def main():
    assert not CHECK.exists(), 'Never overwrite or restart this analysis label'
    started = time.perf_counter()
    result = dict(analysis_checks_passed=False, solver_executed=False, integrated_steps=0,
        production_implemented=False, physical_acceptance=False, automatic_dynamic_run_admitted=False)
    try:
        probe = read(PROBE)
        assert probe['analysis_checks_passed'] and probe['integrated_steps'] == 0
        assert probe['compression_and_all_six_acceleration_float_bits_0ulp']
        assert probe['geometry_and_fstype_unchanged'] and probe['drained_all_four_rates_zero']
        # Check the completed observer's links before trusting any geometry or helper.
        verified = verify(probe['inputs']+probe['artifacts'])
        verified = verify(verified+read(MANIFEST)['inputs'])
        complete = read(COMPLETE)
        assert complete['exit_code'] == 0 and complete['owned_exited'] and complete['integrated_steps'] == 0
        verified = verify(verified+complete['inputs']+complete['outputs'])
        initial = FOLDER/'data/Part_0000.bi4'
        assert any(Path(e['path']).resolve() == initial.resolve() for e in verified)
        inputs = [bound(p) for p in [Path(__file__), PROBE, MANIFEST, COMPLETE, initial, CONFIG,
            READER, LIAN/'lian_release_r1.py', Path(__file__).with_name('cryer_load_pair_r1.py'),
            Path(__file__).with_name('cryer_darcy_closed_r1.py')]]
        result['inputs'] = inputs
        result['completed_probe_verified_file_count'] = len(verified)
        a = native(FOLDER, 0)
        assert len(a) == 37173 and a.id.nunique() == len(a)
        assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.nout.eq(0).all()
        assert a.position_double.eq(1).all() and a.rho.eq(2100).all() and a.mass.eq(a.mass.iloc[0]).all()
        x = a[['x', 'y', 'z']].to_numpy(); h = float(a.h.iloc[0])
        surface = a.fstype.isin([2, 3]).to_numpy(); active = ~surface
        assert surface.sum() == 5153 and active.sum() == 32020
        volume = (a.mass/a.rho).to_numpy()
        volop = (a.mass.to_numpy(np.float32)/a.rho.to_numpy(np.float32)).astype(float)
        scale = float(volop[0]/volume[0]); assert np.all(volop/volume == scale)
        ctes = constants(CONFIG, h); cpu = ctes['backends']['CPU']
        factor = cpu['diffusion_factor_m2_s']
        assert factor > 0 and ctes['eta2_float_m2'] > 0
        pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
        corr, affine = correction(x, a.mass.to_numpy(), a.rho.to_numpy(), h, pairs)
        corr /= ctes['helper_gradient_scale']*scale
        assert np.isfinite(corr).all() and np.linalg.eigvalsh(corr).min() > 0
        n = len(a); names = ['receiver_C', 'symmetric_C']
        outgoing = np.zeros((2, n)); internal = np.zeros_like(outgoing)
        reservoir = np.zeros_like(outgoing); hmin = np.full(2, np.inf); hmax = np.full(2, -np.inf)
        positive_h = np.zeros(2, dtype=np.int64); symmetry = np.zeros((2, 4))
        minimum_conductance = np.full(2, np.inf)
        for i, j, d, g in batches(x, pairs, h):
            g *= ctes['helper_gradient_scale']; den = np.sum(d*d, axis=1)+ctes['eta2_float_m2']
            ci = np.einsum('ni,nij,nj->n', d, corr[i], g)
            cj = np.einsum('ni,nij,nj->n', d, corr[j], g)
            both = active[i]&active[j]
            for op, name in enumerate(names):
                hi = ci/den if name == 'receiver_C' else .5*(ci+cj)/den
                hj = cj/den if name == 'receiver_C' else hi
                hmin[op] = min(hmin[op], float(min(hi.min(), hj.min())))
                hmax[op] = max(hmax[op], float(max(hi.max(), hj.max())))
                positive_h[op] += np.count_nonzero(hi[active[i]] > 0)+np.count_nonzero(hj[active[j]] > 0)
                kij = -factor*volop[j]*hi; kji = -factor*volop[i]*hj
                minimum_conductance[op] = min(minimum_conductance[op], float(min(kij.min(), kji.min())))
                outgoing[op] += np.bincount(i, weights=kij, minlength=n)+np.bincount(j, weights=kji, minlength=n)
                internal[op] += np.bincount(i, weights=kij*active[j], minlength=n)+np.bincount(j, weights=kji*active[i], minlength=n)
                reservoir[op] += np.bincount(i, weights=kij*surface[j], minlength=n)+np.bincount(j, weights=kji*surface[i], minlength=n)
                # Selfadjointness belongs to the non-Dirichlet principal block.
                wi, wj = volop[i]*kij, volop[j]*kji
                ni, nj = volume[i]*kij, volume[j]*kji
                symmetry[op] += [np.sum(abs(wi[both]-wj[both])), np.sum(abs(wi[both])+abs(wj[both])),
                    np.sum(abs(ni[both]-nj[both])), np.sum(abs(ni[both])+abs(nj[both]))]
        assert not positive_h.any() and minimum_conductance.min() >= 0
        rows = []
        for op, name in enumerate(names):
            aa, bb, rr = outgoing[op, active], internal[op, active], reservoir[op, active]
            assert np.isfinite(aa).all() and aa.min() > 0 and bb.min() >= 0 and rr.min() >= 0
            identity = float(abs(aa-bb-rr).max()); budget = 128*np.finfo(float).eps*float(aa.max())
            assert identity <= budget, 'Row diagonal/internal/reservoir identity failed'
            max_index = np.flatnonzero(active)[int(aa.argmax())]; maxrow = float(aa.max())
            ratio_op = float(symmetry[op, 0]/symmetry[op, 1])
            ratio_native = float(symmetry[op, 2]/symmetry[op, 3])
            if name == 'symmetric_C':
                assert ratio_op <= 16*np.finfo(float).eps and ratio_native <= 16*np.finfo(float).eps
            rows.append(dict(stencil=name, receiver_count=int(active.sum()), all_neighbours_include_dirichlet=True,
                H_min=float(hmin[op]), H_max=float(hmax[op]), positive_H_active_count=int(positive_h[op]),
                negative_offdiagonal_count=0, minimum_pair_conductance_per_s=float(minimum_conductance[op]),
                max_outgoing_conductance_sum_per_s=maxrow, max_row_native_id=int(a.id.iloc[max_index]),
                max_row_initial_position_m=x[max_index].tolist(),
                max_internal_offdiagonal_row_sum_per_s=float(bb.max()), max_reservoir_row_sum_per_s=float(rr.max()),
                row_identity_absmax_per_s=identity, row_identity_double_budget_per_s=budget,
                weighted_principal_block_pair_asymmetry_relative_operator_volume=ratio_op,
                weighted_principal_block_pair_asymmetry_relative_native_volume=ratio_native,
                sufficient_FE_Heun_dt_s=1/maxrow,
                gershgorin_spectral_radius_upper_bound_per_s=2*maxrow,
                tighter_gershgorin_abs_upper_bound_per_s=float((aa+bb).max()),
                proposed_steps=[dict(label=label, dt_s=dt, dt_times_max_row=dt*maxrow,
                    sufficient_frozen_scalar_screen_passed=bool(dt*maxrow <= 1))
                    for label, dt in [('coarse_2pow_minus21', 2.**-21), ('half_2pow_minus22', 2.**-22)]]))
        verify(verified+inputs)
        result.update(analysis_checks_passed=True, completed_probe_and_inputs_reverified=True,
            coarse_dt_s=2.**-21, half_dt_s=2.**-22,
            coarse_dt_admitted=rows[1]['proposed_steps'][0]['sufficient_frozen_scalar_screen_passed'],
            half_dt_admitted=rows[1]['proposed_steps'][1]['sufficient_frozen_scalar_screen_passed'],
            dt_admission_scope='Symmetric-C frozen CPU scalar FE/Heun sufficient bound only; not coupled or dynamic admission.',
            native_reader_executed=True, constants=ctes, scalar_backend='CPU_constants_only',
            geometry=dict(native_soil_count=n, dirichlet_count=int(surface.sum()), nondrained_count=int(active.sum()),
                pair_count=len(pairs), h_m=h, operator_over_native_volume=scale,
                correction_positive_eigenvalue_min=float(np.linalg.eigvalsh(corr).min())),
            correction_affine_selfcheck=affine, rows=rows,
            formulas=dict(offdiagonal='kij=-[2Mf*k/(rho_w*g)]*Vop_j*Hij >= 0',
                diagonal='Lii=-ai; ai=sum over ALL neighbours kij, including pressure-zero Dirichlet neighbours',
                principal_row='bi=sum over nondrained neighbours kij; ri=sum over Dirichlet neighbours kij; ai=bi+ri',
                sufficient_step='dt<=1/max(ai): I+dt*L is nonnegative substochastic; Heun=.5I+.5(I+dtL)^2',
                gershgorin='disc(-ai,bi), bi<=ai; rho(L)<=max(ai+bi)<=2max(ai)'),
            limitations=['Frozen original Part0 geometry, uniform density and fixed material coefficients only.',
                'Float bwen/Eta2/volumes and CPU scalar constants, but double geometry/sums; no kernel bit replay.',
                'Symmetric-C is weighted selfadjoint on the frozen principal block; receiver-C need not be, but still has the stated sufficient monotone scalar step bound.',
                'FE/Heun positivity/contraction screen is sufficient, not a measured eigenvalue or necessary limit.',
                'The production coupled symplectic predictor/corrector is not identified with standalone Heun here.',
                'No proof for elastic/inertial coupling, moving graph/density/CorrMat, future states, GPU or complete fluid mass.',
                'No timestep, damping, equations, source, formal inputs or prior thresholds were changed; no dynamic run is automatically admitted.'])
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    result['wall_seconds'] = time.perf_counter()-started
    with CHECK.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'],
        rows=result.get('rows'), error=result.get('error'), check=str(CHECK)), indent=2), flush=True)
    if not result['analysis_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if parser.parse_args().run:
        main()
    else:
        parser.print_help()
