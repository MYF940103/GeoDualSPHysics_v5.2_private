"""CPU event smoke only. Default is help; --prepare seals inputs, --run executes once."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE, TESTS, REPO, READER, READER_SOURCE, bound, native, pore_dt, utc, write_json

TAG = 'cryer_preload_event_r1'
DT = 2.**-21
RAMP, DRAIN, END = 8*DT, 16*DT, 24*DT
CPU_HASH = 'dc4e2a1feb2245e5a9c567d1bc1877e774a6b70b1058e805f4c6d61aa063ca9c'
CONFIG = TESTS/'configs'/(TAG+'_Def.xml')
BAT = TESTS/'configs'/('x'+TAG+'_win64_CPU.bat')
PREP = TESTS/'logs'/(TAG+'.inputs.json')
RUN = TESTS/'logs'/(TAG+'.run.json')
STATE = TESTS/'logs'/(TAG+'.status.json')
COMPLETE = TESTS/'logs'/(TAG+'.completion.json')
CHECK = TESTS/'logs'/(TAG+'.check.json')
CSV = TESTS/'figures'/(TAG+'_summary.csv')
FOLDER = TESTS/'outputs'/TAG
LOG = TESTS/'logs'/(TAG+'.log')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify(entries):
    for entry in entries:
        assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']


def seal(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def reserved():
    assert not any(p.exists() for p in [RUN, STATE, COMPLETE, CHECK, CSV, FOLDER, LOG,
        RUN.with_suffix('.tmp'), STATE.with_suffix('.tmp')]), 'Retained stage exists; never restart or overwrite'


def prerequisites():
    review_path = TESTS/'logs/cryer_grad_fine_r1.review.json'
    review = read(review_path)
    assert review['evidence_consistency_passed'] and review['original_independent_half_screen_passed']
    links = [dict(path=str(review_path.parent/e['path']), sha256=e['sha256']) for e in review['source_links']]
    verify(links)
    check_path = TESTS/'logs/cryer_grad_fine_r1.check.json'
    check = read(check_path); assert check['passed']
    verify([check['run_manifest']]); fine = read(check['run_manifest']['path'])
    assert len(fine['runs']) == 2 and all(r['passed'] and r['owned_exited'] and r['exit_code'] == 0 for r in fine['runs'])
    fine_outputs = [e for r in fine['runs'] for e in r['outputs']]
    verify(fine_outputs)
    verify([fine['prepared_inputs']]); prior = read(fine['prepared_inputs']['path'])
    verify(prior['inputs']+[prior['program']]); assert prior['program']['sha256'] == CPU_HASH
    # This historical run binds the canonical Release build log, source/project inputs and DLL/config runtime.
    build_run_path = TESTS/'logs/cryer_dt_short_r1.run.json'
    build_run = read(build_run_path); verify(build_run['inputs'])
    build_inputs = [e for e in build_run['inputs'] if '/src/' in e['path'].replace('\\', '/')
        or Path(e['path']).name == 'cryer_dt_short_r1_release.build.log'
        or Path(e['path']).parent == REPO/'bin/windows']
    assert any(e['sha256'] == CPU_HASH for e in build_inputs)
    assert any(Path(e['path']).name == 'cryer_dt_short_r1_release.build.log' for e in build_inputs)
    proof = [bound(review_path), bound(check_path), check['run_manifest'], fine['prepared_inputs'],
        bound(build_run_path)]+links+prior['inputs']+build_inputs+fine_outputs
    return prior['program'], proof, build_inputs


def expected_config():
    source = TESTS/'configs/cryer_grad_fine_r1_c_Def.xml'
    text = source.read_text(encoding='utf8')
    for key, value in [('HydroMechTopLoadRampTime', '0.000003814697265625'),
                       ('HydroMechDrainageStartTime', '0.00000762939453125')]:
        text, count = re.subn(r'(<'+key+r' value=")[^"]*(")', lambda m: m[1]+value+m[2], text)
        assert count == 1, key
    for key, value in [('SoilDampingCoef', '0.00004'), ('TimeMax', '0.000011444091796875'),
                       ('TimeOut', '0.000000476837158203125')]:
        text, count = re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")', lambda m: m[1]+value+m[2], text)
        assert count == 1, key
    for old, new in [
        ('No ramp in the formal k=1e-5 one-stage run', 'Event smoke only: load ramp over eight binary fixed steps'),
        ('Drainage starts at t=0', 'Event smoke only: enable drainage at source step sixteen'),
        ('Drain tracked exterior free-surface particles from the start', 'Drain tracked exterior particles after the configured start event'),
        ('CPU Release short-step startup window; not a full Cryer validation', 'CPU event smoke only: twenty-four steps, not equilibrated preload'),
        ('Startup native save interval; five frames including t=0', 'One native frame per step; twenty-five frames including t=0')]:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    text = text.replace('            </hydromechanics>',
        '                <HydroMechDrainageFixedGrid value="1" comment="Use the existing constant-step drainage event policy" />\n            </hydromechanics>')
    return source, text


def prepare():
    assert not PREP.exists(), 'Never overwrite prepared evidence'
    reserved(); program, proof, build_inputs = prerequisites()
    source, expected = expected_config()
    assert CONFIG.read_text(encoding='utf8') == expected, 'Unexpected XML difference'
    template = TESTS/'configs/xcryer_grad_fine_r1_c_win64_CPU.bat'
    assert BAT.read_text(encoding='utf8') == template.read_text(encoding='utf8').replace('cryer_grad_fine_r1_c', TAG)
    files = [__file__, TESTS/'notes'/(TAG+'.md'), CONFIG, BAT, source, template,
        TESTS/'support/cryer_start_r1.py', READER, READER_SOURCE,
        REPO/'src/source/JSph.h', REPO/'src/source/JDsFixedDt.h']
    seal(PREP, dict(status='prepared_not_started', utc=utc(), inputs=proof+[bound(p) for p in files],
        program=program, cpu_build_evidence=build_inputs, config=bound(CONFIG), bat=bound(BAT),
        dt_s=DT, ramp_s=RAMP, drainage_event_s=DRAIN, duration_s=END, expected_steps=24, expected_frames=25,
        physical_accepted=False, preload_equilibrium_accepted=False, half_accepted=False,
        scope='Only existing source-clock loading/drainage events, not a physical preload.'))
    print('PREPARED ONLY', PREP, flush=True)


def inspect_event(a, initial, part):
    assert len(a) == 37173 and a.id.nunique() == 37173 and np.array_equal(a.id, initial.id)
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.nout.eq(0).all()
    assert a.rho.gt(0).all() and a.kplastic.eq(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
    assert np.array_equal(a[['mass', 'h']], initial[['mass', 'h']])
    t = float(a.time_s.iloc[0]); assert a.time_s.eq(part*DT).all()
    assert a.saved_step.eq(part-1 if part else 0).all()
    if part:
        assert a.has_dterror.eq(1).all() and a.dterror_s.le(1e-14).all(), 'Original mechanical natural-step guard'
    assert DT <= pore_dt(float(a.h.iloc[0])), 'Original pore-diffusion guard'
    x = a[['x', 'y', 'z']].to_numpy(); radius = np.linalg.norm(x, axis=1)
    assert radius.max() <= .0525, 'Original radius guard'
    surface = a.fstype.isin([2, 3]).to_numpy(); assert surface.any(), 'Vacuous surface check'
    surface_p = a.pressure.to_numpy()[surface]
    active = t > DRAIN
    if active: assert np.abs(surface_p).max() == 0, 'Original active-drain zero-pressure guard'
    load = a[['load_ax', 'load_ay', 'load_az']].to_numpy()
    force = a.mass.to_numpy()[:, None]*load
    radial = float(-np.sum(force*x/np.where(radius > 0, radius, 1)[:, None]))
    source_time = max(0., t-DT)
    q_expected = 10000.*min(source_time/RAMP, 1.)
    if part <= 1: assert not load.any() and radial == 0, 'Initial source clock q=0'
    else: assert np.linalg.norm(load, axis=1).max() > 0 and radial > 0, 'Expected nonzero inward ramp/plateau load'
    volume = float((a.mass/a.rho).sum()); geom = 4*np.pi*.05**3/3
    return dict(part=part, time_s=t, saved_step=int(a.saved_step.iloc[0]), source_time_s=source_time,
        source_q_expected_pa=q_expected, actual_q_scalar_metadata_available=False,
        expected_drain_active=active, surface_count=int(surface.sum()),
        surface_pressure_nonzero_count=int(np.count_nonzero(surface_p)),
        surface_pressure_abs_max_pa=float(np.abs(surface_p).max()),
        surface_pressure_mean_pa=float(surface_p.mean()), pre_event_zero_pressure_not_required=not active,
        loaded_count=int((np.linalg.norm(load, axis=1)>0).sum()), load_radial_force_N=radial,
        load_vector_rms_m_s2=float(np.sqrt(np.mean(np.sum(load*load, axis=1)))),
        load_net_force_norm_N=float(np.linalg.norm(force.sum(axis=0))),
        load_work_geometric_pa=float(-np.sum(force*x)/(3*geom)),
        load_work_native_pa=float(-np.sum(force*x)/(3*volume)),
        pressure_min_pa=float(a.pressure.min()), pressure_max_pa=float(a.pressure.max()),
        pressure_mean_pa=float(a.pressure.mean()), rho_min_kg_m3=float(a.rho.min()), rho_max_kg_m3=float(a.rho.max()),
        speed_max_m_s=float(np.linalg.norm(a[['vx','vy','vz']], axis=1).max()), radius_max_m=float(radius.max()),
        dterror_s=float(a.dterror_s.max()), pore_dt_s=pore_dt(float(a.h.iloc[0])),
        changed_fstype_count=int((a.fstype.to_numpy()!=initial.fstype.to_numpy()).sum()))


def run():
    prepared = read(PREP); verify(prepared['inputs']+[prepared['program']]); reserved()
    cmd = "Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*'} | Select-Object Name,ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    active = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', cmd], text=True,
        timeout=20, creationflags=subprocess.CREATE_NO_WINDOW).strip()
    assert not active, 'An existing solver is active; do not duplicate it: '+active
    state = dict(status='running', owned_sequence_pid=os.getpid(), started_utc=utc(), prepared_inputs=bound(PREP),
        program=prepared['program'], checked_frames=0, physical_accepted=False, preload_equilibrium_accepted=False)
    def publish():
        for path, data in [(RUN, state), (STATE, dict(status=state['status'], owned_sequence_pid=os.getpid(),
            owned_wrapper_pid=state.get('owned_wrapper_pid'), checked_frames=state['checked_frames']))]:
            temp = path.with_suffix('.tmp'); write_json(temp, data); os.replace(temp, path)
    publish(); child = None; rows = []; started = time.perf_counter()
    try:
        with LOG.open('xb') as stream:
            child = subprocess.Popen([os.environ['ComSpec'], '/d', '/c', prepared['bat']['path']], cwd=CASE,
                stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid'] = child.pid; publish()
            while child.poll() is None: time.sleep(1)
        text = (FOLDER/'Run.out').read_text(errors='replace') if (FOLDER/'Run.out').exists() else ''
        finished = child.returncode == 0 and 'Finished execution (code=0)' in text
        state.update(exit_code=child.returncode, owned_exited=True, wall_seconds=time.perf_counter()-started)
        seal(COMPLETE, dict(solver_finished=finished, exit_code=child.returncode, owned_exited=True,
            owned_wrapper_pid=child.pid, utc=utc(), program=prepared['program'], prepared_inputs=bound(PREP),
            outputs=[bound(p) for p in FOLDER.rglob('*') if p.is_file()]+[bound(LOG)]))
        state['sealed_completion'] = bound(COMPLETE); publish(); assert finished
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)', text)[1]) == 24
        assert len(list((FOLDER/'data').glob('Part_*.bi4'))) == 25
        assert 'OpenMP(Threads:8)' in text and 'SoilStressRateGradCorr="KernelGradient"' in text
        assert 'HydroMechDrainageFixedGrid=True' in text and 'BuiFukagawa2013' in text
        for label, value in [('HydroMechTopLoadQ0', 10000.), ('HydroMechTopLoadRampTime', RAMP),
                             ('HydroMechDrainageStartTime', DRAIN)]:
            found = re.search(re.escape(label)+r':\s*([^\r\n]+)', text); assert found
            assert float(found[1]) == float(format(value, '.6g')), (label, found[1])
        assert float(re.search(r'^\s*SoilDampingCoef=([^\r\n]+)', text, re.M)[1]) == .00004
        initial = native(FOLDER, 0); old_initial = native(TESTS/'outputs/cryer_grad_fine_r1_c', 0)
        assert np.array_equal(initial[['id','x','y','z','rho','mass','h']], old_initial[['id','x','y','z','rho','mass','h']])
        for part in range(25):
            rows.append(inspect_event(initial if part == 0 else native(FOLDER, part), initial, part))
            state['checked_frames'] = len(rows); publish()
        verify(prepared['inputs']+[prepared['program']])
        state.update(status='event_smoke_completed_pending_review', actual_final_time_s=rows[-1]['time_s'],
            actual_steps=24, configured_q0_pa=10000., configured_ramp_s=RAMP, configured_drainage_start_s=DRAIN,
            source_clock_q_is_derived_not_observed_scalar=True)
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
            state['owned_stop_exit_code'] = stop.returncode; child.wait(timeout=20)
        state.update(status='event_smoke_rejected_or_interrupted', error=repr(error), traceback=traceback.format_exc(),
            owned_exited=child is None or child.poll() is not None)
    finally:
        if rows:
            with CSV.open('x', encoding='utf8', newline='') as stream: pd.DataFrame(rows).to_csv(stream, index=False, float_format='%.17g')
            state['summary'] = bound(CSV)
        state['finished_utc'] = utc(); publish()
        seal(CHECK, dict(passed=state['status']=='event_smoke_completed_pending_review', status=state['status'],
            run_manifest=bound(RUN), sealed_completion=state.get('sealed_completion'), checked_frames=len(rows),
            error=state.get('error'), physical_accepted=False, preload_equilibrium_accepted=False,
            half_accepted=False, full_cycle_accepted=False, actual_q_curve_independently_verified=False,
            limits=['Only24-step source-clock/load-presence/drainage switching smoke, not equilibrated preload.',
                'Before saved_t<=16dt no zero-pressure constraint is imposed; actual surface values are reported.',
                'After saved_t>16dt the original active-drain zero-pressure guard is strict.',
                'Expected q comes from saved_t-dt and bound source/config; native load vectors are observed, no q scalar metadata exists.',
                'No queue, GPU, rebuild, half comparison, equilibrium claim or automatic later stage.']))
    print(json.dumps(dict(status=state['status'], checked_frames=len(rows), error=state.get('error'))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(); group.add_argument('--prepare', action='store_true'); group.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.prepare: prepare()
    elif args.run: run()
    else: parser.print_help()
