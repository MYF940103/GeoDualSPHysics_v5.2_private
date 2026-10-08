"""Check a real new double PART through solver restart and initial output.

Does not claim full restart trajectory equivalence: the one-step run is only
needed to complete the executable; comparison uses the initial re-saved frame.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
import run_regression as common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['cpu', 'gpu'], required=True)
    parser.add_argument('--seed', action='store_true', help='Generate a 0.02 s q0 checkpoint with mDBC extra data first')
    parser.add_argument('--verify-only', action='store_true', help='Recheck existing outputs without running the solver')
    args = parser.parse_args()
    backend = args.backend
    part = 1 if args.seed else 10
    name = f'q0_restart_current_{backend}_part{part:04d}'
    source_name = f'q0_checkpoint_current_{backend}' if args.seed else f'q0_current_{backend}_dt1e-05_s0'
    output = common.OUT / name
    if args.verify_only:
        native_result = common.LOG / (name + '.native_verify.json')
        command = [str(common.NATIVE_HARNESS), '--compare-parts', str(common.OUT / source_name / 'data'),
                   str(part), str(output / 'data'), '0', '--json', str(native_result)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(f'Native checkpoint comparison failed: {result.stdout} {result.stderr}')
        print(native_result.read_text(encoding='utf-8'))
        return
    if output.exists():
        raise RuntimeError(f'Refusing overwrite: {output}')
    output.mkdir()
    source_data = common.OUT / source_name / 'data'
    generated = common.CONFIG / f'q0_current_{backend}_dt1e-05_s0' / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4'
    executable = common.REPO / 'bin/windows' / ('DualSPHysics5.2CPU_win64.exe' if backend == 'cpu' else 'DualSPHysics5.2_GEO_win64.exe')
    command = [str(executable), '-' + backend, '-mdbc_noslip', '-stable', '-symplectic']
    if backend == 'cpu':
        command += ['-ompthreads:1']
    if args.seed:
        seed_dir = common.OUT / source_name
        seed_dir.mkdir(exist_ok=False)
        seed = command + ['-tmax:0.02', '-tout:0.01', '-nsteps:2000', '-nortimes:1',
                          '-sv:binx', '-svextraparts:1', '-dirdataout', 'data', '-svres', str(generated), str(seed_dir)]
        with (common.LOG / (source_name + '.solver.log')).open('xb') as log:
            seed_result = subprocess.run(seed, cwd=common.REPO / 'src', stdout=log, stderr=subprocess.STDOUT, timeout=300)
        common.save(common.LOG / (source_name + '.json'), dict(command=seed, exit_code=seed_result.returncode))
        if seed_result.returncode:
            raise RuntimeError('Checkpoint seed run failed')
    command += [f'-partbegin:{part}:0', str(source_data), '-tmax:0.00001', '-tout:0.00001',
                '-nsteps:1', '-nortimes:1', '-sv:binx', '-dirdataout', 'data', '-svres',
                str(generated), str(output)]
    record = dict(command=command, executable_sha256=common.digest(executable),
                  checkpoint_sha256=common.digest(source_data / f'Part_{part:04d}.bi4'), passed=False)
    with (common.LOG / (name + '.solver.log')).open('xb') as log:
        result = subprocess.run(command, cwd=common.REPO / 'src', stdout=log,
                                stderr=subprocess.STDOUT, timeout=120)
    record['solver_exit_code'] = result.returncode
    if result.returncode:
        common.save(common.LOG / (name + '.json'), record)
        raise RuntimeError(f'Restart solver failed, code {result.returncode}')
    native_result = common.LOG / (name + '.native.json')
    compare = [str(common.NATIVE_HARNESS), '--compare-parts', str(source_data), str(part),
               str(output / 'data'), '0', '--json', str(native_result)]
    result = subprocess.run(compare, capture_output=True, text=True, timeout=60)
    record['comparison_command'] = compare
    record['comparison_exit_code'] = result.returncode
    if native_result.exists():
        record['comparison'] = json.loads(native_result.read_text(encoding='utf-8'))
    record['passed'] = result.returncode == 0
    common.save(common.LOG / (name + '.json'), record)
    if not record['passed']:
        raise RuntimeError(f'Native pressure bits changed: {result.stdout} {result.stderr}')
    print(json.dumps(record['comparison'], indent=2))


if __name__ == '__main__':
    main()
