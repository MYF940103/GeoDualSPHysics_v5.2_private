"""Read-only r1 solver evidence audit; writes only new audit JSON/CSV artifacts."""
import json
import numpy as np
import pandas as pd
from lian_release_r1 import TESTS, REPO, READER, native, bound, utc, write_json
from lian_opt3_review_r1 import verify_bindings
from lian_spr_half_review_r1 import metrics
from lian_hg_short_r1 import hg_stats
from lian_hg_prefix_r2 import NATIVE_COLUMNS, STATE_COLUMNS, compare_prefix

TAG = 'lian_hg3_r1_audit'


def comparator_tests(frame):
    # Every field other than the sole interval statistic must remain bitwise exact.
    base = frame.astype('float64')
    tested = []

    def rejects(label, a, b):
        try:
            compare_prefix(a, b)
        except AssertionError:
            tested.append(label)
        else:
            raise AssertionError('Comparator accepted corruption: ' + label)

    for column in STATE_COLUMNS:
        bad = base.copy()
        bad.loc[bad.index[0], column] = np.nextafter(float(bad[column].iloc[0]), np.inf)
        rejects('nextafter_' + column, base, bad)
    for column in NATIVE_COLUMNS:
        bad = base.drop(columns=[column])
        rejects('missing_' + column, bad, bad)
    for field in ['pressure', 'dterror_s']:
        for label, value in [('nan', np.nan), ('positive_inf', np.inf), ('negative_inf', -np.inf)]:
            bad = base.copy()
            bad.loc[bad.index[0], field] = value
            rejects(label + '_' + field, base, bad)
    bad = base.copy()
    bad['dterror_s'] = np.nextafter(1e-14, np.inf)
    rejects('unsafe_dterror_a', bad, base)
    rejects('unsafe_dterror_b', base, bad)
    bad = base.copy()
    bad['has_dterror'] = 0
    rejects('missing_dterror_flag_both', bad, bad)
    safe = base.copy()
    safe['dterror_s'] = -.1
    allowed = compare_prefix(base, safe)
    assert allowed['physical_identity_columns0ulp'] and not allowed['raw_all_columns0ulp']
    assert compare_prefix(base, base)['raw_all_columns0ulp']
    return dict(passed=True, rejected_cases=len(tested), rejected_labels=tested,
        single_element_nextafter_columns=STATE_COLUMNS, allowed_negative_interval_only=allowed)


def main():
    receipt = TESTS/'logs'/(TAG + '.check.json')
    csv = TESTS/'figures'/(TAG + '_prefix.csv')
    assert not receipt.exists() and not csv.exists(), 'Never overwrite audit evidence'
    state_path = TESTS/'logs/lian_hg3_r1.status.json'
    state = json.loads(state_path.read_text())
    assert state['status'] == 'rejected_or_interrupted' and state['error'] == 'AssertionError()'
    assert state['current_run'] == 'lian_hg3_r1_spr0_3s' and len(state['runs']) == 2
    smoke, interrupted = state['runs']
    assert smoke['name'] == 'lian_hg3_r1_spr0_smoke' and smoke['passed']
    assert smoke['exit_code'] == 0 and smoke['owned_exited'] and smoke['checked_frames'] == 31
    assert interrupted['name'] == state['current_run'] and not interrupted['passed']
    assert interrupted['owned_exited'] and interrupted['exit_code'] != 0
    assert state['owned_stop_exit_code'] == 0
    verify_bindings(state['inputs'])
    verify_bindings(smoke['outputs'] + smoke['artifacts'])
    verify_bindings(interrupted['partial_outputs'] + [interrupted['partial_history']])
    manifest = TESTS/'logs'/(smoke['name'] + '.run.json')
    assert json.loads(manifest.read_text()) == smoke
    smoke_folder = TESTS/'outputs'/smoke['name']
    interrupted_folder = TESTS/'outputs'/interrupted['name']
    smoke_text = (smoke_folder/'Run.out').read_text(errors='replace')
    interrupted_text = (interrupted_folder/'Run.out').read_text(errors='replace')
    assert 'Finished execution (code=0)' in smoke_text
    assert 'Finished execution (code=0)' not in interrupted_text
    assert hg_stats(smoke_text) == smoke['hg_stats']
    assert len(list((interrupted_folder/'data').glob('Part_*.bi4'))) == 3
    origin = native(interrupted_folder, 0)
    assert len(origin) == 20301 and origin.id.nunique() == 20301
    saved = {}
    for part in range(31):
        a = native(smoke_folder, part)
        metrics(a, origin, part, 1e-5)
        if part in [0, 10, 20]:
            saved[part] = a
    rows = []
    for part, reference_part in [(0, 0), (1, 10), (2, 20)]:
        a = native(interrupted_folder, part)
        metrics(a, origin, part, 1e-5)
        b = saved[reference_part]
        comparison = compare_prefix(a, b)
        rows.append(dict(part=part, reference_part=reference_part,
            time_s=float(a.time_s.iloc[0]), saved_step=int(a.saved_step.iloc[0]),
            native_ids=len(a), compared_column_count=len(comparison['compared_columns']),
            **{k: v for k, v in comparison.items() if k != 'compared_columns'}))
    assert [row['raw_all_columns0ulp'] for row in rows] == [True, False, False]
    assert rows[-1]['saved_step'] == 10000 and abs(rows[-1]['time_s'] - .10001) < 1e-12
    selftest = comparator_tests(saved[10])
    fixed = REPO/'src/source/JDsFixedDt.cpp'
    sph = REPO/'src/source/JSph.cpp'
    reader_source = TESTS/'scripts/read_hydro_native.cpp'
    fixed_text = fixed.read_text(errors='replace')
    sph_text = sph.read_text(errors='replace')
    reader_text = reader_source.read_text(errors='replace')
    assert 'const double dterror=ret-dtvar;' in fixed_text
    assert 'if(DtError<dterror)DtError=dterror;' in fixed_text
    assert 'if(reset)DtError=-DBL_MAX;' in fixed_text
    assert 'bdpart->SetvDouble("dterror",FixedDt->GetDtError(true))' in sph_text
    assert 'part->GetvDouble("dterror",true,0)' in reader_text
    sources = [bound(p) for p in [__file__, TESTS/'scripts/lian_hg_prefix_r2.py', state_path,
        manifest, READER, fixed, sph, reader_source, TESTS/'scripts/lian_spr_half_review_r1.py',
        TESTS/'scripts/lian_mirror_review_r1.py']]
    pd.DataFrame(rows).to_csv(csv, index=False, float_format='%.17g')
    write_json(receipt, dict(passed=True, utc=utc(), sources=sources, artifacts=[bound(csv)],
        frozen_input_and_output_bindings_passed=True,
        completed_smoke_original_safety_frames=31, interrupted_original_safety_frames=3,
        native_ids=20301, compared_columns=STATE_COLUMNS, comparisons=rows,
        comparator_selftest=selftest, original_dterror_upper_limit_s=1e-14,
        source_semantics='dterror=max(DtFixed-DtVariable) since the preceding PART; GetDtError(true) resets it at each saved output.',
        rejected_assertion='Whole native-array byte comparison included the output-interval dterror statistic. Physical/state/identity/time/step/flag fields match exactly.',
        terminal_reason='The checker intentionally killed its owned wrapper after the prefix assertion. Solver stopped with final sealed PART at .10001s; it did not complete3s.',
        actual_last_sealed_time_s=rows[-1]['time_s'], actual_last_sealed_step=rows[-1]['saved_step'],
        physical_3s_accepted=False, half_3s_accepted=False, formal100_admitted=False,
        plots_not_generated='Interrupted before .5s; no .5/1/3s fields exist.',
        limitations=['No physical threshold was relaxed; each original natural-step guard still passes.',
            'No production/input/formal file was changed and no solver or notifier was launched.']))
    print(pd.DataFrame(rows).to_string(index=False), flush=True)
    print('Comparator corruption rejection cases:', selftest['rejected_cases'], flush=True)


if __name__ == '__main__':
    main()
