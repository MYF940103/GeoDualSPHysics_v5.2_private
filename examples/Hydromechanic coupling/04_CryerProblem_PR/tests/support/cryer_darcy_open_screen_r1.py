"""Six frozen Darcy stencils on the sealed finite-Kw open Cryer fields. No solver."""
import argparse
import json
import time
import traceback
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_radial_consistency_r1 import Reference, TAUS, stats
from cryer_load_pair_r1 import (TESTS, REPO, LIAN, READER, R, Q, DP, native,
    bound, write_json, batches, correction)

TAG = 'cryer_darcy_open_screen_r1'
STENCILS = [(name, denominator) for name in ['receiver_C', 'raw_I', 'symmetric_C']
    for denominator in ['r2_plus_eta2', 'r2']]


def prerequisites():
    records = []; checks = {}
    for name in ['cryer_radial_consistency_r1', 'cryer_radial_force_r2', 'cryer_radial_moments_r1']:
        path = TESTS/'logs'/(name+'.check.json')
        check = json.loads(path.read_text()); assert check['analysis_checks_passed'], name
        checks[name] = check
        records += [bound(path)]+check['inputs']+check['artifacts']
    actual = checks['cryer_radial_force_r2']
    assert actual['integrated_steps'] == 0 and actual['viscosity_pressure_0ulp']
    assert actual['actual_drainage_active'] and actual['drained_rate_pressure_zero']
    completion = checks['cryer_radial_consistency_r1']['peak_verification']['completion']
    assert bound(completion['path'])['sha256'] == completion['sha256']
    sealed = json.loads(Path(completion['path']).read_text())
    initial = [entry for entry in sealed['outputs'] if Path(entry['path']).name == 'Part_0000.bi4']
    assert len(initial) == 1
    records += initial
    records += [bound(p) for p in [Path(__file__), TESTS/'notes'/(TAG+'.json'), READER,
        LIAN/'lian_release_r1.py', Path(__file__).with_name('cryer_radial_consistency_r1.py'),
        Path(__file__).with_name('cryer_load_pair_r1.py'),
        Path(__file__).with_name('cryer_darcy_closed_r1.py')]]
    records += [bound(REPO/'src/source'/p) for p in
        ['JSphCpu.cpp', 'JSphGpu_ker.cu', 'JSph.cpp', 'FunSphKernel.h']]
    unique = {}
    for entry in records:
        assert entry['path'] not in unique or unique[entry['path']]['sha256'] == entry['sha256']
        unique[entry['path']] = entry
    for entry in unique.values():
        assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']
    return checks['cryer_radial_consistency_r1'], list(unique.values())


def apply_stencils(x, pairs, h, corr, volume, volop, ctes, pressure, velocity):
    n, nf = pressure.shape
    lap = np.zeros((6, n, nf)); div = np.zeros((n, len(TAUS)))
    absdiv = np.zeros_like(div); abslap = np.zeros_like(div)
    symmetry = np.zeros((6, 2)); hmin = np.full(6, np.inf); hmax = np.full(6, -np.inf)
    positive_h = np.zeros(6, dtype=np.int64); pair_power = np.zeros((6, 3))
    for i, j, d, g in batches(x, pairs, h):
        g = g*ctes['helper_gradient_scale']; r2 = np.sum(d*d, axis=1); assert r2.min() > 0
        gi = np.einsum('nij,nj->ni', corr[i], g)
        gj = np.einsum('nij,nj->ni', corr[j], g)
        dv = velocity[j]-velocity[i]
        di = volop[j, None]*np.einsum('ntk,nk->nt', dv, gi)
        dj = volop[i, None]*np.einsum('ntk,nk->nt', dv, gj)
        for t in range(len(TAUS)):
            div[:, t] += np.bincount(i, weights=di[:, t], minlength=n)
            div[:, t] += np.bincount(j, weights=dj[:, t], minlength=n)
            absdiv[:, t] += np.bincount(i, weights=abs(di[:, t]), minlength=n)
            absdiv[:, t] += np.bincount(j, weights=abs(dj[:, t]), minlength=n)
        ci = np.sum(d*gi, axis=1); cj = np.sum(d*gj, axis=1)
        raw = np.sum(d*g, axis=1); delta = pressure[i]-pressure[j]
        for op, (name, denominator) in enumerate(STENCILS):
            den = r2+(ctes['eta2_float_m2'] if denominator == 'r2_plus_eta2' else 0.)
            if name == 'receiver_C': hi, hj = ci/den, cj/den
            else:
                hi = (raw if name == 'raw_I' else .5*(ci+cj))/den; hj = hi
            hmin[op] = min(hmin[op], float(min(hi.min(), hj.min())))
            hmax[op] = max(hmax[op], float(max(hi.max(), hj.max())))
            positive_h[op] += np.count_nonzero(hi > 0)+np.count_nonzero(hj > 0)
            wi = 2*volume[i]*volop[j]*hi; wj = 2*volume[j]*volop[i]*hj
            symmetry[op] += [np.sum(abs(wi-wj)), np.sum(abs(wi)+abs(wj))]
            left = 2*volop[j, None]*hi[:, None]*delta
            right = -2*volop[i, None]*hj[:, None]*delta
            for f in range(nf):
                lap[op, :, f] += np.bincount(i, weights=left[:, f], minlength=n)
                lap[op, :, f] += np.bincount(j, weights=right[:, f], minlength=n)
                if op == 0 and f < len(TAUS):
                    abslap[:, f] += np.bincount(i, weights=abs(left[:, f]), minlength=n)
                    abslap[:, f] += np.bincount(j, weights=abs(right[:, f]), minlength=n)
            # Shared-H random-field power identity; receiver-C value is diagnostic only.
            du, dv = delta[:, -2], delta[:, -1]
            pair_power[op] += [np.sum(wi*du*dv), np.sum(wi*du*du), np.sum(wi*dv*dv)]
    return lap, div, absdiv, abslap, symmetry, hmin, hmax, positive_h, pair_power


def main():
    checkpath = TESTS/'logs'/(TAG+'.check.json')
    csv = TESTS/'figures'/(TAG+'_regions.csv'); patchcsv = TESTS/'figures'/(TAG+'_patches.csv')
    assert not any(p.exists() for p in [checkpath, csv, patchcsv]), 'Never overwrite evidence'
    start = time.perf_counter(); result = dict(analysis_checks_passed=False, solver_executed=False,
        production_implemented=False, physical_acceptance=False, automatic_formal_run_admitted=False)
    try:
        prior, inputs = prerequisites(); result['inputs'] = inputs
        a = native(TESTS/'outputs/cryer_preload_peak_r1', 0)
        saved = np.load(TESTS/'figures/cryer_radial_consistency_r1.npz')
        x = a[['x', 'y', 'z']].to_numpy(); r = np.linalg.norm(x, axis=1)
        surface = a.fstype.isin([2, 3]).to_numpy(); volume = (a.mass/a.rho).to_numpy()
        volop = (a.mass.to_numpy(np.float32)/a.rho.to_numpy(np.float32)).astype(float)
        assert len(a) == 37173 and a.id.nunique() == len(a) and a.position_double.eq(1).all() and a.nout.eq(0).all()
        assert a.rho.eq(2100).all() and a.mass.eq(a.mass.iloc[0]).all()
        assert np.array_equal(a.id.to_numpy(), saved['id']) and np.array_equal(r, saved['radius_m'])
        assert np.array_equal(surface, saved['surface']) and surface.sum() == 5153
        scale = float(volop[0]/volume[0]); assert np.all(volop/volume == scale)
        h = float(a.h.iloc[0]); ctes = prior['constants']; assert h == ctes['h_m']
        scalar = ctes['backends']['GPU']
        mf = scalar['kwn_pa']; kappa = ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*scalar['ghyd_m_s2'])
        pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
        corr, _ = correction(x, a.mass.to_numpy(), a.rho.to_numpy(), h, pairs)
        corr /= ctes['helper_gradient_scale']*scale
        eig = np.linalg.eigvalsh(corr); assert eig.min() > 0
        degree = np.bincount(pairs.ravel(), minlength=len(a)); eps = np.finfo(float).eps
        # Budget concerns changed double operation grouping only, never a physical-rate threshold.
        gamma = (64*degree+256)*eps/(1-(64*degree+256)*eps)
        ref = Reference(); fields = [ref.field(r, tau) for tau in TAUS]
        for ti, field in enumerate(fields):
            assert abs(field['p'][surface]).max() < 1e-8
            field['p'][surface] = 0.
            assert np.array_equal(field['p'], saved[f't{ti}_p'])
        velocity = np.stack([x*f['v_over_r'][:, None] for f in fields], axis=1)
        gradient = np.array([17000., -11000., 7000.])
        hessian = np.array([[2e6, 3e5, -4e5], [3e5, -7e5, 2e5], [-4e5, 2e5, 1.4e6]])
        affine = x@gradient; quadratic = affine+.5*np.einsum('ni,ij,nj->n', x, hessian, x)
        random = np.random.default_rng(104729).normal(size=(len(a), 2))*Q
        pressure = np.column_stack([f['p'] for f in fields]+[np.full(len(a), Q), affine, quadratic, random])
        lap, div, absdiv, abslap, sym, hmin, hmax, positive, pairpower = apply_stencils(
            x, pairs, h, corr, volume, volop, ctes, pressure, velocity)
        assert np.isfinite(lap).all() and np.isfinite(div).all() and not positive.any()
        masks = dict(center18=r <= DP+1e-12, full_support_core=r < R-2*h,
            near_surface_interior=(r >= R-2*h)&~surface, nondrained=~surface)
        assert masks['center18'].sum() == 18 and all(mask.any() and not (mask&surface).any() for mask in masks.values())
        rows = []; baseline = []; energies = []; algebra = []; patchrows = []
        for ti, (tau, field) in enumerate(zip(TAUS, fields)):
            comp = -mf*div[:, ti]; ce = -mf*(div[:, ti]-field['div'])
            for op, (name, denominator) in enumerate(STENCILS):
                darcy = mf*kappa*lap[op, :, ti]; de = mf*kappa*(lap[op, :, ti]-field['lap'])
                net = comp+darcy; error = net-field['pt']
                if op == 0:
                    budget = gamma*(mf*absdiv[:, ti]+mf*kappa*abslap[:, ti]
                        +abs(mf*field['div'])+abs(mf*kappa*field['lap'])+abs(field['pt'])+1)
                    for key, value in [('comp_error', ce), ('darcy_error', de), ('net_error', error)]:
                        diff = abs(value-saved[f't{ti}_{key}']); assert np.all(diff <= budget), (tau, key)
                        baseline.append(dict(tau_s=tau, field=key, difference_absmax_pa_s=float(diff.max()),
                            budget_absmax_pa_s=float(budget.max()), worst_budget_fraction=float((diff/budget).max())))
                for region, mask in masks.items():
                    row = dict(tau_s=tau, stencil=name, denominator=denominator, region=region,
                        count=int(mask.sum()), scalar_backend='GPU_constants_only')
                    values = dict(compression_pa_s=comp, darcy_pa_s=darcy, net_pa_s=net,
                        compression_error_pa_s=ce, darcy_error_pa_s=de, net_error_pa_s=error,
                        scalar_model_error_pa_s=mf*(-field['div']+kappa*field['lap'])-field['pt'])
                    for key, value in values.items():
                        row.update({key+'_'+k:v for k,v in stats(value, mask, volume).items() if k != 'count'})
                    rows.append(row)
                p = field['p']; F = .5*float(np.dot(volume, p*p))
                energies.append(dict(tau_s=tau, stencil=name, denominator=denominator,
                    pressure_quadratic_pa2_m3=F, conditional_pressure_energy_J=F/mf,
                    quadratic_comp_change_pa2_m3_s=float(np.dot(volume*p, comp)),
                    quadratic_darcy_change_pa2_m3_s=float(np.dot(volume*p, darcy)),
                    quadratic_net_change_pa2_m3_s=float(np.dot(volume*p, net)),
                    closed_graph_all_receiver_rate_pa_m3_s=float(np.dot(volume, darcy)),
                    open_nondrained_rate_pa_m3_s=float(np.dot(volume[~surface], darcy[~surface])),
                    surface_raw_reservoir_gain_removed_by_clamp_pa_m3_s=float(np.dot(volume[surface], darcy[surface])),
                    note='Surface remains a p=0 neighbour; its raw receiver rate is NOT evolved.'))
        for op, (name, denominator) in enumerate(STENCILS):
            assert np.array_equal(lap[op, :, 5], np.zeros(len(a))), 'Computed constant null failed'
            u, v = random.T; Lu, Lv = lap[op, :, -2], lap[op, :, -1]
            cross = float(np.dot(volume*u, Lv)); reverse = float(np.dot(volume*v, Lu))
            e_u, e_v = float(np.dot(volume*u, Lu)), float(np.dot(volume*v, Lv))
            budget = float(gamma.max()*(np.dot(volume*abs(u), abs(Lv))
                +np.dot(volume*abs(v), abs(Lu))+abs(pairpower[op]).sum()+1))
            if name != 'receiver_C':
                assert abs(cross-reverse) <= budget and abs(cross-pairpower[op, 0]) <= budget
                assert abs(e_u-pairpower[op, 1]) <= budget and abs(e_v-pairpower[op, 2]) <= budget
                assert e_u <= budget and e_v <= budget and sym[op, 0] <= eps*sym[op, 1]*8
            algebra.append(dict(stencil=name, denominator=denominator, H_min=float(hmin[op]), H_max=float(hmax[op]),
                H_positive_count=int(positive[op]), weighted_pair_antisymmetry_L1=float(sym[op, 0]),
                relative_weighted_pair_antisymmetry=float(sym[op, 0]/sym[op, 1]),
                constant_null_actual_absmax=float(abs(lap[op, :, 5]).max()),
                random_cross_power=cross, random_reverse_cross_power=reverse,
                random_selfadjoint_defect=cross-reverse, random_quadratic_power=[e_u, e_v],
                shared_H_pair_power=pairpower[op].tolist(), double_arithmetic_budget=budget,
                closed_graph_only=True, coupled_stability_accepted=False))
            for region, mask in masks.items():
                row = dict(stencil=name, denominator=denominator, region=region, count=int(mask.sum()))
                for key, value in [('affine_laplacian_mismatch_pa_m2', lap[op, :, 6]),
                    ('quadratic_laplacian_error_pa_m2', lap[op, :, 7]-np.trace(hessian))]:
                    row.update({key+'_'+k:v for k,v in stats(value, mask, volume).items() if k != 'count'})
                patchrows.append(row)
        pd.DataFrame(rows).to_csv(csv, index=False, float_format='%.17g')
        pd.DataFrame(patchrows).to_csv(patchcsv, index=False, float_format='%.17g')
        result.update(analysis_checks_passed=True, baseline_reproduction=baseline, constants=ctes,
            scalar_backend='GPU_constants_only', pair_count=len(pairs), source_geometry=bound(TESTS/'outputs/cryer_preload_peak_r1/data/Part_0000.bi4'),
            geometry=dict(native_soil_count=len(a), dirichlet_surface_count=int(surface.sum()),
                center18_count=int(masks['center18'].sum()), radius_min_m=float(r.min()), radius_max_m=float(r.max()),
                native_volume_m3=float(volume.sum()), operator_over_native_volume=scale, correction_eigenvalue_min=float(eig.min())),
            arithmetic_budget='gamma_(64*neighbour_count+256) times absolute baseline rate-term sum, float64 epsilon; not a physical threshold',
            algebra_checks=algebra, pressure_quadratic_and_open_sink=energies,
            patch_definition=dict(affine_gradient_pa_m=gradient.tolist(), quadratic_hessian_pa_m2=hessian.tolist(),
                quadratic_exact_laplacian_pa_m2=float(np.trace(hessian)),
                note='Patch values are not clamped on the outer surface. Nonzero affine Laplacian is measured, not asserted away.'),
            artifacts=[bound(csv), bound(patchcsv)])
    except Exception as exc:
        result.update(error=repr(exc), traceback=traceback.format_exc())
    result.update(wall_seconds=time.perf_counter()-start, limitations=[
        'Frozen finite-Kw quasistatic fields; no trajectory, new production operator, physical acceptance or formal admission.',
        'Compression is always the existing receiver-C divergence; only three Darcy stencils and two denominators vary.',
        'Dirichlet nodes remain pressure-zero neighbours but never enter physical receiver-region statistics.',
        'Zero weighted pair sum/selfadjointness is a closed-graph property, not zero drainage or exact fluid-mass conservation.',
        'H<=0 is the pressure suboperator sign structure, not complete coupled-system energy or time-integration stability.',
        'Native-volume quadratic pressure functional and its Mf-normalized value are conditional observables, not total energy.',
        'Offline double geometry/summation with GPU scalar constants is not a GPU or CPU bitwise kernel replay.',
        'Affine/quadratic patches diagnose local reproduction; surface-truncated supports have nonzero boundary flux.',
        'The baseline reproduction budget is double arithmetic only and does not change any existing physical guard.'])
    write_json(checkpath, result)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'], error=result.get('error'),
        wall_seconds=result['wall_seconds'])), flush=True)
    if not result['analysis_checks_passed']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if parser.parse_args().run: main()
    else: parser.print_help()
