"""Pure offline own-prefix4 and full301 HG phase review; never reads BI4 or solves.

Import defines functions/constants only. Root must separately review/admit the one
fresh invocation. Native decoding and physical/paper acceptance remain separate.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import struct
import sys


T = Path(__file__).resolve().parents[1]
L = T / 'logs'
TAG = 'c08_h18_wall_c_retry_full3_hg_review_r1'
FULL = 'c08_h18_wall_c_retry_full3_GPU_r2'
SHORT = 'c08_h18_wall_c_retry_prefix4_GPU_r1'
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
SCRIPT, NOTE = Path(__file__).resolve(), T / 'notes' / (TAG + '.md')
CHECK, AD = L / (TAG + '.check.json'), L / (TAG + '.root_admission.json')
CSV = T / 'figures' / (TAG + '_phases.csv')
EXT = T / 'figures' / (TAG + '_extrema.csv')
PNG = T / 'figures' / (TAG + '_history.png')
N, IDS, ARRAYS, FIRST, LAST, DT = 5000, 6805, 22, 2000000, 2600000, .000005
INTS = set('completed_step pre_calls cor_calls commits error invalid_id invalid_slot np rows max_degree known_constant_rows elastic smooth apex tension material_checked material_produced cache_consumed cache_input_scalar_checks cache_output_scalar_checks kept born dead accepted_born accepted_dead'.split())
METRICS = tuple('rows max_degree condition lambda_s2 dt_over_0p2_limit min_r max_half_angle elastic smooth apex tension gamma_min gamma_max material_root_ratio Eold Enew Edead loading_loss row_work node_work rotation_change ledger ledger_minus_rotation old_minus_kept_dead ledger_over_recorded_budget adjoint_over_recorded_budget net_over_recorded_budget torque_over_recorded_budget commit_summary_max_over_max max_force max_delta_ace objective_accumulated_angle'.split())


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def stat(path):
    path = Path(path).resolve()
    value = path.stat()
    need(path.is_file(), 'Expected file: ' + str(path))
    return dict(path=str(path), bytes=value.st_size, mtime_ns=value.st_mtime_ns)


def bits(value):
    return struct.pack('<d', float(value))


def ratio(value, budget):
    need(budget >= 0, 'Negative recorded diagnostic budget')
    return abs(value) / budget if budget else None


def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    need(rows and all(None not in row and all(v != '' for v in row.values()) for row in rows),
         'Incomplete CSV: ' + str(path))
    return reader.fieldnames, rows


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def write(path, rows):
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def owned(call):
    need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
         and call['ownership_failure'] is None, 'Actual Popen/Win32 exit0 required')


def context(take):
    runpath, np = L / (FULL + '.run.json'), L / (FULL + '.native_r1.check.json')
    sp, ep = L / (SHORT + '.check.json'), L / (FULL + '.native_r1.exports.json')
    ad = read(take(AD))
    need(ad['authorized'] and ad['offline_only'] and ad['root_thread_id'] == THREAD
         and ad['execution_script'] == stat(SCRIPT) and ad['note'] == stat(NOTE)
         and ad['run'] == stat(runpath) and ad['native_check'] == stat(np)
         and ad['own_prefix_check'] == stat(sp) and ad['native_exports'] == stat(ep),
         'Exact root offline-only admission required')
    run, native, short, exports = [read(take(q)) for q in (runpath, np, sp, ep)]
    need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
         and run['solver_identity_matches'] and run['ownership_failure'] is None
         and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit']
         == run['actual_tool_Win32_exit'] == 0 and run['actual_steps'] == LAST
         and run['saved_frames'] == 301 and run['new_updates'] == 600000,
         'Real completed full301 run required, not an old failed99 result')
    owned(read(take(run['actual_call'])))
    need(native['passed'] and native['reader_invocations'] == 1
         and native['consumed_stats_unchanged'] and native['original_safety_passed'],
         'One original full301 native read/check required')
    owned(read(take(native['actual_call'])))
    need(exports['passed'] and exports['original_unique_read'] == stat(np)
         and exports['original_call'] == native['actual_call']
         and exports['header'] == [IDS, ARRAYS, 301]
         and exports['new_root_snapshot_after_reader_completion']
         and exports['not_claimed_original_reader_receipt_seal'],
         'Actual root after-reader stat snapshot required; do not backdate its seal')
    for entry in exports['files']:
        take(entry)
    full_dir = Path(run['output'])
    need(full_dir == T / 'outputs' / FULL, 'Closed full output path differs')
    nd = read(take(native['native_completion']))
    need(nd['passed'] and nd['samples'] == 301 and nd['completed_steps'] == LAST
         and nd['typed_arrays'] == ARRAYS and nd['typed_bytes_per_particle'] == 212
         and nd['actual_native_IDs_per_frame'] == IDS and nd['soil_IDs'] == N
         and nd['actual_fixed_IDs'] == 1805 and not nd['native_rewritten']
         and nd['max_scalar_clock_error_s'] <= 1e-14 and nd['max_signed_dterror_s'] <= 1e-14
         and nd['nonempty_signed_intervals'] == 301 and not nd['physical_acceptance'],
         'Original full native extent/identity/clock/signed gates differ')
    take(native['metadata'])
    need(short['passed'] and short['all22_native_four_records_byte_equal']
         and short['clock_layout_signed_rows_byte_equal'] and short['HG_eight60column_rows_byte_equal']
         and short['all_original_native_guards'] and short['consumed_stats_unchanged'],
         'Candidate own-prefix4 implementation review required')
    short_run = read(take(short['solver_run']))
    need(short_run['program'] == run['program'] and short_run['source_build'] == run['source_build']
         and short_run['source_pre_file'] == run['source_pre_file'],
         'Own prefix must use the same actual candidate program/build/PRE')
    owned(read(take(short_run['actual_call'])))
    sn = read(take(short['native_completion']))
    need(sn['passed'] and sn['samples'] == 4 and sn['completed_steps'] == FIRST + 6001
         and sn['typed_arrays'] == ARRAYS and sn['actual_native_IDs_per_frame'] == IDS
         and not sn['native_rewritten'], 'Own short native extent differs')
    short_dir = T / 'outputs' / SHORT
    for leaf in short['compared_files']:
        path = (short_dir / leaf).resolve()
        refs = [q for q in short['consumed'] if Path(q['path']).resolve() == path]
        need(refs and all(q == refs[0] for q in refs), 'Own short export has no unique frozen stat')
        take(refs[0])
    b = read(take(run['source_build']))
    opt = read(take(b['original_optimized_build']))
    need(b['passed'] and b['consumed_stats_unchanged'] and not b['private_HG_Node_material_recompiled']
         and opt['passed'], 'Retained actual optimized HG producer source/build required')
    cuda = Path(take(opt['private_sources']['CUDA']))
    source = cuda.read_text(encoding='utf-8-sig')
    headers = re.findall(r'h<<"(phase,completed_step,[^"]+)"', source)
    need(len(headers) == 1 and all(anchor in source for anchor in
        ('o.ledger=(newE-oldE+nodeWork+loss+deadE).v',
         'o.adjoint_defect=(nodeWork-rowWork).v', 'std::swap(p.memory.e,p.graph.next_e)')),
         'Original optimized ledger/adjoint/lifecycle source anchors differ')
    header = headers[0].removesuffix(r'\n').split(',')
    need(len(header) == 60, 'Original HG60 schema required')
    return run, full_dir, short_dir, header


def prefix(run, full, short, take):
    fdir, sdir = full / 'native_r1', short / 'native_r1'
    layout = (fdir / 'typed22_layout.csv').read_bytes()
    need(layout == (sdir / 'typed22_layout.csv').read_bytes(), 'Original22 raw layouts differ')
    _, fields = table(fdir / 'typed22_layout.csv')
    need(len(fields) == ARRAYS and len({q['array'] for q in fields}) == ARRAYS,
         'Original22 typed arrays must all be present exactly once')
    widths = {'uint32': 4, 'float32': 4, 'float64': 8}
    need(all(int(q['bytes_per_particle']) == widths[q['type']] * int(q['components']) for q in fields),
         'Typed layout component widths differ')
    per_particle = sum(int(q['bytes_per_particle']) for q in fields)
    need(per_particle == 212, 'Original typed22 per-particle bytes differ')
    record = 8 + IDS * per_particle  # Real native time precedes every complete array record.
    for directory, count in ((fdir, 301), (sdir, 4)):
        path = directory / 'typed22.bin'
        need(path.stat().st_size == 12 + count * record, 'Typed export length differs')
        with path.open('rb') as stream:
            need(struct.unpack('<III', stream.read(12)) == (IDS, ARRAYS, count),
                 'Original301/4 headers must remain distinct and untouched')
    with (fdir / 'typed22.bin').open('rb') as left, (sdir / 'typed22.bin').open('rb') as right:
        left.seek(12); right.seek(12)
        for part in range(4):
            a, b = left.read(record), right.read(record)
            need(len(a) == record and a == b, 'Own first4 full native record differs at part ' + str(part))
    fraw = (fdir / 'clocks.csv').read_bytes().splitlines(keepends=True)
    sraw = (sdir / 'clocks.csv').read_bytes().splitlines(keepends=True)
    need(len(fraw) == 302 and len(sraw) == 5 and fraw[:5] == sraw,
         'All own first4 raw clock/signed rows, including the first post frame, must match')
    _, clock = table(fdir / 'clocks.csv')
    _, plan = table(take(run['planned_steps']))
    need(len(plan) == len(clock) == 301 and int(plan[-1]['completed_step']) == LAST,
         'Original full301 plan/clock extent differs')
    wanted = {int(q['completed_step']) for q in plan}
    scalar, steps = float(run['actual_source_time_s']), {}
    for step in range(FIRST + 1, LAST + 1):
        previous = scalar
        scalar += DT
        if step in wanted:
            steps[step] = (previous, scalar)
    need(bits(scalar) == bits(run['planned_actual_end_s']), 'Scalar +=dt end differs')
    with (fdir / 'typed22.bin').open('rb') as stream:
        for part, (p, c) in enumerate(zip(plan, clock)):
            step = int(p['completed_step'])
            expected = FIRST + 1 + part * 2000 if part < 300 else LAST
            signed = float(c['signed_dterror_s'])
            need(int(p['part']) == int(c['part']) == part and step == expected
                 and int(c['completed_step']) == step and int(p['saved_step']) == int(c['saved_step']) == step - 1
                 and bits(p['time_s']) == bits(c['time_s']) == bits(steps[step][1])
                 and bits(p['dt_s']) == bits(c['dt_s']) == bits(DT)
                 and c['dterror_interval_empty'] == '0' and math.isfinite(signed) and signed <= 1e-14
                 and int(c['native_IDs']) == IDS, 'Original301 actual clock/signed gate differs')
            stream.seek(12 + part * record)
            need(stream.read(8) == bits(c['time_s']), 'Actual typed time payload differs from clock row')
    return plan, steps, dict(shared_records=4, record_bytes=record,
        compared_record_bytes=4 * record, preserved_headers=[[IDS, ARRAYS, 301], [IDS, ARRAYS, 4]],
        all22_and_time_payload_first4_exact=True, raw_layout_exact=True,
        all_first4_raw_clock_signed_rows_exact=True, checked_full_clock_rows=301,
        all_full_typed_time_payloads_checked=True, no_header_or_record_rewrite=True)


def phases(run, full, short, expected_header, plan, steps, take):
    fp, sp = full / 'C08OptPlasticHGPolicy.json', short / 'C08OptPlasticHGPolicy.json'
    fc, sc = full / 'C08OptPlasticHG.csv', short / 'C08OptPlasticHG.csv'
    observed = [stat(take(q)) for q in (fp, fc)]
    policy = read(fp)
    expected = dict(schema=2, policy='PrivateC08SingleProducerOptPlasticHG', phase='ReleaseOnly',
        active=True, xi=.1, nodes=N, first_id=2060, neighbor_capacity=128, kernel='Wendland',
        h=struct.unpack('<f', struct.pack('<f', .072))[0], dt=DT, old_public_HG_unchanged=True,
        source_PRE_HG_OFF_then_cold_release_e0=True, exact_HG_restart_claimed=False,
        single_material_producer=True, cache_consumers_once_per_ID_stage=True,
        independent_material_return_comparison=False, cache_input_and_commit_bits_checked=True,
        n_h_start_same_committed_e=True, active_only_memory=True, trial_edge_counts_per_phase=True,
        cumulative_deletion_only_at_full_accept=True, new_edge_zero=True, removed_energy_recorded=True,
        full_LS_adjoint=True, HG_value_RN=True, material_original_fast_math=True,
        observer_budget_is_outward_certificate=False, coupled_passivity_claimed=False,
        same_stage_Darcy_required_by_host=True, native_22_layout_changed=False, physical_acceptance=False)
    need(policy == read(sp) == expected, 'Actual own/full optimized schema2 HG policies differ')
    fraw, sraw = fc.read_bytes().splitlines(keepends=True), sc.read_bytes().splitlines(keepends=True)
    need(len(fraw) == 603 and len(sraw) == 9 and fraw[:9] == sraw,
         'HG header and all own first8 actual60-column rows must match verbatim')
    header, raw = table(fc)
    need(header == expected_header and len(raw) == 602, 'Actual602/HG60 extent differs')
    rows, previous_cor, max_defect = [], None, 0.
    for part, p in enumerate(plan):
        pair, step = [], int(p['completed_step'])
        for index, phase in enumerate(('Pre', 'Cor')):
            original = raw[2 * part + index]
            need(original['phase'] == phase, 'Actual Pre/Cor phase order differs')
            row = {name: phase if name == 'phase' else float(value) for name, value in original.items()}
            need(all(math.isfinite(v) for k, v in row.items() if k != 'phase'), 'Nonfinite HG scalar')
            for name in INTS:
                row[name] = int(original[name])
            need(row['completed_step'] == step and bits(row['saved_time_s']) == bits(p['time_s'])
                 and bits(row['source_time_s']) == bits(steps[step][0])
                 and bits(row['saved_time_s']) == bits(steps[step][1]) and bits(row['dt_s']) == bits(DT),
                 'Actual source/saved phase clocks differ')
            need(row['pre_calls'] == row['cor_calls'] == row['commits'] == step - FIRST
                 and row['error'] == 0 and row['invalid_id'] == row['invalid_slot'] == 0xffffffff
                 and row['np'] == IDS and row['elastic'] + row['smooth'] + row['apex'] + row['tension'] == N
                 and row['material_checked'] == row['material_produced'] == row['cache_consumed'] == N
                 and row['cache_input_scalar_checks'] == 13 * N and row['cache_output_scalar_checks'] == 7 * N,
                 'Original coverage/cache/status counters differ')
            need(0 < row['rows'] <= N * 128 and row['rows'] % 2 == 0 and 2 <= row['max_degree'] <= 128
                 and 0 <= row['known_constant_rows'] <= row['rows'] and row['kept'] + row['born'] == row['rows']
                 and 0 <= row['gamma_min'] <= row['gamma_max'] <= 1 and 0 < row['condition'] < 1e8
                 and row['lambda_s2'] > 0 and 0 < row['dt_over_0p2_limit'] <= 1
                 and row['min_r'] > 0 and 0 <= row['max_half_angle'] < .005
                 and all(row[q] >= 0 for q in ('Eold', 'Ekept', 'Edead', 'Enew', 'material_root_ratio',
                                              'accepted_discarded_energy', 'objective_accumulated_angle')),
                 'Original positive/rank/graph/dt/spin/loading domain gate differs')
            ledger = math.fsum([row['Enew'], -row['Eold'], row['node_work'], row['loading_loss'], row['Edead']])
            scale = sum(abs(row[q]) for q in ('Enew', 'Eold', 'node_work', 'loading_loss', 'Edead'))
            u = sys.float_info.epsilon / 2
            bound = (8 * u / (1 - 8 * u)) * scale + 16 * math.ulp(0.)
            defect = abs(ledger - row['ledger'])
            need(defect <= bound and bits(row['node_work'] - row['row_work']) == bits(row['adjoint_defect']),
                 'Original scalar energy/adjoint arithmetic reconciliation failed')
            max_defect = max(max_defect, defect)
            row.update(part=part, tau_s=row['saved_time_s'] - float(run['actual_source_time_s']),
                ledger_recomputed=ledger, ledger_recompute_bound=bound,
                ledger_minus_rotation=row['ledger'] - row['rotation_change'],
                old_minus_kept_dead=math.fsum([row['Eold'], -row['Ekept'], -row['Edead']]),
                ledger_over_recorded_budget=ratio(row['ledger'], row['ledger_budget']),
                adjoint_over_recorded_budget=ratio(row['adjoint_defect'], row['adjoint_budget']),
                net_over_recorded_budget=ratio(max(abs(row['net_x']), abs(row['net_z'])), row['net_budget']),
                torque_over_recorded_budget=ratio(row['torque'], row['torque_budget']),
                commit_summary_max_over_max=ratio(row['max_commit_error'], row['commit_budget']))
            rows.append(row); pair.append(row)
        pre, cor = pair
        need(bits(pre['Eold']) == bits(cor['Eold']), 'Pre/Cor must start from identical committed e')
        for name in ('accepted_born', 'accepted_dead', 'accepted_discarded_energy', 'objective_accumulated_angle'):
            need(bits(pre[name]) == bits(cor[name]), 'Accepted phase-pair lifecycle counters differ')
        need(cor['accepted_born'] - cor['accepted_dead'] == cor['rows'], 'Cold directed-row ledger differs')
        if previous_cor is None:
            need(all(r[k] == 0 for r in pair for k in ('Eold', 'Ekept', 'Edead', 'kept'))
                 and cor['accepted_dead'] == 0 and cor['accepted_born'] == cor['rows']
                 and cor['accepted_discarded_energy'] == 0, 'Cold first accepted memory differs')
        else:
            need(all(cor[k] >= previous_cor[k] for k in
                ('accepted_born', 'accepted_dead', 'accepted_discarded_energy', 'objective_accumulated_angle')),
                'Original cumulative accepted lifecycle observation decreased')
        previous_cor = cor
    need(all(rows[-1][k] == 600000 for k in ('pre_calls', 'cor_calls', 'commits')),
         'Actual final per-stage and full-accept counts must each be600000')
    ratios = ('ledger_over_recorded_budget', 'adjoint_over_recorded_budget',
              'net_over_recorded_budget', 'torque_over_recorded_budget', 'commit_summary_max_over_max')
    summary = dict(reviewed_rows=602, saved_phase_pairs=301, Eold_bit_equal_pairs=301,
        own_first8_HG_rows_exact=True, policy_equal=True, maximum_ledger_scalar_recompute_defect=max_defect,
        all_original_saved_domain_clock_cache_lifecycle_gates=True,
        saved_material_produced=sum(r['material_produced'] for r in rows),
        saved_cache_input_scalar_checks=sum(r['cache_input_scalar_checks'] for r in rows),
        saved_cache_output_scalar_checks=sum(r['cache_output_scalar_checks'] for r in rows),
        ratio_over_one_counts={k: sum(r[k] is not None and r[k] > 1 for r in rows) for k in ratios},
        undefined_ratio_counts={k: sum(r[k] is None for r in rows) for k in ratios},
        material_root_ratio_over_one_rows=sum(r['material_root_ratio'] > 1 for r in rows),
        negative_loading_loss_rows=sum(r['loading_loss'] < 0 for r in rows),
        positive_node_work_rows=sum(r['node_work'] > 0 for r in rows),
        final_counters={k: rows[-1][k] for k in ('pre_calls', 'cor_calls', 'commits')},
        first_HG_review_stat_observation=observed)
    return rows, summary


def extrema(rows):
    result = []
    for phase in ('Pre', 'Cor'):
        group = [r for r in rows if r['phase'] == phase]
        for metric in METRICS:
            finite = [r for r in group if r[metric] is not None]
            if finite:
                low, high = min(finite, key=lambda r: r[metric]), max(finite, key=lambda r: r[metric])
                worst = max(finite, key=lambda r: abs(r[metric]))
                result.append(dict(phase=phase, metric=metric, min=low[metric], min_part=low['part'],
                    min_time_s=low['saved_time_s'], max=high[metric], max_part=high['part'],
                    max_time_s=high['saved_time_s'], absmax=abs(worst[metric]), absmax_part=worst['part'],
                    absmax_time_s=worst['saved_time_s'], undefined_count=301 - len(finite)))
            else:
                result.append(dict(phase=phase, metric=metric, min=None, min_part=None, min_time_s=None,
                    max=None, max_part=None, max_time_s=None, absmax=None, absmax_part=None,
                    absmax_time_s=None, undefined_count=301))
    return result


def plot(rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    charts = [('Eold', 'Enew'), ('row_work', 'node_work'), ('loading_loss', 'rotation_change', 'ledger'),
              ('rows', 'accepted_dead'), ('dt_over_0p2_limit',), ('gamma_min', 'gamma_max'),
              ('max_half_angle',), ('max_commit_error', 'commit_budget'),
              ('ledger_over_recorded_budget', 'adjoint_over_recorded_budget', 'torque_over_recorded_budget')]
    fig, axes = plt.subplots(3, 3, figsize=(17, 12), layout='constrained')
    for ax, columns in zip(axes.flat, charts):
        for phase, style in (('Pre', '--'), ('Cor', '-')):
            group = [r for r in rows if r['phase'] == phase]
            for name in columns:
                ax.plot([r['tau_s'] for r in group], [r[name] for r in group], style,
                        label=phase + ' ' + name, linewidth=1)
        ax.set(xlabel='Actual time after release [s]', title=', '.join(columns))
        ax.grid(alpha=.2); ax.legend(fontsize=7)
    axes[1, 1].axhline(1, color='black', linewidth=.6)
    axes[2, 0].axhline(.005, color='black', linewidth=.6)
    fig.suptitle('C08 candidate full301 HG observations; Pre/Cor are trials from the same committed e\n'
                 'Loading/rotation and diagnostic budgets are not a coupled-energy certificate')
    fig.savefig(PNG, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    need(parser.parse_args().execution_authorized, 'Root must authorize this pure offline review')
    need(not any(q.exists() for q in (CHECK, CSV, EXT, PNG)), 'Existing complete/partial review protected')
    consumed = {}

    def take(value):
        path = Path(value['path'] if isinstance(value, dict) else value).resolve()
        observed = stat(path)
        if isinstance(value, dict):
            need(observed == value, 'Bound stat changed: ' + str(path))
        if str(path) in consumed:
            need(consumed[str(path)] == observed, 'Consumed stat changed: ' + str(path))
        consumed[str(path)] = observed
        return path

    result = dict(stage=TAG, passed=False, analysis_complete=False, physical_acceptance=False,
        solver_invocations=0, reader_invocations=0, build_invocations=0, VTK_invocations=0,
        SHA_scans=0, automatic_next_job=False, old_failed99_modified=False)
    try:
        take(SCRIPT); take(NOTE)
        run, full, short, header = context(take)
        plan, clocks, exact = prefix(run, full, short, take)
        rows, hg = phases(run, full, short, header, plan, clocks, take)
        summary = extrema(rows)
        need(all(stat(q['path']) == q for q in consumed.values()), 'Input changed during offline review')
        write(CSV, rows); write(EXT, summary); plot(rows)
        result.update(passed=True, analysis_complete=True, own_prefix=exact, HG=hg,
            source_run=stat(L / (FULL + '.run.json')),
            source_native_check=stat(L / (FULL + '.native_r1.check.json')),
            native_exports_snapshot=stat(L / (FULL + '.native_r1.exports.json')),
            own_prefix_check=stat(L / (SHORT + '.check.json')),
            consumed_stats_unchanged=True, files=[stat(q) for q in (CSV, EXT, PNG)], visual_QA_pending=True,
            full_solver_completed=True, full_native_safety_inherited_from_unique_read=True,
            no_interpolation=True, full_vs_own_prefix_is_same_dt_not_half=True,
            cache_scope='input13 and exactcommit7 are one-producer coherence, not an independent old material solve',
            energy_scope='Pre/Cor are trials from the same committed e; never add as consecutive accepted work',
            budget_scope='Original diagnostic estimates and undefined ratios retained; not outward/coupled-energy certificates',
            loading_projection_scope='Signed local loading_loss and rotation are preserved; no new loading_loss>=0 gate',
            commit_scope='max(error)/max(budget) is descriptive; original per-node commit guard was internal',
            NoPen_projection_work_not_captured=True, NoPenReactionClosed=False,
            all_updates_scope='Source/control-flow plus completed owner contract;602 saved rows are not every-stage exports',
            old_failed99_remains_failed=True, full_physics_or_paper_accepted=False)
    except Exception as error:
        result['first_failure'] = repr(error)
    result['created_utc'] = datetime.now(timezone.utc).isoformat()
    result['consumed'] = list(consumed.values())
    save(CHECK, result)
    need(result['passed'], result.get('first_failure', 'Offline review failed; preserve outputs'))


if __name__ == '__main__':
    main()
