"""Pure offline review of all frozen-material finite differences; no material evaluation."""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_key, '1')
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap

T = Path(__file__).resolve().parents[1]
L = T / 'logs'
TAG = 'c08_h18_material_tangent_review_r1'
ROOT = T / 'outputs/c08_h18_material_tangent_r1'
PARTS = (38, 76)
FOCUS = (4953, 4954, 6767, 6865)
LAWS = ('original_softening', 'frozen_strength_at_kappa_n')
POWERS = tuple(range(5, 12))
SCALE_POWER = {10.**(-p): p for p in POWERS}
DISPLAY_POWER = 8  # Predeclared display slice only; never selected from results.
STRESS = ('xx', 'yy', 'zz', 'xy', 'yz', 'xz')
STRAIN = ('exx', 'eyy', 'ezz', 'gamma_xy', 'gamma_yz', 'gamma_xz')
EXPECTED_IDS = {38: (2060, 2455, 4656, 4953, 4954, 6767, 6865),
                76: (2060, 2089, 2103, 4953, 4954, 6767, 6865)}
COUNTS = {'points.csv': 14, 'branches.csv': 1176, 'tangents.csv': 7056,
          'acoustic.csv': 35476, 'summary.csv': 196}

def need(ok, text):
    if not ok:
        raise RuntimeError(text)

def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def bind(entry, consumed):
    need(stat(entry['path']) == entry, 'Bound input changed: ' + entry['path'])
    consumed.append(entry)
    return Path(entry['path'])

def table(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def f(row, key):
    return float(row[key])

def key(row):
    h = f(row, 'strain_scale')
    need(h in SCALE_POWER, 'One of all seven original predeclared strain scales required')
    part, native_id, law = int(row['part']), int(row['native_id']), row['law']
    need(part in PARTS and native_id in EXPECTED_IDS[part] and law in LAWS, 'Unexpected original material case')
    return part, native_id, law, SCALE_POWER[h]

def inputs(consumed):
    receipt = L / 'c08_h18_material_tangent_r1.check.json'
    consumed.append(stat(receipt)); check = read(receipt)
    need(check['passed'] and check['component_invocations'] == 1 and check['consumed_stats_unchanged']
         and check['physical_steps'] == check['force_calls'] == check['solver_invocations'] == check['native_decodes'] == 0
         and not check['physical_acceptance'], 'Actual successful one-off standalone material check required')
    call = read(bind(check['actual_call'], consumed)); build = read(bind(check['build'], consumed))
    need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and call['ownership_failure'] is None,
         'Actual standalone component exits failed')
    need(build['passed'] and build['actual_link_objects'] == 1 and build['retained_physical_objects'] == 0
         and build['project_libraries_linked'] == 0 and build['standalone_inline_material'], 'Isolated original material build required')
    program = bind(build['program'], consumed)
    need(Path(call['program']).resolve() == program.resolve(), 'Actual standalone program binding differs')
    done = read(bind(check['completion'], consumed))
    need(done['passed'] and done['parts'] == list(PARTS) and done['baseline_full_rows'] == 10000
         and done['baseline_all6_sigma_kappa_bits_matched'] and done['trial_reconstructed_from_original_stages']
         and done['selected_points'] == 14 and done['branch_rows'] == 1176 and done['tangent_rows'] == 7056
         and done['acoustic_rows'] == 35476 and done['summary_rows'] == 196
         and done['physical_steps'] == done['force_calls'] == done['native_reads'] == 0
         and done['original_law_unchanged'], 'Original baseline/diagnostic completion differs')
    result = {}
    for leaf, count in COUNTS.items():
        matches = [q for q in check['files'] if Path(q['path']).resolve() == (ROOT / leaf).resolve()]
        need(len(matches) == 1, 'Exactly one original CSV binding required: ' + leaf)
        result[leaf] = table(bind(matches[0], consumed))
        need(len(result[leaf]) == count, 'Original CSV coverage differs: ' + leaf)
    return result

def spectrum(row):
    """Real nonsymmetric2x2 Q, not its symmetric part. No epsilon/sign clipping."""
    a, b, c, d = (f(row, k) for k in ('Qxx_Pa', 'Qxz_Pa', 'Qzx_Pa', 'Qzz_Pa'))
    need(all(math.isfinite(x) for x in (a, b, c, d)), 'Available acoustic tensor must be finite')
    trace, det = a+d, a*d-b*c
    disc = (a-d)*(a-d) + 4.*b*c
    disc_trace = trace*trace - 4.*det
    is_real = disc >= 0.
    if is_real:
        root = math.sqrt(disc); lo, hi, imag = .5*(trace-root), .5*(trace+root), 0.
    else:
        lo = hi = .5*trace; imag = .5*math.sqrt(-disc)
    return dict(trace_Pa=trace, determinant_Pa2=det, discriminant_Pa2=disc,
        trace_form_discriminant_Pa2=disc_trace, discriminant_formula_difference_Pa2=disc-disc_trace,
        eigenvalues_pure_real=is_real, lambda_minus_real_Pa=lo, lambda_plus_real_Pa=hi,
        eigenvalue_imaginary_abs_Pa=imag, real_negative_eigenvalues=(int(lo < 0.) + int(hi < 0.)) if is_real else 0)

def cases(raw):
    points = {(int(q['part']), int(q['native_id'])): q for q in raw['points.csv']}
    need(len(points) == 14 and all((p, i) in points for p in PARTS for i in EXPECTED_IDS[p]), 'All14 original points required')
    summaries = {key(q): q for q in raw['summary.csv']}
    need(len(summaries) == 196, 'All196 point/law/scale cases must remain present')
    angles, branches, matrices = {}, {}, {}
    for q in raw['acoustic.csv']:
        k = key(q); angle = int(q['angle_deg']); a = angles.setdefault(k, {})
        need(0 <= angle <= 180 and angle not in a, 'Duplicate/undeclared original angle')
        a[angle] = q
    for q in raw['branches.csv']:
        k = key(q); strain = q['engineering_strain_component']; b = branches.setdefault(k, {})
        need(strain in STRAIN and strain not in b, 'Duplicate/undeclared engineering-strain branch record')
        b[strain] = q
    for q in raw['tangents.csv']:
        k = key(q); entry = (q['stress_component'], q['engineering_strain_component']); c = matrices.setdefault(k, {})
        need(entry[0] in STRESS and entry[1] in STRAIN and entry not in c, 'Duplicate/undeclared tangent entry')
        c[entry] = q
    need(set(angles) == set(branches) == set(matrices) == set(summaries), 'Five CSV case sets differ')
    derived, display_angles = [], []
    for k in sorted(summaries):
        part, native_id, law, power = k; q = summaries[k]; point = points[(part, native_id)]
        need(set(angles[k]) == set(range(181)) and set(branches[k]) == set(STRAIN) and len(matrices[k]) == 36,
             'All181 angles/six perturbation columns/36 tangent entries required for every case')
        available = int(q['available']); same = int(q['all_12_perturbations_same_branch'])
        need(available in (0, 1) and same in (0, 1) and (not same or available), 'Invalid original availability/branch flags')
        base_commit = int(q['base_status']) in (1, 2, 3, 4)
        need(available == int(base_commit and all(int(x['both_commit']) for x in branches[k].values()))
             and same == int(base_commit and all(int(x['same_branch']) for x in branches[k].values())), 'Original case/perturbation branch flags differ')
        need(all(int(x['available']) == available and int(x['all_12_perturbations_same_branch']) == same
                 for x in list(angles[k].values()) + list(matrices[k].values())), 'Original acoustic/tangent flags differ')
        data = []
        for angle in range(181):
            row = angles[k][angle]
            s = spectrum(row) if available else None
            if s is not None:
                data.append((angle, s))
            if power == DISPLAY_POWER and native_id in FOCUS:
                display_angles.append(dict(part=part, native_id=native_id, source_time_s=f(point, 'source_time_s'), law=law,
                    strain_scale=f(q, 'strain_scale'), angle_deg=angle, available=available, same_branch=same,
                    Qxx_Pa=f(row, 'Qxx_Pa'), Qxz_Pa=f(row, 'Qxz_Pa'), Qzx_Pa=f(row, 'Qzx_Pa'), Qzz_Pa=f(row, 'Qzz_Pa'),
                    symmetric_min_Pa=f(row, 'symmetric_min_Pa'), symmetric_max_Pa=f(row, 'symmetric_max_Pa'),
                    elastic_G_Pa=f(row, 'elastic_min_Pa'), **(s if s is not None else dict(
                        trace_Pa=None, determinant_Pa2=None, discriminant_Pa2=None, trace_form_discriminant_Pa2=None,
                        discriminant_formula_difference_Pa2=None, eigenvalues_pure_real=None, lambda_minus_real_Pa=None,
                        lambda_plus_real_Pa=None, eigenvalue_imaginary_abs_Pa=None, real_negative_eigenvalues=None))))
        out = dict(q)
        out.update(source_time_s=f(point, 'source_time_s'), actual_baseline_status=int(point['actual_status']),
            actual_baseline_reason=int(point['actual_reason']), scale_power=power, original_angle_rows=181,
            computed_available_angles=len(data), pure_real_negative_eigenvalue_count=None,
            pure_real_negative_angle_count=None, complex_pair_angle_count=None,
            minimum_real_part_Pa=None, minimum_real_part_angle_deg=None, minimum_pure_real_eigenvalue_Pa=None,
            minimum_trace_Pa=None, minimum_determinant_Pa2=None, minimum_discriminant_Pa2=None,
            maximum_discriminant_Pa2=None, maximum_imaginary_abs_Pa=None,
            maximum_abs_discriminant_formula_difference_Pa2=None,
            previous_larger_strain_scale=None, adjacent_both_available=None, adjacent_both_same_branch=None,
            adjacent_minimum_real_part_change_Pa=None, adjacent_minimum_real_part_abs_change_over_G=None,
            adjacent_C_Frobenius_change_over_G=None)
        if data:
            minimum = min(data, key=lambda x: x[1]['lambda_minus_real_Pa'])
            real = [s['lambda_minus_real_Pa'] for _, s in data if s['eigenvalues_pure_real']]
            out.update(pure_real_negative_eigenvalue_count=sum(s['real_negative_eigenvalues'] for _, s in data),
                pure_real_negative_angle_count=sum(s['real_negative_eigenvalues'] > 0 for _, s in data),
                complex_pair_angle_count=sum(not s['eigenvalues_pure_real'] for _, s in data),
                minimum_real_part_Pa=minimum[1]['lambda_minus_real_Pa'], minimum_real_part_angle_deg=minimum[0],
                minimum_pure_real_eigenvalue_Pa=min(real) if real else None,
                minimum_trace_Pa=min(s['trace_Pa'] for _, s in data),
                minimum_determinant_Pa2=min(s['determinant_Pa2'] for _, s in data),
                minimum_discriminant_Pa2=min(s['discriminant_Pa2'] for _, s in data),
                maximum_discriminant_Pa2=max(s['discriminant_Pa2'] for _, s in data),
                maximum_imaginary_abs_Pa=max(s['eigenvalue_imaginary_abs_Pa'] for _, s in data),
                maximum_abs_discriminant_formula_difference_Pa2=max(abs(s['discriminant_formula_difference_Pa2']) for _, s in data))
        derived.append(out)
    index = {(int(q['part']), int(q['native_id']), q['law'], int(q['scale_power'])): q for q in derived}
    for k, out in index.items():
        part, native_id, law, power = k
        if power == POWERS[0]:
            continue
        previous_key = part, native_id, law, power-1; previous = index[previous_key]
        both = bool(int(out['available']) and int(previous['available']))
        out.update(previous_larger_strain_scale=f(previous, 'strain_scale'), adjacent_both_available=both,
                   adjacent_both_same_branch=bool(int(out['all_12_perturbations_same_branch']) and int(previous['all_12_perturbations_same_branch'])))
        if both:
            g = f(out, 'elastic_shear_modulus_Pa'); need(g > 0, 'Original elastic G must be positive')
            delta = out['minimum_real_part_Pa'] - previous['minimum_real_part_Pa']
            norm2 = sum((f(matrices[k][e], 'C_Pa') - f(matrices[previous_key][e], 'C_Pa'))**2 for e in matrices[k])
            out.update(adjacent_minimum_real_part_change_Pa=delta, adjacent_minimum_real_part_abs_change_over_G=abs(delta)/g,
                       adjacent_C_Frobenius_change_over_G=math.sqrt(norm2)/g)
    need(len(derived) == 196 and len(display_angles) == 2896, 'All196 cases and predeclared focus display angles must be retained')
    return derived, display_angles

def write(path, data):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)

def plots(folder, data, angles):
    index = {(int(q['part']), int(q['native_id']), q['law'], int(q['scale_power'])): q for q in data}
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .23})
    fig, axes = plt.subplots(4, 2, figsize=(13.5, 13.5), constrained_layout=True,
                             gridspec_kw={'height_ratios': (2, 1, 2, 1)})
    cmap = ListedColormap(('#bd3942', '#e8ad45', '#69a877')); norm = BoundaryNorm((-.5, .5, 1.5, 2.5), 3)
    for pidx, part in enumerate(PARTS):
        for lidx, law in enumerate(LAWS):
            ax, flag = axes[2*pidx, lidx], axes[2*pidx+1, lidx]
            grid = []
            for color, native_id in zip(plt.cm.tab10.colors, EXPECTED_IDS[part]):
                seq = [index[(part, native_id, law, power)] for power in POWERS]
                x = [f(q, 'strain_scale') for q in seq]
                ax.plot(x, [q['minimum_real_part_Pa']/1e6 if q['minimum_real_part_Pa'] is not None else np.nan for q in seq],
                        'o-', ms=3, color=color, label=str(native_id))
                ax.plot(x, [f(q, 'minimum_symmetric_acoustic_Pa')/1e6 for q in seq], ':', color=color, alpha=.75)
                grid.append([0 if not int(q['available']) else 2 if int(q['all_12_perturbations_same_branch']) else 1 for q in seq])
            ax.set_xscale('log'); ax.invert_xaxis(); ax.set_yscale('symlog', linthresh=1e-6)
            ax.axhline(0, color='#777777', lw=.6); ax.set_ylabel('Minimum eigenvalue / real part [MPa]')
            ax.set_title(f'Part{part}: {law.replace("_", " ")}'); ax.legend(ncol=4, fontsize=7, title='Native ID', title_fontsize=8)
            flag.imshow(grid, cmap=cmap, norm=norm, aspect='auto', interpolation='nearest')
            flag.set_yticks(range(7), [str(i) for i in EXPECTED_IDS[part]])
            flag.set_xticks(range(7), [f'1e-{p}' for p in POWERS]); flag.set_xlabel('All original engineering-strain scales')
            flag.set_ylabel('Native ID'); flag.grid(False)
    fig.suptitle('All 196 local-law cases: solid = real part of actual nonsymmetric Q; dotted = sym(Q) minimum\n'
                 'Flags: green same branch, amber mixed branch, red unavailable. No scale is selected as truth.', fontsize=11)
    p = folder / 'scales.png'; fig.savefig(p, dpi=170); plt.close(fig)
    fig, axes = plt.subplots(2, 4, figsize=(16, 8.5), constrained_layout=True)
    for r, part in enumerate(PARTS):
        for col, native_id in enumerate(FOCUS):
            ax = axes[r, col]
            for color, law, short in (('#0072B2', LAWS[0], 'Original'), ('#D55E00', LAWS[1], 'Frozen')):
                seq = [q for q in angles if (q['part'], q['native_id'], q['law']) == (part, native_id, law)]
                need(len(seq) == 181, 'Every display curve retains all181 angles')
                seq.sort(key=lambda q: q['angle_deg']); x = [q['angle_deg'] for q in seq]
                ax.plot(x, [q['lambda_minus_real_Pa']/1e6 if q['lambda_minus_real_Pa'] is not None else np.nan for q in seq],
                        color=color, label=short+' real-part min')
                ax.plot(x, [q['symmetric_min_Pa']/1e6 for q in seq], '--', color=color, alpha=.7, label=short+' sym(Q) min')
                complex_rows = [q for q in seq if q['eigenvalues_pure_real'] is False]
                ax.plot([q['angle_deg'] for q in complex_rows], [q['lambda_minus_real_Pa']/1e6 for q in complex_rows],
                        linestyle='none', marker='x', ms=3, color=color)
            g = angles[0]['elastic_G_Pa']/1e6
            ax.axhline(g, color='#333333', linestyle=':', lw=1.1, label='Elastic G')
            ax.axhline(0, color='#888888', lw=.6); ax.set_xlim(0, 180); ax.set_yscale('symlog', linthresh=.01)
            ax.set_title(f'Part{part}, ID{native_id}'); ax.set_xlabel('Angle [deg]'); ax.set_ylabel('[MPa]')
    axes[0, 0].legend(fontsize=7)
    fig.suptitle('Predeclared strain slice 1e-8 only; all scales remain in scales.csv\n'
                 'Solid curves use the actual nonsymmetric Q. An x denotes a complex-conjugate pair, not a real eigenvalue.', fontsize=11)
    q = folder / 'focus_angles_e8.png'; fig.savefig(q, dpi=170); plt.close(fig)
    return [p, q]

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args(); need(args.execution_authorized, 'Root full read and separate offline review admission required')
    check_path, folder = L / (TAG + '.check.json'), T / 'figures' / TAG
    need(not check_path.exists() and not folder.exists(), 'Existing complete/partial review artifacts protected')
    consumed, products = [stat(Path(__file__)), stat(T / 'notes' / (TAG + '.md'))], []
    result = dict(stage=TAG, passed=False, material_evaluations=0, component_invocations=0, force_calls=0,
                  solver_invocations=0, native_reads=0, build_invocations=0, GPU_actions=0, physical_steps=0,
                  SHA_scans=0, physical_acceptance=False)
    try:
        raw = inputs(consumed); data, angles = cases(raw)
        folder.mkdir()
        for name, values in (('scales.csv', data), ('focus_angles_e8.csv', angles)):
            p = folder / name; write(p, values); products.append(p)
        products.extend(plots(folder, data, angles))
        need(all(stat(q['path']) == q for q in consumed), 'Consumed original evidence changed during offline analysis')
        result.update(passed=True, consumed=consumed, consumed_stats_unchanged=True, case_rows=196,
            preserved_strain_powers=list(POWERS), display_power_only=DISPLAY_POWER, display_slice_is_not_scale_selection=True,
            display_angle_rows=2896, outputs=[stat(p) for p in products], visual_QA_pending=True,
            unavailable_cases=sum(not int(q['available']) for q in data),
            mixed_branch_available_cases=sum(int(q['available']) and not int(q['all_12_perturbations_same_branch']) for q in data),
            actual_Q_not_symmetric_Q=True, no_discriminant_sign_clipping=True,
            no_complete_coupled_ellipticity_or_clumping_claim=True, no_cap_or_material_law_change=True,
            no_undrained_TPI_beta_or_diffusion_model=True)
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check_path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)

if __name__ == '__main__':
    main()
