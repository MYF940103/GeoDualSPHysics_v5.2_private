"""CSV-only material-grid geometry/J diagnostic. No physical tools or state changes."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_geometry_J_review_r1'
CHECK = T/'logs/c08_h18_global_modes_r1.check.json'
REVIEW = T/'logs/c08_h18_global_modes_review_r1.check.json'
PARTS = (38, 76, 92, 300)
FOCUS = (4953, 4954, 6767, 6865)
PAIRS = ((4953, 4954), (6767, 6865))
DP = .04
AREA0 = DP*DP
NX, NZ = 100, 50
consumed = []


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def consume(path, expected=None):
    q = stat(path)
    if expected:
        need(Path(expected['path']).resolve() == Path(q['path']) and
             (expected['bytes'], expected['mtime_ns']) == (q['bytes'], q['mtime_ns']),
             'Bound CSV changed: '+str(path))
    consumed.append(q)
    return Path(q['path'])


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        yield from csv.DictReader(f)


def write_csv(path, data):
    need(data, 'Empty geometric table')
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)


def load():
    consume(Path(__file__))
    consume(T/'notes'/(TAG+'.md'))
    consume(CHECK)
    consume(REVIEW)
    c, r = read(CHECK), read(REVIEW)
    need(c['passed'] and c['consumed_stats_unchanged'] and
         r['passed'] and r['consumed_stats_unchanged'] and
         r['source_parts'] == list(PARTS) and
         r['full140000_field_CSV_retained_and_stat_bound'],
         'Passed four-state global-mode component and review required')
    bundle = {part: {} for part in PARTS}
    paths = {}
    for leaf in ('mode_fields.csv', 'soil.csv'):
        found = [q for q in c['files'] if Path(q['path']).name == leaf]
        need(len(found) == 1, 'One sealed global-mode CSV required: '+leaf)
        paths[leaf] = consume(found[0]['path'], found[0])
    picked = 0
    for q in rows(paths['mode_fields.csv']):
        if q['mode'] != 'altX_Uz':
            continue
        part, native_id = int(q['part']), int(q['native_id'])
        need(part in bundle and native_id not in bundle[part] and
             int(q['Nx']) == NX and int(q['Nz']) == NZ, 'Unique original material-grid row required')
        bundle[part][native_id] = dict(id=native_id, ix=int(q['initial_ix']), iz=int(q['initial_iz']),
            x=float(q['x_m']), z=float(q['z_m']), time=float(q['time_s']),
            step=int(q['completed_step']), no_fixed=int(q['no_fixed_neighbors']))
        picked += 1
    seen = set()
    for q in rows(paths['soil.csv']):
        part, native_id = int(q['part']), int(q['id'])
        need((part, native_id) not in seen and part in bundle and native_id in bundle[part],
             'Unique matching actual soil row required')
        n = bundle[part][native_id]
        need(float(q['time_s']) == n['time'] and int(q['completed_step']) == n['step'] and
             float(q['x']) == n['x'] and float(q['z']) == n['z'],
             'Actual geometric CSV join differs')
        n.update(J=float(q['J']), V=float(q['V']), tau=float(q['tau_s']))
        seen.add((part, native_id))
    need(picked == len(seen) == 20000, 'Only four complete5000-node states are admitted')
    reference = None
    for part, group in bundle.items():
        need(len(group) == 5000 and set(group) == set(range(2060, 7060)), 'Original5000 materials required')
        index = {(n['ix'], n['iz']): n for n in group.values()}
        need(set(index) == {(i, j) for i in range(NX) for j in range(NZ)},
             'Complete actual100x50 phase grid required')
        phase = {native_id: (n['ix'], n['iz']) for native_id, n in group.items()}
        need(reference is None or phase == reference, 'Material phase changed between actual states')
        reference = phase
        for n in group.values():
            need(all(math.isfinite(n[k]) for k in ('x', 'z', 'J', 'V', 'time', 'tau')),
                 'Nonfinite actual geometry')
        for i in range(1, NX-1):
            for j in range(1, NZ-1):
                n = index[i, j]
                dx = (point(index[i+1, j])-point(index[i-1, j]))/(2*DP)
                dz = (point(index[i, j+1])-point(index[i, j-1]))/(2*DP)
                F = np.column_stack((dx, dz))
                n['F'] = F
                n['detF'] = float(np.linalg.det(F))
                n['detF_minus_J'] = n['detF']-n['J']
        bundle[part] = dict(nodes=group, index=index)
    return bundle


def point(n):
    return np.array((n['x'], n['z']), dtype=float)


def cross(a, b):
    return float(a[0]*b[1]-a[1]*b[0])


def cells(bundle):
    output = []
    for part in PARTS:
        idx = bundle[part]['index']
        for i in range(NX-1):
            for j in range(NZ-1):
                ns = (idx[i, j], idx[i+1, j], idx[i+1, j+1], idx[i, j+1])
                a, b, c, d = (point(n) for n in ns)
                t1, t2 = .5*cross(b-a, c-a), .5*cross(c-a, d-a)
                t3, t4 = .5*cross(b-a, d-a), .5*cross(c-b, d-b)
                ratio = (t1+t2)/AREA0
                meanJ = math.fsum(n['J'] for n in ns)/4
                tri = [v/(.5*AREA0) for v in (t1, t2, t3, t4)]
                output.append(dict(part=part, actual_time_s=ns[0]['time'], tau_s=ns[0]['tau'],
                    completed_step=ns[0]['step'], initial_ix=i, initial_iz=j,
                    id_A=ns[0]['id'], id_B=ns[1]['id'], id_C=ns[2]['id'], id_D=ns[3]['id'],
                    center_x_m=float(np.mean([n['x'] for n in ns])),
                    center_z_m=float(np.mean([n['z'] for n in ns])),
                    all4_no_fixed_neighbors=int(all(n['no_fixed'] for n in ns)),
                    signed_area_m2=t1+t2, area_ratio_nominal_dp2=ratio,
                    mean_corner_J=meanJ, area_ratio_minus_meanJ=ratio-meanJ,
                    tri_AC_ABC_ratio=tri[0], tri_AC_ACD_ratio=tri[1],
                    tri_BD_ABD_ratio=tri[2], tri_BD_BCD_ratio=tri[3],
                    minimum_signed_triangle_ratio=min(tri),
                    AC_opposite_triangle_signs=int(t1*t2 < 0),
                    BD_opposite_triangle_signs=int(t3*t4 < 0),
                    diagonal_area_sum_difference_m2=(t1+t2)-(t3+t4)))
    need(len(output) == 19404, 'Actual99x49 material-cell coverage differs')
    return output


def stats(values, prefix):
    a = np.asarray(values, dtype=float)
    need(a.size and np.isfinite(a).all(), 'Finite nonempty geometric cohort required')
    return {prefix+'_min': float(np.min(a)), prefix+'_mean': float(np.mean(a)),
            prefix+'_RMS': float(np.sqrt(np.mean(a*a))), prefix+'_max': float(np.max(a))}


def products(bundle, quads):
    summaries, extremes, neighbors, pairs = [], [], [], []
    for part in PARTS:
        group = bundle[part]['nodes']
        qpart = [q for q in quads if q['part'] == part]
        nodes = [n for n in group.values() if 'F' in n]
        for kind, cohort, records in (
                ('quad', 'all', qpart),
                ('quad', 'all4_no_fixed_neighbors', [q for q in qpart if q['all4_no_fixed_neighbors']]),
                ('node_centered', 'all_interior_logical_nodes', nodes),
                ('node_centered', 'receiver_no_fixed_neighbors', [n for n in nodes if n['no_fixed']])):
            summary = dict(part=part, actual_time_s=next(iter(group.values()))['time'],
                tau_s=next(iter(group.values()))['tau'], kind=kind, cohort=cohort, count=len(records))
            # Keep one common schema; irrelevant family columns remain empty rather than zero.
            summary.update({k: None for k in (
                'geometry_min', 'geometry_mean', 'geometry_RMS', 'geometry_max',
                'J_min', 'J_mean', 'J_RMS', 'J_max', 'difference_min', 'difference_mean',
                'difference_RMS', 'difference_max', 'negative_geometry_count',
                'nonpositive_geometry_count', 'negative_any_triangle_count',
                'AC_opposite_sign_count', 'BD_opposite_sign_count')})
            if records:
                geom = [q['area_ratio_nominal_dp2'] if kind == 'quad' else q['detF'] for q in records]
                j = [q['mean_corner_J'] if kind == 'quad' else q['J'] for q in records]
                diff = [a-b for a, b in zip(geom, j)]
                summary.update(stats(geom, 'geometry'))
                summary.update(stats(j, 'J'))
                summary.update(stats(diff, 'difference'))
                summary['negative_geometry_count'] = sum(v < 0 for v in geom)
                summary['nonpositive_geometry_count'] = sum(v <= 0 for v in geom)
                if kind == 'quad':
                    summary['negative_any_triangle_count'] = sum(q['minimum_signed_triangle_ratio'] < 0 for q in records)
                    summary['AC_opposite_sign_count'] = sum(q['AC_opposite_triangle_signs'] for q in records)
                    summary['BD_opposite_sign_count'] = sum(q['BD_opposite_triangle_signs'] for q in records)
            summaries.append(summary)
        ranked = sorted(qpart, key=lambda q: (-abs(q['area_ratio_minus_meanJ']), q['id_A']))
        selected = [(f'abs_area_minus_J_rank{rank+1}', q) for rank, q in enumerate(ranked[:8])]
        selected += [('minimum_signed_quad', min(qpart, key=lambda q: q['area_ratio_nominal_dp2'])),
                     ('minimum_signed_triangle', min(qpart, key=lambda q: q['minimum_signed_triangle_ratio']))]
        for label, q in selected:
            extremes.append(dict(selection=label, **q))
        for focus_id in FOCUS:
            center = group[focus_id]
            i, j = center['ix'], center['iz']
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    n = bundle[part]['index'].get((i+di, j+dj))
                    if n is None:
                        continue
                    neighbors.append(dict(part=part, actual_time_s=n['time'], tau_s=n['tau'],
                        focus_id=focus_id, di=di, dj=dj, native_id=n['id'], initial_ix=n['ix'],
                        initial_iz=n['iz'], x_m=n['x'], z_m=n['z'], J=n['J'],
                        no_fixed_neighbors=n['no_fixed'], centered_F_defined='F' in n,
                        detF=n.get('detF'), detF_minus_J=n.get('detF_minus_J')))
        for ia, ib in PAIRS:
            a, b = group[ia], group[ib]
            d0 = DP*np.array((b['ix']-a['ix'], b['iz']-a['iz']), dtype=float)
            current = point(b)-point(a)
            length0, length = float(np.linalg.norm(d0)), float(np.linalg.norm(current))
            defined = 'F' in a and 'F' in b
            predicted = .5*(a['F']+b['F'])@d0 if defined else None
            predlen = float(np.linalg.norm(predicted)) if defined else None
            pairs.append(dict(part=part, actual_time_s=a['time'], tau_s=a['tau'], id_A=ia, id_B=ib,
                nominal_initial_grid_length_m=length0, current_length_m=length,
                current_length_over_initial=length/length0,
                current_dx_m=float(current[0]), current_dz_m=float(current[1]),
                mean_J=.5*(a['J']+b['J']), detF_A=a.get('detF'), detF_B=b.get('detF'),
                centered_affine_prediction_defined=defined,
                predicted_dx_m=float(predicted[0]) if defined else None,
                predicted_dz_m=float(predicted[1]) if defined else None,
                predicted_length_m=predlen, predicted_length_over_initial=predlen/length0 if defined else None,
                vector_residual_over_initial=float(np.linalg.norm(current-predicted))/length0 if defined else None,
                signed_length_residual_over_initial=(length-predlen)/length0 if defined else None))
    return summaries, extremes, neighbors, pairs


def plots(bundle, quads, summaries, neighbors, pairs, paths):
    plt.rcParams.update({'font.size': 10, 'legend.fontsize': 8})
    area = np.array([q['area_ratio_nominal_dp2'] for q in quads])
    delta = max(abs(q['area_ratio_minus_meanJ']) for q in quads)
    ratio_norm = Normalize(vmin=float(area.min()), vmax=float(area.max()))
    difference_norm = Normalize(vmin=-delta if delta else -1., vmax=delta if delta else 1.)
    fig, axes = plt.subplots(2, 4, figsize=(16, 7), constrained_layout=True, sharex=True, sharey=True)
    for col, part in enumerate(PARTS):
        rows = [q for q in quads if q['part'] == part]
        x, z = [q['center_x_m'] for q in rows], [q['center_z_m'] for q in rows]
        for row, (key, norm, cmap) in enumerate((('area_ratio_nominal_dp2', ratio_norm, 'viridis'),
                                                ('area_ratio_minus_meanJ', difference_norm, 'coolwarm'))):
            scatter = axes[row, col].scatter(x, z, c=[q[key] for q in rows], s=5, cmap=cmap,
                norm=norm, rasterized=True)
            neg = [q for q in rows if q['area_ratio_nominal_dp2'] < 0]
            if neg:
                axes[row, col].scatter([q['center_x_m'] for q in neg], [q['center_z_m'] for q in neg],
                    marker='x', color='black', s=9, linewidths=.5)
            axes[row, col].set_aspect('equal', adjustable='box')
            axes[row, col].set_title(f"P{part}; tau={rows[0]['tau_s']:.6f}s")
            axes[row, col].grid(alpha=.15)
            if row == 1:
                axes[row, col].set_xlabel('Current material-cell center x [m]')
            if col == 0:
                axes[row, col].set_ylabel('Current z [m]')
        if col == 3:
            fig.colorbar(axes[0, col].collections[0], ax=list(axes[0]), label='Signed area / nominal dp2')
            fig.colorbar(axes[1, col].collections[0], ax=list(axes[1]), label='Signed area ratio - mean corner J')
    fig.suptitle('Frozen original material cells: diagnostic geometry, not true particle volume; black x = negative signed area')
    fig.savefig(paths['cells'], dpi=190)
    plt.close(fig)

    colors = ('#0072B2', '#D55E00', '#009E73', '#CC79A7')
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    limits = []
    for color, part in zip(colors, PARTS):
        qs = [q for q in quads if q['part'] == part]
        axes[0, 0].scatter([q['mean_corner_J'] for q in qs], [q['area_ratio_nominal_dp2'] for q in qs],
            s=3, alpha=.25, color=color, label=f'P{part}', rasterized=True)
        ns = [n for n in bundle[part]['nodes'].values() if 'F' in n]
        axes[0, 1].scatter([n['J'] for n in ns], [n['detF'] for n in ns],
            s=3, alpha=.25, color=color, label=f'P{part}', rasterized=True)
    for a in axes[0, :2]:
        lo = min(a.get_xlim()[0], a.get_ylim()[0])
        hi = max(a.get_xlim()[1], a.get_ylim()[1])
        a.plot([lo, hi], [lo, hi], 'k--', lw=.8, label='Identity (not a theory gate)')
        a.set_xlabel('Native J / mean corner J')
        a.legend()
    axes[0, 0].set_ylabel('Signed cell area ratio')
    axes[0, 1].set_ylabel('Centered-coordinate det F')
    axes[0, 0].set_title('All19404 original quadrilaterals')
    axes[0, 1].set_title('Four-neighbor F: logical interior only')
    for kind, cohort, label, style in (
            ('quad', 'all', 'Cell difference, all', '-o'),
            ('quad', 'all4_no_fixed_neighbors', 'Cell difference, no fixed corners', '--o'),
            ('node_centered', 'all_interior_logical_nodes', 'Centered F difference, all', '-s'),
            ('node_centered', 'receiver_no_fixed_neighbors', 'Centered F, no fixed receiver', '--s')):
        rs = [q for q in summaries if q['kind'] == kind and q['cohort'] == cohort and q['count']]
        axes[0, 2].plot([q['tau_s'] for q in rs], [q['difference_RMS'] for q in rs], style, label=label, ms=4)
    axes[0, 2].set_title('Only four sampled states, no inferred onset')
    axes[0, 2].set_ylabel('RMS geometry - J')
    axes[0, 2].legend()
    for color, pair in zip(colors, PAIRS):
        ps = [q for q in pairs if (q['id_A'], q['id_B']) == pair]
        axes[1, 0].plot([q['tau_s'] for q in ps], [q['current_length_over_initial'] for q in ps],
            '-o', color=color, label=f'{pair[0]}/{pair[1]} measured')
        axes[1, 0].plot([q['tau_s'] for q in ps], [q['predicted_length_over_initial'] for q in ps],
            '--s', color=color, label=f'{pair[0]}/{pair[1]} mean-F shadow')
        axes[1, 1].plot([q['tau_s'] for q in ps], [q['vector_residual_over_initial'] for q in ps],
            '-o', color=color, label=f'{pair[0]}/{pair[1]} vector residual')
        axes[1, 1].plot([q['tau_s'] for q in ps], [q['signed_length_residual_over_initial'] for q in ps],
            '--s', color=color, label=f'{pair[0]}/{pair[1]} signed length residual')
    axes[1, 0].set_ylabel('Pair length / nominal original length')
    axes[1, 1].set_ylabel('Residual / nominal original length')
    axes[1, 0].set_title('Local F cannot span a discontinuity exactly')
    axes[1, 1].set_title('Actual pair vs mean local affine shadow')
    axes[1, 0].legend()
    axes[1, 1].legend()
    for color, native_id in zip(colors, FOCUS):
        ns = [q for q in neighbors if q['focus_id'] == native_id and q['di'] == q['dj'] == 0]
        axes[1, 2].plot([q['tau_s'] for q in ns], [q['detF_minus_J'] for q in ns],
            '-o', color=color, label=str(native_id))
    axes[1, 2].set_title('Four fixed materials, not selected extremes')
    axes[1, 2].set_ylabel('Centered det F - native J')
    axes[1, 2].legend()
    for a in axes.flat:
        a.grid(alpha=.2)
    for a in (axes[0, 2], *axes[1]):
        a.set_xlabel('Actual time since PRE release [s]')
    fig.suptitle('Geometric consistency descriptors; no mass-conservation or physical acceptance claim')
    fig.savefig(paths['comparison'], dpi=190)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    a = p.parse_args()
    need(a.execution_authorized, 'Root full review and one offline geometric-analysis admission required')
    prefix = T/'figures'/TAG
    paths = {k: Path(str(prefix)+'_'+k+'.png') for k in ('cells', 'comparison')}
    tables = {k: Path(str(prefix)+'_'+k+'.csv') for k in ('summary', 'extremes', 'focus_neighbors', 'pairs')}
    quad_path = T/'outputs'/(TAG+'_quads.csv')
    check = T/'logs'/(TAG+'.check.json')
    need(not any(q.exists() for q in [*paths.values(), *tables.values(), quad_path, check]),
         'Existing successful or partial derived outputs protected')
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False,
        material_mass_conservation_proven=False, causal_claim=False, solver_invocations=0,
        reader_invocations=0, build_invocations=0, GPU_actions=0, SHA_scans=0)
    try:
        bundle = load()
        quads = cells(bundle)
        summary, extremes, neighbors, pairs = products(bundle, quads)
        need(all(stat(q['path']) == q for q in consumed), 'Bound input changed during geometric extraction')
        write_csv(quad_path, quads)
        for key, data in (('summary', summary), ('extremes', extremes),
                          ('focus_neighbors', neighbors), ('pairs', pairs)):
            write_csv(tables[key], data)
        plots(bundle, quads, summary, neighbors, pairs, paths)
        need(all(stat(q['path']) == q for q in consumed), 'Bound input changed during plotting')
        result.update(analysis_complete=True, source_parts=list(PARTS), extracted_mode='altX_Uz',
            picked_actual_rows=20000, quadrilateral_rows=len(quads), node_centered_rows=18816,
            nominal_reference_dp_m=DP, nominal_reference_cell_area_m2=AREA0,
            exact_initial_Posd_reconstructed=False, signed_values_retained=True,
            negative_values_clipped=False, thresholds_or_physical_gates_added=False,
            diagonal_choice_is_diagnostic_only=True, summaries=summary,
            most_distorted_cell_records=extremes, pair_descriptors=pairs,
            full_quad_CSV_local_only=stat(quad_path), consumed=consumed,
            products=[stat(q) for q in [*tables.values(), *paths.values()]], visual_QA_pending=True)
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
