"""Read-only four-run comparison; creates new analysis records, never solver files.

Run after export_state.exe has created RUN/native/state.csv and frames.csv.
Only native-time pairs within 1e-11 s are compared; no temporal interpolation.
"""
import csv
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

CASE = Path(__file__).resolve().parents[3]
OUT = CASE / 'tests/outputs/pore_double_vel0'
LOG = CASE / 'tests/logs/pore_double_vel0'
REPO = next(p for p in CASE.parents if (p / 'src/VS').is_dir())
TOL = 1e-11
DURATION, FRAMECOUNT = .2, 201
RUNS = [(build, step, f'q0_vel0_{build}_dt{tag}')
        for step, tag in ((1e-5, '1em5'), (5e-6, '5em6'))
        for build in ('baseline', 'current')]
WINDOWS = [('all', -1., .2), ('loading', -1., .01),
           ('early_drainage', .01, .03), ('later', .03, .2)]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def write_csv(path, rows):
    with path.open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def read_run(build, dt, name):
    source = OUT / name / 'native/state.csv'
    a = np.genfromtxt(source, delimiter=',', names=True, dtype=None, encoding='utf-8')
    a = a[np.lexsort((a['id'], a['part']))]
    assert a.size == FRAMECOUNT * 1040, (name, a.size)
    a = a.reshape(FRAMECOUNT, 1040)
    assert np.array_equal(a['id'], np.tile(np.arange(1040), (FRAMECOUNT, 1)))
    assert np.array_equal(a['part'][:, 0], np.arange(FRAMECOUNT))
    assert np.all(a['part'] == a['part'][:, :1])
    assert all(np.isfinite(a[key]).all() for key in a.dtype.names)
    t = a['time_s'][:, 0]
    assert np.all(a['time_s'] == t[:, None]) and np.all(np.diff(t) > 0)
    assert abs(t[0]) < TOL and abs(t[-1] - DURATION) < TOL
    assert np.array_equal(a['pressure_pa'], a['stored_pressure_pa'] + a['residual_pa'])
    z0 = a['z_m'][0]
    top = np.flatnonzero((np.arange(1040) >= 40) & (np.abs(z0 - np.max(z0[40:])) < 1e-9))
    assert np.array_equal(top, np.arange(139, 1040, 100))
    settlement = np.mean(z0[top][None, :] - a['z_m'][:, top], axis=1) * 1000
    record = json.loads((LOG / (name + '.json')).read_text(encoding='utf-8'))
    assert record['passed'] and record['actual_vel0_confirmed']
    assert record['excluded_particles'] == record['dt_min_adjustments'] == 0
    with (OUT / name / 'native/frames.csv').open(encoding='utf-8-sig') as f:
        frame_types = list(csv.DictReader(f))
    assert len(frame_types) == FRAMECOUNT
    for i, metadata in enumerate(frame_types):
        assert int(metadata['part']) == i and int(metadata['particle_count']) == 1040
        assert metadata['pos_type'] == ('float3' if i == 0 else 'double3')
        assert metadata['pressure_type'] == metadata['reference_type'] == ('float' if build == 'baseline' else 'double')
        assert metadata['residual_type'] == ('float' if build == 'baseline' else 'absent')
        assert metadata['fstype_type'] == 'uint' and metadata['sigma_kk_type'] == metadata['sigma_ij_type'] == 'float3'
        assert int(metadata['case_nfixed']) == 40 and int(metadata['case_nfluid']) == 1000
    return dict(name=name, build=build, dt=dt, a=a, t=t, top=top,
                settlement=settlement, mean=np.mean(a['pressure_pa'][:, 40:], axis=1),
                record=record, frame_types=frame_types, source_sha256=digest(source))


def align(runs):
    """Intersection by measured time, not nominal PART number. No interpolation."""
    indices = [[] for _ in runs]
    for i, time in enumerate(runs[0]['t']):
        row = [i]
        for r in runs[1:]:
            j = int(np.argmin(np.abs(r['t'] - time)))
            if abs(r['t'][j] - time) > TOL:
                break
            row.append(j)
        if len(row) == len(runs):
            for bucket, index in zip(indices, row):
                bucket.append(index)
    assert len(indices[0]) >= 8
    assert all(len(set(i)) == len(i) for i in indices)
    return [np.array(i, dtype=int) for i in indices]


def compare(before, after, bi, ai, label, kind):
    b, a = before['a'][bi], after['a'][ai]
    t = before['t'][bi]
    assert np.array_equal(b['id'], a['id'])
    time_delta = after['t'][ai] - t
    assert np.max(np.abs(time_delta)) <= TOL
    p = a['pressure_pa'][:, 40:] - b['pressure_pa'][:, 40:]
    s = after['settlement'][ai] - before['settlement'][bi]
    metrics = dict(label=label, kind=kind, before=before['name'], after=after['name'],
                   frames=len(t), max_time_mismatch_s=float(np.max(np.abs(time_delta))), windows={})
    history = []
    for k, time in enumerate(t):
        history.append(dict(comparison=label, kind=kind, time_s=float(time),
                            after_time_s=float(after['t'][ai[k]]), before_part=int(bi[k]), after_part=int(ai[k]),
                            rms_pressure_difference_pa=float(np.sqrt(np.mean(p[k] ** 2))),
                            max_pressure_difference_pa=float(np.max(np.abs(p[k]))),
                            mean_pressure_difference_pa=float(np.mean(p[k])),
                            settlement_difference_mm=float(s[k])))
    for window, low, high in WINDOWS:
        mask = (t > low + TOL) & (t <= high + TOL)
        if not mask.any():
            metrics['windows'][window] = None
            continue
        delta = p[mask]
        peak = np.unravel_index(np.argmax(np.abs(delta)), delta.shape)
        metrics['windows'][window] = dict(frames=int(mask.sum()), soil_particle_samples=int(delta.size),
            rms_pressure_pa=float(np.sqrt(np.mean(delta ** 2))),
            max_pressure_pa=float(np.max(np.abs(delta))),
            peak_time_s=float(t[mask][peak[0]]), peak_soil_id=int(peak[1] + 40),
            max_abs_settlement_difference_mm=float(np.max(np.abs(s[mask]))))
    metrics['final'] = history[-1]
    mechanical = {}
    for key in a.dtype.names:
        if key in ('part', 'id', 'time_s', 'stored_pressure_pa', 'residual_pa'):
            continue
        d = a[key].astype(float) - b[key].astype(float)
        mechanical[key] = dict(max_abs=float(np.max(np.abs(d))), rms=float(np.sqrt(np.mean(d*d))))
    metrics['all_particle_fields'] = mechanical
    metrics['reference_bit_mismatches'] = int(np.count_nonzero(
        np.ascontiguousarray(a['reference_pa'], dtype=np.float64).view('u8') !=
        np.ascontiguousarray(b['reference_pa'], dtype=np.float64).view('u8')))
    if kind == 'migration':
        full = metrics['windows']['all']
        metrics['previous_pressure_screening_pass'] = full['rms_pressure_pa'] <= .01 and full['max_pressure_pa'] <= .1
    return metrics, history


def main():
    global FRAMECOUNT, DURATION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event', action='store_true', help='Analyze the separate 0--30 ms sampling diagnostic.')
    args = parser.parse_args()
    prefix = 'event_' if args.event else ''
    if args.event:
        FRAMECOUNT, DURATION = 61, .03
    specs = [(b,dt,n + ('_event' if args.event else '')) for b,dt,n in RUNS]
    destinations = [LOG / (prefix+n) for n in ('analysis.json', 'history.csv', 'differences.csv', 'time_alignment.csv')]
    assert not any(p.exists() for p in destinations), 'Refusing to overwrite prior analysis'
    runs = [read_run(*spec) for spec in specs]
    manifest_path = CASE / 'tests/notes/pore_double_stage1_manifest.json'
    source_manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    for item in source_manifest['sources']:
        path = REPO / 'src' / item['file']
        if item['current_sha256'] is None:
            assert not path.exists(), f'Production file unexpectedly restored: {path}'
        else:
            assert digest(path).upper() == item['current_sha256'], f'Production source changed: {path}'
    for r in runs:
        assert all(digest(Path(p)).upper() == h.upper() for p,h in r['record']['input_sha256'].items())
        exe = (CASE / 'tests/outputs/pore_double_baseline' if r['build']=='baseline' else REPO / 'bin/windows') / 'DualSPHysics5.2CPU_win64.exe'
        assert digest(exe).upper() == r['record']['executable_sha256'].upper()
    # Index order: baseline/current 10 us; baseline/current 5 us.
    for b, a in ((runs[0], runs[1]), (runs[2], runs[3])):
        assert b['record']['generated_xml_sha256'] == a['record']['generated_xml_sha256']
        assert b['record']['input_sha256'] == a['record']['input_sha256']
        assert np.array_equal(b['a'][0]['z_m'], a['a'][0]['z_m'])
    assert all(np.array_equal(runs[0]['a'][0]['z_m'], r['a'][0]['z_m']) for r in runs)
    indices = align(runs)
    alignment = []
    for i, t in enumerate(runs[0]['t']):
        row = dict(baseline_10us_part=i, baseline_10us_time_s=float(t), matched_all_four=bool(i in indices[0]))
        for r in runs[1:]:
            j = int(np.argmin(np.abs(r['t'] - t)))
            row[r['name'] + '_nearest_part'] = j
            row[r['name'] + '_time_delta_s'] = float(r['t'][j] - t)
        alignment.append(row)
    result = dict(scope=f'CPU formal Vel0, four short runs, 0--{DURATION} s. No truth/reference solution and no performance claim.',
        production_sources_unchanged=True, production_source_entries_checked=len(source_manifest['sources']),
        source_manifest_sha256=digest(manifest_path), formal_inputs_unchanged=True, executables_unchanged=True,
        time_alignment_tolerance_s=TOL, interpolation=False, common_frames=len(indices[0]),
        excluded_from_timestep_comparison=FRAMECOUNT-len(indices[0]),
        top_particle_ids=runs[0]['top'].tolist(),
        settlement_definition='Mean saved initial z minus current native z for fixed initial top IDs, mm. Part0 float origin is common; Part>0 double coordinates.',
        runs=[], comparisons=[], common_sample_comparisons=[])
    history, differences = [], []
    for r in runs:
        result['runs'].append(dict(name=r['name'], build=r['build'], dt_s=r['dt'], frames=FRAMECOUNT,
            state_csv_sha256=r['source_sha256'], frame_type_first=r['frame_types'][0], frame_type_last=r['frame_types'][-1],
            final_mean_pressure_pa=float(r['mean'][-1]), final_settlement_mm=float(r['settlement'][-1]),
            final_time_s=float(r['t'][-1]), maximum_absolute_soil_pressure_pa=float(np.max(np.abs(r['a']['pressure_pa'][:,40:])))))
        for i, t in enumerate(r['t']):
            history.append(dict(run=r['name'], build=r['build'], dt_s=r['dt'], part=i, time_s=float(t),
                soil_count=1000, top_count=10, mean_pressure_pa=float(r['mean'][i]),
                fixed_top_settlement_mm=float(r['settlement'][i])))
    for ib, ia, label, kind in ((0,1,'migration_10us','migration'), (2,3,'migration_5us','migration'),
                                (0,2,'step_baseline','timestep'), (1,3,'step_current','timestep')):
        ri = [np.arange(FRAMECOUNT), np.arange(FRAMECOUNT)] if kind == 'migration' else [indices[ib], indices[ia]]
        metrics, rows = compare(runs[ib], runs[ia], *ri, label, kind)
        result['comparisons'].append(metrics)
        differences.extend(rows)
        common, _ = compare(runs[ib], runs[ia], indices[ib], indices[ia], label, kind)
        result['common_sample_comparisons'].append(common)
    write_csv(destinations[1], history)
    write_csv(destinations[2], differences)
    write_csv(destinations[3], alignment)
    with destinations[0].open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: result[k] for k in ('common_frames', 'excluded_from_timestep_comparison', 'runs')}, indent=2))
    for c in result['comparisons']:
        print(c['label'], c['windows']['all'], c.get('previous_pressure_screening_pass'))


if __name__ == '__main__':
    main()
