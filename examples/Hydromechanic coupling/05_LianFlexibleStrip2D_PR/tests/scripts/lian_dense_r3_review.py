"""Seal the offline dense-reference review after source-pixel/figure inspection."""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from PIL import Image

CASE = Path(__file__).resolve().parents[2]
TAG = 'lian_hgspr100_r3'
LOG = CASE / 'tests/logs'


def bound(path):
    p = Path(path)
    return dict(path=str(p), bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def verify(entries):
    for e in entries:
        a = bound(e['path'])
        assert (a['bytes'], a['sha256']) == (e['bytes'], e['sha256']), e['path']


def path_entries(obj):
    if isinstance(obj, dict):
        if {'path', 'sha256', 'bytes'} <= obj.keys():
            yield obj
        for value in obj.values():
            yield from path_entries(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from path_entries(value)


def main():
    target = LOG / (TAG + '.final_review.json')
    assert not target.exists(), 'Already sealed'
    record_path = LOG / (TAG + '.plots.json')
    record = json.loads(record_path.read_text(encoding='utf8'))
    verify(record['sources'] + record['artifacts'])
    previous = json.loads((LOG / 'lian_hgspr100_r2.plots.json').read_text(encoding='utf8'))
    # Check all old r2 products, not just the reused history.
    verify(previous['artifacts'] + previous['unchanged_formal_artifacts'])
    ref = pd.read_csv(CASE / 'figures' / (TAG + '_reference.csv'), dtype={'figure': str}, float_precision='round_trip')
    pair = pd.read_csv(CASE / 'figures' / (TAG + '_comparison.csv'), dtype={'figure': str}, float_precision='round_trip')
    assert len(ref) == 730 and len(pair) == 640
    assert len(ref[~ref.branch_resolved]) == 90
    assert set(pair.reference_id) == set(ref.loc[ref.branch_resolved, 'reference_id'])
    assert ref.reference_id.is_unique and pair.reference_id.is_unique
    assert np.isfinite(ref[['pixel_x', 'pixel_y', 'time_s', 'value', 'value_uncertainty']]).all().all()
    assert ref.value_uncertainty.gt(0).all()
    assert np.isfinite(pair[['current_value', 'current_minus_reference', 'native_coordinate_sensitivity']]).all().all()
    assert np.array_equal(pair.current_minus_reference.to_numpy(), (pair.current_value - pair.value).to_numpy())
    assert ref.loc[ref.figure.eq('11'), 'units'].eq('kPa').all()
    assert ref.loc[ref.figure.ne('11'), 'units'].eq('m').all()
    assert not ((ref.figure == '11') & (ref.reference_method == 'FEM') & ref.branch_resolved & (ref.pixel_x >= 534)).any()
    assert not ((ref.figure == '11') & (ref.reference_method == 'FEM') & (ref.pixel_x == 232)).any()
    assert not ((ref.figure == '12a') & (ref.reference_method == 'FEM') & (ref.pixel_x == 322)).any()
    profile = ref[ref.figure.eq('12b')]
    assert profile.elevation_m.between(0, 10).all()
    assert profile.loc[profile.reference_method.eq('SPH'), 'elevation_m'].ge(7.5).all()
    fem_top = profile[(profile.reference_method == 'FEM') & (profile.pixel_x == 1374)]
    assert len(fem_top) == 1 and fem_top.pixel_y.iloc[0] == 82.5
    for fig in ('11', '12a'):
        for method in ('SPH', 'FEM'):
            a = ref[(ref.figure == fig) & (ref.reference_method == method) & (ref.paper_point == 'A')]
            b = ref[(ref.figure == fig) & (ref.reference_method == method) & (ref.paper_point == 'B')]
            assert np.array_equal(a.pixel_x.to_numpy(), b.pixel_x.to_numpy())
            assert (a.value.to_numpy() > b.value.to_numpy()).all()
    for e in record['artifacts']:
        if Path(e['path']).suffix == '.png':
            with Image.open(e['path']) as im:
                im.verify()
    changed = [Path(e['path']) for e in record['artifacts']] + [
        Path(record['sources'][0]['path']), Path(__file__), record_path, target,
        CASE / 'README.md', CASE / 'figures/README.md', CASE / '.gitattributes', CASE / 'tests/.gitattributes']
    cryer = CASE.parent / '04_CryerProblem_PR'
    prepared = cryer / 'tests/logs/cryer_preload_peak_half_r1.inputs.json'
    run = json.loads((cryer / 'tests/logs/cryer_preload_peak_half_r1.run.json').read_text(encoding='utf8'))
    verify([run['prepared_inputs'], run['program']])
    frozen = json.loads(prepared.read_text(encoding='utf8'))
    protected = {str(Path(e['path']).resolve()).lower() for e in path_entries(frozen)}
    assert not protected.intersection(str(p.resolve()).lower() for p in changed)
    assert all(str(p.resolve()).lower().startswith(str(CASE.resolve()).lower() + '\\') for p in changed)
    # Read-only status, no signal or command is sent to a solver/monitor.
    cmd = "Get-CimInstance Win32_Process -Filter 'ProcessId=59224' | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"
    proc = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True))
    assert proc['ProcessId'] == 59224 and proc['ParentProcessId'] == 42452
    result = dict(passed=True, visual_review_passed=True, utc=datetime.now(timezone.utc).isoformat(),
                  reference_rows=730, resolved_comparison_rows=640, unresolved_envelope_rows=90,
                  counts=record['counts'], previous_reference_rows=25, physical_accuracy_changed=False,
                  old_r1_r2_products_hash_unchanged=True, formal_input_native_output_edited=False,
                  spreadsheet_qa='Both CSVs imported via artifact-tool Workbook.fromCSV; headers, units and numeric columns additionally checked with pandas.',
                  independent_review='Original raster overlays/units reviewed; ambiguous FEM falling branches unresolved, x232/x322 excluded, upper-profile x1374 ROI fixed.',
                  visual_artifacts_reviewed=[e['path'] for e in record['artifacts'] if Path(e['path']).suffix == '.png'],
                  cryer=dict(read_only_owned_process=proc, bound_paths_intersect_changes=False,
                             prepared_inputs=bound(prepared), executable=bound(run['program']['path']),
                             solver_or_watcher_changed=False, new_solver_or_watcher_started=False),
                  sources=[bound(record_path), bound(Path(__file__))],
                  final_artifacts=[bound(p) for p in changed if p.exists() and p != Path(__file__)],
                  limitations=record['limitations'])
    with target.open('x', encoding='utf8') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ['passed', 'reference_rows', 'resolved_comparison_rows', 'unresolved_envelope_rows', 'cryer']}, indent=2))


if __name__ == '__main__':
    main()
