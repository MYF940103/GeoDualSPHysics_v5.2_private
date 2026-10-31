"""Review actual fresh-extraction nu smoke runs; never starts a solver."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import pandas as pd
import cryer_full_native_r1 as fn
from cryer_load_pair_r1 import bound

CASE = fn.CASE
TAG = 'cryer_nu_portable_r1'
EXTRACTED = fn.TESTS/'outputs/cryer_nu_portable_r1'


def main():
    check = fn.LOGS/(TAG+'.check.json'); csv = fn.FIGURES/(TAG+'_summary.csv')
    assert not check.exists() and not csv.exists(), 'Fresh review only'
    manifest_path = CASE/'support/cryer_nu_server_manifest_r1.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    package_check = fn.LOGS/'cryer_nu_package_r1.check.json'
    package = json.loads(package_check.read_text())
    assert package['package_consistency_passed'] and bound(manifest_path) == package['manifest']
    inputs = [bound(__file__), bound(package_check), bound(manifest_path)]
    for key in ['zip', 'checksum']:
        assert bound(package[key]['path']) == package[key]; inputs.append(package[key])
    entries = {e['entry']:e for e in manifest['files']}
    with zipfile.ZipFile(package['zip']['path']) as archive:
        assert len(archive.namelist()) == 19
        for entry in archive.namelist():
            root = bound(CASE/entry); extracted = bound(EXTRACTED/entry)
            assert root['sha256'] == extracted['sha256'] == hashlib.sha256(archive.read(entry)).hexdigest()
            if entry in entries:
                assert root['sha256'] == entries[entry]['sha256'] and root['bytes'] == entries[entry]['bytes']
            inputs.extend([root, extracted])
    assert manifest['verified_program_sha256'] == '652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096'
    full = json.loads(fn.CHECK.read_text()); sealed = {e['path'].lower():e for e in json.loads(fn.INPUTS.read_text())['inputs']}
    assert full['native_safety_passed'] and bound(fn.INPUTS)['sha256'] == full['inputs_manifest']['sha256']
    for path in [fn.READER, fn.READER_SOURCE, fn.FOLDER/'data/Part_0000.bi4']:
        b = bound(path); assert b == sealed[b['path'].lower()]; inputs.append(b)
    initial_control = fn.native(fn.FOLDER, 0)
    rows = []; runs = []
    for variant in manifest['variants']:
        stem = 'CaseCryerProblem_PR_release_nu'+variant['nu_tag']+'_r1'
        folder = EXTRACTED/(stem+'_smoke_out')
        receipt_path = folder/'execution_receipt_nu_r1.json'
        receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
        assert receipt['status'] == 'solver_exited_zero_pending_native_review'
        assert receipt['solver_exited_zero'] and not receipt['restart_used'] and receipt['mode'] == 'smoke'
        assert receipt['nu_tag'] == variant['nu_tag'] and receipt['selected_variant'] == variant
        assert len(receipt['stages']) == 2 and all(s['exit_code'] == 0 for s in receipt['stages'])
        assert receipt['expected_steps'] == 128 and receipt['expected_native_frames'] == 2
        assert '-tmax:0.0001220703125' in receipt['stages'][1]['argv']
        for stage in receipt['stages']:
            assert bound(stage['executable_before']['path']) == stage['executable_before'] == stage['executable_after']
        assert receipt['actual_runtime_before_solver'] == receipt['actual_runtime_after_solver']
        for b in receipt['actual_runtime_after_solver']:
            assert bound(b['path']) == b; inputs.append(b)
        for key in ['generated_xml', 'generated_initial_bi4', 'run_log']:
            assert bound(receipt[key]['path']) == receipt[key]; inputs.append(receipt[key])
        inputs.append(bound(receipt_path))
        xml = folder/(stem+'.xml'); root = ET.parse(xml).getroot()
        assert float(root.find('.//PRvs').get('value')) == variant['nu']
        p = fn.parameters(xml); assert p['dt'] == 2**-20 and p['end'] == float(variant['end_s'])
        assert p['TD'] == 2**-7 and p['ramp'] == 2**-8
        grid = np.array([0, 128]); times = grid*p['dt']
        runtext = (folder/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in runtext and re.search(r'Steps of simulation\.*:\s*128\s', runtext)
        assert 'PoreDarcySymmetricCorr="SymmetricSoilPair"' in runtext
        assert 'PoreCompressionSourceMode="PairDivergence"' in runtext
        cs = float(re.search(r'^Cs0=([^\r\n]+)', runtext, re.M)[1])
        assert np.isclose(cs, variant['expected_initial_soil_cs_m_s'], rtol=2e-7, atol=0)
        gpu = [line for line in runtext.splitlines() if '3050' in line]
        assert gpu, 'Record actual local selected device, not the target A6000'
        zero = fn.native(folder, 0); assert np.array_equal(zero.to_numpy(), initial_control.to_numpy())
        ctx = fn.context(zero)
        assert len(list((folder/'data').glob('Part_[0-9][0-9][0-9][0-9].bi4'))) == 2
        for part, a in [(0, zero), (1, fn.native(folder, 1))]:
            row, _, issues = fn.inspect(a, ctx, part, p, grid, times); assert not issues, issues
            row.update(nu_tag=variant['nu_tag'], nu=variant['nu']); rows.append(row)
        for path in folder.rglob('*'):
            if path.is_file(): inputs.append(bound(path))
        runs.append(dict(nu_tag=variant['nu_tag'], nu=variant['nu'], actual_gpu_lines=gpu,
            actual_steps=128, actual_end_s=float(times[-1]), native_frames=2, native_ids=37173,
            initial35_exact_to_retained_nu030=True, saved_native_safety_passed=True,
            actual_cs_m_s=cs, scalar_pore_budget_s=rows[-1]['pore_diffusion_dt_s'],
            observed_dterror_s=rows[-1]['dterror_s'], actual_execution_receipt=bound(receipt_path)))
    pd.DataFrame(rows).to_csv(csv, index=False, float_format='%.17g', mode='x')
    unique = {}
    for b in inputs:
        assert b['path'] not in unique or unique[b['path']] == b
        unique[b['path']] = b
    for b in unique.values(): assert bound(b['path']) == b
    fn.seal(check, dict(portable_smoke_passed=True, native_smoke_verified=True, runs=runs,
        independent_checked_frames=6, initial_exact_fields=35, initial_exact_frames=3,
        verified_input_files=len(unique), verified_input_bytes=sum(b['bytes'] for b in unique.values()),
        inputs=list(unique.values()), artifacts=[bound(csv)], full_run_started=False,
        physical_acceptance=False, full_half_validated=False, actual_A6000_tested=False,
        limits='128-step startup only: no drainage, closed equilibrium, Mandel peak or full-cycle accuracy. Final nu trajectories are not required to equal nu=.3. Execution receipt native flag intentionally remains false; this is the separate native review.'))
    print(json.dumps(dict(portable_smoke_passed=True, checked_frames=6, runs=runs), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--run', action='store_true')
    if p.parse_args().run: main()
    else: p.print_help()
