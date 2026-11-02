"""Independent offline adoption of completed pair outputs; never rerun a solver."""
import csv
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

T = Path(__file__).resolve().parents[1]
P, A, U = 1023.9999974568686, 2.**-9, 7.589099058944216e-8
seen = {}

def item(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)

def state(folder, name):
    path = T/'outputs'/folder/name
    with path.open('rb') as stream:
        assert struct.unpack('<III', stream.read(12)) == (512, 33, 257)
    assert path.stat().st_size == 12+257*(1+512*33)*8
    raw = np.memmap(path, mode='r', dtype='<f8', offset=12, shape=(257, 1+512*33))
    assert np.array_equal(raw[:, 0], np.arange(257)*2.**-23)
    return raw[:, 1:].reshape(257, 512, 33)

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

dest = T/'logs'/'upl_gravity_periodic_r2_adoption.json'
assert not dest.exists()
c = 'upl_gravity_periodic_cpu_ReleaseCPU_c_r1_review'
h = 'upl_gravity_periodic_cpu_ReleaseCPU_h_r1_review'
zc = 'upl_gpu_perm_actual_CPU_variable_c_r1_review'
zh = 'upl_gpu_perm_actual_CPU_variable_h_r1_review'
pairs = []
for name, left, right, right_name in [('half', c, h, 'frame.bin'), ('frame_c', c, zc, 'physical.bin'), ('frame_h', h, zh, 'physical.bin')]:
    check = T/'logs'/('upl_gravity_periodic_'+name+'_r2.check.json')
    j = read_json(check)
    assert j['passed'] and all(j['gates'].values()) and not j['physical_acceptance']
    for e in j['inputs']+j['files']:
        key = e['path'].casefold()
        if key not in seen:
            seen[key] = item(e['path'])
        assert seen[key] == e
    x, y = state(left, 'frame.bin'), state(right, right_name)
    assert np.isfinite(x).all() and np.isfinite(y).all()
    d = x-y
    p = np.sqrt((d[:, :, 6]**2).mean(1))
    v = np.sqrt((d[:, :, 3:6]**2).sum(2).mean(1))/A
    u = np.sqrt((d[:, :, 25:28]**2).sum(2).mean(1))/U
    um = np.linalg.norm(d[:, :, 25:28], axis=2).max(1)*1000
    assert p.max() <= 5 and um.max() <= .005 and p.max()/P <= 1e-4 and v.max() <= 1e-4 and u.max() <= 1e-4
    assert [float(p.max()), float(v.max()), float(u.max()), float(um.max())] == [j[k] for k in ['max_pressure_RMS_Pa', 'max_velocity_RMS_over_A', 'max_material_u_RMS_over_Ustar', 'max_material_u_mm']]
    for suffix, count in [('.csv', 257), ('_fields.csv', 8481)]:
        with (T/'figures'/('upl_gravity_periodic_'+name+'_r2'+suffix)).open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == count
    pairs.append(dict(pair=name, check=item(check), pressure_RMS_max_Pa=float(p.max()), normalized_velocity_RMS_max=float(v.max()), normalized_material_u_RMS_max=float(u.max()), gates=j['gates']))

result = dict(passed=True, status='completed_r2_pair_outputs_independently_verified_and_adopted', script=item(__file__), pairs=pairs, bindings=list(seen.values()), verified_unique_bindings=len(seen), original_wrapper_shell_exit_codes=[1, 1, 1], original_analysis_typed_exit0_receipt_available=False, metadata_failure='Silent Python produced no Tee stdout file; outer receipt Get-Item failed after complete JSON/CSV/PNG. No original exit receipt or phantom stdout log is fabricated. A preliminary PowerShell adoption also failed exact CSV/JSON floating comparison; this independent binary64 Python calculation does not use that failed comparison.', solvers_rerun=False, completed_analysis_outputs_rerun=False, public_gravity_accepted=False, physical_acceptance=False)
with dest.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2, allow_nan=False)
    stream.write('\n')
print(json.dumps(dict(passed=True, verified_unique_bindings=len(seen), pairs=pairs)))
