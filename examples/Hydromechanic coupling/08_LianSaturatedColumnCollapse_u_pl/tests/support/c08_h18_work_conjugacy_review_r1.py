"""Offline review of one sealed four-state, zero-advance CPU work component.

No decoder, force call, build, physical update, SHA scan or automatic next stage.
The component's supplied arithmetic budgets are implementation checks, not new
physical tolerances.  G1 gaps and virtual responses remain descriptive.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_work_conjugacy_review_r1'
COMPONENT = 'c08_h18_work_conjugacy_r2'
O = T / 'outputs' / COMPONENT
PARTS = (38, 76, 92, 300)
SOIL = set(range(2060, 7060))
WALL = set(range(1805))
PROBES = ('pair6767_6865', 'pair4953_4954', 'healthy_pair', 'translation_x')


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bind(entry):
    need(stat(entry['path']) == entry, 'Bound input stat differs: ' + entry['path'])
    return Path(entry['path'])


def table(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)),
             'Empty or duplicate CSV header: ' + str(path))
        rows = list(reader)
    need(all(None not in r and all(v is not None for v in r.values()) for r in rows),
         'CSV row width differs: ' + str(path))
    return rows


def number(row, key):
    value = float(row[key])
    need(math.isfinite(value), 'Nonfinite ' + key)
    return value


def integer(row, key):
    return int(row[key])


def finite_rows(rows, text_fields=()):
    for row in rows:
        for key in row:
            if key not in text_fields:
                number(row, key)


def write_csv(path, rows):
    need(rows, 'Cannot write empty review CSV')
    with path.open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def original_budget(row, error, budget, signed=False):
    value, limit = number(row, error), number(row, budget)
    need(limit >= 0 and (signed or value >= 0), 'Negative arithmetic error/budget')
    need(abs(value) <= limit, 'Original arithmetic budget failed: ' + error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Root full-read and independent offline admission required')
    check = T / 'logs' / (TAG + '.check.json')
    prefix = T / 'figures' / TAG
    need(not check.exists() and not list(prefix.parent.glob(TAG + '_*')),
         'Existing complete or partial review is protected; no overwrite/retry')
    consumed, outputs = [], []
    try:
        receipt_path = T / 'logs' / (COMPONENT + '.check.json')
        receipt = read(receipt_path)
        consumed.append(stat(receipt_path))
        need(receipt['passed'] and receipt['component_invocations'] == 1 and
             receipt['physical_steps'] == receipt['solver_invocations'] ==
             receipt['native_invocations'] == 0 and not receipt['physical_acceptance'],
             'One independently sealed zero-advance component required')
        call_path, build_path, done_path = [bind(receipt[k]) for k in
                                            ('actual_call', 'build', 'completion')]
        need(build_path.resolve() == (T / 'logs' / (COMPONENT + '.build.json')).resolve()
             and done_path.resolve() == (O / 'completion.json').resolve(),
             'Only the successful r2 component paths are admitted')
        consumed += [stat(p) for p in (call_path, build_path, done_path)]
        call, build, done = map(read, (call_path, build_path, done_path))
        need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and
             call['ownership_failure'] is None and call['child']['parent_pid'] ==
             call['owner']['pid'] and Path(call['child']['exe']).resolve() ==
             Path(call['program']).resolve() == Path(build['program']['path']).resolve()
             and call['child']['argv'] == [call['program'], *call['arguments']],
             'Original owned component exit/program/argv differs')
        need(build['passed'] and build['configuration'] == 'DebugCPU' and
             build['consumed_stats_unchanged'] and build['actual_link_objects'] == 87
             and build['physical_objects_compiled'] == 0 and
             build['original_Single_no_hook'], 'Original frozen CPU-object build required')
        consumed.append(stat(bind(build['program'])))
        need(done['stage'] == COMPONENT and done['passed'] and
             done['source_parts'] == list(PARTS) and done['force_calls'] == 4 and
             done['soil_rows'] == 20000 and done['group_rows'] == 40000 and
             done['wall_rows'] == 7220 and done['summary_rows'] == 8 and
             done['virtual_rows'] == 16 and done['virtual_soil_only'] and
             not done['virtual_wall_closure'] and
             done['all5000_soil_primary_bits_unchanged'] and
             done['physical_steps'] == done['material_steps'] == done['new_OFF_windows'] == 0
             and done['fixed_wall_physical_power'] == 0 and
             done['mass_and_storage_are_not_fluid_mass'] and
             done['raw_adjoint_and_corrected_gap_are_conditional_operator_diagnostics'] and
             not done['total_energy_closure_asserted'] and not done['physical_acceptance'],
             'Original completion/coverage/no-advance declarations differ')
        files = {Path(q['path']).name: q for q in receipt['files']}
        names = ('soil.csv', 'groups.csv', 'walls.csv', 'summary.csv', 'virtual.csv')
        data = {}
        for name in names:
            path = O / name
            need(path.resolve() == bind(files[name]).resolve(), 'CSV binding path differs')
            consumed.append(stat(path))
            data[name] = table(path)
        soil, groups, walls, summary, virtual = [data[n] for n in names]
        need(tuple(map(len, (soil, groups, walls, summary, virtual))) ==
             (20000, 40000, 7220, 8, 16), 'Actual complete row coverage differs')
        finite_rows(soil)
        finite_rows(groups, ('donor_group',))
        finite_rows(walls)
        finite_rows(summary, ('group',))
        finite_rows(virtual, ('probe',))

        # Select authentic saved clocks, never n*dt or a fitted/aligned time.
        review_path = T / 'logs/c08_h18_as03n255_full3_review_r1.check.json'
        review = read(review_path)
        need(review['analysis_complete'] and review['consumed_stats_unchanged'] and
             review['actual_samples'] == 301, 'Sealed full301 source review required')
        clock_path = T / 'outputs/c08_h18_as03n255_full3_r1/native_r1/clocks.csv'
        clock_entry = next(q for q in review['consumed']
                           if Path(q['path']).resolve() == clock_path.resolve())
        consumed += [stat(review_path), stat(bind(clock_entry))]
        clocks = table(clock_path)
        need(len(clocks) == 301 and [integer(q, 'part') for q in clocks] == list(range(301)),
             'Actual original full301 clock table differs')
        selected = {part: clocks[part] for part in PARTS}
        expected_steps = dict(zip(PARTS, (2076001, 2152001, 2184001, 2600000)))
        for part, row in selected.items():
            need(integer(row, 'completed_step') == expected_steps[part], 'Saved step differs')

        def check_clock(row, tau=False, step=False):
            part = integer(row, 'part')
            need(part in selected, 'Undeclared source part')
            original = selected[part]
            need(number(row, 'time_s') == number(original, 'time_s'), 'Actual saved time differs')
            if tau:
                need(number(row, 'tau_s') == number(original, 'tau_from_actual_release_s'),
                     'Actual drainage/release-relative time differs')
            if step:
                need(integer(row, 'completed_step') == integer(original, 'completed_step'),
                     'Actual saved completed step differs')
            return part

        by_soil, by_group = {}, {}
        for row in soil:
            part = check_clock(row, tau=True, step=True)
            key = part, integer(row, 'id')
            need(key[1] in SOIL and key not in by_soil, 'Duplicate/foreign soil ID')
            by_soil[key] = row
            for error, budget in (('theta_error', 'theta_budget'),
                                  ('rate_error_max', 'rate_budget'),
                                  ('force_error_max', 'force_budget')):
                original_budget(row, error, budget)
            need(integer(row, 'force_bits_equal') in (0, 1) and
                 integer(row, 'rate_bits_equal') in (0, 1), 'Invalid observed bit flag')
        for part in PARTS:
            need({identity for p, identity in by_soil if p == part} == SOIL,
                 'All 5000 original material IDs are required')
        for row in groups:
            part = check_clock(row)
            key = part, integer(row, 'id'), row['donor_group']
            need(key[1] in SOIL and key[2] in ('soil', 'wall') and key not in by_group,
                 'Duplicate/foreign material donor partition')
            need(integer(row, 'donors') >= 0, 'Negative donor count')
            by_group[key] = row
        need(set(by_group) == {(p, i, g) for p in PARTS for i in SOIL
                              for g in ('soil', 'wall')}, 'Complete donor partitions required')
        wall_keys = set()
        for row in walls:
            part = check_clock(row)
            key = part, integer(row, 'id')
            need(key[1] in WALL and key not in wall_keys, 'Duplicate/foreign wall ID')
            wall_keys.add(key)
            need(all(number(row, 'motion_' + axis) == 0 for axis in 'xyz'),
                 'Original fixed physical wall motion differs')
        need(wall_keys == {(p, i) for p in PARTS for i in WALL}, 'All 1805 retained wall IDs required')

        summary_keys, summary_rows, diagnostics = set(), [], []
        for row in summary:
            part = check_clock(row, tau=True)
            key = part, row['group']
            need(key[1] in ('soil', 'wall') and key not in summary_keys,
                 'Duplicate/foreign summary partition')
            summary_keys.add(key)
            need(integer(row, 'receivers') == 5000 and integer(row, 'primary_unchanged') == 1,
                 'Original complete receiver/primary guard differs')
            members = [by_group[(part, i, key[1])] for i in sorted(SOIL)]
            need(sum(integer(q, 'donors') for q in members) == integer(row, 'directed_donors'),
                 'Actual donor partition count differs')
            original_budget(row, 'raw_closure_or_wall_port_residual', 'arithmetic_budget', True)
            derived = dict(row)
            derived['completed_step'] = expected_steps[part]
            derived['force_bit_equal_receivers'] = sum(integer(by_soil[(part, i)],
                                                             'force_bits_equal') for i in SOIL)
            derived['rate_bit_equal_receivers'] = sum(integer(by_soil[(part, i)],
                                                            'rate_bits_equal') for i in SOIL)
            summary_rows.append(derived)
            # Independent totals are observations, not a fresh tolerance on AS/AV
            # or a claim that NumPy/Python and the original accumulator are bit-equal.
            diag = dict(part=part, group=key[1])
            for src, dst in (('P_total_stress_double', 'P_stress'),
                             ('Iraw_derivative', 'Iraw'), ('IC_derivative', 'IC'),
                             ('G1_minus_raw', 'G1_gap'), ('P_AS_double', 'P_AS'),
                             ('P_AV_double', 'P_AV')):
                acc = 0.0
                for q in members:
                    acc += number(q, src)
                diag[dst + '_ordered_sum_minus_summary'] = acc - number(row, dst)
            port = 0.0
            for q in members:
                port += number(q, 'ghost_port_expected')
            derived['ordered_group_ghost_port'] = port
            derived['reconstructed_raw_residual_descriptive'] = (
                number(row, 'P_stress') + number(row, 'Iraw') - port)
            derived['literal_G1_minus_reported'] = (
                number(row, 'IC') - number(row, 'Iraw') - number(row, 'G1_gap'))
            diagnostics.append(diag)
        need(summary_keys == {(p, g) for p in PARTS for g in ('soil', 'wall')},
             'All raw soil/wall closures required')

        virtual_keys, virtual_rows = set(), []
        for row in virtual:
            part, probe = integer(row, 'part'), row['probe']
            key = part, probe
            need(part in PARTS and probe in PROBES and key not in virtual_keys,
                 'Duplicate/foreign virtual probe')
            virtual_keys.add(key)
            need(integer(row, 'soil_only') == 1 and integer(row, 'walls_closed') == 0,
                 'Virtual wall closure cannot be silently asserted')
            original_budget(row, 'raw_closure_residual', 'arithmetic_budget', True)
            need(integer(row, 'soil_directed_edges') == integer(next(q for q in summary
                 if integer(q, 'part') == part and q['group'] == 'soil'), 'directed_donors'),
                 'Virtual and actual frozen soil-stencil edge counts differ')
            for field in ('r_m', 'Vnorm_u', 'Vnorm_symLraw', 'Vnorm_symLC',
                          'Vnorm_traceLraw', 'Vnorm_traceLC',
                          'symLraw_over_u_s_1', 'symLC_over_u_s_1'):
                need(number(row, field) >= 0, 'Negative virtual norm or distance')
            if probe.startswith('pair'):
                expected = (6767, 6865) if probe == PROBES[0] else (4953, 4954)
                need((integer(row, 'id_i'), integer(row, 'id_j')) == expected,
                     'Suspect virtual material pair changed')
            elif probe == 'healthy_pair':
                need(integer(row, 'id_i') in SOIL and integer(row, 'id_j') in SOIL,
                     'Healthy reference must contain actual material IDs')
            else:
                need(integer(row, 'id_i') == integer(row, 'id_j') == 4294967295,
                     'Original translation ID sentinels differ')
            derived = dict(row)
            derived.update(time_s=number(selected[part], 'time_s'),
                           tau_s=number(selected[part], 'tau_from_actual_release_s'),
                           completed_step=expected_steps[part])
            virtual_rows.append(derived)
        need(virtual_keys == {(p, probe) for p in PARTS for probe in PROBES},
             'All sixteen predeclared virtual probes required')

        spatial = []
        for part in PARTS:
            for identity in sorted(SOIL):
                row = by_soil[(part, identity)]
                a, b = [by_group[(part, identity, g)] for g in ('soil', 'wall')]
                spatial.append(dict(part=part, time_s=number(row, 'time_s'),
                    tau_s=number(row, 'tau_s'), completed_step=expected_steps[part],
                    id=identity, x=number(row, 'x'), z=number(row, 'z'),
                    p_Pa=number(row, 'p'), P0_Pa=number(row, 'P0'),
                    J=number(row, 'J'), kappa=number(row, 'kappa'),
                    soil_G1_gap=number(a, 'G1_minus_raw'),
                    wall_G1_gap=number(b, 'G1_minus_raw'),
                    total_G1_gap=number(a, 'G1_minus_raw') + number(b, 'G1_minus_raw'),
                    wall_directed_donors=integer(b, 'donors'),
                    force_error=number(row, 'force_error_max'),
                    force_budget=number(row, 'force_budget'),
                    rate_error=number(row, 'rate_error_max'), rate_budget=number(row, 'rate_budget'),
                    theta_error=number(row, 'theta_error'), theta_budget=number(row, 'theta_budget')))
        for suffix, rows in (('summary', summary_rows), ('spatial', spatial),
                             ('virtual', virtual_rows)):
            path = Path(str(prefix) + '_' + suffix + '.csv')
            write_csv(path, rows)
            outputs.append(path)

        fig, axes = plt.subplots(2, 2, figsize=(14, 10), layout='constrained')
        series = (('P_stress', 1, 'Stress force power'), ('Iraw', -1, '- raw strain power'),
                  ('IC', -1, '- corrected strain power'), ('P_AS', 1, 'AS power'),
                  ('P_AV', 1, 'AV power'))
        for col, group in enumerate(('soil', 'wall')):
            rs = sorted((r for r in summary_rows if r['group'] == group), key=lambda r: int(r['part']))
            x = np.arange(4)
            for k, (field, sign, label) in enumerate(series):
                axes[0, col].bar(x + (k - 2) * .15,
                    [sign * float(r[field]) for r in rs], .15, label=label)
            for field, label in (('G1_gap', 'Corrected minus raw strain power'),
                                ('raw_closure_or_wall_port_residual', 'Raw algebraic residual'),
                                ('arithmetic_budget', 'Original arithmetic budget')):
                axes[1, col].plot(x, [float(r[field]) for r in rs], 'o-', label=label)
            for row in range(2):
                ax = axes[row, col]
                ax.set_xticks(x, [f"{float(r['tau_s']):.3f}" for r in rs])
                ax.set_xlabel('Actual time after release [s], four frozen samples')
                ax.set_ylabel('Conditional power [W/m]')
                ax.set_yscale('symlog', linthresh=1e-7)
                ax.axhline(0, color='black', lw=.6)
                ax.grid(axis='y', alpha=.25)
                ax.legend(fontsize=8)
            axes[0, col].set_title(('Soil-soil' if group == 'soil' else
                                   'Soil-wall ghost port, not physical wall reaction'))
        fig.suptitle('Frozen original CPU operators: raw closure and corrected-gradient gap\n'
                     'No time update; conditional partitions are not total coupled energy closure')
        path = Path(str(prefix) + '_powers.png')
        fig.savefig(path, dpi=160); plt.close(fig); outputs.append(path)

        fig, axes = plt.subplots(2, 2, figsize=(14, 11), layout='constrained')
        for ax, part in zip(axes.flat, PARTS):
            rs = [r for r in spatial if r['part'] == part]
            values = np.asarray([r['total_G1_gap'] for r in rs])
            bound = float(np.max(np.abs(values)))
            # Independent full signed ranges; no field clipping or smoothing.
            sc = ax.scatter([r['x'] for r in rs], [r['z'] for r in rs], c=values,
                            s=4, cmap='coolwarm', vmin=-bound if bound else -1,
                            vmax=bound if bound else 1, rasterized=True)
            fig.colorbar(sc, ax=ax, label='Per-material corrected - raw strain power [W/m]')
            for ia, ib, color in ((6767, 6865, 'black'), (4953, 4954, 'lime')):
                selected_rows = [r for r in rs if r['id'] in (ia, ib)]
                ax.plot([r['x'] for r in selected_rows], [r['z'] for r in selected_rows],
                        'o-', color=color, ms=4, lw=1, label=f'{ia}/{ib}')
            ax.set_title(f"Part {part}: actual tau={rs[0]['tau_s']:.6f}s\nIndependent full signed color range")
            ax.set_xlabel('x [m]'); ax.set_ylabel('z [m]'); ax.set_aspect('equal')
            ax.legend(fontsize=8); ax.grid(alpha=.2)
        fig.suptitle('All 5000 material points: descriptive corrected-gradient work gap\n'
                     'Same source states and stencil; nonzero gap alone does not establish instability')
        path = Path(str(prefix) + '_spatial.png')
        fig.savefig(path, dpi=160); plt.close(fig); outputs.append(path)

        fig, axes = plt.subplots(2, 2, figsize=(14, 10), layout='constrained')
        labels = ('6767 / 6865 radial', '4953 / 4954 radial',
                  'Spacing-qualified interior pair', 'All-soil x translation')
        for ax, probe, title in zip(axes.flat, PROBES, labels):
            rs = sorted((r for r in virtual_rows if r['probe'] == probe), key=lambda r: int(r['part']))
            x = np.arange(4)
            for key, label in (('symLraw_over_u_s_1', 'Raw strain response'),
                               ('symLC_over_u_s_1', 'Corrected strain response')):
                ax.plot(x, [float(r[key]) for r in rs], 'o-', label=label)
            # The original header says s_1; norm(grad u)/norm(u) has unit 1/m.
            ax.set_ylabel('Volume-weighted ||sym grad u|| / ||u|| [1/m]')
            ax.set_xticks(x, [f"{float(r['tau_s']):.3f}\n{r['id_i']}/{r['id_j']}"
                             if probe == 'healthy_pair' else f"{float(r['tau_s']):.3f}" for r in rs])
            ax.set_xlabel('Actual release-relative sample time [s]')
            ax.set_title(title); ax.set_yscale('symlog', linthresh=1e-6)
            ax.grid(alpha=.25); ax.legend(fontsize=8); ax.axhline(0, color='black', lw=.6)
        fig.suptitle('Predeclared soil-only virtual velocities on frozen original stencils\n'
                     'No virtual wall closure, force update, eigenvalue or physical acceptance')
        path = Path(str(prefix) + '_virtual.png')
        fig.savefig(path, dpi=160); plt.close(fig); outputs.append(path)

        need(all(stat(q['path']) == q for q in consumed), 'Consumed input changed during review')
        result = dict(stage=TAG, analysis_complete=True, consumed=consumed,
            consumed_stats_unchanged=True, script=stat(Path(__file__)),
            component_source=COMPONENT, component_invocations=0, solver_invocations=0,
            decoder_invocations=0, physical_steps=0, material_steps=0, SHA_scans=0,
            row_counts=dict(soil=len(soil), groups=len(groups), walls=len(walls),
                            summary=len(summary), virtual=len(virtual)),
            original_arithmetic_budgets_passed=True,
            force_bit_equal_rows=sum(integer(r, 'force_bits_equal') for r in soil),
            rate_bit_equal_rows=sum(integer(r, 'rate_bits_equal') for r in soil),
            summary_rows=summary_rows, virtual_rows=virtual_rows,
            independent_partition_sums_descriptive=diagnostics,
            actual_material_source='AS0.3/n2.55 original full301, not AV0.2 trajectory',
            virtual_soil_only=True, virtual_wall_closure=False,
            normalized_virtual_response_unit='1/m; original CSV header suffix s_1 preserved',
            shear_storage_order='Sigma_ij=(xy,yz,xz)',
            total_energy_closure_asserted=False, root_cause_established=False,
            physical_acceptance=False, other_psi_unlocked=False, visual_QA_pending=True,
            plot_symlog_linear_thresholds_display_only=dict(powers_W_per_m=1e-7,
                                                          virtual_inverse_m=1e-6),
            files=[stat(p) for p in outputs])
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    except Exception as error:
        if not check.exists():
            with check.open('x', encoding='utf-8') as f:
                json.dump(dict(stage=TAG, analysis_complete=False, first_failure=str(error),
                    consumed=consumed, partial_outputs_preserved=True,
                    component_invocations=0, solver_invocations=0, decoder_invocations=0,
                    physical_steps=0, physical_acceptance=False, SHA_scans=0),
                    f, indent=2, allow_nan=False)
                f.write('\n')
        raise


if __name__ == '__main__':
    main()
