"""Offline verification of the already executed portable two-frame startup; never runs a solver."""
import hashlib
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
from cryer_start_r1 import CASE, TESTS, native, bound, utc
from cryer_preload_peak_r1 import inspect, prefix_compare


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def check_binding(path, record):
    value = bound(path)
    assert value['bytes'] == record['bytes'] and value['sha256'] == record['sha256'], str(path)


def normalized(root):
    for node in root.iter():
        node.attrib.pop('comment', None)
        if node.text is not None: node.text = node.text.strip() or None
        node.tail = None
    return ET.tostring(root)


def main():
    target = TESTS/'logs/cryer_server_review_r1.check.json'
    assert not target.exists(), 'Fresh offline receipt only; never overwrite evidence'
    manifest_path = CASE/'support/cryer_server_manifest_r1.json'
    manifest = read(manifest_path)
    bundle = CASE/'Cryer_symC_nu030_Windows_RTXA6000_r1.zip'
    extracted = TESTS/'outputs/cryer_server_smoke_r1'
    output = extracted/'CaseCryerProblem_PR_symc_nu030_smoke_out'
    control = TESTS/'outputs/cryer_darcy_switch_native_r1_gpu_on'
    sources = [bound(p) for p in [Path(__file__), manifest_path, bundle,
        TESTS/'logs/cryer_darcy_switch_native_review_r1.check.json']]
    assert manifest['implementation_regression_passed'] and not manifest['full_cycle_accepted']
    assert manifest['source_head_supplied_by_packager'] == '7c0006ea9d90571b72a5d691c652577b025f5b83'
    with zipfile.ZipFile(bundle) as archive:
        expected = {row['entry'] for row in manifest['files']} | {'support/cryer_server_manifest_r1.json'}
        assert len(archive.namelist()) == len(expected) == 16 and set(archive.namelist()) == expected
        assert archive.read('support/cryer_server_manifest_r1.json') == manifest_path.read_bytes()
        for row in manifest['files']:
            assert hashlib.sha256(archive.read(row['entry'])).hexdigest() == row['sha256']
            check_binding(Path(row['path']), row)
            check_binding(extracted/row['entry'], row)
    assert (extracted/'support/cryer_server_manifest_r1.json').read_bytes() == manifest_path.read_bytes()
    formal_path = CASE/manifest['formal_input']; formal = ET.parse(formal_path).getroot()
    original = ET.parse(TESTS/'configs/cryer_darcy_switch_native_r1_gpu_on_Def.xml').getroot()
    schedule = formal.find('./execution/special/timeout')
    rates = [(float(n.get('time')), float(n.get('timeout'))) for n in schedule]
    assert rates == [(0., 2.**-13), (2.**-7, float(12753/14000000))]
    dt = float(formal.find('.//parameter[@key="DtFixed"]').get('value'))
    end = float(formal.find('.//parameter[@key="TimeMax"]').get('value'))
    assert dt == 2.**-21 and end == 1926740*dt
    assert float(formal.find('.//parameter[@key="TimeOut"]').get('value')) == rates[1][1]
    formal.find('./execution/special').remove(schedule)
    for key in ['TimeMax', 'TimeOut']:
        formal.find('.//parameter[@key="'+key+'"]').set('value', original.find('.//parameter[@key="'+key+'"]').get('value'))
    assert normalized(formal) == normalized(original), 'An unreviewed physical input changed'
    # Expected JDsOutputTime events, quantized upward by the unchanged fixed-step loop.
    nominal = np.r_[np.arange(65)*2.**-13, 2.**-7+np.arange(1,1001)*(12753/14000000)]
    expected_times = np.ceil(nominal/dt)*dt
    assert len(np.unique(expected_times)) == 1065 and expected_times[-1] == end
    assert np.array_equal(expected_times[:65], np.arange(65)*2.**-13)
    assert np.all(expected_times >= nominal) and np.max(expected_times-nominal) < dt
    stdout = TESTS/'logs/cryer_server_smoke_r1.stdout.log'
    stderr = TESTS/'logs/cryer_server_smoke_r1.stderr.log'
    text = (output/'Run.out').read_text(errors='replace')
    assert 'Finished execution (code=0)' in text and 'Steps of simulation..............: 256' in text
    assert 'PoreDarcySymmetricCorr="SymmetricSoilPair"' in text and 'NVIDIA GeForce RTX 3050' in text
    assert 'Calculation finished.' in stdout.read_text(errors='replace') and stderr.stat().st_size == 0
    assert len(list((output/'data').glob('Part_*.bi4'))) == 2
    initial = native(output, 0); rows, pairs = [], []
    assert np.array_equal(initial.id, np.arange(8, 37181))
    receipt = read(TESTS/'logs/cryer_darcy_switch_native_r1_gpu_on.receipt.json')
    completion = read(receipt['sealed_completion']['path'])
    for part in range(2):
        new = initial if part == 0 else native(output, part)
        rows.append(inspect(new, initial, part))
        retained = control/'data'/('Part_%04d.bi4'%part)
        check_binding(retained, next(r for r in completion['outputs'] if r['path'] == str(retained)))
        pair = prefix_compare(new, native(control, part), part)
        assert pair['all_35_columns0ulp'] and not pair['differences']
        pairs.append(pair)
    sources += [bound(p) for p in [formal_path, CASE/manifest['formal_bat'], stdout, stderr,
        Path(receipt['sealed_completion']['path'])]]
    result = dict(utc=utc(), portable_startup_passed=True, package_integrity_passed=True,
        formal_physics_unchanged_from_verified_on=True, zip_entries_checked=16,
        manifest=bound(manifest_path), bundle=bound(bundle), source_links=sources,
        full_run_expected_steps=1926740, full_run_expected_frames=1065,
        schedule_checked_by_source_and_clock_arithmetic=True, actual_full_history_checked=False,
        startup_native_rows=rows, startup_native_pairs=pairs,
        startup_program_reported_exit_code=0, startup_wrapper_exit_code_directly_observed=False,
        wrapper_metadata_limit='The PowerShell Start-Process handle returned null ExitCode after WaitForExit. The outer diagnostic assertion rejected that missing value; it was not a solver rejection. Preserved Run.out reports code0 and BAT reached its success-only branch. No completed physical solver was rerun.',
        existing_output_refusal_exit_code=1,
        existing_output_refusal_observed_at='2026-10-30T12:11:58.1862106+09:00',
        refusal_did_not_launch_a_solver=True,
        outputs=[bound(p) for p in sorted(output.rglob('*')) if p.is_file()],
        solver_started_by_this_review=False, full_cycle_accepted=False,
        server_hardware_accepted=False, physical_acceptance=False)
    with target.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(str(target))


if __name__ == '__main__':
    main()
