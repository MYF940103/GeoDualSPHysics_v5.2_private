"""Offline native 2x2 HG/SPR audit; no solver, chart, queue or source mutation."""
from concurrent.futures import ThreadPoolExecutor
import ast
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, utc, write_json
from lian_opt3_review_r1 import verify_bindings
from lian_spr_half_review_r1 import metrics
from lian_hg_short_r1 import hg_stats
from lian_hg_prefix_r2 import compare_prefix

TAG = 'lian_hg3_review_r1'
RUNS = {
    'H0S0': ('lian_spr_mix_r1_off_3s', 0., 0, 'lian_spr_mix_r1_off_smoke'),
    'H0S1': ('lian_spr_mix_r1_on_3s', 0., 1, 'lian_spr_mix_r1_on_smoke'),
    'H1S0': ('lian_hg3_r2_spr0_3s', .1, 0, 'lian_hg3_r1_spr0_smoke'),
    'H1S1': ('lian_hg3_r2_spr1_3s', .1, 1, 'lian_hg_short_r1_on_c'),
}
EFFECTS = {
    'HG_at_SPR0': {'H1S0': 1, 'H0S0': -1},
    'HG_at_SPR1': {'H1S1': 1, 'H0S1': -1},
    'SPR_at_HG0': {'H0S1': 1, 'H0S0': -1},
    'SPR_at_HG1': {'H1S1': 1, 'H1S0': -1},
    'interaction': {'H1S1': 1, 'H1S0': -1, 'H0S1': -1, 'H0S0': 1},
}


def verify_historical_inputs(state):
    """Verify old hashes at retained files, never rewrite their canonical paths."""
    records = []
    for entry in state['inputs']:
        current = bound(entry['path'])
        if current['sha256'] == entry['sha256'] and current['bytes'] == entry['bytes']:
            records.append(dict(original=entry, verified=current, location='original'))
        else:
            retained = TESTS/'outputs/lian_hg_np_control_r1'/Path(entry['path']).name
            actual = bound(retained)
            assert actual['sha256'] == entry['sha256'] and actual['bytes'] == entry['bytes'], entry['path']
            records.append(dict(original=entry, verified=actual, location='retained_old_build_or_source',
                current_canonical=current, canonical_is_not_the_old_control=True))
    for snapshot in state['local_program_snapshots']:
        verify_bindings([snapshot['retained']])
        assert snapshot['source']['sha256'] == snapshot['retained']['sha256']
    return records


def config_signature(path, xi, spr):
    tree = ET.parse(path)
    pars = {e.attrib['key']: e.attrib['value'] for e in tree.findall('.//execution/parameters/parameter')}
    assert float(pars['SoilHourglassXi']) == xi and int(pars['SoilBoundaryDerivativeSPR']) == spr
    assert float(pars['DtIni']) == float(pars['DtFixed']) == 1e-5
    assert float(pars['TimeMax']) == 3 and float(pars['TimeOut']) == .05
    assert pars['SoilStressRateGradCorr'] == '1' and pars['SoilDamping'] == '1'
    assert float(pars['SoilDampingCoef']) == .04 and pars['SavePosDouble'] == '1'
    assert pars['Boundary'] == '2' and pars['StepAlgorithm'] == '2' and pars['Shifting'] == '0'
    assert {int(e.attrib['mkbound']): int(e.attrib['slipmode']) for e in tree.findall('.//mdbcslip/bound')} == {0: 3, 1: 2, 2: 3}
    planes = tree.findall('.//initialize/boundnormal_plane')
    assert len(planes) == 3 and {int(e.attrib['mkbound']) for e in planes} == {0, 1, 2}
    hydro = tree.find('.//hydromechanics')
    for tag, value in [('HydroMech', 1), ('HydraulicConductivity', .001), ('Porosity', .4),
        ('HydroMechTopLoadMode', 4), ('HydroMechTopLoadQ0', 10000),
        ('HydroMechTopLoadRampTime', 1), ('HydroMechDrainage', 1), ('HydroMechDrainageStartTime', 1)]:
        assert float(hydro.find(tag).attrib['value']) == value, tag
    def canonical(element):
        attrs = {k: v for k, v in element.attrib.items() if k not in ['comment', 'units_comment', '_rem']}
        if element.tag == 'parameter' and attrs.get('key') in ['SoilHourglassXi', 'SoilBoundaryDerivativeSPR']:
            attrs['value'] = 'FACTOR'
        elif element.tag == 'parameter' and attrs.get('key') in ['DtIni', 'DtFixed', 'TimeMax', 'TimeOut']:
            # Prepared files spell the same binary64 numbers as .00001/0.00001, 3/3.0 and .05/0.05.
            attrs['value'] = float(attrs['value']).hex()
        return element.tag, tuple(sorted(attrs.items())), (element.text or '').strip(), tuple(canonical(e) for e in element)
    return canonical(tree.getroot())


def verify_saved_row(row, saved, index):
    for col in saved.columns:
        actual, expected = row[col], saved[col].iloc[index]
        assert (actual is None and pd.isna(expected)) or actual == expected, (index, col, actual, expected)


def main():
    receipt = TESTS/'logs'/(TAG+'.check.json')
    assert not receipt.exists()
    for suffix in ['history', 'summary', 'effects', 'prefix']:
        assert not (TESTS/'figures'/(TAG+'_'+suffix+'.csv')).exists()
    old_path = TESTS/'logs/lian_spr_mix_r1.status.json'
    new_path = TESTS/'logs/lian_hg3_r2.status.json'
    old, new = [json.loads(p.read_text()) for p in [old_path, new_path]]
    assert old['status'] == 'pair_completed_pending_review'
    assert new['status'] == 'matrix_3s_passed_pending_review' and len(new['runs']) == 2
    print('Verify frozen current inputs', flush=True)
    verify_bindings(new['inputs'])
    print('Verify historical retained inputs', flush=True)
    old_bindings = verify_historical_inputs(old)
    source_paths = [Path(__file__), old_path, new_path, READER,
        TESTS/'scripts/lian_hg_prefix_r2.py', TESTS/'scripts/lian_hg_short_r1.py',
        TESTS/'scripts/lian_release_r1.py', TESTS/'scripts/lian_spr_half_review_r1.py',
        TESTS/'scripts/lian_mirror_review_r1.py', TESTS/'scripts/lian_opt3_review_r1.py',
        CASE/'support/postprocess_lian_release.py']
    source_paths += [REPO/'src/source'/n for n in ['JSphCpuSingle.cpp', 'JSphGpuSingle.cpp',
        'JSphHourglassCpu.cpp', 'JSphHourglassCpu.h', 'JSphHourglassGpu.cpp',
        'JSphHourglassGpu_ker.cu', 'JSphHourglassGpu_ker.h']]
    sources = [bound(p) for p in source_paths]
    command = "@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'DualSPHysics|python|cmd'} | Select-Object ProcessId,ParentProcessId,Name,CommandLine) | ConvertTo-Json -Depth 3 -Compress"
    raw_processes = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', command],
        creationflags=subprocess.CREATE_NO_WINDOW)
    processes = json.loads(raw_processes.decode('utf8', errors='replace'))
    if isinstance(processes, dict): processes = [processes]
    active_owned = [p for p in processes if p.get('Name', '').lower().startswith('dualsphysics') and
        any(name in (p.get('CommandLine') or '') for name, _, _, _ in RUNS.values())]
    assert not active_owned, active_owned
    # Only scoped ownership observations are retained; unrelated command lines are not evidence.
    processes = [dict(ProcessId=p['ProcessId'], ParentProcessId=p['ParentProcessId'], Name=p['Name'])
        for p in processes if any(name in (p.get('CommandLine') or '') for name, _, _, _ in RUNS.values())]
    manifests = {}; signature = None; saved = {}; saved_prefix = {}; runtime = {}
    for key, (name, xi, spr, reference) in RUNS.items():
        print('Verify output hashes/configuration', key, flush=True)
        path = TESTS/'logs'/(name+'.run.json'); m = json.loads(path.read_text())
        state = new if xi else old
        assert m == next(r for r in state['runs'] if r['name'] == name)
        assert m['passed'] and m['owned_exited'] and m['exit_code'] == 0 and m['checked_frames'] == 61
        assert abs(m['actual_final_time_s']-3) < 2e-5
        verify_bindings(m['outputs']+m['artifacts']); sources.append(bound(path)); manifests[key] = m
        config = TESTS/'configs'/(name+'_Def.xml'); current_signature = config_signature(config, xi, spr)
        if signature is None: signature = current_signature
        else: assert current_signature == signature, ('Unexpected XML difference', name)
        sources.append(bound(config))
        text = (TESTS/'outputs'/name/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text and 'RTX 3050' in text
        for mk, mode in [(0, 'Free slip'), (1, 'No-slip'), (2, 'Free slip')]:
            assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode, text)
        if spr: assert 'SPR stationary wall planes (one per mk): 3' in text
        if xi:
            runtime[key] = hg_stats(text); assert runtime[key] == m['hg_stats']
        saved[key] = pd.read_csv(TESTS/'figures'/(name+'_history.csv'), float_precision='round_trip')
        saved_prefix[key] = pd.read_csv(TESTS/'figures'/(name+'_prefix.csv'), float_precision='round_trip')
        assert len(saved[key]) == 61 and len(saved_prefix[key]) == 4
        rp = TESTS/'logs'/(reference+'.run.json'); reference_manifest = json.loads(rp.read_text())
        assert reference_manifest['passed'] and reference_manifest['owned_exited'] and reference_manifest['exit_code'] == 0
        verify_bindings(reference_manifest['outputs']+reference_manifest['artifacts']); sources.append(bound(rp))
    history = []; effects = []; prefixes = []; snapshots = []; origin = None
    metric_deltas = ['paper_A_pressure_pa', 'paper_B_pressure_pa', 'pressure_mean_pa', 'pressure_min_pa',
        'pressure_max_pa', 'paper_A_settlement_mm', 'paper_B_settlement_mm', 'total_sigma_zz_rms_pa',
        'left_normal_max_mm', 'right_normal_max_mm', 'bottom_normal_max_mm', 'bottom_tangent_max_mm', 'vmax_m_s']
    with ThreadPoolExecutor(max_workers=4) as pool:
        for part in range(61):
            arrays = dict(zip(RUNS, pool.map(lambda value: native(TESTS/'outputs'/value[0], part), RUNS.values())))
            if origin is None:
                origin = arrays['H0S0']; assert origin.id.nunique() == 20301
                for a in arrays.values(): assert np.array_equal(a[['id', 'x', 'y', 'z']], origin[['id', 'x', 'y', 'z']])
            rows = {}; time_s = float(arrays['H0S0'].time_s.iloc[0]); step = int(arrays['H0S0'].saved_step.iloc[0])
            for key, a in arrays.items():
                assert float(a.time_s.iloc[0]) == time_s and int(a.saved_step.iloc[0]) == step
                row = metrics(a, origin, part, 1e-5)
                verify_saved_row(row, saved[key], part)
                row.update(run=key, output_name=RUNS[key][0], hg_xi=RUNS[key][1], spr=RUNS[key][2],
                    pressure_rms_pa=float(np.sqrt(np.mean(a.pressure**2))), saved_step=step,
                    dterror_s=float(a.dterror_s.iloc[0]))
                history.append(row); rows[key] = row
                if part in [10, 20, 60]: snapshots.append(row.copy())
                if part <= 3:
                    b = native(TESTS/'outputs'/RUNS[key][3], part*10)
                    shared = float(b.time_s.iloc[0]) == time_s and int(b.saved_step.iloc[0]) == step
                    p = dict(run=key, output_name=RUNS[key][0], part=part, reference_part=part*10,
                        time_s=time_s, reference_time_s=float(b.time_s.iloc[0]), shared_actual_time_step=shared)
                    previous = saved_prefix[key].iloc[part]
                    assert previous.time_s == time_s and previous.reference_time_s == p['reference_time_s']
                    if shared:
                        p.update(compare_prefix(a, b))
                        if RUNS[key][1]:
                            for col in ['raw_all_columns0ulp', 'physical_identity_columns0ulp', 'a_dterror_s', 'b_dterror_s', 'dterror_abs_difference_s']:
                                assert p[col] == previous[col], (key, part, col)
                            assert p['compared_columns'] == ast.literal_eval(previous.compared_columns)
                        else: assert previous.all_native_fields0ulp and p['raw_all_columns0ulp']
                    else: assert part == 3, ('Only a final-only unmatched save is allowed', key, part)
                    prefixes.append(p)
            top = origin.z.gt(9.99).to_numpy()
            for label, coefficients in EFFECTS.items():
                pressure = sum(c*arrays[k].pressure.to_numpy() for k, c in coefficients.items())
                total = sum(c*(arrays[k].sigma_zz-arrays[k].pressure).to_numpy() for k, c in coefficients.items())
                dz = sum(c*arrays[k].z.to_numpy() for k, c in coefficients.items())
                e = dict(comparison=label, part=part, time_s=time_s,
                    pressure_rms_pa=float(np.sqrt(np.mean(pressure**2))), pressure_max_abs_pa=float(abs(pressure).max()),
                    top_material_max_mm=1000*float(abs(dz[top]).max()), total_stress_rms_pa=float(np.sqrt(np.mean(total**2))))
                e.update({'delta_'+field: sum(c*rows[k][field] for k, c in coefficients.items()) for field in metric_deltas})
                effects.append(e)
            if part % 10 == 0: print('Audited four actual native frames', part, time_s, flush=True)
    history = pd.DataFrame(history); effects = pd.DataFrame(effects); prefixes = pd.DataFrame(prefixes)
    assert len(history) == 244 and len(prefixes) == 16
    for key in RUNS:
        p = prefixes[prefixes.run.eq(key)]
        assert p.shared_actual_time_step.sum() >= 3 and p.loc[p.shared_actual_time_step, 'physical_identity_columns0ulp'].all()
    summary = []
    for key in RUNS:
        h = history[history.run.eq(key)]; end = h.iloc[-1]
        row = dict(run=key, output_name=RUNS[key][0], actual_end_s=float(end.time_s),
            end_saved_step=int(end.saved_step), hg_xi=RUNS[key][1], spr=RUNS[key][2])
        for field in metric_deltas+['pressure_rms_pa', 'sigma_zz_rms_pa', 'force_N_m', 'expected13_node_force_N_m', 'loaded_count']:
            row['end_'+field] = float(end[field])
        row.update(window_pressure_min_pa=float(h.pressure_min_pa.min()), window_max_speed_m_s=float(h.vmax_m_s.max()),
            max_force_error_N_m=float(abs(h.force_N_m-h.expected13_node_force_N_m).max()),
            active_drained_sample_count=int(h.loc[h.drainage_active, 'potential_drained_count'].sum()),
            active_drained_abs_max_pa=float(h.loc[h.drainage_active, 'drained_abs_max_pa'].max()),
            window_min_dterror_s=float(h.dterror_s.min()), window_max_dterror_s=float(h.dterror_s.max()))
        assert row['active_drained_sample_count'] > 0 and row['active_drained_abs_max_pa'] == 0
        for field in ['left_normal_max_mm', 'right_normal_max_mm', 'bottom_normal_max_mm', 'bottom_tangent_max_mm']:
            row['window_max_'+field] = float(h[field].max())
        summary.append(row)
    artifacts = []
    for label, frame in [('history', history), ('summary', pd.DataFrame(summary)), ('effects', effects), ('prefix', prefixes)]:
        p = TESTS/'figures'/(TAG+'_'+label+'.csv'); frame.to_csv(p, index=False, float_format='%.17g'); artifacts.append(bound(p))
    effect_summary = []
    for label in EFFECTS:
        d = effects[effects.comparison.eq(label)]; end = d.iloc[-1]
        effect_summary.append(dict(comparison=label, endpoint=end.to_dict(),
            all_window_maxima={c: float(d[c].max()) for c in ['pressure_rms_pa', 'pressure_max_abs_pa', 'top_material_max_mm', 'total_stress_rms_pa']},
            all_window_max_abs_metric_deltas={c: float(abs(d[c]).max()) for c in d.columns if c.startswith('delta_')}))
    write_json(receipt, dict(passed=True, offline_numeric_only=True, visual_review_passed=False, utc=utc(),
        sources=sources, artifacts=artifacts, current_build_inputs_verified=True, historical_input_verification=old_bindings,
        native_frames=244, matched_times=61, native_ids=20301, exact_same_dt_times_and_steps=True,
        no_active_owned_solver=True, observed_processes=processes, manifests_equal_status=True,
        summary=summary, snapshot_metrics=snapshots, effects=effect_summary, hg_runtime=runtime,
        prefix_shared_count=int(prefixes.shared_actual_time_step.sum()),
        unmatched_final_saves=prefixes[~prefixes.shared_actual_time_step].fillna('').to_dict('records'),
        sole_prefix_exception='dterror_s: output-interval max, independently <=1e-14 in both arrays; other34 columns exact',
        half_3s_accepted=False, formal100_admitted=False, physical_full_accepted=False,
        limitations=['Cross-option HG/SPR effects and their interaction are not half-step errors or theory/FEM errors.',
            'HG0 controls use retained earlier GPU executable; old inputs verified at exact retained archives where canonical binaries/source advanced.',
            'HG-off CPU3frame/GPU31frame0ULP regression supports the build bridge, not an isolated same-build full3s factorial.',
            'All61 saved native states checked, not every integration substep; HG guards are end-of-run counters/extrema, not per-step history.',
            'Fixed planar sideFreeSlip/bottomNoSlip, elastic/smallrotation/freshHG; original13node load quadrature remains+4percent.',
            'Only startup.15s HG and3s HG0 SPR half evidence exists; no new3sHG half or100s/late/full/general-boundary acceptance.',
            'Adjacent SOIL-layer displacement is not wall motion or exact continuum boundary error; paperA/B retain initial material stencils.']))
    print(pd.DataFrame(summary)[['run', 'end_pressure_max_pa', 'end_paper_A_settlement_mm', 'end_paper_B_settlement_mm']].to_string(index=False), flush=True)
    print('PASS:', receipt, flush=True)


if __name__ == '__main__': main()
