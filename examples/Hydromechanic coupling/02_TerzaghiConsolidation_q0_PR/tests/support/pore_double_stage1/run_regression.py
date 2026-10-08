"""Stage 1 pore-state migration: same-input retained-patch/double smoke regressions.

Runs only categorized temporary cases. Never changes formal XML or old results.
  py -3 tests/support/pore_double_stage1/run_regression.py --build baseline --backend cpu
  py -3 tests/support/pore_double_stage1/run_regression.py --build current --backend cpu
  py -3 tests/support/pore_double_stage1/run_regression.py --compare
These short tests establish migration compatibility, not full consolidation accuracy.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

sys.dont_write_bytecode = True
CASE = Path(__file__).resolve().parents[3]
TESTS = CASE / 'tests'
REPO = next(p for p in CASE.parents if (p / 'src/VS').is_dir())
OUT = TESTS / 'outputs/pore_double_stage1'
LOG = TESTS / 'logs/pore_double_stage1'
CONFIG = TESTS / 'configs/pore_double_stage1'
NATIVE_HARNESS = OUT / 'cpu_state_DebugCPU_r3/cpu_state_DebugCPU_r3.exe'
READER = CASE.parent / 'validation/tpi_cleanup_release_20260906/compare_particle_fields.py'
SPEC = importlib.util.spec_from_file_location('particle_reader', READER)
VTK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VTK)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def parameter(parent, tag, value, key=None):
    node = parent.find(tag if key is None else f"{tag}[@key='{key}']")
    if node is None:
        node = ET.SubElement(parent, tag, {} if key is None else {'key': key})
    node.set('value', str(value))


def native_state(run_name, part):
    """Read full authoritative pressure, including retained-patch low bits."""
    target = OUT / run_name / 'native_state'
    target.mkdir(exist_ok=True)
    csv_path = target / f'Part_{part:04d}.csv'
    if not csv_path.exists():
        command = [str(NATIVE_HARNESS), '--export-state', str(OUT / run_name / 'data'),
                   str(part), '--csv', str(csv_path)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(f'Native BI4 export failed: {result.stdout}\n{result.stderr}')
    values = np.genfromtxt(csv_path, delimiter=',', names=True,
                          dtype=[('id', 'u4')] + [(k, 'f8') for k in ('pressure_pa', 'reference_pa', 'stored_pressure_pa', 'residual_pa', 'time_s')], encoding='utf-8')
    values = values[np.argsort(values['id'])]
    assert np.array_equal(values['id'], np.arange(1040))
    return values


def run_case(build, backend, suite, dt, shepard=0, dry=False):
    name = f'{suite}_{build}_{backend}_dt{dt:.9g}_s{shepard}' + ('_dry' if dry else '')
    output = OUT / name
    config = CONFIG / name
    record_path = LOG / (name + '.json')
    for target in (output, config, record_path):
        if target.exists():
            raise RuntimeError(f'Refusing to overwrite {target}')
    output.mkdir(parents=True)
    config.mkdir(parents=True)
    LOG.mkdir(parents=True, exist_ok=True)
    if suite == 'q0':
        prefix = CASE / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_out/CaseTerzaghiConsolidation_q0_PR_full_k1em4'
        duration, tout, restart = 0.2, 0.01, None
    else:
        archive = CASE.parent / '01_SelfWeightConsolidation_PR/tests/outputs'
        prefix = archive / 'CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/CaseSWSc2_MLSDirect_Tv2'
        restart = archive / 'CaseSWSt1_MLSDirect_GPU_out/data'
        duration, tout = 0.0005, 0.00005
    inputs = [prefix.with_suffix('.xml'), prefix.with_suffix('.bi4'),
              prefix.with_name(prefix.name + '_Normals.nbi4')]
    if restart:
        inputs += sorted(restart.glob('*_0056.bi4')) + sorted(restart.glob('*.ibi4'))
    hashes = {str(p): digest(p) for p in inputs}
    generated = config / prefix.name
    for source in inputs[1:3]:
        shutil.copy2(source, config / source.name)
    tree = ET.parse(inputs[0])
    special = tree.getroot().find('execution/special')
    hydro = special.find('hydromechanics')
    if any('upl' in node.tag.lower() or 'dynamicdarcy' in node.tag.lower() for node in hydro):
        raise RuntimeError('Input is not the restored u-pw path')
    for node in list(special.findall('timeout')):
        special.remove(node)
    parameter(hydro, 'PoreShepardRegularization', int(shepard > 0))
    parameter(hydro, 'PoreShepardInterval', max(1, shepard))
    if dry:
        parameter(hydro, 'HydroMech', 0)
    params = tree.getroot().find('execution/parameters')
    for key, value in {'DtFixed': dt, 'DtIni': dt, 'TimeMax': duration, 'TimeOut': tout}.items():
        parameter(params, 'parameter', f'{value:.16g}', key)
    tree.write(generated.with_suffix('.xml'), encoding='utf-8', xml_declaration=True)
    exe_name = 'DualSPHysics5.2CPU_win64.exe' if backend == 'cpu' else 'DualSPHysics5.2_GEO_win64.exe'
    binary_dir = TESTS / 'outputs/pore_double_baseline' if build == 'baseline' else REPO / 'bin/windows'
    exe = binary_dir / exe_name
    steps = round(duration / dt)
    args = [str(exe), '-' + backend, '-mdbc_noslip', '-stable', '-symplectic']
    if backend == 'cpu':
        args += ['-ompthreads:' + ('4' if suite == 'q0' else '1')]
    if restart:
        args += ['-partbegin:56:0', str(restart)]
    args += [f'-tmax:{duration:.16g}', f'-tout:{tout:.16g}', f'-nsteps:{steps}',
             '-nortimes:1', '-sv:binx', '-svextraparts:1', '-dirdataout', 'data', '-svres', str(generated), str(output)]
    record = dict(name=name, build=build, backend=backend, suite=suite, dt=dt,
                  shepard=shepard, dry=dry, steps_requested=steps, command=args,
                  executable_sha256=digest(exe), source_input_sha256=hashes,
                  generated_xml_sha256=digest(generated.with_suffix('.xml')), passed=False)
    print('RUN', name, flush=True)
    try:
        start = time.perf_counter()
        with (LOG / (name + '.solver.log')).open('xb') as log:
            result = subprocess.run(args, cwd=REPO / 'src', stdout=log, stderr=subprocess.STDOUT, timeout=2700)
        record['wall_seconds'] = time.perf_counter() - start
        record['exit_code'] = result.returncode
        if result.returncode:
            raise RuntimeError(f'Solver exit {result.returncode}; see solver.log')
        text = (output / 'Run.out').read_text(encoding='utf-8-sig', errors='replace')
        for key, pattern in {
            'steps': r'Steps of simulation\.+:\s*(\d+)',
            'excluded_particles': r'Excluded particles\.+:\s*(\d+)',
            'dt_min_adjustments': r'DTs adjusted to DtMin\.+:\s*(\d+)'
        }.items():
            match = re.search(pattern, text)
            record[key] = int(match[1]) if match else None
        assert record['steps'] == steps, (record['steps'], steps)
        assert record['excluded_particles'] == record['dt_min_adjustments'] == 0
        record['inputs_unchanged'] = all(digest(Path(p)) == h for p, h in hashes.items())
        assert record['inputs_unchanged']
        vtk_dir = output / 'vtk'
        vtk_dir.mkdir()
        variables = '-vars:-all,+idp,+vel,+rhop,+sigma_kk,+sigma_ij,+fstype'
        if not dry:
            variables += ',+porepress,+porepress0,+excessporepress'
        converter = REPO / 'bin/windows/PartVTK_win64.exe'
        conversion = [str(converter), '-dirin', str(output / 'data'), '-savevtk',
                      str(vtk_dir / 'PartAll'), '-onlytype:+all', variables]
        record['conversion_command'] = conversion
        with (LOG / (name + '.vtk.log')).open('xb') as log:
            result = subprocess.run(conversion, cwd=REPO / 'src', stdout=log, stderr=subprocess.STDOUT, timeout=120)
        assert result.returncode == 0, 'PartVTK failed; check native double compatibility'
        files = sorted(vtk_dir.glob('*.vtk'))
        assert len(files) == round(duration / tout) + 1, len(files)
        frames = []
        for path in files:
            arrays, title = VTK.parse_vtk(path)
            order = np.argsort(arrays['Idp'])
            arrays = {key: value[order] for key, value in arrays.items()}
            assert np.array_equal(arrays['Idp'], np.arange(1040))
            assert all(np.isfinite(value).all() for value in arrays.values())
            frame = dict(file=path.name, sha256=digest(path), count=1040, title=title,
                         vtk_dtypes={key: str(value.dtype) for key, value in arrays.items()})
            if not dry:
                key = next(k for k in arrays if k.lower() == 'porepress')
                frame['soil_pressure_pa'] = arrays[key][40:].astype(float).tolist()
            frames.append(frame)
        record['frames'] = frames
        record['passed'] = True
    finally:
        save(record_path, record)
    print('PASS', name, flush=True)


def compare():
    report = {'scope': 'Short same-input migration regression; not full consolidation accuracy or performance. Builds and tests overlapped, so walltime is not comparable.',
              'acceptance_limits': dict(soil_pressure_all_frames_rms_pa=0.01, soil_pressure_max_pa=0.1,
                                        position_max_m=1e-6, velocity_max_m_s=1e-5, stress_max_pa=1.,
                                        reference_bit_exact=True, dry_value_exact=True),
              'pairs': [], 'timestep_pairs': []}
    history = []
    for before_path in sorted(LOG.glob('*_baseline_*.json')):
        after_path = before_path.with_name(before_path.name.replace('_baseline_', '_current_'))
        if not after_path.exists():
            continue
        before, after = (json.loads(p.read_text(encoding='utf-8')) for p in (before_path, after_path))
        assert before['passed'] and after['passed']
        assert before['source_input_sha256'] == after['source_input_sha256']
        assert before['generated_xml_sha256'] == after['generated_xml_sha256']
        pair = {'before': before['name'], 'after': after['name'], 'fields': {}, 'frames': len(before['frames'])}
        pair['pressure_definition'] = 'Native BI4: baseline double(PorePress high)+double(PorePressRes), current double PorePress. Native reference retained; Excess computed from full states. VTK visible-pressure differences reported separately.'
        assert len(before['frames']) == len(after['frames'])
        times_before = VTK.read_run_log(OUT / before['name'] / 'Run.out')
        times_after = VTK.read_run_log(OUT / after['name'] / 'Run.out')
        assert set(times_before) == set(times_after)
        assert all(times_before[i]['time'] == times_after[i]['time'] and
                   times_before[i]['logged_step'] == times_after[i]['logged_step'] for i in times_before)
        pair['actual_output_times_match'] = True
        sums, counts, maxima = {}, {}, {}
        visible_sums, visible_count, visible_max = 0., 0, 0.
        soil_sums, soil_count, soil_max, reference_bit_mismatches, fs_mismatches = 0., 0, 0., 0, 0
        for index, (bf, af) in enumerate(zip(before['frames'], after['frames'])):
            b, _ = VTK.parse_vtk(OUT / before['name'] / 'vtk' / bf['file'])
            a, _ = VTK.parse_vtk(OUT / after['name'] / 'vtk' / af['file'])
            b = {k: v[np.argsort(b['Idp'])] for k, v in b.items()}
            a = {k: v[np.argsort(a['Idp'])] for k, v in a.items()}
            assert set(a) == set(b)
            if index == 0:
                pair['before_vtk_dtypes'] = {k: str(v.dtype) for k, v in b.items()}
                pair['after_vtk_dtypes'] = {k: str(v.dtype) for k, v in a.items()}
            if not before['dry']:
                pk = next(k for k in a if k.lower() == 'porepress')
                visible_delta = a[pk].astype(float) - b[pk].astype(float)
                visible_sums += float(np.sum(visible_delta * visible_delta))
                visible_count += visible_delta.size
                visible_max = max(visible_max, float(np.max(np.abs(visible_delta))))
                native_b, native_a = native_state(before['name'], index), native_state(after['name'], index)
                assert np.array_equal(native_b['time_s'], native_a['time_s'])
                reference_bit_mismatches += int(np.count_nonzero(native_a['reference_pa'].copy().view('u8') != native_b['reference_pa'].copy().view('u8')))
                for arrays, native in ((b, native_b), (a, native_a)):
                    for key in arrays:
                        if key.lower() == 'porepress':
                            arrays[key] = native['pressure_pa']
                        elif key.lower() == 'porepress0':
                            arrays[key] = native['reference_pa']
                        elif key.lower() == 'excessporepress':
                            arrays[key] = native['pressure_pa'] - native['reference_pa']
            for key in a:
                delta = a[key].astype(float) - b[key].astype(float)
                sums[key] = sums.get(key, 0.) + float(np.sum(delta * delta))
                counts[key] = counts.get(key, 0) + delta.size
                maxima[key] = max(maxima.get(key, 0.), float(np.max(np.abs(delta))))
                if key.lower() == 'fstype':
                    fs_mismatches += int(np.count_nonzero(a[key] != b[key]))
            if not before['dry']:
                pk = next(k for k in a if k.lower() == 'porepress')
                delta = a[pk][40:].astype(float) - b[pk][40:].astype(float)
                soil_sums += float(np.sum(delta * delta))
                soil_count += delta.size
                soil_max = max(soil_max, float(np.max(np.abs(delta))))
                history.append(dict(suite=before['suite'], backend=before['backend'], dt=before['dt'],
                                    shepard=before['shepard'], part=index,
                                    time_s=0. if index == 0 else times_before[index]['time'],
                                    baseline_mean_pressure_pa=float(np.mean(b[pk][40:].astype(float))),
                                    double_mean_pressure_pa=float(np.mean(a[pk][40:].astype(float))),
                                    rms_difference_pa=float(np.sqrt(np.mean(delta * delta))),
                                    max_abs_difference_pa=float(np.max(np.abs(delta)))))
        pair['fields'] = {k: {'rms_difference': float(np.sqrt(sums[k] / counts[k])),
                             'max_abs_difference': maxima[k]} for k in sums}
        pair['bitwise_numeric_equal'] = all(v == 0 for v in maxima.values())
        if visible_count:
            pair['vtk_visible_pressure_difference'] = dict(rms_pa=float(np.sqrt(visible_sums / visible_count)), max_pa=visible_max)
        pair['reference_bit_mismatches'] = reference_bit_mismatches
        pair['free_surface_classification_mismatches'] = fs_mismatches
        if soil_count:
            pair['soil_pressure_native'] = dict(all_frames_rms_pa=float(np.sqrt(soil_sums / soil_count)), max_abs_pa=soil_max)
        gates = {}
        if soil_count:
            gates['soil_pressure_rms'] = pair['soil_pressure_native']['all_frames_rms_pa'] <= .01
            gates['soil_pressure_max'] = soil_max <= .1
            gates['reference_bit_exact'] = reference_bit_mismatches == 0
        for key, maximum in maxima.items():
            if key.lower() == 'pos':
                gates['position_max'] = maximum <= 1e-6
            elif key.lower() == 'vel':
                gates['velocity_max'] = maximum <= 1e-5
            elif 'sigma' in key.lower():
                gates[key + '_max'] = maximum <= 1.
        gates['free_surface_classification'] = fs_mismatches == 0
        pair['dry_path_identical'] = pair['bitwise_numeric_equal'] if before['dry'] else None
        if before['dry']:
            assert pair['dry_path_identical'], 'Dry path changed'
            gates['dry_value_exact'] = pair['dry_path_identical']
        pair['acceptance_checks'] = gates
        pair['passed'] = all(gates.values())
        report['pairs'].append(pair)
    for build in ('baseline', 'current'):
        for backend in ('cpu', 'gpu'):
            records = {}
            for dt in (2.5e-7, 1.25e-7, 6.25e-8):
                path = LOG / f'selfweight_{build}_{backend}_dt{dt:.9g}_s0.json'
                if path.exists():
                    record = json.loads(path.read_text(encoding='utf-8'))
                    if record.get('passed'):
                        records[dt] = record
            for dt1, dt2 in ((2.5e-7, 1.25e-7), (1.25e-7, 6.25e-8)):
                if dt1 in records and dt2 in records:
                    p1, p2 = (native_state(records[dt]['name'], len(records[dt]['frames']) - 1)['pressure_pa'][40:] for dt in (dt1, dt2))
                    report['timestep_pairs'].append(dict(build=build, backend=backend, dt1=dt1, dt2=dt2,
                                                         final_pressure_rms_pa=float(np.sqrt(np.mean((p1 - p2) ** 2))),
                                                         final_pressure_max_difference_pa=float(np.max(np.abs(p1 - p2)))))
    assert report['pairs'], 'No completed matching baseline/current records'
    report['passed'] = all(pair['passed'] for pair in report['pairs'])
    save(LOG / 'regression_comparison.json', report)
    if history:
        with (LOG / 'regression_history.csv').open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(history[0]))
            writer.writeheader()
            writer.writerows(history)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['passed']:
        raise RuntimeError('A prespecified Stage 1 migration check exceeded its limit; inspect saved comparison')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', choices=['baseline', 'current'])
    parser.add_argument('--backend', choices=['cpu', 'gpu'])
    parser.add_argument('--suite', choices=['q0', 'selfweight', 'all'], default='all')
    parser.add_argument('--compare', action='store_true')
    args = parser.parse_args()
    if args.compare:
        compare()
        return
    if not args.build or not args.backend:
        parser.error('--build and --backend are required for a run')
    if args.suite in ('q0', 'all'):
        run_case(args.build, args.backend, 'q0', 1e-5)
    if args.suite in ('selfweight', 'all'):
        for dt in (2.5e-7, 1.25e-7, 6.25e-8):
            run_case(args.build, args.backend, 'selfweight', dt)
        run_case(args.build, args.backend, 'selfweight', 2.5e-7, shepard=40)
        run_case(args.build, args.backend, 'selfweight', 2.5e-7, dry=True)


if __name__ == '__main__':
    main()
