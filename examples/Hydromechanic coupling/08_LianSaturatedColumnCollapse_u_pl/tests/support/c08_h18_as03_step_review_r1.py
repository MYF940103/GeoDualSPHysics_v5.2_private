"""Offline AS03 onset-step attribution; no solver, native reader, build or physics change."""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_key, '1')
import argparse
import csv
import json
import math
import re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
L = T / 'logs'
TAG = 'c08_h18_as03_step_review_r1'
PARTS = (38, 76)
STEPS = (2076001, 2152001)
IDS = set(range(2060, 7060))
FOCUS = (4953, 4954, 6767, 6865)
ADMITTED = ('Elastic', 'Smooth', 'Apex', 'TensionRepair')
TRACE = ('logJ_minus_elastic_trace', 'kinematic_log_quadrature',
         'rate_trace_minus_3Ktheta_equivalent', 'trial_addition_roundoff_equivalent', 'return_trace_equivalent')
CONTACT = ('pre_contact_dx', 'pre_contact_dz', 'pre_contact_dvx', 'pre_contact_dvz',
           'corr_contact_dx', 'corr_contact_dz', 'corr_contact_dvx', 'corr_contact_dvz')
HEADERS = {
    'material_shadow.csv': ('stage,native_id,source_time_s,stage_width_s,source_completed_step,shadow_status,shadow_reason,trigger,'
        'kappa_n,kappa_continuous,shadow_kappa,actual_saved_kappa,I_n,I_trial,I_committed,q_trial,q_committed,lambda_shear,'
        'lambda_apex,lambda_tension,Rsigma_trace_Pa_s,theta_s_1,K_Pa,G_Pa,return_deltaI_Pa'),
    'trace_balance.csv': ('native_id,source_time_s,source_completed_step,dt_s,J_n,J_h,J_raw,I_n,I_trial_full,I_raw,'
        'Rsigma_trace_h_Pa_s,theta_h_s_1,delta_logJ,deltaI_over_3K,logJ_minus_elastic_trace,kinematic_log_quadrature,'
        'rate_trace_minus_3Ktheta_equivalent,trial_addition_roundoff_equivalent,return_trace_equivalent,closure,closure_budget,'
        'shadow_half_status,shadow_full_status,lambda_tension_full,kappa_n,kappa_next'),
    'balance.csv': ('native_id,force_h_group,FS_n,FS_force_n,FS_half_divide,FS_h,FS_completed,J_n,J_h,J_star,J_next,p_n,p_h,p_star,'
        'p_next,theta_n,theta_h,R_n,R_h,R_h_literal,D_h,delta_J,delta_p,delta_cap,c,hydraulic,cap,rate_cast_Pa_s,p_add_Pa,'
        'p_cast_Pa,p_update_residual_Pa,J_update_residual,source_order_residual,fp_predicted,balance_defect,closure_error,'
        'closure_budget,E_Pa,pre_contact_dx,pre_contact_dz,pre_contact_dvx,pre_contact_dvz,corr_contact_dx,corr_contact_dz,'
        'corr_contact_dvx,corr_contact_dvz'),
    'summary.csv': ('force_h_receiver_group,IDs,capped_IDs,sumV0_deltaJ,sumV0_c_deltaP,sumV0_hydraulic,sumV0_cap,sumV0_fp,'
        'sumV0_balance_defect,sumV0_closure,sumV0_abs_closure,sumV0_local_budget,aggregate_closure,aggregate_budget,'
        'sumV0_E_Pa_m2,max_abs_E_Pa')}

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)

def bind(entry, consumed):
    need(stat(entry['path']) == entry, 'Bound evidence changed: ' + entry['path'])
    consumed.append(entry)
    return Path(entry['path'])

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames == HEADERS[path.name].split(','), 'Exact original CSV schema required: ' + path.name)
        result = list(reader)
    strings = {'stage', 'force_h_group', 'force_h_receiver_group'}
    need(all(all(key in strings or math.isfinite(float(value)) for key, value in q.items()) for q in result),
         'Nonfinite original diagnostic value: ' + path.name)
    return result

def idmap(seq, label):
    need(len(seq) == 5000 and {int(q['native_id']) for q in seq} == IDS, 'Original5000-ID coverage differs: ' + label)
    return {int(q['native_id']): q for q in seq}

def array(seq, key):
    return np.array([float(q[key]) for q in seq], dtype=float)

def metric(base, stage, family, cohort, name, unit, seq, values=None, count=None):
    result = dict(**base, stage=stage, stage_width_s=base['dt_s'] * (.5 if stage == 'half' else 1.),
        family=family, cohort=cohort, metric=name, unit=unit, IDs=len(seq), count=count,
        mean=None, minimum=None, maximum=None, RMS=None, maxabs=None, maxabs_native_id=None)
    if values is not None and len(seq):
        a = np.asarray(values, dtype=float)
        need(len(a) == len(seq) and np.isfinite(a).all(), 'Finite scalar-per-ID statistic required')
        k = int(np.argmax(np.abs(a)))
        result.update(mean=float(a.mean()), minimum=float(a.min()), maximum=float(a.max()),
                      RMS=float(np.sqrt(np.mean(a*a))), maxabs=float(abs(a[k])), maxabs_native_id=int(seq[k]['native_id']))
    return result

def write(path, data):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)

def load_part(part, step, build_path, program, statuses, reasons, consumed):
    tag = 'c08_h18_as03_step_r1_p' + str(part)
    receipt = L / (tag + '.check.json'); consumed.append(stat(receipt)); check = read(receipt)
    need(check['passed'] and check['consumed_stats_unchanged'] and check['component_invocations'] == 1
         and check['physical_steps'] == 1 and not check['physical_acceptance'], 'Passed original one-step receipt required')
    need(bind(check['build'], consumed).resolve() == build_path.resolve(), 'Original common step program required')
    call, done = read(bind(check['actual_call'], consumed)), read(bind(check['completion'], consumed))
    need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and call['ownership_failure'] is None
         and Path(call['program']).resolve() == program.resolve() and call['arguments'][3:5] == ['--part', str(part)],
         'Actual successful part-specific owned CPU call required')
    need(done['passed'] and done['source_part'] == part and done['source_completed_step'] == step
         and done['completed_step'] == step + 1 and done['dt_s'] == 5e-6 and done['physical_steps'] == 1
         and done['actual_force_calls'] == done['actual_Darcy_calls'] == 2 and done['material_shadow_rows'] == 10000
         and done['trace_balance_rows'] == done['balance_rows'] == 5000 and done['summary_rows'] == 3
         and done['completed_time_s'] == done['source_time_s'] + done['dt_s']
         and done['all6_material_sigma_and_policy_kappa_bits_matched'] and done['sorted_predictor_scalar_bases_bit_equal']
         and done['positive_only_completed_cap_verified'] and done['shadow_status_not_instrumented_original_status'],
         'Original step/material/clock/completion policy differs')
    raw = {}
    for leaf in HEADERS:
        path = (T / 'outputs' / tag / leaf).resolve()
        matches = [q for q in check['files'] if Path(q['path']).resolve() == path]
        need(len(matches) == 1, 'Original CSV binding unavailable: ' + leaf)
        raw[leaf] = rows(bind(matches[0], consumed))
    material = raw['material_shadow.csv']
    need(len(material) == 10000 and {q['stage'] for q in material} == {'half', 'full'}, 'Actual two material stages required')
    mm = {name: idmap([q for q in material if q['stage'] == name], name) for name in ('half', 'full')}
    trace, balance = idmap(raw['trace_balance.csv'], 'trace'), idmap(raw['balance.csv'], 'balance')
    for name in ('half', 'full'):
        for q in mm[name].values():
            status, reason = int(q['shadow_status']), int(q['shadow_reason'])
            need(0 <= status < len(statuses) and statuses[status] in ADMITTED and 0 <= reason < len(reasons),
                 'Unaccepted original shadow status/reason')
            need(float(q['source_time_s']) == done['source_time_s'] and int(q['source_completed_step']) == step
                 and float(q['stage_width_s']) == done['dt_s']*(.5 if name == 'half' else 1.), 'Original material stage clock differs')
            need(float(q['K_Pa']) > 0 and float(q['actual_saved_kappa']) == float(q['kappa_n'] if name == 'half' else q['shadow_kappa']),
                 'Original predictor/corrector history policy differs')
    need(all(float(q['source_time_s']) == done['source_time_s'] and int(q['source_completed_step']) == step
             and float(q['dt_s']) == done['dt_s'] and abs(float(q['closure'])) <= float(q['closure_budget'])
             for q in trace.values()), 'Original trace arithmetic gate differs')
    need(all(abs(float(q['closure_error'])) <= float(q['closure_budget']) for q in balance.values()),
         'Original pressure/J arithmetic gate differs')
    summary = raw['summary.csv']
    need(len(summary) == 3 and {q['force_h_receiver_group'] for q in summary} == {'all', 'interior', 'FS'}
         and all(abs(float(q['aggregate_closure'])) <= float(q['aggregate_budget']) for q in summary),
         'Original aggregate arithmetic gate differs')
    return done, mm, trace, balance

def analyze(part, done, mm, trace, balance, statuses, reasons):
    base = dict(part=part, source_time_s=done['source_time_s'], source_tau_s=done['source_tau_s'],
                source_completed_step=done['source_completed_step'], completed_time_s=done['completed_time_s'], dt_s=done['dt_s'])
    stats, focus = [], []
    for stage in ('half', 'full'):
        seq = [mm[stage][i] for i in sorted(IDS)]
        for status in ADMITTED:
            stats.append(metric(base, stage, 'status', 'all', status, 'IDs', seq,
                                count=sum(statuses[int(q['shadow_status'])] == status for q in seq)))
        for region in ('all', 'TensionRepair'):
            chosen = seq if region == 'all' else [q for q in seq if statuses[int(q['shadow_status'])] == region]
            d = -array(chosen, 'return_deltaI_Pa')
            eq = d / (3 * array(chosen, 'K_Pa'))
            for name, unit, values in (('Dret', 'Pa', d), ('Dret_over_3K', 'dimensionless', eq),
                ('lambda_tension', 'dimensionless', array(chosen, 'lambda_tension')),
                ('continuous_kappa_increment', 'dimensionless', array(chosen, 'kappa_continuous') - array(chosen, 'kappa_n')),
                ('shadow_float_kappa_increment', 'dimensionless', array(chosen, 'shadow_kappa') - array(chosen, 'kappa_n')),
                ('actual_saved_kappa_increment', 'dimensionless', array(chosen, 'actual_saved_kappa') - array(chosen, 'kappa_n'))):
                stats.append(metric(base, stage, 'material', region, name, unit, chosen, values))
        lost = sum(float(q['kappa_continuous']) > float(q['kappa_n']) and float(q['shadow_kappa']) == float(q['kappa_n']) for q in seq)
        stats.append(metric(base, stage, 'history', 'all', 'positive_continuous_increment_but_shadow_float_unchanged', 'IDs', seq, count=lost))
    ts, bs = [trace[i] for i in sorted(IDS)], [balance[i] for i in sorted(IDS)]
    for name in TRACE + ('closure', 'closure_budget'):
        stats.append(metric(base, 'full', 'trace', 'all', name, 'dimensionless', ts, array(ts, name)))
    for name in ('delta_p', 'delta_cap', 'p_update_residual_Pa'):
        stats.append(metric(base, 'full', 'pressure', 'all', name, 'Pa', bs, array(bs, name)))
    stats.append(metric(base, 'full', 'pressure', 'all', 'completed_positive_FS_cap_changed_IDs', 'IDs', bs,
                        count=int(np.count_nonzero(array(bs, 'delta_cap')))))
    for name in CONTACT:
        stats.append(metric(base, 'half' if name.startswith('pre_') else 'full', 'contact', 'all', name,
                            'm/s' if 'dv' in name else 'm', bs, array(bs, name)))
    trace_ratios = [abs(float(q['closure'])) / float(q['closure_budget']) if float(q['closure_budget']) else 0. for q in ts]
    pressure_ratios = [abs(float(q['closure_error'])) / float(q['closure_budget']) if float(q['closure_budget']) else 0. for q in bs]
    for name, seq, values in (('trace_closure_original_budget_ratio', ts, trace_ratios),
                              ('pressure_J_closure_original_budget_ratio', bs, pressure_ratios)):
        stats.append(metric(base, 'full', 'arithmetic', 'all', name, 'dimensionless', seq, values))
    for native_id in FOCUS:
        item = dict(**base, native_id=native_id)
        for stage in ('half', 'full'):
            q = mm[stage][native_id]
            item.update({stage + '_' + k: v for k, v in q.items() if k not in ('native_id', 'source_time_s', 'source_completed_step', 'stage')})
            item[stage + '_status_name'] = statuses[int(q['shadow_status'])]
            item[stage + '_reason_name'] = reasons[int(q['shadow_reason'])]
            item[stage + '_Dret_Pa'] = -float(q['return_deltaI_Pa'])
            item[stage + '_Dret_over_3K'] = item[stage + '_Dret_Pa'] / (3 * float(q['K_Pa']))
        item.update({'trace_' + k: v for k, v in trace[native_id].items() if k not in ('native_id', 'source_time_s', 'source_completed_step', 'dt_s')})
        item.update({'balance_' + k: v for k, v in balance[native_id].items() if k != 'native_id'})
        focus.append(item)
    return stats, focus

def plots(folder, stats, focus):
    def value(part, stage, family, region, name, key='mean'):
        selected = [q for q in stats if (q['part'], q['stage'], q['family'], q['cohort'], q['metric']) == (part, stage, family, region, name)]
        need(len(selected) == 1, 'Unique plotted summary statistic required')
        out = selected[0][key]
        return np.nan if out is None else out
    plt.rcParams.update({'font.size': 10, 'axes.grid': True, 'grid.alpha': .22})
    profiles = [(p, stage) for p in PARTS for stage in ('half', 'full')]
    x = np.arange(4); labels = [f"P{p} {stage}" for p, stage in profiles]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    bottom = np.zeros(4)
    colors = ('#7299b8', '#dfac4a', '#9d72b2', '#bd3942')
    for status, color in zip(ADMITTED, colors):
        counts = np.array([value(p, s, 'status', 'all', status, 'count') for p, s in profiles])
        axes[0, 0].bar(x, counts, bottom=bottom, label=status, color=color); bottom += counts
    axes[0, 0].set(title='Bit-matched same-input shadow status', ylabel='Soil IDs'); axes[0, 0].legend(fontsize=8)
    for region, color in (('all', '#0072B2'), ('TensionRepair', '#D55E00')):
        axes[0, 1].plot(x, [value(p, s, 'material', region, 'Dret_over_3K') for p, s in profiles], 'o-', color=color, label='Mean: ' + region)
    axes[0, 1].set_yscale('symlog', linthresh=1e-15)
    axes[0, 1].set(title='Return-equivalent volumetric strain', ylabel='Dret / (3K) [-]'); axes[0, 1].legend(fontsize=8)
    short = ('logJ - elastic trace', 'log quadrature', 'rate trace mismatch', 'trial addition roundoff', 'material return')
    for name, label in zip(TRACE, short):
        axes[1, 0].plot(np.arange(2), [value(p, 'full', 'trace', 'all', name, 'RMS') for p in PARTS], 'o-', label=label)
    axes[1, 0].set_yscale('symlog', linthresh=1e-19)
    axes[1, 0].set(title='Full-stage trace decomposition: per-ID RMS', ylabel='Dimensionless'); axes[1, 0].legend(fontsize=8)
    z = np.arange(2)
    axes[1, 1].bar(z-.16, [value(p, 'full', 'pressure', 'all', 'delta_p') for p in PARTS], .32, label='Actual completed delta p')
    axes[1, 1].bar(z+.16, [value(p, 'full', 'pressure', 'all', 'delta_cap') for p in PARTS], .32, label='Completed positive-FS cap contribution')
    axes[1, 1].set(title='Mean pressure change in one 5 us CPU step', ylabel='Pressure [Pa]'); axes[1, 1].legend(fontsize=8)
    for ax in axes[0]:
        ax.set_xticks(x, labels)
    actual = [next(q['source_tau_s'] for q in stats if q['part'] == p) for p in PARTS]
    for ax in axes[1]:
        ax.set_xticks(z, [f'P{p}: {t:.9f}' for p, t in zip(PARTS, actual)]); ax.set_xlabel('Actual saved source tau [s]')
    fig.suptitle('Two independent CPU steps from saved AS03 GPU states; no GPU trajectory replay', fontsize=12)
    p = folder / 'summary.png'; fig.savefig(p, dpi=180); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for row, part in enumerate(PARTS):
        seq = [next(q for q in focus if q['part'] == part and q['native_id'] == i) for i in FOCUS]
        z = np.arange(4)
        for offset, stage, color in ((-.18, 'half', '#0072B2'), (.18, 'full', '#D55E00')):
            axes[row, 0].bar(z+offset, [q[stage+'_Dret_Pa'] for q in seq], .36, color=color, label=stage)
        axes[row, 0].set_ylabel('Trace reduction Dret [Pa]')
        axes[row, 0].set_title(f"P{part}, actual source tau={seq[0]['source_tau_s']:.9f} s")
        for key, label, marker in (('p_n', 'Saved source p_n', 'o'), ('p_star', 'CPU raw corrector p', '^'), ('p_next', 'CPU completed-cap p', 'x')):
            axes[row, 1].plot(z, [float(q['balance_'+key]) for q in seq], marker=marker, linestyle='none', ms=7, label=label)
        axes[row, 1].set(title='Four original material IDs: pressures', ylabel='Pressure [Pa]')
        for ax in axes[row]:
            ax.set_xticks(z, [str(i) for i in FOCUS]); ax.set_xlabel('Native material ID'); ax.axhline(0, color='#888888', lw=.6)
    axes[0, 0].legend(fontsize=8); axes[0, 1].legend(fontsize=8)
    fig.suptitle('Same-input material return and one CPU increment at fixed IDs; no inferred unsaved GPU state', fontsize=12)
    q = folder / 'focus.png'; fig.savefig(q, dpi=180); plt.close(fig)
    return [p, q]

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args(); need(args.execution_authorized, 'Root full-file review and separate offline admission required')
    check_path, folder = L / (TAG + '.check.json'), T / 'figures' / TAG
    need(not check_path.exists() and not folder.exists(), 'Existing complete/failed derived artifacts protected')
    consumed, products = [stat(Path(__file__)), stat(T / 'notes' / (TAG + '.md'))], []
    result = dict(stage=TAG, passed=False, component_invocations=0, solver_invocations=0, native_decodes=0,
                  build_invocations=0, GPU_actions=0, physical_steps=0, SHA_scans=0, physical_acceptance=False)
    try:
        build_path = L / 'c08_h18_as03_step_r1.build.json'; consumed.append(stat(build_path)); build = read(build_path)
        need(build['passed'] and build['consumed_stats_unchanged'] and build['physical_objects_compiled'] == 0
             and build['actual_link_objects'] == 87 and build['material_shadow_not_feedback']
             and build['entry_derivation']['actual_step_call_block_byte_equal'], 'Original no-hook AS03 step build required')
        program = bind(build['program'], consumed)
        headers = [q for q in build['archived_headers'] if Path(q['path']).name == 'FunSoilMaterial.h']
        need(len(headers) == 1, 'One actual frozen material header required')
        header = bind(headers[0], consumed).read_text(encoding='utf-8-sig')
        statuses = [q.strip() for q in re.search(r'enum class Status:unsigned\{([^}]+)\};', header).group(1).split(',')]
        reasons = [q.strip() for q in re.search(r'enum class Reason:unsigned\{([^}]+)\};', header).group(1).split(',')]
        need(statuses == ['Invalid', 'Elastic', 'Smooth', 'Apex', 'TensionRepair', 'NoAdmissibleFlow', 'NonConverged', 'UnresolvedPath'],
             'Frozen material status definition differs')
        stats, focus, completions = [], [], []
        for part, step in zip(PARTS, STEPS):
            done, mm, trace, balance = load_part(part, step, build_path, program, statuses, reasons, consumed)
            a, b = analyze(part, done, mm, trace, balance, statuses, reasons)
            stats.extend(a); focus.extend(b); completions.append(done)
        folder.mkdir()
        for leaf, data in (('summary.csv', stats), ('focus.csv', focus)):
            path = folder / leaf; write(path, data); products.append(path)
        products.extend(plots(folder, stats, focus))
        need(all(stat(q['path']) == q for q in consumed), 'Bound original/derived-input evidence changed during review')
        result.update(passed=True, consumed=consumed, consumed_stats_unchanged=True, source_parts=list(PARTS),
            original_completed_components=2, actual_original_CPU_force_calls=4, actual_original_CPU_steps=2,
            material_shadow_rows=20000, trace_rows=10000, balance_rows=10000, focus_IDs=list(FOCUS),
            outputs=[stat(p) for p in products], summary_rows=len(stats), focus_rows=len(focus),
            status_names_from_frozen_header=statuses, actual_completions=completions,
            original_arithmetic_budgets_unrelaxed=True, Dret_is_trace_reduction_Pa=True,
            Dret_over_3K_is_equivalent_strain_not_extra_native_volume=True,
            shadow_status_is_not_original_call_instrumentation=True, GPU_full_history_attribution=False,
            no_material_or_pressure_cap_change=True, no_added_J_or_pressure_source=True, visual_QA_pending=True)
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check_path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)

if __name__ == '__main__':
    main()
