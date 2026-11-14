"""Offline four-snapshot global-mode review; never runs a physical/native program."""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_key, '1')
import argparse
import csv
import json
import math
import struct
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
L = T / 'logs'
TAG = 'c08_h18_global_modes_review_r1'
NOTE = T / 'notes' / (TAG + '.md')
ROOT = T / 'outputs/c08_h18_global_modes_r1'
OLD = T / 'outputs/c08_h18_work_conjugacy_r2'
PARTS = (38, 76, 92, 300)
STEPS = (2076001, 2152001, 2184001, 2600000)
MODES = ('altX_Uz', 'altZ_Ux', 'checkerXZ_Ux', 'checkerXZ_Uz',
         'translation_xz', 'affine_expansion_xz', 'actual_velocity')
COHORTS = ('all_soil', 'no_fixed_neighbors')
SOIL_IDS = set(range(2060, 7060))
MODE_HEADER = ('part,time_s,completed_step,mode,receiver_cohort,receivers,soil_directed_edges,Nx,Nz,'
    'Vnorm_u,Vnorm_symLraw,Vnorm_symLC,Vnorm_divraw,Vnorm_divC,symLraw_over_u_m_1,symLC_over_u_m_1,'
    'divraw_over_u_m_1,divC_over_u_m_1,u_norm_nonzero,P_frozen_stress,Iraw,IC,G1_gap,cohort_cut_port,'
    'raw_adjoint_residual,arithmetic_budget,actual_velocity_projection_coefficient,affine_target_valid,'
    'affine_raw_error_Vnorm,affine_C_error_Vnorm,soil_only,walls_closed').split(',')
INTS = {'part', 'completed_step', 'receivers', 'soil_directed_edges', 'Nx', 'Nz', 'u_norm_nonzero',
        'affine_target_valid', 'soil_only', 'walls_closed', 'native_id', 'initial_ix', 'initial_iz', 'no_fixed_neighbors'}

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def read(path):
    with Path(path).open(encoding='utf-8-sig') as stream:
        return json.load(stream)

def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)

def bind(entry, consumed):
    current = stat(entry['path'])
    need(current == entry, 'Bound artifact changed: ' + entry['path'])
    consumed.append(current)
    return Path(current['path'])

def bound_file(check, path, consumed):
    matches = [q for q in check['files'] if Path(q['path']).resolve() == Path(path).resolve()]
    need(len(matches) == 1, 'Exactly one original file binding required: ' + str(path))
    return bind(matches[0], consumed)

def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def same_bytes(a, b):
    need(a.stat().st_size == b.stat().st_size, 'Baseline CSV extent changed: ' + a.name)
    with a.open('rb') as left, b.open('rb') as right:
        while True:
            x, y = left.read(1048576), right.read(1048576)
            need(x == y, 'Baseline CSV bytes changed: ' + a.name)
            if not x:
                return a.stat().st_size

def bits(x):
    return struct.pack('<d', x)

def parsed(row):
    result = {}
    for key, value in row.items():
        if key in ('mode', 'receiver_cohort'):
            result[key] = value
        elif key in INTS:
            result[key] = int(value)
        else:
            result[key] = float(value)
            need(math.isfinite(result[key]), 'Nonfinite diagnostic field: ' + key)
    return result

def input_checks(consumed):
    check_path = L / 'c08_h18_global_modes_r1.check.json'
    old_path = L / 'c08_h18_work_conjugacy_r2.check.json'
    consumed.extend((stat(check_path), stat(old_path)))
    check, old = read(check_path), read(old_path)
    for q, stage in ((check, 'c08_h18_global_modes_r1'), (old, 'c08_h18_work_conjugacy_r2')):
        need(q['passed'] and q['stage'] == stage and q['component_invocations'] == 1 and q['physical_steps'] == 0,
             'Original passed one-call/zero-step component receipt required')
    need(check['solver_invocations'] == check['reader_invocations'] == check['material_steps'] == check['GPU_actions'] == 0,
         'Unexpected component physical/native/GPU work')
    call = read(bind(check['actual_call'], consumed))
    need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and call['ownership_failure'] is None,
         'Original component exits/ownership failed')
    need(call['child']['parent_pid'] == call['owner']['pid'] and Path(call['child']['exe']) == Path(call['program'])
         and call['child']['argv'] == [call['program']] + call['arguments'], 'Original actual child binding differs')
    build = read(bind(check['build'], consumed))
    need(build['passed'] and build['configuration'] == 'DebugCPU' and Path(build['program']['path']) == Path(call['program']),
         'Passed bound DebugCPU program required')
    bind(build['program'], consumed)
    done = read(bind(check['completion'], consumed))
    expected = dict(force_calls=4, soil_rows=20000, group_rows=40000, wall_rows=7220, summary_rows=8,
                    mode_rows=56, mode_field_rows=140000, physical_steps=0, material_steps=0, new_OFF_windows=0,
                    initial_native_grid_Nx=100, initial_native_grid_Nz=50,
                    max_literal_force_error=0, max_literal_stress_rate_error=0, max_literal_theta_error=0)
    need(done['passed'] and done['stage'] == 'c08_h18_global_modes_r1' and done['source_parts'] == list(PARTS)
         and all(done[k] == v for k, v in expected.items()), 'Original completion coverage/literal checks differ')
    need(done['all5000_soil_primary_bits_unchanged'] and done['initial_grid_mapped_by_ID_and_coordinates']
         and done['virtual_soil_only'] and not done['virtual_wall_closure'] and not done['near_null_threshold_defined']
         and not done['physical_acceptance'], 'Original bounded scope differs')
    old_done = read(bind(old['completion'], consumed))
    need(old_done['passed'] and old_done['force_calls'] == 4 and old_done['physical_steps'] == 0,
         'Retained baseline component is not complete')
    proof = []
    for name, count in (('soil.csv', 20000), ('groups.csv', 40000), ('walls.csv', 7220), ('summary.csv', 8)):
        a, b = bound_file(check, ROOT / name, consumed), bound_file(old, OLD / name, consumed)
        size = same_bytes(a, b)
        with a.open(encoding='utf-8-sig', newline='') as stream:
            rows = sum(1 for _ in csv.DictReader(stream))
        need(rows == count, 'Original baseline CSV count differs: ' + name)
        proof.append(dict(file=name, bytes_compared=size, rows=rows, byte_identical=True))
    for name in ('modes.csv', 'mode_fields.csv'):
        bound_file(check, ROOT / name, consumed)
    return proof

def collect_modes():
    summary = table(ROOT / 'summary.csv')
    times = {}
    for q in summary:
        part = int(q['part'])
        point = (float(q['time_s']), float(q['tau_s']))
        need(part not in times or times[part] == point, 'Actual baseline time differs by donor cohort')
        times[part] = point
    need(set(times) == set(PARTS), 'Actual baseline saved-state coverage differs')
    with (ROOT / 'modes.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames == MODE_HEADER, 'Exact modes.csv schema required')
        rows = [parsed(q) for q in reader]
    need(len(rows) == 56, '56 real mode/cohort records required')
    out = {}
    for q in rows:
        key = (q['part'], q['mode'], q['receiver_cohort'])
        need(q['part'] in PARTS and q['mode'] in MODES and q['receiver_cohort'] in COHORTS and key not in out,
             'Duplicate or undeclared saved mode/cohort')
        need(q['time_s'] == times[q['part']][0] and q['completed_step'] == STEPS[PARTS.index(q['part'])]
             and q['Nx'] == 100 and q['Nz'] == 50 and q['soil_only'] == 1 and q['walls_closed'] == 0,
             'Actual saved clocks/grid/virtual closure differs')
        need(0 < q['receivers'] <= 5000 and q['soil_directed_edges'] > 0 and q['arithmetic_budget'] >= 0
             and abs(q['raw_adjoint_residual']) <= q['arithmetic_budget'], 'Original raw-work arithmetic gate failed')
        need(bits(q['IC'] - q['Iraw']) == bits(q['G1_gap'])
             and bits((q['P_frozen_stress'] + q['Iraw']) - q['cohort_cut_port']) == bits(q['raw_adjoint_residual']),
             'Original literal work subtotal differs')
        need(q['affine_target_valid'] == int(q['mode'] == 'affine_expansion_xz'), 'Affine reference flag differs')
        q['tau_s'] = times[q['part']][1]
        out[key] = q
    need(len(out) == len(PARTS) * len(MODES) * len(COHORTS), 'Incomplete mode/cohort grid')
    return out

def write_csv(path, rows):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def outputs(modes, folder):
    rows = [modes[(p, name, cohort)] for p in PARTS for cohort in COHORTS for name in MODES]
    response = [q for q in rows if q['mode'] in MODES[:4]]
    controls = [q for q in rows if q['mode'] in MODES[4:6]]
    projections = []
    for q in response:
        a = modes[(q['part'], 'actual_velocity', q['receiver_cohort'])]
        projections.append(dict(part=q['part'], time_s=q['time_s'], tau_s=q['tau_s'], completed_step=q['completed_step'],
            mode=q['mode'], receiver_cohort=q['receiver_cohort'], receivers=q['receivers'],
            signed_projection_coefficient=q['actual_velocity_projection_coefficient'],
            actual_Vnorm_velocity=a['Vnorm_u'], actual_symLraw_over_u_m_1=a['symLraw_over_u_m_1'],
            actual_symLC_over_u_m_1=a['symLC_over_u_m_1'], actual_divraw_over_u_m_1=a['divraw_over_u_m_1'],
            actual_divC_over_u_m_1=a['divC_over_u_m_1'], modal_energy_claimed=False))
    paths = []
    for name, data in (('response', response), ('controls', controls), ('projections', projections)):
        p = folder / (name + '.csv')
        write_csv(p, data)
        paths.append(p)
    plt.rcParams.update({'font.size': 10, 'axes.grid': True, 'grid.alpha': .25, 'figure.dpi': 120})
    colors = dict(zip(MODES[:4], ('#0072B2', '#D55E00', '#009E73', '#CC79A7')))
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8), sharex=True, constrained_layout=True)
    for row, cohort in enumerate(COHORTS):
        for name in MODES[:4]:
            series = [modes[(p, name, cohort)] for p in PARTS]
            x = [q['tau_s'] for q in series]
            for col, prefix in enumerate(('symL', 'div')):
                for suffix, style in (('raw', '--'), ('C', '-')):
                    axes[row, col].plot(x, [q[prefix+suffix+'_over_u_m_1'] for q in series], style,
                        marker='o', ms=4, color=colors[name], label=name + (' raw' if suffix == 'raw' else ' C'))
                axes[row, col].set_ylabel(('Strain' if col == 0 else 'Divergence') + ' norm / velocity norm [1/m]')
                axes[row, col].set_title(cohort.replace('_', ' '))
    for ax in axes[1]:
        ax.set_xlabel('Actual saved time since release [s]')
    axes[0, 0].legend(ncol=2, fontsize=8)
    fig.suptitle('Frozen soil-only response to global alternating fields; four saved states')
    p = folder / 'response.png'; fig.savefig(p, dpi=180); plt.close(fig); paths.append(p)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.8), constrained_layout=True)
    for color, cohort in zip(('#0072B2', '#D55E00'), COHORTS):
        a = [modes[(p, 'affine_expansion_xz', cohort)] for p in PARTS]
        t = [modes[(p, 'translation_xz', cohort)] for p in PARTS]
        x = [q['tau_s'] for q in a]
        for suffix, style in (('raw', '--'), ('C', '-')):
            label = cohort.replace('_', ' ') + ' ' + suffix
            axes[0, 0].plot(x, [q['symL'+suffix+'_over_u_m_1'] for q in a], style, marker='o', color=color, label=label)
            axes[0, 1].plot(x, [q['affine_'+('raw' if suffix == 'raw' else 'C')+'_error_Vnorm'] for q in a], style, marker='o', color=color, label=label)
            axes[1, 0].plot(x, [q['symL'+suffix+'_over_u_m_1'] for q in t], style, marker='o', color=color, label=label)
            axes[1, 1].plot(x, [q['div'+suffix+'_over_u_m_1'] for q in t], style, marker='o', color=color, label=label)
    axes[0, 0].set_title('Analytic affine expansion: normalized strain'); axes[0, 0].set_ylabel('[1/m]')
    axes[0, 1].set_title('Affine sym-gradient error to diag(1,0,1)/s'); axes[0, 1].set_ylabel('V-weighted error [m/s]')
    axes[1, 0].set_title('Rigid translation: normalized strain'); axes[1, 0].set_ylabel('[1/m]')
    axes[1, 1].set_title('Rigid translation: normalized divergence'); axes[1, 1].set_ylabel('[1/m]')
    axes[0, 0].legend(fontsize=8)
    for ax in axes.flat:
        ax.set_xlabel('Actual saved time since release [s]')
    fig.suptitle('Algebraic soil-only controls; wall closure is excluded')
    p = folder / 'controls.png'; fig.savefig(p, dpi=180); plt.close(fig); paths.append(p)
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 7.8), sharex=True, constrained_layout=True)
    for col, cohort in enumerate(COHORTS):
        for name in MODES[:4]:
            series = [modes[(p, name, cohort)] for p in PARTS]
            axes[0, col].plot([q['tau_s'] for q in series], [q['actual_velocity_projection_coefficient'] for q in series],
                marker='o', color=colors[name], label=name)
        a = [modes[(p, 'actual_velocity', cohort)] for p in PARTS]
        axes[1, col].plot([q['tau_s'] for q in a], [q['Vnorm_u'] for q in a], 'o-', color='#333333', label='Actual velocity V-norm')
        axes[0, col].axhline(0, color='#777777', lw=.7)
        axes[0, col].set_yscale('symlog', linthresh=1e-7)
        axes[1, col].set_yscale('log')
        axes[0, col].set_title(cohort.replace('_', ' '))
        axes[0, col].set_ylabel('Signed one-field projection coefficient [-]')
        axes[1, col].set_ylabel('Actual velocity V-norm [m²/s]')
        axes[1, col].set_xlabel('Actual saved time since release [s]')
    axes[0, 0].legend(fontsize=8); axes[1, 0].legend(fontsize=8)
    fig.suptitle('Actual velocity projection onto nonorthogonal fields; not modal energy')
    p = folder / 'projections.png'; fig.savefig(p, dpi=180); plt.close(fig); paths.append(p)
    return paths

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Root full read and offline execution admission required')
    check_path = L / (TAG + '.check.json')
    folder = T / 'figures' / TAG
    need(not check_path.exists() and not folder.exists(), 'Existing complete/failed review artifacts protected')
    consumed = [stat(Path(__file__)), stat(NOTE)]
    result = dict(stage=TAG, passed=False, component_invocations=0, solver_invocations=0, reader_invocations=0,
                  build_invocations=0, GPU_actions=0, physical_steps=0, SHA_scans=0, physical_acceptance=False)
    try:
        proof = input_checks(consumed)
        modes = collect_modes()
        folder.mkdir()
        products = outputs(modes, folder)
        need(all(stat(q['path']) == q for q in consumed), 'A consumed artifact changed during offline review')
        interior = [modes[(p, 'altX_Uz', 'no_fixed_neighbors')] for p in PARTS]
        result.update(passed=True, consumed=consumed, consumed_stats_unchanged=True, baseline_CSV_byteproof=proof,
            full140000_field_CSV_retained_and_stat_bound=True, source_parts=list(PARTS), actual_force_calls_in_consumed_component=4,
            mode_records=56, output_CSVs=3, output_PNGs=3, products=[stat(p) for p in products],
            interior_altX_Uz=[dict(part=q['part'], time_s=q['time_s'], tau_s=q['tau_s'],
                C_strain_over_u_m_1=q['symLC_over_u_m_1'], raw_strain_over_u_m_1=q['symLraw_over_u_m_1'],
                signed_actual_projection_coefficient=q['actual_velocity_projection_coefficient']) for q in interior],
            actual_field_projections_are_not_modal_energy=True, near_null_threshold_defined=False,
            complete_eigenvalue_or_wall_analysis=False, clumping_repair_or_causal_claim=False,
            all22_primary_bitproof_claimed=False,
            conclusions_scope='Finite frozen soil-gradient response; no exact-null or full-system eigenvalue claim.')
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check_path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
