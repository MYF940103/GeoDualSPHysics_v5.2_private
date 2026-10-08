"""Bounded original-float rollback regression; never launches a full case BAT.

From this case directory:
  py -3 -B tests/support/upw_float_restore/run_smoke.py --check
  py -3 -B tests/support/upw_float_restore/run_smoke.py --run
Each new --tag (default r1) exclusively creates four categorized short runs.
The original fe72537-era new_release inputs/results are read, never copied or
overwritten. CPU/GPU each run PairDivergence and DensityRate for 2000 steps.
Acceptance compares the saved native fields, not unsaved internal state and
not mathematical/physical accuracy. Runtime is traceability, not a benchmark.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
CASE = Path(__file__).resolve().parents[3]
REPO = next(p for p in CASE.parents if (p / 'src/VS').is_dir())
LEGACY = CASE.parent / 'validation/tpi_cleanup_release_20260906'
OUTPUT = CASE / 'tests/outputs/upw_float_restore'
LOG = CASE / 'tests/logs/upw_float_restore'
READER = CASE / 'tests/outputs/pore_double_vel0/reader/export_state.exe'
READER_RECORD = CASE / 'tests/logs/pore_double_vel0/reader.build.json'
CHECKPOINT = 'fe72537f8b61616e98134535bfaf0535a4269855'
LOADER_SAFETY_SHA = '2dcf4561bc9df4695a732359a5307305dddfe506c191b16f0966a1a5542b3c20'
EXES = {'cpu': 'DualSPHysics5.2CPU_win64.exe', 'gpu': 'DualSPHysics5.2_GEO_win64.exe'}
LEGACY_SHA = {
    'cpu': '71b20060be8c8aed4ee604ac1b4fe41fe4e6d6042e2e20de9caa1ce28c113f04',
    'gpu': '3594f0a60841a59657e9f2d64cabad47ba5abc6fcd1219abd1adb47ee4cced0c',
}
DOUBLE_SHA = {
    'cpu': '95683ea87702a50cc8246b7c32c7de9c2b203435985a373378a6fcdda7347dbd',
    'gpu': 'ad6056e835d06b1726791c1512aec39ff5faa5fc5c2e11c0cbafce60085f4aff',
}
SCENARIOS = ('pair_symplectic', 'density_symplectic')
COLUMNS = ('part,id,time_s,x_m,y_m,z_m,pressure_pa,reference_pa,stored_pressure_pa,'
           'residual_pa,velx_m_s,vely_m_s,velz_m_s,rhop_kg_m3,sigma_xx_pa,'
           'sigma_yy_pa,sigma_zz_pa,sigma_xy_pa,sigma_yz_pa,sigma_xz_pa,fstype').split(',')
COL = {name: i for i, name in enumerate(COLUMNS)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_new(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def check_completion(folder):
    text = (folder / 'Run.out').read_text(encoding='utf-8-sig', errors='replace')
    require('Finished execution (code=0).' in text, f'Not completed: {folder}')
    require(not re.search(r'Finished execution \(code=[1-9]', text), 'Failed run log')
    for key, expected in (('Steps of simulation', 2000), ('Excluded particles', 0),
                          ('DTs adjusted to DtMin', 0), ('PART files', 11)):
        match = re.search(re.escape(key) + r'\.+:\s*(\d+)', text)
        require(match and int(match[1]) == expected, f'Unexpected {key}: {folder}')
    require('SlipMode="DBC vel=0"' in text, 'Actual mDBC condition is not the original Vel0')
    return {'steps': 2000, 'excluded_particles': 0, 'dtmin_adjustments': 0, 'frames': 11}


def inventory(folder):
    files = sorted((folder / 'data').glob('Part_[0-9]*.bi4'))
    require(len(files) == 11, f'Expected 11 native frames: {folder}')
    files += [folder / 'data/Part_Head.ibi4']
    return [{'path': str(p.resolve()), 'sha256': sha(p)} for p in files]


def baseline(backend, scenario):
    folder = LEGACY / 'runs' / f'new_release__{backend}__{scenario}'
    path = folder / 'run_metadata.json'
    metadata = json.loads(path.read_text(encoding='utf-8-sig'))
    require(metadata['executable_sha256'].lower() == LEGACY_SHA[backend], 'Not the original float release reference')
    require(metadata['passed'] and metadata['steps'] == 2000, 'Unaccepted legacy reference')
    for file, expected in metadata['input_sha256'].items():
        require(sha(file) == expected, f'Historical input changed: {file}')
    check_completion(folder)
    return folder, path, metadata


def verify_tools_and_sources(backends):
    diff = subprocess.run(['git', '-C', str(REPO), 'diff', '--name-only', CHECKPOINT,
                           '--', 'src/source', 'src/VS'], capture_output=True, text=True, check=True)
    changed = diff.stdout.strip().splitlines()
    require(set(changed) <= {'src/source/JPartsLoad4.cpp'},
            'Production source/project differs beyond the exact authorized loader safety patch:\n' + diff.stdout)
    exemptions = []
    if changed:
        loader = REPO / 'src/source/JPartsLoad4.cpp'
        require(sha(loader) == LOADER_SAFETY_SHA, 'Loader safety exception SHA differs')
        exemptions.append({'path': str(loader), 'sha256': LOADER_SAFETY_SHA,
                           'purpose': 'Authorized float-only restart validation, piece count and pressure mapping safety; not precision accumulation.'})
    require(not (REPO / 'src/source/FunPorePressure.h').exists(), 'Precision helper remains in production source')
    reader = json.loads(READER_RECORD.read_text(encoding='utf-8-sig'))
    require(sha(READER) == reader['executable_sha256'].lower(), 'Native reader differs from validated build')
    hashes = {}
    for backend in backends:
        name = EXES[backend]
        executable = REPO / 'bin/windows' / name
        actual = sha(executable)
        forbidden = {DOUBLE_SHA[backend]}
        high_low = CASE / 'tests/outputs/pore_double_baseline' / name
        if high_low.is_file():
            forbidden.add(sha(high_low))
        require(actual not in forbidden, f'{backend} executable is still a double/high-low build')
        hashes[backend] = actual
    return {'source_checkpoint': CHECKPOINT, 'tracked_source_project_diff': changed,
            'exact_source_exemptions': exemptions,
            'release_sha256': hashes, 'native_reader_sha256': sha(READER),
            'native_reader_record_sha256': sha(READER_RECORD)}


def export_native(folder, output, logfile):
    require(not output.exists(), f'Refusing existing native export: {output}')
    command = [str(READER), '--dir', str(folder / 'data'), '--out', str(output)]
    with logfile.open('xb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    require(result.returncode == 0 and (output / 'complete.txt').is_file(), f'Native export failed: {logfile}')
    return {'command': command, 'state_sha256': sha(output / 'state.csv'),
            'frames_sha256': sha(output / 'frames.csv')}


def read_native(folder):
    with (folder / 'frames.csv').open(encoding='utf-8', newline='') as stream:
        frames = list(csv.DictReader(stream))
    require(len(frames) == 11, 'Native frame count differs')
    for i, row in enumerate(frames):
        require(int(row['part']) == i and int(row['particle_count']) == 1040, 'Native particle/frame count differs')
        require((row['pressure_type'], row['reference_type'], row['residual_type']) == ('float', 'float', 'absent'),
                'Not original single-float pore state')
        require(row['pos_type'] == 'float3' and row['velocity_type'] == 'float3' and row['rhop_type'] == 'float',
                'Native position/velocity/density precision differs from old saved float state')
        require(row['sigma_kk_type'] == row['sigma_ij_type'] == 'float3' and row['fstype_type'] != 'absent',
                'Missing or changed native stress/free-surface fields')
    with (folder / 'state.csv').open(encoding='utf-8') as stream:
        require(stream.readline().strip().split(',') == COLUMNS, 'Native column schema differs')
        data = np.loadtxt(stream, delimiter=',', dtype=np.float64).reshape(11, 1040, len(COLUMNS))
    require(np.isfinite(data).all(), 'Nonfinite native state')
    times = np.array([float(r['time_s']) for r in frames])
    require(times[0] == 0 and np.all(np.diff(times) > 0), 'Invalid native times')
    require(np.array_equal(data[:, :, COL['id']], np.broadcast_to(np.arange(1040), (11, 1040))), 'Missing/duplicate ID')
    require(np.array_equal(data[:, :, COL['part']], np.broadcast_to(np.arange(11)[:, None], (11, 1040))), 'PART mismatch')
    require(np.array_equal(data[:, :, COL['time_s']], np.broadcast_to(times[:, None], (11, 1040))), 'Row/time mismatch')
    require(np.all(data[:, :, COL['residual_pa']] == 0), 'Unexpected residual')
    require(np.array_equal(data[:, :, COL['pressure_pa']], data[:, :, COL['stored_pressure_pa']]), 'Unexpected pressure reconstruction')
    return frames, times, data


def compare_native(old_path, new_path):
    old_frames, old_times, a = read_native(old_path)
    new_frames, new_times, b = read_native(new_path)
    require(old_frames == new_frames, 'Native frame metadata/types/times differ')
    require(np.array_equal(old_times, new_times), 'Actual native times differ; no interpolation permitted')
    metrics = {}
    for name in COLUMNS[3:]:
        old = np.ascontiguousarray(a[:, :, COL[name]])
        new = np.ascontiguousarray(b[:, :, COL[name]])
        delta = new - old
        metrics[name] = {'unequal_values': int(np.count_nonzero(old != new)),
                         'unequal_decoded_bits': int(np.count_nonzero(old.view(np.uint64) != new.view(np.uint64))),
                         'max_abs': float(np.max(np.abs(delta))), 'rms': float(np.sqrt(np.mean(delta * delta)))}
    passed = all(m['unequal_values'] == 0 and m['unequal_decoded_bits'] == 0 for m in metrics.values())
    return {'passed': passed, 'frames': 11, 'particles_per_frame': 1040, 'actual_times_s': old_times.tolist(),
            'same_backend': True, 'interpolation': False, 'absolute_tolerance': 0, 'relative_tolerance': 0,
            'comparison_scope': 'Exported native Pos, Vel, Rhop, Sigma_kk, Sigma_ij, PorePress, PorePress0, FSType; IDs/time/types checked. No claim about unsaved fields or whole BI4 byte identity.',
            'bitwise_definition': 'Finite saved float32 promoted exactly to float64 and printed with 17 digits; compare recovered float64 bits including signed zero.',
            'fields': metrics}


def run_one(backend, scenario, tag, tools):
    name = f'{tag}_{backend}_{scenario}'
    out = OUTPUT / name
    old_native = OUTPUT / (name + '_reference_native')
    record_path = LOG / (name + '.json')
    original, metadata_path, metadata = baseline(backend, scenario)
    original_inventory = inventory(original)
    command = list(metadata['command'])
    command[0] = str(REPO / 'bin/windows' / EXES[backend])
    command[-1] = str(out)
    record = {'name': name, 'source_checkpoint': CHECKPOINT, 'reference_directory': str(original),
              'reference_metadata_sha256': sha(metadata_path), 'reference_executable_sha256': metadata['executable_sha256'],
              'input_sha256': metadata['input_sha256'], 'original_native_inventory': original_inventory,
              'command': command, 'cwd': str(REPO / 'src'), 'tools': tools,
              'started_utc': datetime.now(timezone.utc).isoformat(), 'passed': False}
    print('START ' + name, flush=True)
    started = time.perf_counter()
    out.mkdir(parents=True)
    try:
        with (LOG / (name + '.solver.log')).open('xb') as stream:
            result = subprocess.run(command, cwd=REPO / 'src', stdout=stream, stderr=subprocess.STDOUT, timeout=300)
        record.update(process_exit_code=result.returncode, wall_s=time.perf_counter()-started)
        require(result.returncode == 0, 'Solver exit code is not zero')
        record['completion'] = check_completion(out)
        require(sha(command[0]) == tools['release_sha256'][backend], 'Executable changed while running')
        for file, expected in metadata['input_sha256'].items():
            require(sha(file) == expected, f'Historical input changed during run: {file}')
        record['reference_export'] = export_native(original, old_native, LOG / (name + '.reference_reader.log'))
        record['current_export'] = export_native(out, out / 'native', LOG / (name + '.reader.log'))
        require(inventory(original) == original_inventory, 'Historical native output changed')
        record['current_native_inventory'] = inventory(out)
        record['comparison'] = compare_native(old_native, out / 'native')
        record['passed'] = record['comparison']['passed']
    except Exception as error:
        record['error'] = str(error)
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save_new(record_path, record)
    print('DONE ' + name + ' ' + json.dumps({'passed': record['passed'], 'wall_s': record.get('wall_s'),
                                           'error': record.get('error')}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true', help='Read-only old-reference/input check; no source requirement or launches')
    group.add_argument('--run', action='store_true', help='After restored CPU/GPU builds, run the four short regressions serially')
    parser.add_argument('--tag', default='r1')
    parser.add_argument('--backend', nargs='+', choices=tuple(EXES), default=list(EXES))
    args = parser.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9_-]+', args.tag), 'Unsafe output tag')
    require(len(set(args.backend)) == len(args.backend), 'Duplicate backend selection')
    for backend in args.backend:
        for scenario in SCENARIOS:
            baseline(backend, scenario)
    if args.check:
        print('CHECK PASSED: selected original-float references and all recorded inputs exist and match; no solver launched.')
        return
    tools = verify_tools_and_sources(args.backend)
    summary_path = LOG / (args.tag + '_' + '_'.join(args.backend) + '_summary.json')
    targets = [summary_path]
    for backend in args.backend:
        for scenario in SCENARIOS:
            name = f'{args.tag}_{backend}_{scenario}'
            targets += [OUTPUT/name, OUTPUT/(name+'_reference_native')]
            targets += [LOG/(name+suffix) for suffix in ('.json', '.solver.log', '.reader.log', '.reference_reader.log')]
    require(not any(p.exists() for p in targets), 'Output/log exists; refusing every overwrite. Choose a new --tag.')
    LOG.mkdir(parents=True, exist_ok=True)
    records = [run_one(backend, scenario, args.tag, tools) for backend in args.backend for scenario in SCENARIOS]
    passed = all(r['passed'] for r in records)
    save_new(summary_path, {'passed': passed, 'source_checkpoint': CHECKPOINT,
             'purpose': 'Original-float rollback reproduction only; no physical accuracy or speedup claim.',
             'tools': tools, 'runs': [{'name': r['name'], 'passed': r['passed'],
                                     'record': str(LOG/(r['name']+'.json'))} for r in records]})
    print('SUMMARY ' + ('PASSED' if passed else 'FAILED'), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('RESTORE CHECK ERROR: ' + str(error), file=sys.stderr, flush=True)
        sys.exit(1)
