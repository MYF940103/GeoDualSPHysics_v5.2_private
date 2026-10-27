"""Prepare/run one GenCase-only Cartesian sphere smoke; never runs the solver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import CASE, TESTS, REPO, R, DP, bound, write_json

TAG = 'cryer_cartesian_geom_r1'
SOURCE = TESTS/'configs/cryer_grad_peak_r1_Def.xml'
CONFIG = TESTS/'configs'/(TAG+'_Def.xml')
BAT = TESTS/'configs'/('x'+TAG+'_win64_GenCase.bat')
PREPARED = TESTS/'logs'/(TAG+'.inputs.json')
FOLDER = TESTS/'outputs'/TAG
GENCASE = REPO/'bin/windows/GenCase_win64.exe'


def coordinates():
    extent = int(np.ceil(R/DP)); axis = np.arange(-extent, extent+1)*DP
    x = np.stack(np.meshgrid(axis, axis, axis, indexing='ij'), axis=-1).reshape(-1,3)
    x = x[np.linalg.norm(x, axis=1)<=R+1e-12]
    assert len(x) == 33401 and len(np.unique(x, axis=0)) == len(x)
    return x


def expected_config(x):
    source = SOURCE.read_text(encoding='utf8')
    old = ('                    <setfrdrawmode auto="true" />\n'
        '                    <drawsphere radius="#radius">\n'
        '                        <point x="0" y="0" z="0" />\n'
        '                    </drawsphere>\n'
        '                    <setfrdrawmode auto="false" />')
    assert source.count(old) == 1
    points = '\n'.join('                        <point x="'+format(v[0],'.17g')+
        '" y="'+format(v[1],'.17g')+'" z="'+format(v[2],'.17g')+'" />' for v in x)
    replacement = ('                    <setactive drawpoints="1" drawshapes="0" />\n'
        '                    <setfrdrawmode auto="true" />\n'
        '                    <drawpoints>\n'+points+'\n                    </drawpoints>\n'
        '                    <setfrdrawmode auto="false" />\n'
        '                    <setactive drawpoints="1" drawshapes="1" />')
    return source.replace(old, replacement)


def expected_bat():
    return ('@echo off\nsetlocal\ncd /d "%~dp0..\\.."\nset name='+TAG+
        '\nset dirout=tests\\outputs\\%name%\nset dirbin=../../../bin/windows\n'
        'set gencase="%dirbin%/GenCase_win64.exe"\nif exist "%dirout%" goto fail\n'
        '%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all\n'
        'if not "%ERRORLEVEL%" == "0" goto fail\nexit /b 0\n:fail\n'
        'echo Geometry generation aborted; retained outputs are never deleted.\nexit /b 1\n')


def exclusive(path, text):
    with path.open('x', encoding='utf8', newline='\n') as f: f.write(text)


def prepare():
    assert not any(p.exists() for p in [CONFIG, BAT, PREPARED, FOLDER]), 'Never overwrite/reuse a prepared smoke'
    x = coordinates(); xml = expected_config(x)
    parsed = ET.fromstring(xml)
    assert len(parsed.findall('.//drawpoints/point')) == len(x)
    exclusive(CONFIG, xml); exclusive(BAT, expected_bat())
    inputs = [Path(__file__), TESTS/'notes'/(TAG+'.md'), SOURCE, CONFIG, BAT, GENCASE,
        REPO/'bin/windows/DsphConfig.xml', Path(__file__).with_name('cryer_load_pair_r1.py'),
        REPO/'doc/xml_format/CaseTemplate.xml']
    runtime = REPO/'bin/windows/vcomp140.dll'
    if runtime.exists(): inputs.append(runtime)
    binary = x.astype('<f8').tobytes()
    record = dict(tag=TAG, scope='GenCase only; no solver command or physical admission.',
        inputs=[bound(p) for p in inputs], source_config=str(SOURCE),
        expected_coordinates=dict(node_count=len(x), shape=[len(x),3], dtype='<f8', bytes=len(binary),
            sha256=hashlib.sha256(binary).hexdigest(), ordering='meshgrid ij flattened in C order, radial mask',
            radius_max_m=float(np.linalg.norm(x, axis=1).max()), center_count=int((np.linalg.norm(x,axis=1)<=DP+1e-12).sum())),
        unchanged='All source XML outside the sphere block, including dummy8 and all physical parameters, is byte-text identical.',
        physical_acceptance=False, solver_executed=False)
    exclusive(PREPARED, json.dumps(record, indent=2)+'\n')
    print('Prepared XML/BAT/identity only; GenCase has not run.', flush=True)


def vtk_points(path):
    with path.open('rb') as f:
        assert f.readline().startswith(b'# vtk DataFile Version')
        f.readline(); mode = f.readline().strip(); assert f.readline().strip() == b'DATASET POLYDATA'
        header = f.readline().split(); assert header[0] == b'POINTS'
        count, storage = int(header[1]), header[2].decode('ascii')
        dtype = {'float':np.dtype('>f4'), 'double':np.dtype('>f8')}[storage]
        if mode == b'BINARY':
            values = np.frombuffer(f.read(count*3*dtype.itemsize), dtype=dtype).astype(float)
        else:
            assert mode == b'ASCII'; values = []
            while len(values)<count*3:
                line = f.readline(); assert line, 'Truncated ASCII VTK points'
                values.extend(map(float, line.split()))
            values = np.asarray(values)
        assert values.size == count*3 and np.isfinite(values).all()
        return values.reshape(count,3), storage


def sorted_points(x): return x[np.lexsort((x[:,2], x[:,1], x[:,0]))]


def run_geometry():
    run_path = TESTS/'logs'/(TAG+'.run.json'); check = TESTS/'logs'/(TAG+'.check.json')
    log = TESTS/'logs'/(TAG+'.log')
    assert os.name == 'nt' and not any(p.exists() for p in [FOLDER, run_path, check, log])
    prepared = json.loads(PREPARED.read_text())
    for entry in prepared['inputs']:
        assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']
    x = coordinates(); assert hashlib.sha256(x.astype('<f8').tobytes()).hexdigest() == prepared['expected_coordinates']['sha256']
    assert CONFIG.read_text(encoding='utf8') == expected_config(x) and BAT.read_text(encoding='utf8') == expected_bat()
    inventory = "Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'GenCase*' -and $_.CommandLine -match 'cryer_cartesian_geom_r1'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    active = subprocess.check_output(['powershell.exe','-NoProfile','-Command',inventory], text=True,
        creationflags=subprocess.CREATE_NO_WINDOW).strip()
    assert not active, 'An owned-tag GenCase is already active: '+active
    result = dict(tag=TAG, prepared_inputs=bound(PREPARED), command=[os.environ['ComSpec'],'/d','/c',str(BAT)],
        physical_acceptance=False, solver_executed=False, geometry_vtk_equivalence_passed=False,
        native_double_coordinates_verified=False, native_FSType_verified=False, owned_exited=False)
    exclusive(run_path, json.dumps(result, indent=2)+'\n')
    started = time.perf_counter(); child = None
    try:
        with log.open('xb') as stream:
            child = subprocess.Popen(result['command'], cwd=CASE, stdout=stream, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            result['owned_wrapper_pid'] = child.pid; result['exit_code'] = child.wait()
        result['owned_exited'] = True; assert result['exit_code'] == 0
        output_log = FOLDER/(TAG+'.out'); text = output_log.read_text(errors='replace')
        assert 'Finished execution (code=0)' in text
        result['gencase_version'] = re.search(r'GenCase v[^\r\n]+',text)[0]
        generated = ET.parse(FOLDER/(TAG+'.xml')).getroot()
        particles = generated.find('./execution/particles')
        assert particles.get('np') == '33409' and particles.get('nb') == '8'
        assert particles.find('fixed').get('count') == '8' and particles.find('fluid').get('count') == '33401'
        constants = {n:float(generated.find('./execution/constants/'+n).get('value'))
            for n in ['rhop0','dp','h','massfluid','massbound']}
        for key, expected in [('rhop0',2100.),('dp',DP),('h',1.8*DP),('massfluid',2100.*DP**3),('massbound',2100.*DP**3)]:
            assert abs(constants[key]-expected)<=1e-14*max(1.,abs(expected)), key
        actual, storage = vtk_points(FOLDER/(TAG+'_Fluid.vtk'))
        expected = x.astype(np.float32 if storage=='float' else np.float64).astype(float)
        assert len(actual) == 33401 and len(np.unique(actual,axis=0)) == len(actual)
        assert np.array_equal(sorted_points(actual), sorted_points(expected)), 'VTK point set was resampled/shifted'
        boundary, bs = vtk_points(FOLDER/(TAG+'_Bound.vtk'))
        axis = [.09, .09+DP]; dummy = np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1).reshape(-1,3)
        dummy = dummy.astype(np.float32 if bs=='float' else np.float64).astype(float)
        assert len(boundary) == 8 and np.array_equal(sorted_points(boundary),sorted_points(dummy)), 'Dummy8 changed'
        distances = cKDTree(actual).query(actual,k=2)[0][:,1]
        result.update(generated_XML_constants=constants,
            vtk_position_storage=storage, expected_lattice_radius_max_m=float(np.linalg.norm(x,axis=1).max()),
            vtk_radius_max_m=float(np.linalg.norm(actual,axis=1).max()),
            vtk_quantization_max_coordinate_error_m=float(np.abs(expected-x).max()),
            nearest_distance_m=dict(min=float(distances.min()),median=float(np.median(distances)),max=float(distances.max())),
            native_volume_ratio_from_XML_constants=float(33401*constants['massfluid']/constants['rhop0']/(4*np.pi*R**3/3)),
            generated_particle_metadata=particles.attrib,
            output_identity=[bound(p) for p in sorted(FOLDER.iterdir()) if p.is_file()])
        for entry in prepared['inputs']:
            assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']
        result['geometry_vtk_equivalence_passed'] = True
    except BaseException as error:
        if child is not None and child.poll() is None:
            stopped = subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            result['owned_stop_exit_code'] = stopped.returncode; child.wait(timeout=15)
        result.update(error=repr(error), traceback=traceback.format_exc(), owned_exited=child is None or child.poll() is not None)
    result.update(wall_seconds=time.perf_counter()-started, log=bound(log), limitations=[
        'GenCase-only geometry smoke. No solver, stress/pore/density evolution or physical/FSType/drainage acceptance.',
        'The reader supports solver PART files, not the generated case BI4. VTK coordinates are compared at their declared storage precision.',
        'Float VTK radius can exceed .05 by serialization rounding; strict native-double radius remains unverified, not silently accepted with a relaxed physical bound.',
        'Mass/rho/h above are generated-XML metadata, not read-back native per-particle arrays. The case BI4 is hashed and retained for a later native decode.',
        'GenCase free-particle warnings remain retained. Changed node/center/surface quadrature does not establish dynamic accuracy or shifting validity.'])
    write_json(run_path, result); exclusive(check, json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(geometry_vtk_equivalence_passed=result['geometry_vtk_equivalence_passed'],error=result.get('error'))),flush=True)
    if not result['geometry_vtk_equivalence_passed']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare',action='store_true'); modes.add_argument('--run-geometry',action='store_true')
    args = parser.parse_args()
    if args.prepare: prepare()
    elif args.run_geometry: run_geometry()
    else: parser.print_help()
