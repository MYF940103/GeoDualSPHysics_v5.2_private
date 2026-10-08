"""One exact-command CPU q0 baseline repeat to measure solver determinism.

Reuses the already-generated baseline XML and executable. Only the output
directory changes; existing baseline data and formal case files are untouched.
"""
import json
import subprocess
import sys
import time

import numpy as np

sys.dont_write_bytecode = True
import run_regression as common


def main():
    original = 'q0_baseline_cpu_dt1e-05_s0'
    name = 'q0_baseline_cpu_repeat'
    source_record = common.LOG / (original + '.json')
    before = json.loads(source_record.read_text(encoding='utf-8'))
    output = common.OUT / name
    output.mkdir(exist_ok=False)
    command = before['command'].copy()
    command[-1] = str(output)
    assert common.digest(common.Path(command[0])) == before['executable_sha256']
    assert common.digest(common.Path(command[-2]).with_suffix('.xml')) == before['generated_xml_sha256']
    record = dict(original_record=str(source_record), original_record_sha256=common.digest(source_record),
                  command=command, only_command_change='Final output directory',
                  original_executable_sha256=before['executable_sha256'], passed=False)
    started = time.perf_counter()
    with (common.LOG / (name + '.solver.log')).open('xb') as log:
        result = subprocess.run(command, cwd=common.REPO / 'src', stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    record['solver_exit_code'] = result.returncode
    record['wall_seconds_not_performance_measure'] = time.perf_counter() - started
    if result.returncode:
        common.save(common.LOG / (name + '.json'), record)
        raise RuntimeError('Repeat solver failed')
    times_before = common.VTK.read_run_log(common.OUT / original / 'Run.out')
    times_after = common.VTK.read_run_log(output / 'Run.out')
    assert set(times_before) == set(times_after)
    assert all(times_before[i]['time'] == times_after[i]['time'] and
               times_before[i]['logged_step'] == times_after[i]['logged_step'] for i in times_before)
    record['actual_times_steps_match'] = True
    fields = {k: dict(bit_mismatches=0, max_abs_difference_pa=0.)
              for k in ('pressure_pa', 'reference_pa', 'stored_pressure_pa', 'residual_pa')}
    frame_count = len(before['frames'])
    for index in range(frame_count):
        b = common.native_state(original, index)
        a = common.native_state(name, index)
        assert np.array_equal(b['time_s'], a['time_s'])
        for key, stats in fields.items():
            stats['bit_mismatches'] += int(np.count_nonzero(a[key].copy().view('u8') != b[key].copy().view('u8')))
            stats['max_abs_difference_pa'] = max(stats['max_abs_difference_pa'], float(np.max(np.abs(a[key] - b[key]))))
    record['frames'] = frame_count
    record['particle_count_per_frame'] = 1040
    record['fields'] = fields
    record['passed'] = all(s['bit_mismatches'] == 0 for s in fields.values())
    common.save(common.LOG / (name + '.json'), record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if not record['passed']:
        raise RuntimeError('Baseline repeat is not bitwise deterministic')


if __name__ == '__main__':
    main()
