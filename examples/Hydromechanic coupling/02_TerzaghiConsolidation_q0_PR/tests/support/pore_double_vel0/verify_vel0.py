"""Independent native-CSV QA; never imports the primary analyzer or runs a solver.

python verify_vel0.py --partial   # report completed runs to stdout, write nothing
python verify_vel0.py             # require four runs + primary analysis; save QA JSON
python verify_vel0.py --event     # separate event QA, including original-run overlap
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

CASE = Path(__file__).resolve().parents[3]
OUTPUTS = CASE / 'tests/outputs/pore_double_vel0'
LOGS = CASE / 'tests/logs/pore_double_vel0'
SPECS = [('baseline', '1em5'), ('current', '1em5'),
         ('baseline', '5em6'), ('current', '5em6')]
TOP = [139 + 100 * i for i in range(10)]
TOL = 1e-11
COLUMNS = ('part,id,time_s,x_m,y_m,z_m,pressure_pa,reference_pa,'
           'stored_pressure_pa,residual_pa,velx_m_s,vely_m_s,velz_m_s,'
           'rhop_kg_m3,sigma_xx_pa,sigma_yy_pa,sigma_zz_pa,sigma_xy_pa,'
           'sigma_yz_pa,sigma_xz_pa,fstype').split(',')
IX = {key: i for i, key in enumerate(COLUMNS)}
WINDOWS = {'all': (-1., .2), 'loading': (-1., .01),
           'early_drainage': (.01, .03), 'later': (.03, .2)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fsum_mean(values):
    return math.fsum(map(float, np.ravel(values))) / np.size(values)


def rms(values):
    return math.sqrt(math.fsum(float(v) * float(v) for v in np.ravel(values)) / np.size(values))


def read_one(build, tag, event=False):
    name = f'q0_vel0_{build}_dt{tag}' + ('_event' if event else '')
    framecount, duration = (61, .03) if event else (201, .2)
    native = OUTPUTS / name / 'native'
    require((native / 'complete.txt').is_file(), name + ': incomplete native export')
    with (native / 'state.csv').open(encoding='utf-8-sig', newline='') as stream:
        require(next(csv.reader(stream)) == COLUMNS, name + ': unexpected state schema')
    a = np.loadtxt(native / 'state.csv', delimiter=',', skiprows=1, dtype=np.float64)
    require(a.shape == (framecount * 1040, len(COLUMNS)), name + ': row/column count')
    require(np.isfinite(a).all(), name + ': non-finite or absent state value')
    a = a[np.lexsort((a[:, IX['id']], a[:, IX['part']]))].reshape(framecount, 1040, len(COLUMNS))
    require(np.array_equal(a[:, :, IX['id']], np.broadcast_to(np.arange(1040), (framecount, 1040))), name + ': missing/duplicate ID')
    require(np.array_equal(a[:, :, IX['part']], np.broadcast_to(np.arange(framecount)[:, None], (framecount, 1040))), name + ': missing/duplicate frame')
    t = a[:, 0, IX['time_s']]
    require(np.array_equal(a[:, :, IX['time_s']], np.broadcast_to(t[:, None], (framecount, 1040))), name + ': within-frame time mismatch')
    require(t[0] == 0 and abs(t[-1] - duration) <= TOL and np.all(np.diff(t) > 0), name + ': time extent/order')
    with (native / 'frames.csv').open(encoding='utf-8-sig', newline='') as stream:
        frames = list(csv.DictReader(stream))
    require(len(frames) == framecount, name + ': frame metadata count')
    for index, frame in enumerate(frames):
        expected = dict(part=str(index), particle_count='1040', piece_count='1', id_type='uint',
            pos_type='float3' if index == 0 else 'double3',
            pressure_type='float' if build == 'baseline' else 'double',
            reference_type='float' if build == 'baseline' else 'double',
            residual_type='float' if build == 'baseline' else 'absent',
            velocity_type='float3', rhop_type='float', sigma_kk_type='float3',
            sigma_ij_type='float3', fstype_type='uint', case_nfixed='40',
            case_nmoving='0', case_nfloat='0', case_nfluid='1000')
        require(all(frame.get(k) == v for k, v in expected.items()), name + f': schema mismatch at frame {index}')
        require(float(frame['time_s']) == t[index], name + ': native metadata time mismatch')
    p = a[:, :, IX['pressure_pa']]
    hi = a[:, :, IX['stored_pressure_pa']]
    lo = a[:, :, IX['residual_pa']]
    require(np.array_equal(p, hi + lo), name + ': full pressure not stored+residual')
    require(not np.any(a[:, :, IX['reference_pa']]), name + ': q0 reference expected zero')
    if build == 'baseline':
        require(np.array_equal(hi, hi.astype('f4').astype('f8')), name + ': legacy high not float-exact')
        require(np.array_equal(lo, lo.astype('f4').astype('f8')), name + ': legacy low not float-exact')
    else:
        require(not np.any(lo), name + ': double state has runtime residual')
    fs = a[:, :, IX['fstype']]
    require(np.array_equal(fs, fs.astype('i8')) and np.isin(fs, np.arange(5)).all(), name + ': invalid/missing FSType')
    require(np.all(fs[:, :40] == 4), name + ': fixed-boundary FSType')
    z = a[:, :, IX['z_m']]
    detected_top = np.flatnonzero((np.arange(1040) >= 40) & (abs(z[0] - np.max(z[0, 40:])) <= 1e-9)).tolist()
    require(detected_top == TOP, name + ': initial top-ID set differs')
    settlement = np.array([math.fsum(float(z[0, j] - row[j]) for j in TOP) * 1000 / len(TOP) for row in z])
    mean = np.array([fsum_mean(row[40:]) for row in p])
    record = json.loads((LOGS / (name + '.json')).read_text(encoding='utf-8'))
    require(record['passed'] and record['actual_vel0_confirmed'] and record['inputs_unchanged'], name + ': failed runner checks')
    require(record['excluded_particles'] == record['dt_min_adjustments'] == 0, name + ': exclusions/timestep adjustment')
    require('-mdbc' in record['command'] and '-mdbc_noslip' not in record['command'], name + ': not formal Vel0')
    report = dict(name=name, state_csv_sha256=sha(native / 'state.csv'), frames_csv_sha256=sha(native / 'frames.csv'),
        rows=framecount * 1040, frames=framecount, soil_particles=1000, boundary_particles=40,
        finite_all_fields=True, unique_part_id=True, complete_fs_pressure_schema=True,
        pressure_reconstruction_exact=True, pressure_schema=frames[0]['pressure_type'],
        residual_schema=frames[0]['residual_type'], pos_schema_initial=frames[0]['pos_type'],
        pos_schema_later=frames[-1]['pos_type'], fstype_values=sorted(map(int, np.unique(fs))),
        final_time_s=float(t[-1]), final_mean_pressure_pa=float(mean[-1]),
        final_settlement_mm=float(settlement[-1]))
    return dict(name=name, a=a, t=t, pressure=p[:, 40:], mean=mean,
                settlement=settlement, report=report, record=record)


def intersection(runs):
    """Monotone multiway time merge; no PART-index assumption or interpolation."""
    cursors = [0] * len(runs)
    found = [[] for _ in runs]
    while all(i < len(r['t']) for i, r in zip(cursors, runs)):
        times = [float(r['t'][i]) for i, r in zip(cursors, runs)]
        if max(times) - min(times) <= TOL:
            for k in range(len(runs)):
                found[k].append(cursors[k])
                cursors[k] += 1
        else:
            for k, time in enumerate(times):
                if time == min(times):
                    cursors[k] += 1
    return [np.array(x, dtype=int) for x in found]


def compare(left, right, il, ir, label):
    require(len(il) > 0 and len(il) == len(ir), label + ': empty match')
    times = left['t'][il]
    d = right['pressure'][ir] - left['pressure'][il]
    sd = right['settlement'][ir] - left['settlement'][il]
    require(np.max(np.abs(right['t'][ir] - times)) <= TOL, label + ': time mismatch')
    result = dict(label=label, frames=len(il), max_time_mismatch_s=float(np.max(np.abs(right['t'][ir] - times))), windows={})
    for key, (low, high) in WINDOWS.items():
        selected = [j for j, time in enumerate(times) if time > low + TOL and time <= high + TOL]
        if not selected:
            result['windows'][key] = None
            continue
        delta = d[selected]
        peak_flat = int(np.abs(delta).argmax())
        peak_row, peak_col = divmod(peak_flat, 1000)
        result['windows'][key] = dict(frames=len(selected), soil_particle_samples=delta.size,
            rms_pressure_pa=rms(delta), max_pressure_pa=float(abs(delta[peak_row, peak_col])),
            peak_time_s=float(times[selected[peak_row]]), peak_soil_id=peak_col + 40,
            max_abs_settlement_difference_mm=float(max(abs(sd[j]) for j in selected)))
    result['history'] = [dict(time_s=float(times[j]), before_part=int(il[j]), after_part=int(ir[j]),
        rms_pressure_difference_pa=rms(row), max_pressure_difference_pa=float(np.max(abs(row))),
        mean_pressure_difference_pa=fsum_mean(row), settlement_difference_mm=float(sd[j])) for j, row in enumerate(d)]
    return result


def mismatch_summary(mask, times, first_id=40):
    locations = np.argwhere(mask)
    if len(locations):
        i, j = map(int, locations[0])
        first = dict(part=i, time_s=float(times[i]), id=j + first_id)
    else:
        first = None
    return dict(differing_particle_frame_samples=int(np.count_nonzero(mask)),
                affected_frames=int(np.any(mask, axis=1).sum()), first=first,
                counts_per_frame=np.count_nonzero(mask, axis=1).tolist())


def diagnose_10us(left, right):
    require(np.array_equal(left['t'], right['t']), 'diagnostic needs identical saved times')
    b, c = left['a'], right['a']
    oldhigh = b[:, 40:, IX['stored_pressure_pa']]
    oldroundtrip = b[:, 40:, IX['pressure_pa']].astype('f4').astype('f8')
    newhigh = c[:, 40:, IX['pressure_pa']].astype('f4').astype('f8')
    legacy = mismatch_summary(oldhigh != oldroundtrip, left['t'])
    legacy['maximum_abs_high_difference_pa'] = float(np.max(abs(oldhigh - oldroundtrip)))
    if legacy['first']:
        part, particle = legacy['first']['part'], legacy['first']['id']
        legacy['first'].update(stored_high_pa=float(b[part, particle, IX['stored_pressure_pa']]),
            residual_pa=float(b[part, particle, IX['residual_pa']]),
            reconstructed_pressure_pa=float(b[part, particle, IX['pressure_pa']]),
            float_reprojected_pressure_pa=float(oldroundtrip[part, particle - 40]))
    migration = mismatch_summary(oldhigh != newhigh, left['t'])
    migration['maximum_abs_high_difference_pa'] = float(np.max(abs(oldhigh - newhigh)))
    if migration['first']:
        part, particle = migration['first']['part'], migration['first']['id']
        migration['first'].update(stored_legacy_high_pa=float(oldhigh[part, particle - 40]),
            projected_current_high_pa=float(newhigh[part, particle - 40]))
    fields = {}
    for key in ['pressure_pa', 'x_m', 'y_m', 'z_m', 'velx_m_s', 'vely_m_s', 'velz_m_s',
                'rhop_kg_m3', 'sigma_xx_pa', 'sigma_yy_pa', 'sigma_zz_pa',
                'sigma_xy_pa', 'sigma_yz_pa', 'sigma_xz_pa', 'fstype']:
        delta = c[:, 40:, IX[key]] - b[:, 40:, IX[key]]
        fields[key] = mismatch_summary(delta != 0, left['t'])
        fields[key]['maximum_absolute_difference'] = float(np.max(abs(delta)))
        if fields[key]['first']:
            part, particle = fields[key]['first']['part'], fields[key]['first']['id']
            fields[key]['first'].update(baseline_value=float(b[part, particle, IX[key]]),
                current_value=float(c[part, particle, IX[key]]),
                difference=float(delta[part, particle - 40]))
    return dict(scope='Soil IDs 40--1039 in saved frames only; not every integration substep.',
        legacy_high_vs_float_reconstruction=legacy, legacy_high_vs_float_current=migration,
        migration_field_first_difference=fields,
        causal_limit='Saved-frame timing and midpoint counts do not establish a within-step causal chain or the cause of the final pressure maximum.')


def compare_primary(result, event=False):
    prefix = 'event_' if event else ''
    framecount = 61 if event else 201
    primary = json.loads((LOGS / (prefix + 'analysis.json')).read_text(encoding='utf-8'))
    checks = []

    def equal(label, observed, expected):
        if isinstance(expected, float):
            ok = math.isclose(float(observed), expected, rel_tol=2e-12, abs_tol=2e-12)
        else:
            ok = observed == expected
        require(ok, f'Primary mismatch {label}: {observed!r} vs independent {expected!r}')
        checks.append(label)

    equal('common_frames', primary['common_frames'], result['common_frames'])
    equal('top_particle_ids', primary['top_particle_ids'], TOP)
    for table in ('comparisons', 'common_sample_comparisons'):
        by_label = {r['label']: r for r in primary[table]}
        for independent in result[table]:
            main = by_label[independent['label']]
            equal(table + '/' + independent['label'] + '/frames', main['frames'], independent['frames'])
            for window, values in independent['windows'].items():
                if values is None:
                    equal(table + '/' + window, main['windows'][window], None)
                else:
                    for key, value in values.items():
                        equal(table + '/' + independent['label'] + '/' + window + '/' + key, main['windows'][window][key], value)
    with (LOGS / (prefix + 'history.csv')).open(encoding='utf-8-sig', newline='') as stream:
        history = list(csv.DictReader(stream))
    expected_history = {(r['run'], r['part']): r for r in result['history']}
    require(len(history) == len(expected_history), 'Primary history row count')
    seen = set()
    for row in history:
        pair = (row['run'], int(row['part']))
        require(pair not in seen and pair in expected_history, 'Primary history key duplicate/missing')
        seen.add(pair)
        independent = expected_history[pair]
        for key in ('time_s', 'mean_pressure_pa', 'fixed_top_settlement_mm'):
            equal('history/' + str(pair) + '/' + key, float(row[key]), independent[key])
    with (LOGS / (prefix + 'differences.csv')).open(encoding='utf-8-sig', newline='') as stream:
        differences = list(csv.DictReader(stream))
    expected_differences = {(r['label'], h['before_part'], h['after_part']): h
        for r in result['comparisons'] for h in r['history']}
    require(len(differences) == len(expected_differences), 'Primary differences row count')
    seen = set()
    for row in differences:
        pair = (row['comparison'], int(row['before_part']), int(row['after_part']))
        require(pair not in seen and pair in expected_differences, 'Primary difference key duplicate/missing')
        seen.add(pair)
        independent = expected_differences[pair]
        for key in ('time_s', 'rms_pressure_difference_pa', 'max_pressure_difference_pa',
                    'mean_pressure_difference_pa', 'settlement_difference_mm'):
            equal('differences/' + str(pair) + '/' + key, float(row[key]), independent[key])
    with (LOGS / (prefix + 'time_alignment.csv')).open(encoding='utf-8-sig', newline='') as stream:
        alignment = list(csv.DictReader(stream))
    require(len(alignment) == framecount, 'Primary alignment row count')
    wanted = {row['parts'][0] for row in result['common_time_alignment']}
    matched = {int(row['baseline_10us_part']) for row in alignment if row['matched_all_four'] == 'True'}
    equal('time_alignment/common_PART_set', sorted(matched), sorted(wanted))
    return dict(passed=True, numerical_checks=len(checks), primary_analysis_sha256=sha(LOGS / (prefix + 'analysis.json')),
        independent_numeric_tolerance='abs 2e-12 + rel 2e-12; exact IDs, counts and keys',
        validated_artifacts=[prefix + n for n in ('analysis.json', 'history.csv', 'differences.csv', 'time_alignment.csv')])


def verify_original_overlap(event_run, build, tag):
    """Bitwise state check of unchanged-version/unchanged-dt output schedules."""
    original = read_one(build, tag, event=False)
    io, ie = intersection([original, event_run])
    require(len(io) >= 2, event_run['name'] + ': insufficient original/event overlap')
    original_record, event_record = original['record'], event_run['record']
    require(original_record['executable_sha256'].lower() == event_record['executable_sha256'].lower(), 'Event changed executable')
    require(original_record['dt'] == event_record['dt'], 'Event changed dt')
    fields = {}
    for name in COLUMNS:
        if name in ('part', 'id', 'time_s'):
            continue
        before = np.ascontiguousarray(original['a'][io, :, IX[name]])
        after = np.ascontiguousarray(event_run['a'][ie, :, IX[name]])
        mask = before.view('u8') != after.view('u8')
        fields[name] = dict(compared_particle_frame_samples=int(before.size),
                           bit_mismatches=int(np.count_nonzero(mask)),
                           max_absolute_difference=float(np.max(abs(after - before))))
    require(all(v['bit_mismatches'] == 0 for v in fields.values()), event_run['name'] + ': output schedule altered matched physical state')
    return dict(original=original['name'], event=event_run['name'], common_frames=len(io),
        same_executable_sha256=True, same_dt=True, all_physical_fields_bit_identical=True,
        all_particle_scope='All 1040 IDs, including 40 boundaries; pressure high/low, reference, pos, vel, rhop, stress, FSType.',
        original_state_csv_sha256=original['report']['state_csv_sha256'], event_state_csv_sha256=event_run['report']['state_csv_sha256'],
        maximum_time_mismatch_s=float(np.max(abs(original['t'][io] - event_run['t'][ie]))),
        common_time_alignment=[dict(original_part=int(a), event_part=int(b), original_time_s=float(original['t'][a]),
            event_time_s=float(event_run['t'][b])) for a, b in zip(io, ie)], fields=fields,
        coverage_limit='Bit identity is established only at the listed shared saved times, not at every step or all unmatched times.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--partial', action='store_true')
    parser.add_argument('--event', action='store_true')
    args = parser.parse_args()
    suffix = '_event' if args.event else ''
    prefix = 'event_' if args.event else ''
    framecount, duration = (61, .03) if args.event else (201, .2)
    destination = LOGS / (prefix + 'independent_validation.json')
    require(args.partial or not destination.exists(), 'Refusing existing independent validation JSON')
    runs = []
    for build, tag in SPECS:
        marker = OUTPUTS / (f'q0_vel0_{build}_dt{tag}' + suffix) / 'native/complete.txt'
        if args.partial and not marker.exists():
            continue
        runs.append(read_one(build, tag, args.event))
    require(len(runs) >= 2, 'Need at least first completed baseline/current pair')
    by_name = {r['name']: r for r in runs}
    result = dict(scope=f'Independent CPU Vel0 0--{duration} s native saved-frame QA; no solver, no interpolation, no truth solution.',
        time_tolerance_s=TOL, top_particle_ids=TOP, runs=[r['report'] for r in runs],
        same_dt_partial=len(runs) != 4, comparisons=[], common_sample_comparisons=[], history=[])
    for r in runs:
        require(np.array_equal(runs[0]['a'][0], r['a'][0]), 'Initial exported state not identical across runs')
        result['history'].extend(dict(run=r['name'], part=i, time_s=float(t), mean_pressure_pa=float(r['mean'][i]),
            fixed_top_settlement_mm=float(r['settlement'][i])) for i, t in enumerate(r['t']))
    for tag, label in [('1em5', 'migration_10us'), ('5em6', 'migration_5us')]:
        names = [f'q0_vel0_{build}_dt{tag}' + suffix for build in ('baseline', 'current')]
        if all(name in by_name for name in names):
            left, right = [by_name[name] for name in names]
            require(left['record']['generated_xml_sha256'] == right['record']['generated_xml_sha256'], label + ': XML mismatch')
            require(left['record']['input_sha256'] == right['record']['input_sha256'], label + ': source inputs mismatch')
            il, ir = intersection([left, right])
            require(len(il) == framecount, label + ': not all frames matched')
            result['comparisons'].append(compare(left, right, il, ir, label))
    result['saved_frame_diagnostics_10us'] = diagnose_10us(runs[0], runs[1])
    if len(runs) == 4:
        common = intersection(runs)
        result['common_frames'] = len(common[0])
        result['excluded_from_timestep_comparison'] = framecount - len(common[0])
        result['common_time_alignment'] = [dict(parts=[int(x[k]) for x in common],
            times_s=[float(r['t'][x[k]]) for r, x in zip(runs, common)]) for k in range(len(common[0]))]
        for ib, ia, label in [(0, 1, 'migration_10us'), (2, 3, 'migration_5us'),
                              (0, 2, 'step_baseline'), (1, 3, 'step_current')]:
            metric = compare(runs[ib], runs[ia], common[ib], common[ia], label)
            result['common_sample_comparisons'].append(metric)
            if label.startswith('step_'):
                result['comparisons'].append(metric)
    if not args.partial:
        require(len(runs) == 4, 'All four runs required for final verification')
        result['primary_analysis_verification'] = compare_primary(result, args.event)
        if args.event:
            result['original_output_schedule_invariance'] = [verify_original_overlap(r, *spec) for r, spec in zip(runs, SPECS)]
        result['assessment'] = 'Share with caveats: independent metrics verified; short saved-time intersection is not convergence order, a truth solution, or step-level causal proof.'
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write('\n')
    summary = {key: result[key] for key in ('runs', 'common_frames', 'primary_analysis_verification') if key in result}
    summary['comparisons'] = [dict(label=x['label'], all=x['windows']['all']) for x in result['comparisons']]
    summary['diagnostics'] = {key: {k: v for k, v in value.items() if k != 'counts_per_frame'}
        for key, value in result['saved_frame_diagnostics_10us'].items() if isinstance(value, dict) and key != 'migration_field_first_difference'}
    summary['first_field_differences'] = {key: value['first'] for key, value in result['saved_frame_diagnostics_10us']['migration_field_first_difference'].items()}
    if args.event and not args.partial:
        summary['output_schedule_invariance'] = [dict(original=r['original'], event=r['event'], common_frames=r['common_frames'],
            all_physical_fields_bit_identical=r['all_physical_fields_bit_identical'],
            first_time_s=r['common_time_alignment'][0]['original_time_s'],
            last_time_s=r['common_time_alignment'][-1]['original_time_s']) for r in result['original_output_schedule_invariance']]
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
