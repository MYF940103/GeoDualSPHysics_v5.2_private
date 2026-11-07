"""Fresh r2 ZIP/help/GenCase/fail-gate check. No physical solver or native decode."""
import ctypes
import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile
import xml.etree.ElementTree as ET
from ctypes import wintypes as w
import numpy as np

T = Path(__file__).resolve().parents[1]
C = T.parent
L = T / 'logs'
TAG = 'upl_c08_shared_portable_r2'
OUT = T / 'outputs' / TAG
CHECK = L / (TAG + '.check.json')
PACKAGE = 'LianCollapse_upl_win64_r2'
SOURCE = 'CaseLianSaturatedColumnCollapse_shared_preload_r2'
MARKER = '__GRAVITY_PRELOAD_STATE__'


def need(ok, text):
    if not ok:
        raise RuntimeError(text)


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return {'path': str(path), 'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


K = ctypes.WinDLL('kernel32', use_last_error=True)
K.GetExitCodeProcess.argtypes = [w.HANDLE, ctypes.POINTER(w.DWORD)]
K.GetProcessTimes.argtypes = [w.HANDLE, *([ctypes.POINTER(w.FILETIME)] * 4)]
K.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]


def invoke(label, argv, cwd, expected_exit=0, env=None, commandline=None):
    log, call = L / (TAG + '_' + label + '.log'), L / (TAG + '_' + label + '.call.json')
    need(not log.exists() and not call.exists(), 'Existing invocation protected: ' + label)
    program = stat(argv[0])
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    wall = time.monotonic()
    with log.open('xb') as stream:
        p = subprocess.Popen(commandline or argv, cwd=cwd, env=env, stdout=stream,
                             stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        ft = [w.FILETIME() for _ in range(4)]
        created = bool(K.GetProcessTimes(int(p._handle), *[ctypes.byref(x) for x in ft]))
        size = w.DWORD(32768)
        image = ctypes.create_unicode_buffer(size.value)
        observed = bool(K.QueryFullProcessImageNameW(int(p._handle), 0, image, ctypes.byref(size)))
        rc = p.wait()
        code = w.DWORD()
        got = bool(K.GetExitCodeProcess(int(p._handle), ctypes.byref(code)))
    result = {'label': label, 'passed': got and rc == code.value == expected_exit,
              'expected_exit': expected_exit, 'issued_argv': argv, 'actual_commandline': commandline,
              'cwd': str(cwd), 'PID': p.pid, 'program': program,
              'creation_filetime_100ns': (ft[0].dwHighDateTime << 32) | ft[0].dwLowDateTime if created else None,
              'actual_image_observed_before_wait': image.value if observed else None,
              'actual_Popen_wait_exit': rc, 'actual_Win32_exit': code.value if got else None,
              'started_utc': started, 'ended_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'elapsed_s': time.monotonic() - wall, 'log': stat(log), 'physical_solver_updates': 0}
    save(call, result)  # Seal actual exits even if the following observation check fails.
    need(result['passed'] and created and observed and Path(image.value).samefile(argv[0])
         and stat(argv[0]) == program, 'Actual invocation/identity failed: ' + label)
    return stat(call)


def main():
    need(not OUT.exists() and not CHECK.exists(), 'Existing portable output/check protected')
    need(not list(L.glob(TAG + '_*.call.json')) and not list(L.glob(TAG + '_*.log')),
         'Prior partial invocation evidence exists; do not repeat')
    archive = C / 'support' / (PACKAGE + '.zip')
    manifest_path = C / 'support/server_manifest_r2.json'
    manifest = read(manifest_path)
    expected = [PACKAGE + '/' + x['entry'] for x in manifest['files']]
    expected += [PACKAGE + '/support/server_manifest_r2.json', PACKAGE + '/support/SHA256SUMS_r2.txt']
    before = [stat(archive), stat(manifest_path)]
    OUT.mkdir()
    with zipfile.ZipFile(archive) as z:
        need(z.namelist() == expected, 'r2 ZIP whitelist differs')
        for name in z.namelist():
            need((OUT / name).resolve().is_relative_to(OUT.resolve()), 'ZIP target escapes fresh workspace')
        z.extractall(OUT)  # Each decompressed payload has ZIP CRC verification; no SHA pass.
    root = OUT / PACKAGE
    runtime = root / 'support/runtime_r2'
    payload_before = [stat(root / x['entry']) for x in manifest['files']]
    need(all((root / x['entry']).stat().st_size == x['bytes'] for x in manifest['files']), 'Extracted payload size differs')
    need(read(root / 'support/server_manifest_r2.json') == manifest, 'Extracted manifest differs')
    proof = read(root / 'support/preload_schedule_r2.json')
    need(proof['completed_steps'] == 4000000 and proof['part_files'] == 1001
         and proof['last_part'] == 'Part_1000.bi4', 'Prepared writer schedule differs')
    calls, geometries = [], []
    for backend, executable in [('CPU', 'DualSPHysics5.2CPU_win64.exe'), ('GPU', 'DualSPHysics5.2_GEO_win64.exe')]:
        calls.append(invoke('help_' + backend, [str(runtime / executable), '-h'], root))
        text = (L / (TAG + '_help_' + backend + '.log')).read_text(encoding='utf-8', errors='replace')
        need('dualsphysics' in text.lower() and len(text) > 500, 'Actual help output missing')

    # Exercise the delivered missing-source early return, not a physical target.
    sourceout = root / (SOURCE + '_CPU_out')
    receiverout = root / 'CaseLianSaturatedColumnCollapse_psi0_shared_r2_CPU_out'
    need(not sourceout.exists() and not receiverout.exists(), 'Unexpected physical output before fail-gate check')
    cmd = str(Path(os.environ['COMSPEC']).resolve())
    entry = root / 'xCaseLianSaturatedColumnCollapse_psi0_shared_r2_win64_CPU.bat'
    commandline = f'"{cmd}" /d /s /c ""{entry}" --unattended"'
    calls.append(invoke('missing_source', [cmd, '/d', '/s', '/c', str(entry), '--unattended'], root,
                        expected_exit=1, commandline=commandline))
    text = (L / (TAG + '_missing_source.log')).read_text(encoding='utf-8', errors='replace')
    need('Execution aborted.' in text and 'GenCase' not in text and 'Initialising simulation' not in text
         and not sourceout.exists() and not receiverout.exists(), 'Missing-source early return did not preserve the no-output gate')

    spec = importlib.util.spec_from_file_location('retained_geometry_reader', T / 'support/lian_collapse_geometry_review_r1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Main-guarded retained VTK parser, not r1 portable output.
    vtk = module.vtk
    retained = T / 'outputs/lian_collapse_geometry_r1/CaseLianSaturatedColumnCollapse_geometry_r1'
    oldxyz, oldfields = vtk(Path(str(retained) + '_All.vtk'))
    oldnormalxyz, oldnormalfields = vtk(Path(str(retained) + '_Normals.vtk'))
    powershell = str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
    # The identical BAT substitution statement; the source path is planned and
    # absent. No PRE is fabricated and GenCase does not certify or load it.
    substitution = "try { $t=[IO.File]::ReadAllText($env:template); if(([regex]::Matches($t,'__GRAVITY_PRELOAD_STATE__')).Count -ne 1){throw 'Statefile marker differs'}; $t=$t.Replace('__GRAVITY_PRELOAD_STATE__',[Security.SecurityElement]::Escape($env:prestate)); [IO.File]::WriteAllText($env:prepared,$t,(New-Object Text.UTF8Encoding($false))) } catch { Write-Error $_; exit 1 }"
    launcher = (root / 'support/run_lian_collapse_shared_r2_win64.bat').read_text(encoding='ascii')
    need('powershell -NoProfile -Command "' + substitution + '"' in launcher, 'Delivered substitution statement changed')
    for group, cohesion, psi, sf in [('PRELOAD', 5000., 0., 0.), ('psi0', 5000., 0., 0.),
                                      ('psi2p5', 5000., 2.5, .2), ('psim5', 7500., -5., .2)]:
        stem = SOURCE if group == 'PRELOAD' else f'CaseLianSaturatedColumnCollapse_{group}_shared_r2'
        seedout = OUT / ('GenCase_' + group)
        seedout.mkdir()
        prefix = seedout / stem
        definition = root / (stem + '_Def.xml')
        if group != 'PRELOAD':
            prepared = seedout / (stem + '_Def.xml')
            env = dict(os.environ, template=str(definition), prepared=str(prepared),
                       prestate=str(sourceout / 'data' / proof['last_part']))
            calls.append(invoke('substitute_' + group, [powershell, '-NoProfile', '-Command', substitution], root, env=env))
            definition = prepared
        calls.append(invoke('GenCase_' + group,
                            [str(runtime / 'GenCase_win64.exe'), str(definition.with_suffix('')), str(prefix), '-save:all'], root))
        r = ET.parse(str(prefix) + '.xml').getroot()
        particles = r.find('execution/particles')
        need(particles is not None and int(particles.get('np')) == 7060, 'Actual particle registry differs')
        blocks = [x for x in particles if x.tag in ('fixed', 'fluid')]
        need([(x.tag, int(x.get('mk')), int(x.get('count'))) for x in blocks]
             == [('fixed', 10, 255), ('fixed', 11, 1545), ('fixed', 12, 260), ('fluid', 1, 5000)], 'Actual MK/counts differ')
        xyz, fields = vtk(Path(str(prefix) + '_All.vtk'))
        normalxyz, normalfields = vtk(Path(str(prefix) + '_Normals.vtk'))
        need(np.array_equal(xyz, oldxyz) and set(fields) == set(oldfields)
             and all(np.array_equal(fields[k], oldfields[k]) for k in fields), 'Actual VTK geometry/IDs differ')
        need(np.array_equal(normalxyz, oldnormalxyz) and set(normalfields) == set(oldnormalfields)
             and all(np.array_equal(normalfields[k], oldnormalfields[k]) for k in normalfields), 'Actual VTK normals differ')
        soils = {q.tag: q.get('value') for q in r.findall('.//soils/*')}
        hm = {q.tag: q.get('value') for q in r.findall('.//hydromechanics/*')}
        params = {q.get('key'): q.get('value') for q in r.findall('.//parameter')}
        event = r.find('.//gravitypreload')
        slip = {int(q.get('mkbound')): int(q.get('slipmode')) for q in r.findall('.//mdbcslip/bound')}
        need(all(float(soils[k]) == v for k, v in dict(coh=cohesion, dlt=psi, DilationDecay=sf,
             coh_r=1000, n_coh=5, MaterialReturn=1, phi=25, phi_r=25, n_phi=0, ModulusE=20e6, PRvs=.33).items()), 'Actual material settings differ')
        need(all(float(hm[k]) == v for k, v in dict(HydroMech=1, HydroMechDynamicSeepage=1, HydroMechConductivityModel=1,
             HydroMechConductivityCk=2, HydroMechInitZ=2, HydroMechFreeSeepage=1,
             HydroMechDrainage=0, PoreShepardRegularization=1, PoreShepardInterval=40,
             PoreWaterRho=1000, PoreWaterBulkModulus=1e9, Porosity=.35,
             HydraulicConductivity=.0002).items()) and hm['HydroMechInitMode'] == 'ConstantZ', 'Actual hydraulic settings differ')
        need(all(float(params[k]) == v for k, v in dict(TimeMax=13, TimeOut=.01, DtFixed=2.5e-6,
             SavePosDouble=1, SoilDamping=1, SoilDampingCoef=.02, PartsOutMax=0,
             StepAlgorithm=2, Kernel=1, DPCtes=3, SoilHourglassXi=0, SoilBoundaryDerivativeSPR=0,
             Shifting=0, DensityDT=0, RhopOutMin=700, RhopOutMax=3000).items())
             and float(event.get('time')) == 10 and event.get('release_mkbound') == '2'
             and slip == {0: 3, 1: 2, 2: 3}, 'Actual event/timing/slip settings differ')
        if group == 'PRELOAD':
            need(event.get('elastic_source') == 'true' and event.get('statefile') is None, 'Source role differs')
        else:
            need(event.get('elastic_source') is None and event.get('statefile') == str(sourceout / 'data' / proof['last_part'])
                 and MARKER not in definition.read_text(encoding='utf-8'), 'Actual receiver statefile substitution differs')
        need(all(Path(str(prefix) + suffix).is_file() for suffix in ('.xml', '.bi4', '_Normals.nbi4')), 'Fresh GenCase seed incomplete')
        geometries.append({'group': group, 'actual_total': 7060, 'actual_soil': 5000, 'actual_fixed': 2060,
                           'geometry_and_normals_VTK_equal_retained': True, 'double_BI4_bit_equality_claimed': False,
                           'definition': stat(definition), 'generated_companion': stat(str(prefix) + '.xml'),
                           'statefile_is_planned_not_present_or_certified': group != 'PRELOAD'})
    need(before == [stat(archive), stat(manifest_path)]
         and payload_before == [stat(root / x['entry']) for x in manifest['files']], 'Package/payload changed during portable check')
    need(not sourceout.exists() and not receiverout.exists(), 'Physical output unexpectedly appeared')
    save(CHECK, {'stage': TAG, 'passed': True, 'fresh_CRC_extraction': True, 'archive': before[0],
                 'manifest': before[1], 'extracted_root': str(root), 'calls': calls, 'GenCase_groups': geometries,
                 'CPU_GPU_help_exit0': True, 'missing_source_CMD_exit1_no_receiver_out': True,
                 'missing_source_solver_not_reached_by_reviewed_early_return': True, 'kernel_process_event_trace_claimed': False,
                 'r1_portable_extraction_consumed': False, 'physical_solver_updates': 0, 'native_decoder_invoked': False,
                 'actual10s_elastic_source_certified': False, 'full13s_physical_acceptance': False, 'extra_SHA_scans': 0})
    print(json.dumps({'passed': True, 'check': str(CHECK), 'GenCase_groups': 4,
                      'help_targets': 2, 'missing_source_exit': 1, 'physical_solver_updates': 0}), flush=True)


if __name__ == '__main__':
    main()
