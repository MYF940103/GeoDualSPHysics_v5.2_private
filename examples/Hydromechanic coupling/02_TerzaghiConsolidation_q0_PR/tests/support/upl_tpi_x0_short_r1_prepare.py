"""Prepare one closed CPU TPI-X0 .15 s test; never run GenCase, a solver or a reader."""
import argparse
import csv
import io
import json
import re
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'upl_tpi_x0_short_r1'
BASE = T / 'configs/upl_column_public_coarse_r1.xml'
OUT = T / 'configs' / (TAG + '_Def.xml')
PLAN = T / 'configs' / (TAG + '.clock.csv')
CHECK = T / 'logs' / (TAG + '.prepare.json')
DT, END, CADENCE, EVENT_STEP = 5e-6, .15, .001, 2000
HEADER = ('part', 'completed_steps', 'saved_step', 'time_s', 'dt_s',
          'post_open_by_completed_step', 'target_time_s', 'forced_final')


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def next_time(t):
    # Literal single-segment JDsOutputTime::GetNextTime (tb=0, tout=.001).
    nt = int(t / CADENCE)
    nxt = CADENCE * nt
    while nxt <= t:
        nxt = CADENCE * nt
        nt += 1
    return nxt


def make_plan():
    rows = [(0, 0, 0, 0., DT, 0, 0., 0)]
    time, completed, target = 0., 0, next_time(0.)
    while time < END:
        time += DT  # actual binary64 scalar accumulation, never n*dt
        completed += 1
        if time >= target or time >= END:
            rows.append((len(rows), completed, completed-1, time, DT,
                         int(completed > EVENT_STEP), target,
                         int(time < target)))
            target = next_time(time)
    need(completed >= EVENT_STEP and completed < 40000, 'Closed .15 s step range differs')
    need(all(a[1] < b[1] and a[3] < b[3] for a, b in zip(rows, rows[1:])),
         'Nonmonotone scalar plan')
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow([format(v, '.17g') if isinstance(v, float) else v for v in row])
    return rows, stream.getvalue().encode('ascii')


def configuration():
    data = BASE.read_bytes()
    text = data.decode('utf-8-sig')
    # Preserve the complete existing geometry/generated constants/particles and all
    # hydromechanical material/load/drainage inputs. Only these closed test options differ.
    values = {
        'Visco': ('0.1', 'Original artificial viscosity alpha=0.1; common to all three CPU test programs'),
        'SoilBoundaryDerivativeSPR': ('1', 'Explicit derivative SPR flag; dynamic wall remains the authoritative same-stage image'),
        'SoilDamping': ('1', 'Retained soil damping enabled for the common short test'),
        'SoilDampingCoef': ('0.04', 'Retained soil damping coefficient'),
        'SoilStressRateGradCorr': ('1', 'Retained corrected velocity gradient'),
        'SoilHourglassXi': ('0', 'HG disabled; this test isolates pressure time integration'),
        'DtIni': ('0.000005', 'Common initial step; original current-state necessary bounds remain mandatory'),
        'DtFixed': ('0.000005', 'Common fixed 5 microsecond step; no clipping or acceptance implied'),
        'TimeMax': ('0.15', 'One fresh bounded CPU implementation and phase window; not full consolidation'),
        'TimeOut': ('0.001', 'Regular 1 millisecond native saves, plus the actual final TimeMax crossing'),
    }
    changes = []
    for key, (value, comment) in values.items():
        pattern = rf'(<parameter key="{re.escape(key)}" value=")[^"]*(" comment=")[^"]*(")'
        text, count = re.subn(pattern, lambda m: m[1]+value+m[2]+comment+m[3], text)
        need(count == 1, f'Expected exactly one original parameter {key}')
        changes.append(dict(key=key, value=value, comment=comment))
    text, count = re.subn(r'            <timeout active="true"[^>]*>.*?</timeout>\r?\n', '', text, flags=re.S)
    need(count == 1, 'Expected one original special timeout block')
    need('<HydroMechTopLoadRampTime value="0.01"' in text and
         '<HydroMechDrainageStartTime value="0.01"' in text and
         '<PoreShepardRegularization value="0"' in text and
         '<HydroMechConductivityModel value="0"' in text,
         'Original event/Shepard/constant-k contract differs')
    return text.encode('utf-8'), changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    need(parser.parse_args().execution_authorized, 'Root must review and admit pure preparation separately')
    need(all(not p.exists() for p in (OUT, PLAN, CHECK)), 'Existing/partial preparation protected')
    before = [stat(Path(__file__)), stat(BASE)]
    xml, changes = configuration()
    rows, plan = make_plan()
    with OUT.open('xb') as f:
        f.write(xml)
    with PLAN.open('xb') as f:
        f.write(plan)
    need(before == [stat(Path(__file__)), stat(BASE)], 'Preparation inputs changed')
    result = dict(stage=TAG+'.prepare', passed=True, consumed=before,
                  XML=stat(OUT), clock_plan=stat(PLAN), changes=changes,
                  special_timeout_removed=True, original_events_s=.01,
                  dt_s=DT, nominal_end_s=END, cadence_s=CADENCE,
                  planned_samples=len(rows), planned_completed_steps=rows[-1][1],
                  planned_scalar_end_s=rows[-1][3],
                  event_completed_step=EVENT_STEP,
                  event_native_part=next((r[0] for r in rows if r[1] == EVENT_STEP), None),
                  first_post_open_part=next(r[0] for r in rows if r[5]),
                  post_open_frames=sum(r[5] for r in rows),
                  scalar_clock_not_n_times_dt=True,
                  fixed_grid_event_preopen_until_completed_2000=True,
                  expected_controls=['frozen_original', 'private_default_OFF', 'private_X0_ON'],
                  control_runs_not_started=True, original_source_and_formal_inputs_untouched=True,
                  original_SPR_flag_does_not_override_DynamicPoreWall=True,
                  TPI_beta=0, TPI_alpha=.5,
                  ON_is_incompressible_limit_not_same_finite_Kw_equations=True,
                  ON_OFF_5Pa_equivalence_claimed=False, SHA_scans=0,
                  GenCase_invocations=0, solver_invocations=0, reader_invocations=0,
                  physical_acceptance=False)
    with CHECK.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
