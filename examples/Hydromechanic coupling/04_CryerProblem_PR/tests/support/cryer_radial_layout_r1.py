"""Offline A-force decomposition and virtual layout control; explicit --run only."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import (TESTS, Q, R, DP, native, bound, write_json,
    batches, pair_components, add_pair, force_metrics)
from cryer_radial_patch_r1 import field, analytic_checks

TAG = 'cryer_radial_layout_r1'
P_OVER_Q = 1.2


def screen(x, mass, rho, h, true_surface=None):
    """Uniform-rho A=z+d; every term is accumulated from actual pairs."""
    n = len(x); volume = mass/rho; radius = np.linalg.norm(x, axis=1)
    pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
    degree = np.bincount(pairs.ravel(), minlength=n)
    stress, pore, _ = field(x, P_OVER_Q*Q)
    shifted = stress+(Q-pore)[:, None, None]*np.eye(3)
    raw = np.zeros((3, n, 3)); zero = np.zeros((n, 3))
    difference = np.zeros((n, 3)); partition_gradient = np.zeros((n, 3))
    for i, j, d, g in batches(x, pairs, h):
        identity = np.broadcast_to(np.eye(3), (len(i), 3, 3))
        original = pair_components(stress[i], stress[j], pore[i], pore[j],
            rho[i], rho[j], identity, identity, g)[0][0]
        for comp in range(3):
            add_pair(raw[comp], i, j, mass[j, None]*original[comp], -mass[i, None]*original[comp])
        ti_g = np.einsum('nij,nj->ni', shifted[i], g)
        tj_g = np.einsum('nij,nj->ni', shifted[j], g)
        delta_g = np.einsum('nij,nj->ni', shifted[j]-shifted[i], g)
        add_pair(zero, i, j, (2*volume[j]/rho[i])[:, None]*ti_g,
            (-2*volume[i]/rho[j])[:, None]*tj_g)
        add_pair(difference, i, j, (volume[j]/rho[i])[:, None]*delta_g,
            (volume[i]/rho[j])[:, None]*delta_g)
        add_pair(partition_gradient, i, j, volume[j, None]*g, -volume[i, None]*g)
    total = raw.sum(axis=0); recombined = zero+difference
    from_partition = 2/rho[:, None]*np.einsum('nij,nj->ni', shifted, partition_gradient)
    # Conservative roundoff budget for the algebra identity, not a force gate.
    scale = max(1., float(np.abs(raw).max()), float(np.abs(zero).max()), float(np.abs(difference).max()))
    budget = 256*np.finfo(float).eps*max(1, int(degree.max()))*scale
    mismatch = float(np.abs(total-recombined).max())
    partition_mismatch = float(np.abs(zero-from_partition).max())
    assert mismatch <= budget and partition_mismatch <= budget, 'A decomposition is not rounding-consistent'
    masks = dict(whole=np.ones(n, dtype=bool), center=radius<=DP+1e-12,
        interior=radius<R-2*h, outer_shell=radius>=R-2*h)
    if true_surface is not None: masks['native_true_surface'] = true_surface
    assert all(mask.any() for mask in masks.values())
    rows = []
    for region, mask in masks.items():
        z, d = zero[mask], difference[mask]
        zrms = float(np.sqrt(np.mean(np.sum(z*z, axis=1))))
        drms = float(np.sqrt(np.mean(np.sum(d*d, axis=1))))
        cross = float(np.mean(np.sum(z*d, axis=1)))
        for term, values in [('A_original', total), ('zero_order', zero),
                             ('difference_only_diagnostic', difference), ('zero_plus_difference', recombined)]:
            selected = values[mask]; norm2 = np.sum(selected*selected, axis=1)
            rms = float(np.sqrt(np.mean(norm2)))
            rows.append(dict(region=region, term=term, count=int(mask.sum()),
                radius_min_m=float(radius[mask].min()), radius_max_m=float(radius[mask].max()),
                native_volume_m3=float(volume[mask].sum()),
                component_rms_m_s2=float(np.sqrt(np.mean(selected*selected))),
                vector_rms_m_s2=rms, vector_max_m_s2=float(np.sqrt(norm2.max())),
                volume_weighted_vector_rms_m_s2=float(np.sqrt(np.average(norm2, weights=volume[mask]))),
                zero_difference_cross_mean_m2_s4=cross,
                sum_rms_over_component_rms_sum=float(np.sqrt(np.mean(np.sum(recombined[mask]**2, axis=1)))/(zrms+drms)) if zrms+drms else None,
                neighbor_count_min=int(degree[mask].min()), neighbor_count_mean=float(degree[mask].mean()),
                neighbor_count_max=int(degree[mask].max()),
                partition_gradient_vector_rms_m_inv=float(np.sqrt(np.mean(np.sum(partition_gradient[mask]**2, axis=1)))),
                partition_gradient_vector_max_m_inv=float(np.linalg.norm(partition_gradient[mask], axis=1).max())))
    metrics = {name:force_metrics(x, mass, rho, values) for name,values in
        [('A_original', total), ('zero_order', zero), ('difference_only_diagnostic', difference)]}
    return dict(node_count=n, pair_count=len(pairs), h_m=h, particle_mass_kg=float(mass[0]),
        density_kg_m3=float(rho[0]), native_volume_m3=float(volume.sum()),
        native_volume_over_geometric_sphere=float(volume.sum()/(4*np.pi*R**3/3)),
        center_count=int(masks['center'].sum()), origin_node_count=int((radius<=1e-12).sum()),
        nodes_on_geometric_sphere=int((np.abs(radius-R)<=1e-12).sum()),
        interior_count=int(masks['interior'].sum()), outer_shell_count=int(masks['outer_shell'].sum()),
        decomposition_max_abs_m_s2=mismatch, zero_partition_identity_max_abs_m_s2=partition_mismatch,
        algebra_roundoff_budget_m_s2=budget, force_metrics=metrics), rows


def main():
    target = TESTS/'logs'/(TAG+'.check.json')
    csv = TESTS/'figures'/(TAG+'_metrics.csv')
    assert not target.exists() and not csv.exists(), 'Never overwrite retained evidence'
    started = time.perf_counter(); rows = []
    result = dict(scope='Offline causal decomposition and virtual clipped-Cartesian layout control.',
        physical_acceptance=False, production_implemented=False, solver_executed=False,
        analysis_checks_passed=False, q_pa=Q, p_over_q=P_OVER_Q, radius_m=R, dp_m=DP)
    try:
        prior_path = TESTS/'logs/cryer_radial_patch_r1.check.json'
        prior = json.loads(prior_path.read_text())
        assert prior['analysis_checks_passed'] and not prior['physical_acceptance']
        for entry in prior['inputs']:
            assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']
        result['inputs'] = [bound(Path(__file__)), bound(TESTS/'notes'/(TAG+'.md')),
            bound(prior_path)]+prior['inputs']
        result['analytic_selfcheck'] = analytic_checks()
        folder = TESTS/'outputs/cryer_grad_peak_r1'; initial = native(folder, 0)
        assert len(initial) == 37173 and initial.id.nunique() == len(initial)
        assert np.isfinite(initial.to_numpy(dtype='<f8')).all()
        assert initial.position_double.eq(1).all() and initial.rho.eq(2100).all()
        assert initial.mass.eq(initial.mass.iloc[0]).all()
        x = initial[['x','y','z']].to_numpy(); radius = np.linalg.norm(x, axis=1)
        center = radius<=DP+1e-12
        assert center.sum() == 18 and initial.time_s.eq(0).all()
        result['native_identity'] = dict(ids_sha256=hashlib.sha256(initial.id.to_numpy(dtype='<u4').tobytes()).hexdigest(),
            center_ids=list(map(int, initial.id[center])), actual_time_s=0., initial_position_double=1,
            fstype_counts={str(int(k)):int(v) for k,v in initial.fstype.value_counts().items()})
        extent = int(np.ceil(R/DP)); axis = np.arange(-extent, extent+1)*DP
        lattice = np.stack(np.meshgrid(axis, axis, axis, indexing='ij'), axis=-1).reshape(-1,3)
        lattice = lattice[np.linalg.norm(lattice, axis=1)<=R+1e-12]
        result['virtual_lattice'] = dict(rule='Origin-centered integer grid times dp; retain |x|<=R+1e-12m.',
            node_coordinates_sha256=hashlib.sha256(lattice.astype('<f8').tobytes()).hexdigest(),
            particle_volume_from_native_m3=float(initial.mass.iloc[0]/initial.rho.iloc[0]),
            dp_cubed_m3=DP**3, mass_rescaled=False, density_rescaled=False,
            note='No native IDs/FSType are fabricated. Same physical center radius; origin and center-node counts differ.')
        result['layouts'] = {}
        for name, points, surface in [('FrDraw_native', x, initial.fstype.isin([2,3]).to_numpy()),
                                      ('Cartesian_virtual', lattice, None)]:
            print('Offline layout '+name+' nodes='+str(len(points)), flush=True)
            mass = np.full(len(points), initial.mass.iloc[0]); rho = np.full(len(points), 2100.)
            metrics, table = screen(points, mass, rho, float(initial.h.iloc[0]), surface)
            result['layouts'][name] = metrics
            rows += [dict(layout=name, **row) for row in table]
        for entry in result['inputs']:
            assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']
        result['analysis_checks_passed'] = True
    except Exception as error:
        result.update(error=repr(error), traceback=traceback.format_exc())
    if rows:
        pd.DataFrame(rows).to_csv(csv, index=False, float_format='%.17g')
        result['metrics_csv'] = bound(csv)
    result.update(wall_seconds=time.perf_counter()-started, limitations=[
        'One fixed P/q=1.2 static field; offline double/rounded-kernel algebra, not production0ULP or dynamic accuracy.',
        'The virtual lattice changes node counts, native volume, center sampling and surface quadrature together; it does not prove causality from particle disorder alone.',
        'FrDraw true FSType2/3 and a geometric clipped boundary are not interchangeable. Outer-shell membership and actual neighbor counts characterize truncation.',
        'Zero-order and difference terms can cancel strongly; separate RMS contributions are not independent additive error fractions.',
        'Difference-only loses common-stress boundary traction and generally pairwise momentum balance. It is a diagnostic, not a proposed production repair.',
        'No force/mass/geometry normalization, solver, shifting, density transport or production source change.'])
    write_json(target, result)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'], physical_acceptance=False,
        wall_seconds=result['wall_seconds'], error=result.get('error'))), flush=True)
    if not result['analysis_checks_passed']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    if parser.parse_args().run: main()
    else: parser.print_help()
