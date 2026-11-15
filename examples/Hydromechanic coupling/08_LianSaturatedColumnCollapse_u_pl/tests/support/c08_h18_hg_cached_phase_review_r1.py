"""Closed offline review of the completed cached-HG window sidecar; no native reads."""
import argparse
import csv
import json
import math
from pathlib import Path
import re
import struct
import sys

TAG = 'c08_h18_hg_cached_phase_review_r1'
JOB = 'c08_h18_hg_cached_window_GPU_r1'
T = Path(__file__).resolve().parents[1]
L = T / 'logs'
OUT = T / 'outputs' / JOB
CHECK = L / (TAG + '.check.json')
SUMMARY = T / 'figures' / (TAG + '_summary.csv')
N, DT, FIRST, LAST = 5000, .000005, 2000000, 2180000


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bits(x):
    return struct.pack('<d', float(x))


def ratio(value, budget):
    need(budget >= 0, 'Negative recorded budget')
    return abs(value) / budget if budget else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Explicit offline execution authorization required')
    need(not CHECK.exists() and not SUMMARY.exists(), 'Fresh exclusive outputs required; never overwrite/retry')
    consumed = []

    def observe(path):
        entry = stat(path)
        consumed.append(entry)
        return entry

    def bind(entry):
        need(stat(entry['path']) == entry, 'Bound stat changed: ' + entry['path'])
        consumed.append(entry)
        return Path(entry['path'])

    result = dict(stage=TAG, passed=False, offline_only=True, solver_invocations=0,
                  native_decodes=0, build_invocations=0, VTK_invocations=0, SHA_scans=0,
                  physical_acceptance=False, coupled_passivity_proven=False,
                  outward_certificate=False, all_updates_exported=False,
                  new_physics_candidate=False)
    try:
        run_path = L / (JOB + '.run.json')
        result['source_run'] = observe(run_path)
        run = read(run_path)
        need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
             and run['actual_steps'] == LAST and run['saved_frames'] == 91
             and run['solver_invocations'] == run['solver_launch_attempts'] == 1
             and run['ownership_failure'] is None
             and all(run[k] == 0 for k in ('actual_exit', 'actual_Win32_exit', 'actual_tool_exit', 'actual_tool_Win32_exit')),
             'Completed uniquely owned solver/window receipt required')
        need(run['operator'] == 'EnergyNormalizedAdjointLoadingOnlyCachedMaterial'
             and run['policy_schema'] == 2 and run['fixed_dt_s'] == DT
             and run['new_updates'] == LAST - FIRST
             and run['environment_override'] == {'C08_HG_CACHED_H18': '1'}, 'Exact cached window scope differs')
        call = read(bind(run['actual_call']))
        start_path = L / (JOB + '.start.json')
        result['original_start'] = observe(start_path)
        start = read(start_path)
        need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
             and call['ownership_failure'] is None and call['child'] == run['solver_identity']
             and call['child']['parent_pid'] == run['owner']['pid'] == call['owner']['pid']
             and call['owner']['created_epoch'] == run['owner']['created_epoch']
             and call['child']['creation_filetime_100ns'] > 0
             and call['child']['argv'] == run['argv'] == start['argv']
             and call['child']['exe'] == run['program']['path'] == call['program']
             and run['owner'] == start['owner'], 'Original actual child/owner/argv/exits differ')
        result.update(actual_call=run['actual_call'], owner=run['owner'], solver_identity=call['child'],
                      actual_Popen_wait_exit=0, actual_Win32_exit=0)
        for key in ('program', 'source_capture', 'source_archive', 'baseline_source_capture',
                    'source_pre_file', 'input_xml', 'planned_steps', 'solver_completion', 'Run_out', 'Run_csv'):
            bind(run[key])
        for key in ('root_admission', 'preparation', 'physical_decision'):
            bind(run[key])
        for entry in run['private_sources'].values():
            bind(entry)
        build = read(bind(run['source_build']))
        need(build['passed'] and build['consumed_stats_unchanged']
             and build['configuration'] == 'Release' and build['program'] == run['program']
             and build['retained_original_objects'] == 111 and build['private_objects'] == 3
             and build['actual_link_objects'] == 114 and build['policy_schema'] == 2
             and build['single_material_producer'] and build['original_physical_CUDA_objects_retained']
             and build['OFF_calls_original_compiled_integrators'], 'Frozen build/producer closure differs')
        need(build['private_sources'] == run['private_sources'], 'Run/build private source bindings differ')
        for entry in build['calls']:
            c = read(bind(entry))
            need(c['actual_Popen_wait_exit'] == c['actual_Win32_exit'] == 0 and c['ownership_failure'] is None,
                 'A source build tool did not genuinely complete')
        source = read(run['source_capture']['path'])
        need(source['passed'] and source['private_sources'] == run['private_sources']
             and source['exact_reverse_original_hosts_bytes'] and source['exact_reverse_original_integrators_bytes'],
             'Reversible source capture differs')
        for key in ('source_diff', 'source_proof'):
            bind(source[key])
        text = Path(run['private_sources']['CUDA']['path']).read_text(encoding='utf-8-sig')
        header = re.search(r'h<<"(phase,completed_step,[^"]+)"', text)
        need(header is not None, 'Frozen 60-column source header missing')
        expected_header = header.group(1).removesuffix(r'\n').split(',')
        need(len(expected_header) == 60 and 'fsoil::EvaluateMaterial(' in text
             and 'std::swap(p.memory.e,p.graph.next_e)' in text
             and 'o.ledger=(newE-oldE+nodeWork+loss+deadE).v' in text
             and 'o.adjoint_defect=(nodeWork-rowWork).v' in text,
             'Frozen source arithmetic/lifecycle anchor differs')
        policy_path, sidecar_path = OUT / 'C08CachedPlasticHGPolicy.json', OUT / 'C08CachedPlasticHG.csv'
        # The owner sealed runtime completion, not these sidecars. These two current
        # stats are explicitly FIRST observed for this offline review, not historical seals.
        result['sidecar_first_review_observation'] = [observe(policy_path), observe(sidecar_path)]
        policy = read(policy_path)
        expected_policy = dict(schema=2, policy='PrivateC08SingleProducerCachedPlasticHG', phase='ReleaseOnly',
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
        need(policy == expected_policy, 'Actual schema2 cached policy differs')
        with sidecar_path.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            need(reader.fieldnames == expected_header, 'Actual/source 60-column header differs')
            raw = list(reader)
        need(len(raw) == 182 and all(None not in r and all(v != '' for v in r.values()) for r in raw),
             'Expected exactly 182 complete phase rows')
        with Path(run['planned_steps']['path']).open(newline='', encoding='utf-8-sig') as f:
            plan = list(csv.DictReader(f))
        need(len(plan) == 91 and [int(p['part']) for p in plan] == list(range(91)), 'Original91 plan differs')
        wanted = {int(p['completed_step']) for p in plan}
        scalar, clock = float(run['actual_source_time_s']), {}
        for step in range(FIRST + 1, LAST + 1):
            previous = scalar
            scalar += DT
            if step in wanted:
                clock[step] = (previous, scalar)
        need(bits(scalar) == bits(run['planned_actual_end_s']), 'Actual scalar source clock chain differs')
        integer_columns = set('completed_step pre_calls cor_calls commits error invalid_id invalid_slot np rows max_degree known_constant_rows elastic smooth apex tension material_checked material_produced cache_consumed cache_input_scalar_checks cache_output_scalar_checks kept born dead accepted_born accepted_dead'.split())
        rows, maximum_arithmetic_defect = [], 0.
        previous_cor = None
        for part, p in enumerate(plan):
            pair = []
            step = int(p['completed_step'])
            for k, phase in enumerate(('Pre', 'Cor')):
                original = raw[2 * part + k]
                need(original['phase'] == phase, 'Phase row order differs at part ' + str(part))
                r = {name: (phase if name == 'phase' else float(value)) for name, value in original.items()}
                need(all(math.isfinite(v) for name, v in r.items() if name != 'phase'), 'Nonfinite sidecar scalar')
                for name in integer_columns:
                    r[name] = int(original[name])
                need(r['completed_step'] == step and bits(r['saved_time_s']) == bits(p['time_s'])
                     and bits(r['source_time_s']) == bits(clock[step][0])
                     and bits(r['saved_time_s']) == bits(clock[step][1]) and bits(r['dt_s']) == bits(DT),
                     'Original scalar clock/plan mismatch at part ' + str(part))
                need(r['pre_calls'] == r['cor_calls'] == r['commits'] == step - FIRST
                     and r['error'] == 0 and r['invalid_id'] == r['invalid_slot'] == 0xffffffff
                     and r['np'] == 6805 and r['elastic'] + r['smooth'] + r['apex'] + r['tension'] == N
                     and r['material_checked'] == r['material_produced'] == r['cache_consumed'] == N
                     and r['cache_input_scalar_checks'] == 13 * N and r['cache_output_scalar_checks'] == 7 * N,
                     'Saved coverage/cache/status counters differ at part ' + str(part))
                need(0 < r['rows'] <= N * 128 and r['rows'] % 2 == 0 and 2 <= r['max_degree'] <= 128
                     and 0 <= r['known_constant_rows'] <= r['rows'] and r['kept'] + r['born'] == r['rows']
                     and 0 <= r['gamma_min'] <= r['gamma_max'] <= 1 and 0 < r['condition'] < 1e8
                     and r['lambda_s2'] > 0 and 0 < r['dt_over_0p2_limit'] <= 1
                     and r['min_r'] > 0 and 0 <= r['max_half_angle'] < .005
                     and all(r[x] >= 0 for x in ('Eold', 'Ekept', 'Edead', 'Enew', 'material_root_ratio',
                                                'accepted_discarded_energy', 'objective_accumulated_angle')),
                     'Original domain/graph/positive/rank/dt/rotation gate differs')
                # Python fsum is an independent arithmetic reconciliation, not the
                # source reduction sequence. Gamma8 bounds only this scalar re-evaluation.
                ledger = math.fsum([r['Enew'], -r['Eold'], r['node_work'], r['loading_loss'], r['Edead']])
                adjoint = r['node_work'] - r['row_work']
                scale = sum(abs(r[x]) for x in ('Enew', 'Eold', 'node_work', 'loading_loss', 'Edead'))
                arithmetic_bound = (8 * (sys.float_info.epsilon / 2) / (1 - 8 * (sys.float_info.epsilon / 2))) * scale + 16 * math.ulp(0.)
                defect = abs(ledger - r['ledger'])
                need(defect <= arithmetic_bound and bits(adjoint) == bits(r['adjoint_defect']),
                     'Source scalar ledger/adjoint arithmetic reconciliation failed')
                maximum_arithmetic_defect = max(maximum_arithmetic_defect, defect)
                r.update(part=part, tau_s=r['saved_time_s'] - float(run['actual_source_time_s']),
                         ledger_recomputed=ledger, ledger_recompute_bound=arithmetic_bound,
                         ledger_minus_rotation=r['ledger'] - r['rotation_change'],
                         old_minus_kept_dead=math.fsum([r['Eold'], -r['Ekept'], -r['Edead']]),
                         ledger_over_recorded_budget=ratio(r['ledger'], r['ledger_budget']),
                         adjoint_over_recorded_budget=ratio(r['adjoint_defect'], r['adjoint_budget']),
                         net_over_recorded_budget=ratio(max(abs(r['net_x']), abs(r['net_z'])), r['net_budget']),
                         torque_over_recorded_budget=ratio(r['torque'], r['torque_budget']),
                         commit_summary_max_over_max=ratio(r['max_commit_error'], r['commit_budget']))
                rows.append(r)
                pair.append(r)
            pre, cor = pair
            need(bits(pre['Eold']) == bits(cor['Eold']), 'Pre/Cor do not start from identical committed energy')
            for name in ('accepted_born', 'accepted_dead', 'accepted_discarded_energy', 'objective_accumulated_angle'):
                need(bits(pre[name]) == bits(cor[name]), 'Accepted save counters differ across the phase pair')
            need(cor['accepted_born'] - cor['accepted_dead'] == cor['rows'], 'Cold active directed-row integer ledger differs')
            if previous_cor is None:
                need(all(r[name] == 0 for r in pair for name in ('Eold', 'Ekept', 'Edead', 'kept'))
                     and cor['accepted_dead'] == 0 and cor['accepted_born'] == cor['rows']
                     and cor['accepted_discarded_energy'] == 0, 'Cold first accepted memory differs')
            else:
                need(all(cor[name] >= previous_cor[name] for name in
                         ('accepted_born', 'accepted_dead', 'accepted_discarded_energy', 'objective_accumulated_angle')),
                     'Accepted cumulative lifecycle observation decreased')
            previous_cor = cor
        metrics = ('rows', 'max_degree', 'condition', 'lambda_s2', 'dt_over_0p2_limit', 'min_r', 'max_half_angle',
                   'elastic', 'smooth', 'apex', 'tension', 'gamma_min', 'gamma_max', 'material_root_ratio',
                   'Eold', 'Enew', 'Edead', 'loading_loss', 'row_work', 'node_work', 'rotation_change',
                   'ledger', 'ledger_minus_rotation', 'old_minus_kept_dead', 'ledger_over_recorded_budget',
                   'adjoint_over_recorded_budget', 'net_over_recorded_budget', 'torque_over_recorded_budget',
                   'commit_summary_max_over_max', 'max_force', 'max_delta_ace', 'objective_accumulated_angle')
        extrema = []
        for phase in ('Pre', 'Cor'):
            group = [r for r in rows if r['phase'] == phase]
            for metric in metrics:
                finite = [r for r in group if r[metric] is not None]
                if not finite:
                    extrema.append(dict(phase=phase, metric=metric, min=None, min_part=None, min_time_s=None,
                        max=None, max_part=None, max_time_s=None, absmax=None, absmax_part=None,
                        absmax_time_s=None, undefined_count=91))
                    continue
                low, high = min(finite, key=lambda r: r[metric]), max(finite, key=lambda r: r[metric])
                worst = max(finite, key=lambda r: abs(r[metric]))
                extrema.append(dict(phase=phase, metric=metric, min=low[metric], min_part=low['part'],
                    min_time_s=low['saved_time_s'], max=high[metric], max_part=high['part'], max_time_s=high['saved_time_s'],
                    absmax=abs(worst[metric]), absmax_part=worst['part'], absmax_time_s=worst['saved_time_s'],
                    undefined_count=91 - len(finite)))
        diagnostic_ratios = ('ledger_over_recorded_budget', 'adjoint_over_recorded_budget',
                             'net_over_recorded_budget', 'torque_over_recorded_budget')
        flags = {key: sum(r[key] is not None and r[key] > 1 for r in rows) for key in diagnostic_ratios}
        flags['material_root_ratio_over_one'] = sum(r['material_root_ratio'] > 1 for r in rows)
        negative_losses = sum(r['loading_loss'] < 0 for r in rows)
        for entry in consumed:
            need(stat(entry['path']) == entry, 'Consumed input changed during review: ' + entry['path'])
        with SUMMARY.open('x', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(extrema[0]))
            writer.writeheader()
            writer.writerows(extrema)
        result.update(passed=True, analysis_complete=True, source_build=run['source_build'],
            source_policy=stat(policy_path), source_sidecar=stat(sidecar_path), source_columns=60,
            reviewed_rows=182, saved_phase_pairs=91, Eold_bit_equal_pairs=91,
            final_pre_calls=rows[-1]['pre_calls'], final_cor_calls=rows[-1]['cor_calls'], final_commits=rows[-1]['commits'],
            saved_material_produced=sum(r['material_produced'] for r in rows),
            saved_cache_input_scalar_checks=sum(r['cache_input_scalar_checks'] for r in rows),
            saved_cache_output_scalar_checks=sum(r['cache_output_scalar_checks'] for r in rows),
            maximum_ledger_scalar_recompute_defect=maximum_arithmetic_defect,
            diagnostic_ratio_over_one_counts=flags, negative_saved_loading_loss_count=negative_losses,
            undefined_ratio_counts={key: sum(r[key] is None for r in rows)
                                    for key in (*diagnostic_ratios, 'commit_summary_max_over_max')},
            saved_positive_node_work_count=sum(r['node_work'] > 0 for r in rows),
            final_accepted_state={k: rows[-1][k] for k in ('completed_step', 'saved_time_s', 'source_time_s', 'rows',
                'Eold', 'Enew', 'accepted_born', 'accepted_dead', 'accepted_discarded_energy', 'objective_accumulated_angle')},
            extrema=extrema, summary_csv=stat(SUMMARY), consumed_stats_unchanged=True,
            all_updates_internal_counters_and_guards='source/control-flow plus successful terminal receipt; sparse CSV is not per-update export',
            material_validation='single cached Result input identity and exact writeback; not an independent old producer comparison',
            commit_ratio_scope='max(error)/max(budget) is descriptive; per-node commit guard was internal',
            energy_scope='Pre and Cor are trials from identical committed e; never sum them as consecutive accepted work',
            rotation_scope='ledger includes rotation energy change; ledger_minus_rotation is separately reported',
            diagnostic_budget_scope='recorded estimates, not outward certificates or coupled physical energy bounds')
    except Exception as error:
        result['first_failure'] = str(error)
    result['consumed'] = consumed
    with CHECK.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: result.get(k) for k in ('stage', 'passed', 'reviewed_rows', 'final_commits', 'first_failure')}, ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
