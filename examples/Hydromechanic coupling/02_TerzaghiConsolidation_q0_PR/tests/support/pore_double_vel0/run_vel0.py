"""Serial formal-Vel0 q0 regression: retained patch/double, dt/dt2.

Reuses historical GenCase particle/normal data after checking the casedef,
hydromechanics and parameters against the formal precision Def. XML text format
is preserved; only four time controls and optional timeout override are changed.
Never overwrites existing inputs, outputs, or records. No production code edits.
"""
import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

CASE = Path(__file__).resolve().parents[3]
TESTS = CASE / 'tests'
REPO = next(p for p in CASE.parents if (p / 'src/VS').is_dir())
CONFIG = TESTS / 'configs/pore_double_vel0'
OUT = TESTS / 'outputs/pore_double_vel0'
LOG = TESTS / 'logs/pore_double_vel0'
PREFIX = CASE / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_out/CaseTerzaghiConsolidation_q0_PR_full_k1em4'
FORMAL = CASE / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_Def.xml'
EXPECTED = {
    'baseline': 'A2CD2B1023F6487EAC3F7D7185F02175494FE680B238C558C478B71E29B6EFF6',
    'current': '95683EA87702A50CC8246B7C32C7DE9C2B203435985A373378A6FCDDA7347DBD',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def normalized(value):
    try:
        return str(Decimal(value).normalize())
    except InvalidOperation:
        return value.strip()


def signature(node):
    if node is None:
        return None
    attrs = tuple(sorted((k, normalized(v)) for k, v in node.attrib.items()
                         if k not in ('comment', 'units_comment', '_rem')))
    return node.tag, attrs, (node.text or '').strip(), tuple(signature(c) for c in node if c.tag != 'timeout')


def prepare(event=False, reuse=False):
    for folder in (CONFIG, OUT, LOG):
        folder.mkdir(parents=True, exist_ok=True)
    original = PREFIX.with_suffix('.xml')
    data = PREFIX.with_suffix('.bi4')
    normals = PREFIX.with_name(PREFIX.name + '_Normals.nbi4')
    generated, formal = ET.parse(original).getroot(), ET.parse(FORMAL).getroot()
    checks = {}
    for section in ('casedef', 'execution/parameters', 'execution/special'):
        checks[section] = signature(generated.find(section)) == signature(formal.find(section))
    if not all(checks.values()):
        raise RuntimeError(f'Generated input differs from formal precision Def: {checks}')
    assert generated.find("execution/parameters/parameter[@key='SlipMode']").get('value') == '1'
    hashes = {str(p): digest(p) for p in (original, data, normals, FORMAL)}
    configurations = []
    source = original.read_bytes().decode('utf-8')
    duration, tout, frames = ('0.03', '0.00049999', 61) if event else ('0.2', '0.001', 201)
    for dt, label in (('0.00001', 'dt1em5'), ('0.000005', 'dt5em6')):
        if event:
            label += '_event'
        directory = CONFIG / label
        if not reuse:
            directory.mkdir(exist_ok=False)
        target = directory / PREFIX.name
        text = source
        for key, value in {'DtIni': dt, 'DtFixed': dt, 'TimeMax': duration, 'TimeOut': tout}.items():
            pattern = rf'(<parameter\s+key="{key}"\s+value=")[^"]*(")'
            text, count = re.subn(pattern, lambda m: m[1] + value + m[2], text)
            assert count == 1, (key, count)
        text, timeout_count = re.subn(r'(?ms)^[\t ]*<timeout>.*?</timeout>\r?\n', '', text)
        # These are generated temporary test inputs, not formal XML replacements.
        if reuse:
            assert target.with_suffix('.xml').read_bytes() == text.encode('utf-8'), 'Existing config differs'
            assert digest(target.with_suffix('.bi4')) == digest(data)
            assert digest(target.with_name(target.name + '_Normals.nbi4')) == digest(normals)
        else:
            with target.with_suffix('.xml').open('xb') as stream:
                stream.write(text.encode('utf-8'))
            shutil.copy2(data, target.with_suffix('.bi4'))
            shutil.copy2(normals, target.with_name(target.name + '_Normals.nbi4'))
        configurations.append(dict(label=label, dt=float(dt), prefix=target,
                                   duration=float(duration), tout=float(tout), expected_frames=frames,
                                   xml_sha256=digest(target.with_suffix('.xml')),
                                   removed_timeout_blocks=timeout_count))
    return hashes, checks, configurations


def run_one(build, config, hashes, checks):
    name = f'q0_vel0_{build}_{config["label"]}'
    directory = OUT / name
    directory.mkdir(exist_ok=False)
    exe = (TESTS / 'outputs/pore_double_baseline' if build == 'baseline' else REPO / 'bin/windows') / 'DualSPHysics5.2CPU_win64.exe'
    assert digest(exe) == EXPECTED[build], f'Unexpected {build} executable'
    assert digest(config['prefix'].with_suffix('.xml')) == config['xml_sha256']
    steps = round(config['duration'] / config['dt'])
    # -mdbc, as used by the formal BAT, selects DBC vel=0. Never use -mdbc_noslip.
    command = [str(exe), '-cpu', '-ompthreads:4', '-mdbc', '-stable', '-symplectic',
               f'-nsteps:{steps}', '-nortimes:1', '-sv:binx', '-svextraparts:1',
               '-dirdataout', 'data', '-svres', str(config['prefix']), str(directory)]
    record = dict(name=name, build=build, dt=config['dt'], duration_s=config['duration'], time_out_s=config['tout'],
                  command=command, executable_sha256=EXPECTED[build],
                  input_sha256=hashes, formal_physics_checks=checks,
                  shared_generated_xml=str(config['prefix'].with_suffix('.xml')),
                  generated_xml_sha256=config['xml_sha256'],
                  removed_timeout_blocks=config['removed_timeout_blocks'],
                  position_output_policy='Unchanged CLI -svextraparts:1: PART0 Pos float; PART>0 Posd double via JSph::SavePartData/JDsExtraDataSave::CheckSave. No -saveposdouble override.',
                  requested_steps=steps, passed=False)
    print(f'START {name}', flush=True)
    try:
        start = time.perf_counter()
        with (LOG / (name + '.solver.log')).open('xb') as log:
            result = subprocess.run(command, cwd=REPO / 'src', stdout=log, stderr=subprocess.STDOUT, timeout=3600)
        record['wall_seconds'] = time.perf_counter() - start
        record['solver_exit_code'] = result.returncode
        assert result.returncode == 0, 'Solver failed; inspect solver.log'
        runtext = (directory / 'Run.out').read_text(encoding='utf-8-sig', errors='replace')
        for key, pattern in {
            'steps': r'Steps of simulation\.+:\s*(\d+)',
            'excluded_particles': r'Excluded particles\.+:\s*(\d+)',
            'dt_min_adjustments': r'DTs adjusted to DtMin\.+:\s*(\d+)'
        }.items():
            match = re.search(pattern, runtext)
            record[key] = int(match[1]) if match else None
        slip = re.search(r'^\s*SlipMode="([^"]+)"', runtext, re.MULTILINE)
        record['actual_slip_mode'] = slip[1] if slip else None
        record['actual_vel0_confirmed'] = record['actual_slip_mode'] == 'DBC vel=0'
        assert record['actual_vel0_confirmed'], 'Run did not use formal Vel0'
        assert record['steps'] == steps, (record['steps'], steps)
        assert record['excluded_particles'] == record['dt_min_adjustments'] == 0
        record['inputs_unchanged'] = all(digest(Path(p)) == h for p, h in hashes.items())
        assert record['inputs_unchanged']
        records = re.findall(r'^Part_(\d+)\s+([\d.Ee+-]+)\s+(\d+)', runtext, re.MULTILINE)
        record['actual_frames'] = [{'part': 0, 'time_s': 0., 'step': 0}] + [
            {'part': int(p), 'time_s': float(t), 'step': int(s)} for p, t, s in records]
        record['bi4_frame_count'] = len(list((directory / 'data').glob('Part_*.bi4')))
        assert record['bi4_frame_count'] == len(record['actual_frames']) == config['expected_frames']
        particles = directory / 'particles'
        particles.mkdir()
        variables = '-vars:-all,+idp,+vel,+rhop,+sigma_kk,+sigma_ij,+kplastic,+fstype,+porepress,+porepress0,+excessporepress'
        conversion = [str(REPO / 'bin/windows/PartVTK_win64.exe'), '-dirin', str(directory / 'data'),
                      '-savevtk', str(particles / 'PartAll'), '-onlytype:+all', variables]
        record['conversion_command'] = conversion
        with (LOG / (name + '.vtk.log')).open('xb') as log:
            result = subprocess.run(conversion, cwd=REPO / 'src', stdout=log, stderr=subprocess.STDOUT, timeout=300)
        record['conversion_exit_code'] = result.returncode
        assert result.returncode == 0
        record['vtk_frame_count'] = len(list(particles.glob('*.vtk')))
        assert record['vtk_frame_count'] == config['expected_frames']
        record['passed'] = True
    finally:
        save(LOG / (name + '.json'), record)
    print(f'DONE {name}: {steps} steps, {config["expected_frames"]} frames, Vel0', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event', action='store_true', help='0.03 s event diagnostic; output deadlines just before 0.5 ms grids')
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--first-only', action='store_true', help='Run the first event case before native timestamp verification')
    choice.add_argument('--remaining', action='store_true', help='Reuse unchanged event configs and run the remaining three cases')
    args = parser.parse_args()
    if (args.first_only or args.remaining) and not args.event:
        parser.error('--first-only/--remaining require --event')
    hashes, checks, configs = prepare(args.event, args.remaining)
    index = 0
    for config in configs:
        for build in ('baseline', 'current'):
            if args.remaining and index == 0:
                original = json.loads((LOG / f'q0_vel0_{build}_{config["label"]}.json').read_text(encoding='utf-8'))
                assert original['passed'] and original['generated_xml_sha256'] == config['xml_sha256']
                index += 1
                continue
            run_one(build, config, hashes, checks)
            index += 1
            if args.first_only:
                return


if __name__ == '__main__':
    main()
