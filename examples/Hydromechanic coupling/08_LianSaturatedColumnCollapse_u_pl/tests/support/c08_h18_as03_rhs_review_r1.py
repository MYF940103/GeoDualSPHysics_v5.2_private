"""Offline two-state AS03 RHS partition/normal review; no native or physical call."""
import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

import c08_h18_work_conjugacy_review_r1 as common

T = Path(__file__).resolve().parents[1]
TAG, COMPONENT = 'c08_h18_as03_rhs_review_r1', 'c08_h18_as03_rhs_r1'
O = T / 'outputs' / COMPONENT
PARTS, STEPS = (38, 76), (2076001, 2152001)
IDS, WALLS = set(range(2060, 7060)), set(range(1805))
TERMS = ('compression', 'LP', 'Taylor_pressure', 'Da', 'FS_Ace_Lx',
         'chain_pressure', 'chain_Ace')
GROUPS = ('all', 'fluid_donors', 'fixed_donors')
COHORTS = ('FS', 'wall_adjacent', 'interior')
need, stat, read, bind = common.need, common.stat, common.read, common.bind
table, number, integer = common.table, common.number, common.integer


def ordered_sum(rows, key):
    value = 0.0
    for row in rows:
        value += number(row, key)
    return value


def rms(values):
    return math.sqrt(math.fsum(float(v) * float(v) for v in values) / len(values)) if len(values) else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    need(parser.parse_args().execution_authorized, 'Independent root offline admission required')
    check, prefix = T / 'logs' / (TAG + '.check.json'), T / 'figures' / TAG
    need(not check.exists() and not list(prefix.parent.glob(TAG + '_*')),
         'Existing complete or partial analysis is protected')
    consumed = [stat(Path(__file__)), stat(T / 'notes' / (TAG + '.md')),
                stat(Path(common.__file__))]
    outputs = []
    try:
        receipt_path = T / 'logs' / (COMPONENT + '.check.json')
        receipt = read(receipt_path); consumed.append(stat(receipt_path))
        need(receipt['passed'] and receipt['component_invocations'] == 1 and
             receipt['physical_steps'] == receipt['solver_invocations'] ==
             receipt['native_invocations'] == 0 and receipt['consumed_stats_unchanged'] and
             not receipt['physical_acceptance'], 'One sealed zero-step component required')
        call_path, build_path, done_path = [bind(receipt[k]) for k in
                                            ('actual_call', 'build', 'completion')]
        need(build_path.resolve() == (T / 'logs' / (COMPONENT + '.build.json')).resolve()
             and done_path.resolve() == (O / 'completion.json').resolve(),
             'Only the admitted AS03 two-state component is allowed')
        consumed += [stat(p) for p in (call_path, build_path, done_path)]
        call, build, done = map(read, (call_path, build_path, done_path))
        need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and
             call['ownership_failure'] is None and call['child']['parent_pid'] == call['owner']['pid']
             and Path(call['child']['exe']).resolve() == Path(call['program']).resolve() ==
             Path(build['program']['path']).resolve() and
             call['child']['argv'] == [call['program'], *call['arguments']],
             'Actual owned component identity or exits differ')
        need(build['passed'] and build['configuration'] == 'DebugCPU' and
             build['consumed_stats_unchanged'] and build['actual_link_objects'] == 87 and
             build['physical_objects_compiled'] == 0 and build['original_Single_no_hook'],
             'Frozen original CPU objects and unchanged Single required')
        consumed.append(stat(bind(build['program'])))
        need(done['stage'] == COMPONENT and done['passed'] and done['source_parts'] == list(PARTS)
             and done['source_samples'] == 301 and
             done['actual_force_calls'] == done['actual_Darcy_calls'] == 2 and
             done['soil_rows'] == done['literal_final_float_bits_matched'] == 10000 and
             done['term_rows'] == 30000 and done['summary_rows'] == 18 and
             done['wall_rows'] == 3610 and done['all5000_primary_bits_unchanged_per_call'] and
             done['physical_steps'] == done['material_return_calls'] == done['filter_calls'] ==
             done['extra_Darcy_calls'] == 0 and done['fresh_actual_CPU_corrector_mode_on_completed_states']
             and not done['saved_GPU_force_stage_reconstructed'] and
             done['wall_partition_is_additive_not_counterfactual'] and
             done['coefficient_change_included'] and done['original_Single_no_hook'] and
             not done['physical_acceptance'], 'Original two-state completion differs')
        for key in ('max_final_float_budget_ratio', 'max_expanded_budget_ratio'):
            need(0 <= float(done[key]) <= 1, 'Original component arithmetic ratio failed')
        entries = {Path(q['path']).name: q for q in receipt['files']}
        data = {}
        for name in ('soil_rhs.csv', 'terms.csv', 'summary.csv', 'walls.csv'):
            path = O / name
            need(path.resolve() == bind(entries[name]).resolve(), 'Bound CSV path differs')
            consumed.append(stat(path)); data[name] = table(path)
        soil, terms, summary, walls = [data[k] for k in
                                      ('soil_rhs.csv', 'terms.csv', 'summary.csv', 'walls.csv')]
        need(tuple(map(len, (soil, terms, summary, walls))) == (10000, 30000, 18, 3610),
             'Actual complete two-state CSV coverage differs')
        common.finite_rows(soil, ('receiver_cohort',))
        common.finite_rows(terms, ('donor_group',))
        common.finite_rows(summary, ('donor_group', 'receiver_group'))

        full_review_path = T / 'logs/c08_h18_as03n255_full3_review_r1.check.json'
        full_review = read(full_review_path); consumed.append(stat(full_review_path))
        need(full_review['analysis_complete'] and full_review['consumed_stats_unchanged'] and
             full_review['actual_samples'] == 301, 'Original full301 analysis required')
        clock_path = T / 'outputs/c08_h18_as03n255_full3_r1/native_r1/clocks.csv'
        clock_entry = next(q for q in full_review['consumed'] if
                           Path(q['path']).resolve() == clock_path.resolve())
        consumed.append(stat(bind(clock_entry))); clocks = table(clock_path)
        need(len(clocks) == 301 and [integer(r, 'part') for r in clocks] == list(range(301)),
             'Original actual-clock coverage differs')
        expected = dict(zip(PARTS, STEPS))

        def clock(row, tau=True):
            part = integer(row, 'part')
            need(part in expected and integer(row, 'completed_step') == expected[part] ==
                 integer(clocks[part], 'completed_step') and
                 number(row, 'time_s') == number(clocks[part], 'time_s'),
                 'Actual source step or scalar saved clock differs')
            if tau:
                need(number(row, 'tau_s') == number(clocks[part], 'tau_from_actual_release_s'),
                     'Actual release-relative clock differs')
            return part

        by_soil, by_terms = {}, {}
        for row in soil:
            part = clock(row); key = part, integer(row, 'native_id')
            need(key[1] in IDS and key not in by_soil, 'Foreign or duplicate original material ID')
            by_soil[key] = row
            need(row['receiver_cohort'] in COHORTS and
                 integer(row, 'fresh_is_FS') in (0, 1) and integer(row, 'normal_valid') in (0, 1)
                 and integer(row, 'baseline_same_time_step') == 1 and
                 integer(row, 'baseline_FS_equal') in (0, 1), 'Original role/identity flags differ')
            need(bool(integer(row, 'normal_valid')) == (number(row, 'normal_norm') > 0),
                 'The original zero-normal flag differs')
            for err, budget in (('final_float_error_Pa_s', 'final_float_budget_Pa_s'),
                                ('expanded_error_Pa_s', 'expanded_budget_Pa_s')):
                common.original_budget(row, err, budget)
            actual, literal = number(row, 'actual_rate_Pa_s'), number(row, 'literal_reference_Pa_s')
            need(struct.pack('<f', actual) == struct.pack('<f', literal),
                 'Original literal/final float bit gate failed')
            need(abs(actual - literal) <= number(row, 'final_float_budget_Pa_s') and
                 abs(actual - number(row, 'expanded_rate_Pa_s')) <= number(row, 'expanded_budget_Pa_s'),
                 'Independent original arithmetic reconciliation failed')
        need(set(by_soil) == {(p, i) for p in PARTS for i in IDS}, 'All original5000 IDs required')
        for row in terms:
            part = clock(row); key = part, integer(row, 'native_id'), row['donor_group']
            need(key[1] in IDS and key[2] in GROUPS and key not in by_terms and
                 integer(row, 'neighbors') >= 0, 'Duplicate or foreign donor partition')
            by_terms[key] = row
            need(integer(row, 'fresh_FS') == integer(by_soil[key[:2]], 'fresh_FS'),
                 'Fresh per-material FS identity differs')
        need(set(by_terms) == {(p, i, g) for p in PARTS for i in IDS for g in GROUPS},
             'All three original donor partitions required')
        partition_residual = {}
        for (part, identity), row in by_soil.items():
            a, b, c = [by_terms[(part, identity, group)] for group in GROUPS]
            role = 'FS' if integer(row, 'fresh_is_FS') else (
                'wall_adjacent' if integer(c, 'neighbors') else 'interior')
            need(row['receiver_cohort'] == role, 'Original mutually exclusive cohort rule differs')
            need(integer(a, 'neighbors') == integer(b, 'neighbors') + integer(c, 'neighbors'),
                 'Original additive donor count differs')
            expanded, partition = 0.0, 0.0
            for term in TERMS:
                expanded += number(a, term + '_Pa_s')
                partition += number(b, term + '_Pa_s') + number(c, term + '_Pa_s')
            partition += number(a, 'compression_Pa_s')
            need(number(b, 'compression_Pa_s') == number(c, 'compression_Pa_s') == 0,
                 'Compression may only be counted in the all partition')
            # The component enforces its original dbudget before writing. It is
            # not exported separately: subtracting two rounded budget columns
            # cannot recover it. Retain this reconstruction descriptively.
            partition_residual[(part, identity)] = partition - expanded

        wall_keys = set()
        optional = tuple('derivative_v' + a for a in 'xyz') + tuple(
            'C' + a + b for a in 'xyz' for b in 'xyz')
        for row in walls:
            part = clock(row, tau=False); key = part, integer(row, 'native_id')
            need(key[1] in WALLS and key not in wall_keys, 'Duplicate or foreign retained wall ID')
            wall_keys.add(key)
            need(integer(row, 'active') in (0, 1), 'Invalid active-wall flag')
            for field, value in row.items():
                if value == '':
                    need(field in optional and integer(row, 'active') == 0,
                         'Only inactive wall derivative/C scratch may be absent')
                else:
                    number(row, field)
        need(wall_keys == {(p, i) for p in PARTS for i in WALLS}, 'All1805 wall rows/state required')
        summary_keys = set()
        for row in summary:
            part = clock(row); key = part, row['donor_group'], row['receiver_group']
            need(key[1] in GROUPS and key[2] in ('all', 'interior', 'FS') and
                 key not in summary_keys, 'Duplicate or foreign original summary group')
            summary_keys.add(key)
            selected = [q for (p, _), q in by_soil.items() if p == part and
                        (key[2] == 'all' or bool(integer(q, 'fresh_is_FS')) == (key[2] == 'FS'))]
            need(len(selected) == integer(row, 'receivers'), 'Original receiver summary count differs')
            common.original_budget(row, 'sum_weighted_abs_rate_error_m2_s',
                                   'sum_weighted_rate_budget_m2_s')
            common.original_budget(row, 'global_reconciliation_error_all_only_m2_s',
                                   'global_reconciliation_budget_all_only_m2_s')
            if key[1] == 'all':
                need(abs(number(row, 'actual_Q_all_only_m2_s') - number(row, 'expanded_Q_m2_s')) <=
                     number(row, 'global_reconciliation_budget_all_only_m2_s'),
                     'Original global signed-source arithmetic budget failed')
        need(summary_keys == {(p, g, r) for p in PARTS for g in GROUPS
                              for r in ('all', 'interior', 'FS')}, 'All18 original summaries required')

        materials, cohorts, normal_stats, focus = [], [], [], []
        fixed_focus = {6767, 6865, 4953, 4954, 7010}
        records = {}
        for part in PARTS:
            state = [by_soil[(part, identity)] for identity in sorted(IDS)]
            total_weight = ordered_sum(state, 'storage_weight')
            need(total_weight > 0, 'Positive actual full-state storage weight required')
            records[part] = state
            for cohort in COHORTS:
                selected = [q for q in state if q['receiver_cohort'] == cohort]
                local_weight = ordered_sum(selected, 'storage_weight')
                valid = [q for q in selected if integer(q, 'normal_valid')]
                invalid = [q for q in selected if not integer(q, 'normal_valid')]
                ns = dict(part=part, time_s=number(state[0], 'time_s'), tau_s=number(state[0], 'tau_s'),
                    completed_step=expected[part], receiver_cohort=cohort, receivers=len(selected),
                    normal_valid=len(valid), normal_invalid=len(invalid),
                    invalid_normal_not_counted_as_zero_flux=True,
                    p_mean_Pa=ordered_sum(selected, 'p_Pa') / len(selected) if selected else 0,
                    actual_rate_RMS_Pa_s=rms([number(q, 'actual_rate_Pa_s') for q in selected]),
                    H_dot_n_valid_RMS_Pa_per_m=rms([number(q, 'H_dot_n_Pa_m') for q in valid]),
                    H_dot_n_valid_absmax_Pa_per_m=max((abs(number(q, 'H_dot_n_Pa_m')) for q in valid), default=0),
                    q_n_local_shadow_valid_RMS_m_s=rms([number(q, 'q_n_local_shadow_m_s') for q in valid]),
                    baseline_FS_differences=sum(1 - integer(q, 'baseline_FS_equal') for q in selected),
                    baseline_rate_difference_RMS_Pa_s=rms([number(q, 'baseline_rate_difference_Pa_s') for q in selected]),
                    baseline_theta_difference_RMS_s_1=rms([number(q, 'baseline_theta_difference_s_1') for q in selected]),
                    baseline_Ace_difference_RMS_components_m_s2=rms([
                        number(q, 'baseline_Ace_d' + axis) for q in selected for axis in 'xyz']))
                normal_stats.append(ns)
                for group in GROUPS:
                    out = dict(part=part, time_s=ns['time_s'], tau_s=ns['tau_s'],
                        completed_step=expected[part], receiver_cohort=cohort, donor_group=group,
                        receivers=len(selected), cohort_storage_weight=local_weight,
                        full_state_storage_weight=total_weight, has_positive_cohort_weight=local_weight > 0,
                        cohort_actual_Q_m2_s=math.fsum(number(q, 'storage_weight') *
                            number(q, 'actual_rate_Pa_s') for q in selected),
                        coefficient_Q_m2_s=ordered_sum(selected, 'coefficient_Q_m2_s'),
                        storage_proxy_m2=math.fsum(number(q, 'storage_weight') * number(q, 'p_Pa') for q in selected))
                    for term in TERMS:
                        values = [number(by_terms[(part, integer(q, 'native_id'), group)],
                                         term + '_Q_m2_s') for q in selected]
                        out[term + '_Q_m2_s'] = math.fsum(values)
                        out[term + '_absQ_m2_s'] = math.fsum(abs(v) for v in values)
                        out[term + '_global_weighted_kPa_s'] = out[term + '_Q_m2_s'] / total_weight / 1000
                    cohorts.append(out)
            for row in state:
                identity = integer(row, 'native_id'); out = dict(row)
                out['donor_partition_minus_expanded_Pa_s_descriptive'] = partition_residual[(part, identity)]
                for group in GROUPS:
                    termrow = by_terms[(part, identity, group)]
                    out[group + '_neighbors'] = integer(termrow, 'neighbors')
                    for term in TERMS:
                        out[group + '_' + term + '_Pa_s'] = number(termrow, term + '_Pa_s')
                        out[group + '_' + term + '_Q_m2_s'] = number(termrow, term + '_Q_m2_s')
                out['p_minus_P0_Pa_diagnostic_only'] = number(row, 'p_Pa') - number(row, 'P0_Pa')
                out['H_norm_Pa_per_m'] = math.sqrt(sum(number(row, 'H' + a + '_Pa_m') ** 2 for a in 'xyz'))
                materials.append(out)
            reasons = {identity: ['fixed material focus'] for identity in fixed_focus}
            for label, field, chooser in (('maximum actual RHS', 'actual_rate_Pa_s', max),
                                           ('minimum actual RHS', 'actual_rate_Pa_s', min)):
                q = chooser(state, key=lambda q: number(q, field))
                reasons.setdefault(integer(q, 'native_id'), []).append(label)
            fs_valid = [q for q in state if integer(q, 'fresh_is_FS') and integer(q, 'normal_valid')]
            if fs_valid:
                q = max(fs_valid, key=lambda q: abs(number(q, 'H_dot_n_Pa_m')))
                reasons.setdefault(integer(q, 'native_id'), []).append('maximum absolute valid-FS Hdotn')
            for identity, why in sorted(reasons.items()):
                original = next(q for q in materials if integer(q, 'part') == part and
                                integer(q, 'native_id') == identity)
                focus.append(dict(original, selection_reason='; '.join(why)))
        for suffix, rows in (('cohorts', cohorts), ('normal_stats', normal_stats),
                             ('materials', materials), ('focus', focus)):
            path = Path(str(prefix) + '_' + suffix + '.csv')
            common.write_csv(path, rows); outputs.append(path)

        fig, axes = plt.subplots(3, 2, figsize=(16, 13), layout='constrained')
        short_names = ('Compression', 'Laplacian', 'Taylor p', 'div a', 'FS a.L', 'chain p', 'chain a')
        for col, part in enumerate(PARTS):
            for row_index, cohort in enumerate(COHORTS):
                ax = axes[row_index, col]
                for k, group in enumerate(GROUPS):
                    q = next(q for q in cohorts if q['part'] == part and
                             q['receiver_cohort'] == cohort and q['donor_group'] == group)
                    ax.bar(np.arange(7) + (k - 1) * .25,
                           [q[t + '_global_weighted_kPa_s'] for t in TERMS], .25, label=group)
                ax.set_xticks(np.arange(7), short_names, rotation=35, ha='right')
                ax.set_yscale('symlog', linthresh=1e-4); ax.axhline(0, color='black', lw=.6)
                ax.set_ylabel('Signed contribution / full-state storage weight [kPa/s]')
                ax.set_title(f"Actual tau={q['tau_s']:.6f}s; {cohort}; N={q['receivers']}")
                ax.grid(axis='y', alpha=.2)
        axes[0, 0].legend(fontsize=8)
        fig.suptitle('Original CPU RHS on two frozen AS0.3 states: signed storage-weighted partitions\n'
                     'All overlaps fluid/fixed donors; compression occurs only in All. Not fluid mass or integrated error.')
        path = Path(str(prefix) + '_terms.png'); fig.savefig(path, dpi=170); plt.close(fig); outputs.append(path)

        fig, axes = plt.subplots(2, 4, figsize=(22, 10), layout='constrained')
        specs = (('p_Pa', 1000, 'Pore pressure p [kPa]'),
                 ('actual_rate_Pa_s', 1000, 'Fresh CPU RHS [kPa/s]'),
                 ('fresh_theta_s_1', 1, 'Fresh CPU theta [1/s]'),
                 ('H_dot_n_Pa_m', 1000, 'Valid FS H dot n [kPa/m]'))
        for col, (field, divisor, label) in enumerate(specs):
            samples = [[q for q in records[part] if col != 3 or
                        (integer(q, 'fresh_is_FS') and integer(q, 'normal_valid'))] for part in PARTS]
            extreme = max((abs(number(q, field) / divisor) for rs in samples for q in rs), default=0)
            norm = SymLogNorm(linthresh=max(extreme / 1000, 1e-12),
                              vmin=-extreme if extreme else -1, vmax=extreme if extreme else 1)
            for row_index, (part, selected) in enumerate(zip(PARTS, samples)):
                ax = axes[row_index, col]; state = records[part]
                if col == 3:
                    ax.scatter([number(q, 'x_m') for q in state], [number(q, 'z_m') for q in state],
                               s=2, c='0.9', rasterized=True)
                sc = ax.scatter([number(q, 'x_m') for q in selected], [number(q, 'z_m') for q in selected],
                                c=[number(q, field) / divisor for q in selected], s=4,
                                cmap='coolwarm', norm=norm, rasterized=True)
                if col == 3:
                    invalid = [q for q in state if integer(q, 'fresh_is_FS') and not integer(q, 'normal_valid')]
                    ax.scatter([number(q, 'x_m') for q in invalid], [number(q, 'z_m') for q in invalid],
                               c='black', marker='x', s=14, label=f'FS null normal: {len(invalid)}')
                for ia, ib, color in ((6767, 6865, 'black'), (4953, 4954, 'lime')):
                    pair = [by_soil[(part, identity)] for identity in (ia, ib)]
                    ax.plot([number(q, 'x_m') for q in pair], [number(q, 'z_m') for q in pair],
                            'o-', color=color, ms=4, lw=.8, label=f'{ia}/{ib}')
                ax.set_aspect('equal'); ax.set_xlabel('x [m]'); ax.set_ylabel('z [m]')
                ax.set_title(f"tau={number(state[0], 'tau_s'):.6f}s; {label}", fontsize=10)
                if col in (0, 3): ax.legend(fontsize=7)
                ax.grid(alpha=.2)
            fig.colorbar(sc, ax=axes[:, col], label=label, shrink=.75)
        fig.suptitle('Complete material fields and separately flagged free-surface normals\n'
                     'Shared full signed column ranges; invalid zero normals are not zero-flux evidence. No smoothing/clipping.')
        path = Path(str(prefix) + '_fields.png'); fig.savefig(path, dpi=170); plt.close(fig); outputs.append(path)

        need(all(stat(q['path']) == q for q in consumed), 'Consumed input changed during analysis')
        result = dict(stage=TAG, analysis_complete=True, consumed=consumed,
            consumed_stats_unchanged=True, source_parts=list(PARTS),
            row_counts=dict(soil=10000, terms=30000, summary=18, walls=3610),
            original_literal_and_expanded_arithmetic_gates_passed=True,
            original_donor_budget_enforced_by_component_not_recovered_from_rounded_sum=True,
            original_source_calls=2, component_invocations=0, physical_steps=0,
            solver_invocations=0, decoder_invocations=0, SHA_scans=0,
            cohort_rows=cohorts, normal_statistics=normal_stats,
            focus_material_ids={str(p): sorted(integer(q, 'native_id') for q in focus if integer(q, 'part') == p)
                                for p in PARTS},
            storage_proxy_is_not_fluid_mass=True, actual_GPU_substage_reconstructed=False,
            zero_normal_is_not_zero_flux_acceptance=True, baseline_differences_descriptive=True,
            original_summary_interior_means_all_non_FS=True,
            p_minus_P0_is_diagnostic_not_paper_plastic_excess=True,
            shear_storage_order='Sigma_ij=(xy,yz,xz)', physical_acceptance=False,
            root_cause_established=False, other_psi_unlocked=False, visual_QA_pending=True,
            files=[stat(p) for p in outputs])
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    except Exception as error:
        if not check.exists():
            with check.open('x', encoding='utf-8') as f:
                json.dump(dict(stage=TAG, analysis_complete=False, first_failure=str(error),
                    consumed=consumed, partial_outputs_preserved=True, physical_steps=0,
                    component_invocations=0, solver_invocations=0, decoder_invocations=0,
                    physical_acceptance=False, SHA_scans=0), f, indent=2, allow_nan=False)
                f.write('\n')
        raise


if __name__ == '__main__':
    main()
