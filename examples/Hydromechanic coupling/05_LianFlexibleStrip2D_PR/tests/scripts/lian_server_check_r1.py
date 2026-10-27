"""One fresh portable-package .15-s smoke; never runs half/100s or changes originals."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from lian_release_r1 import CASE, TESTS, READER, native, bound, utc, write_json
from lian_spr_half_review_r1 import metrics
from lian_hg_short_r1 import hg_stats
from lian_hg_prefix_r2 import compare_prefix
from lian_opt3_review_r1 import verify_bindings

TAG = 'lian_server_check_r1'
DEST = TESTS/'outputs/lian_server_smoke_r1'
ZIP = CASE/'Lian_HGSPR_Windows_RTXA6000.zip'
ZIP_SHA = '9426799182eb71815573c4f481fcbaabed602c3fde831ad9639d593c9b69680c'
STATE = TESTS/'logs'/(TAG+'.status.json')
CHECK = TESTS/'logs'/(TAG+'.check.json')
LOG = TESTS/'logs'/(TAG+'.run.log')
REPEAT_LOG = TESTS/'logs'/(TAG+'.refuse.log')
REFERENCE = 'lian_hg3_r2_spr1_3s'


def ps_json(command):
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', command],
        creationflags=subprocess.CREATE_NO_WINDOW)
    return json.loads(raw.decode('utf8', errors='replace')) if raw.strip() else []


def scoped_processes():
    rows = ps_json("@(Get-CimInstance Win32_Process | Where-Object {($_.Name -like 'DualSPHysics*' -and $_.CommandLine -match 'CaseLian|lian_') -or ($_.Name -match 'python|cmd' -and $_.CommandLine -match 'lian_(hg3_r[12]|spr_half_r1|hg_short_r1|server_check_r1)\\.py')} | Select-Object ProcessId,ParentProcessId,Name,CommandLine) | ConvertTo-Json -Compress")
    if isinstance(rows, dict): rows = [rows]
    return [p for p in rows if p['ProcessId'] != os.getpid()]


def signature(path):
    root = ET.parse(path).getroot()
    def node(e):
        attrs = {k: v for k, v in e.attrib.items() if k not in ['date', 'comment', 'units_comment', '_rem']}
        for key, value in list(attrs.items()):
            try: attrs[key] = float(value).hex()
            except ValueError: pass
        if e.tag == 'parameter' and e.attrib.get('key') == 'TimeMax': attrs['value'] = 'DURATION'
        return e.tag, tuple(sorted(attrs.items())), (e.text or '').strip(), tuple(node(child) for child in e)
    return node(root)


def file_set(folder):
    return [bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]


def main():
    global STATE, CHECK
    resume_preflight = sys.argv[1:] == ['--resume-preflight']
    assert not sys.argv[1:] or resume_preflight
    prior = None
    if resume_preflight:
        prior = json.loads(STATE.read_text())
        assert prior['status'] == 'failed' and prior['error'] == "LookupError('unknown encoding: utf8-sig')"
        assert 'owned_wrapper_pid' not in prior and DEST.exists()
        assert not (DEST/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out').exists()
        prior = dict(status=bound(STATE), check=bound(CHECK), solver_ever_started=False)
        STATE = TESTS/'logs'/(TAG+'.r2.status.json'); CHECK = TESTS/'logs'/(TAG+'.r2.check.json')
    else: assert not DEST.exists()
    assert not STATE.exists() and not CHECK.exists() and not LOG.exists() and not REPEAT_LOG.exists()
    assert not scoped_processes(), 'An existing Lian solver or worker is active'
    assert bound(ZIP)['sha256'] == ZIP_SHA
    ref_path = TESTS/'logs'/(REFERENCE+'.run.json'); reference = json.loads(ref_path.read_text())
    assert reference['passed'] and reference['owned_exited'] and reference['exit_code'] == 0
    verify_bindings(reference['outputs']+reference['artifacts'])
    state = dict(status='preparing', utc=utc(), owned_pid=os.getpid(), package=bound(ZIP),
        source=bound(__file__), sources=[bound(ref_path), bound(READER), bound(TESTS/'scripts/lian_hg_prefix_r2.py'),
            bound(TESTS/'scripts/lian_spr_half_review_r1.py'), bound(TESTS/'scripts/lian_hg_short_r1.py'),
            bound(TESTS/'scripts/lian_release_r1.py'), bound(TESTS/'scripts/lian_mirror_review_r1.py')],
        half_3s_accepted=False, formal100_admitted=False, run_duration_s=.15, prior_preflight_failure=prior)
    write_json(STATE, state); child = None
    try:
        if not resume_preflight: DEST.mkdir()
        with zipfile.ZipFile(ZIP) as archive:
            names = archive.namelist(); assert len(names) == len(set(names))
            for name in names:
                target = (DEST/name).resolve()
                assert target.is_relative_to(DEST.resolve()) and not name.startswith(('/', '\\'))
            if not resume_preflight: archive.extractall(DEST)
        manifest_path = DEST/'support/server_manifest.json'; manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        assert set(names) == {e['entry'] for e in manifest['files']} | {manifest['manifest_entry']}
        package_files = []
        for entry in manifest['files']:
            actual = bound(DEST/entry['entry'])
            assert actual['sha256'] == entry['sha256'] and actual['bytes'] == entry['bytes'], entry['entry']
            package_files.append(actual)
        xml = DEST/manifest['formal_input']; bat = DEST/manifest['formal_bat']; bat_before = bound(bat)
        tested_xml = TESTS/'configs'/(REFERENCE+'_Def.xml')
        assert signature(xml) == signature(tested_xml), 'Unexpected physical XML difference'
        parameters = {e.attrib['key']: e.attrib['value'] for e in ET.parse(xml).findall('.//execution/parameters/parameter')}
        assert float(parameters['TimeMax']) == 100 and float(parameters['TimeOut']) == .05
        assert float(parameters['DtFixed']) == 1e-5 and parameters['SoilBoundaryDerivativeSPR'] == '1'
        assert float(parameters['SoilHourglassXi']) == .1
        print('All17 ZIP entries and16 manifest file hashes verified; XML physics equivalent', flush=True)
        text = xml.read_bytes().decode('utf8')
        text, count = re.subn(r'(<parameter key="TimeMax" value=")[^"]*(")', lambda m: m[1]+'.15'+m[2], text)
        assert count == 1
        xml.write_text(text, encoding='utf8', newline='')
        assert signature(xml) == signature(tested_xml) and bound(bat) == bat_before
        state.update(status='running', manifest=bound(manifest_path), manifest_files_verified=package_files,
            tested_xml=bound(tested_xml), smoke_xml=bound(xml), original_bat=bat_before,
            moved_package_directory=str(DEST), invocation_cwd=str(TESTS), path_contains_spaces=' ' in str(DEST),
            source_timeMax_s=100, smoke_timeMax_s=.15, bat_modified=False)
        write_json(STATE, state)
        assert not scoped_processes(), 'A Lian solver/worker appeared during preparation'
        command = '"'+os.environ['ComSpec']+'" /d /s /c ""'+str(bat)+'" --unattended"'
        state['command'] = command; started = time.perf_counter(); modules = None
        folder = DEST/manifest['new_output']; checked = 0; rows = []; prefixes = []; initial = None
        with LOG.open('xb') as log:
            child = subprocess.Popen(command, cwd=TESTS, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid'] = child.pid; write_json(STATE, state)
            print('Started sole portable.15s BAT smoke wrapper', child.pid, flush=True)
            while True:
                code = child.poll()
                if modules is None:
                    processes = ps_json("@(Get-CimInstance Win32_Process -Filter \"Name='DualSPHysics5.2_GEO_win64.exe'\" | Where-Object {$_.ParentProcessId -eq "+str(child.pid)+"} | Select-Object ProcessId,ParentProcessId,Name) | ConvertTo-Json -Compress")
                    if isinstance(processes, dict): processes = [processes]
                    if processes:
                        assert len(processes) == 1
                        solver_pid = processes[0]['ProcessId']
                        loaded = ps_json("@((Get-Process -Id "+str(solver_pid)+").Modules | Where-Object {$_.ModuleName -in @('msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')} | Select-Object ModuleName,FileName) | ConvertTo-Json -Compress")
                        if isinstance(loaded, dict): loaded = [loaded]
                        if len(loaded) == 3:
                            assert {m['ModuleName'].lower() for m in loaded} == {'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'}
                            for module in loaded:
                                assert Path(module['FileName']).resolve().parent == (DEST/'support/bin').resolve(), module
                                verify_bindings([next(e for e in package_files if Path(e['path']).name.lower() == module['ModuleName'].lower())])
                            modules = loaded; state.update(actual_solver_pid=solver_pid, app_local_CRT_modules=modules)
                parts = sorted((folder/'data').glob('Part_*.bi4'))
                available = len(parts) if code is not None else max(0, len(parts)-1)
                while checked < available:
                    a = native(folder, checked)
                    if initial is None: initial = a
                    row = metrics(a, initial, checked, 1e-5); rows.append(row)
                    b = native(TESTS/'outputs'/REFERENCE, checked)
                    shared = float(a.time_s.iloc[0]) == float(b.time_s.iloc[0]) and int(a.saved_step.iloc[0]) == int(b.saved_step.iloc[0])
                    pair = dict(part=checked, actual_time_s=float(a.time_s.iloc[0]), reference_time_s=float(b.time_s.iloc[0]),
                        actual_step=int(a.saved_step.iloc[0]), reference_step=int(b.saved_step.iloc[0]), shared_actual_time_step=shared)
                    if shared: pair.update(compare_prefix(a, b))
                    else: assert checked == 3, 'Only final-only timing mismatch is allowed; no interpolation'
                    prefixes.append(pair); checked += 1
                state.update(checked_frames=checked, last_actual_time_s=rows[-1]['time_s'] if rows else None)
                write_json(STATE, state)
                if code is not None: break
                assert time.perf_counter()-started < 1800, 'Bounded portable smoke wall limit'
                time.sleep(5)
        assert code == 0 and child.poll() == 0
        run_text = (folder/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in run_text and 'RTX 3050' in run_text
        assert len(rows) == 4 and abs(rows[-1]['time_s']-.15) < 2e-5 and modules is not None
        for mk, mode in [(0, 'Free slip'), (1, 'No-slip'), (2, 'Free slip')]:
            assert re.search(r'mkbound:\s*'+str(mk)+r'\s*->\s*'+mode, run_text)
        assert 'SPR stationary wall planes (one per mk): 3' in run_text
        stats = hg_stats(run_text)
        assert sum(p.get('physical_identity_columns0ulp', False) for p in prefixes) >= 3
        assert bound(bat) == bat_before
        outputs_before = file_set(folder)
        repeat_started = time.perf_counter()
        with REPEAT_LOG.open('xb') as log:
            repeated = subprocess.run(command, cwd=TESTS, stdout=log, stderr=subprocess.STDOUT,
                timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        assert repeated.returncode == 1
        assert 'Nothing was overwritten or restarted.' in REPEAT_LOG.read_text(errors='replace')
        assert file_set(folder) == outputs_before
        assert not scoped_processes()
        state.update(status='passed', finished_utc=utc(), exit_code=code, owned_exited=True,
            wall_seconds=time.perf_counter()-started, actual_hardware='RTX 3050, not an RTX A6000 server test',
            hg_stats=stats, history=rows, prefix=prefixes, app_local_CRT_modules=modules,
            refusal_exit_code=repeated.returncode, refusal_seconds=time.perf_counter()-repeat_started,
            refusal_no_output_mutation=True, no_surviving_owned_process=True, bat_after=bound(bat),
            outputs=outputs_before, artifacts=[bound(LOG), bound(REPEAT_LOG)],
            limitations=['One .15-s startup run at50ms cadence, only4saved native frames; no activated drainage after1s.',
                'No3s half, formal100s, late/full-cycle accuracy or actualRTXA6000hardware/driver acceptance.',
                'dterror_s is output-interval telemetry; all other34columns exact for actualtime-step shared saves.',
                'BAT is unchanged and resolves its own moved directory from a different invocation cwd; it deliberately refuses retained outputs.'])
        write_json(STATE, state); write_json(CHECK, state)
        print('PASS', CHECK, 'frames', checked, 'shared0ULP', sum(p.get('physical_identity_columns0ulp', False) for p in prefixes), flush=True)
    except Exception as error:
        if child is not None and child.poll() is None:
            stopped = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
            state['owned_stop_exit_code'] = stopped.returncode; child.wait(timeout=15)
        state.update(status='failed', error=repr(error), traceback=traceback.format_exc(), finished_utc=utc(),
            owned_exited=child is None or child.poll() is not None, partial_outputs=file_set(DEST))
        write_json(STATE, state); write_json(CHECK, state)
        raise


if __name__ == '__main__': main()
