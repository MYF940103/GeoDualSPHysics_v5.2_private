"""Eleven saved post-release geometries; offline wall-fit risk, not a GPU replay."""
import argparse
import csv
import json
import math
import struct
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree
from upl_c08_fsmask_r1 import SCHEMA, TYPES, need

T = Path(__file__).resolve().parents[1]
TAG = 'upl_c08_wall_geometry_r1'
H = np.float32(.048)
RADIUS = np.float32(np.float32(2)*H)
R2 = float(np.float32(RADIUS*RADIUS))
LOWER = float(np.float32(1e-18))
SOLID0 = 1-float(np.float32(.35))
VOL0 = float(np.float32(3.316))/2072.5
# KDTree broad phase only; all memberships use the original predicates below.
SEARCH = math.nextafter(math.sqrt(float(np.nextafter(np.float32(R2), np.float32(np.inf))))*(1+4*np.finfo(np.float32).eps), math.inf)


def stat(p):
    p = Path(p).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def table(p):
    with Path(p).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def normals_vtk(path):
    """Read the actual initialized B/float Normal/ID export, not GenCase normals."""
    types = {'float': np.dtype('>f4'), 'double': np.dtype('>f8'),
             'unsigned_int': np.dtype('>u4'), 'unsigned_short': np.dtype('>u2')}
    with path.open('rb') as f:
        def line():
            s = f.readline()
            while s in (b'\n', b'\r\n'): s = f.readline()
            return s.decode('ascii').strip().split()
        def array(kind, count):
            dt = types[kind]; b = f.read(dt.itemsize*count)
            need(len(b) == dt.itemsize*count, 'Truncated initialized-normal VTK')
            return np.frombuffer(b, dtype=dt).astype(dt.newbyteorder('='))
        need(f.readline().startswith(b'# vtk DataFile Version'), 'Expected legacy VTK')
        f.readline()
        need(line() == ['BINARY'] and line() == ['DATASET', 'POLYDATA'], 'Expected binary POLYDATA')
        head = line(); need(head == ['POINTS', '2060', 'double'], 'Actual B must retain double coordinates')
        x = array('double', 2060*3).reshape(2060, 3)
        need(line() == ['VERTICES', '2060', '4120'], 'Unexpected normal vertex layout')
        vertices = np.frombuffer(f.read(2060*8), dtype='>i4').reshape(2060, 2)
        need(np.all(vertices[:, 0] == 1) and np.array_equal(vertices[:, 1], np.arange(2060)), 'Normal vertices differ')
        need(line() == ['POINT_DATA', '2060'], 'Normal point count differs')
        need(line() == ['SCALARS', 'Idp', 'unsigned_int'] and line() == ['LOOKUP_TABLE', 'default'], 'Normal ID field differs')
        ids = array('unsigned_int', 2060)
        head = line(); need(head == ['FIELD', 'FieldData', '3'], 'Actual initialized fields differ')
        fields = {}
        for _ in range(3):
            name, nc, n, kind = line(); need(int(n) == 2060, 'Normal field count differs')
            fields[name] = array(kind, 2060*int(nc)).reshape(2060, int(nc))
        need(not f.read().strip(), 'Unexpected trailing normal VTK payload')
    order = np.argsort(ids); ids, x = ids[order], x[order]
    need(np.array_equal(ids, np.arange(2060)) and set(fields) == {'Mk', 'Normal', 'NormalSize'}, 'Full original wall IDs/fields required')
    normal = fields['Normal'][order]
    need(normal.dtype == np.dtype('float32') and np.isfinite(x).all() and np.isfinite(normal).all(), 'Expected finite float initialized normals')
    need(np.all(x[:, 1] == 0) and np.all(normal[:, 1] == 0) and np.all(np.count_nonzero(normal, axis=1) == 1), 'Only actual axis-aligned 2D walls handled')
    return x, normal.astype(float), fields['Mk'][order, 0]


def load(native, normals):
    files = [native/s for s in ('completion.json', 'typed22_layout.csv', 'typed22.bin', 'clocks.csv')]+[normals]
    before = [stat(p) for p in files]
    done = json.loads(files[0].read_text(encoding='utf-8'))
    need(done.get('passed') is True and done.get('samples') == 11 and done.get('typed_arrays') == 22, 'Closed eleven-frame partial native export required; failed solver is not accepted as complete')
    layout = table(files[1]); need(len(layout) == 22, 'Exactly22 native arrays required')
    names, formats, offsets, extent = ['time'], ['<f8'], [0], 8
    for row, (name, kind, nc) in zip(layout, SCHEMA):
        dt = TYPES[kind]
        need((row['array'], row['type'], int(row['components']), int(row['bytes_per_particle'])) == (name, kind, nc, dt.itemsize*nc), 'Original typed22 layout differs')
        names.append(name); formats.append((dt, (6800, nc)) if nc > 1 else (dt, (6800,)))
        offsets.append(extent); extent += 6800*nc*dt.itemsize
    with files[2].open('rb') as f: need(struct.unpack('<III', f.read(12)) == (6800, 22, 11), 'Actual native header differs')
    need(files[2].stat().st_size == 12+11*extent, 'Incomplete or extra native records')
    raw = np.memmap(files[2], mode='r', offset=12, shape=(11,), dtype=np.dtype(dict(names=names, formats=formats, offsets=offsets, itemsize=extent)))
    clocks = table(files[3]); need(len(clocks) == 11, 'Eleven actual saved clocks required')
    expected = np.r_[np.arange(1800), np.arange(2060, 7060)].astype(np.uint32)
    b, normal, mk = normals_vtk(normals)
    for part, (frame, clock) in enumerate(zip(raw, clocks)):
        need(np.array_equal(frame['Idp'], expected), 'Retired or missing/duplicate native ID')
        need(np.array_equal(frame['Posd'][:1800], b[:1800]), 'Initialized B differs from saved fixed positions')
        need(np.isfinite(frame['Posd']).all() and np.isfinite(frame['PoroVolumeRatio']).all() and np.all(frame['PoroVolumeRatio'] > SOLID0), 'Invalid geometry/J in retained saved state')
        need(int(clock['part']) == part and int(clock['completed_step']) == 4004000+4000*part and int(clock['saved_step'])+1 == int(clock['completed_step']), 'Unexpected saved global Step')
        need(struct.pack('<d', float(clock['time_s'])) == struct.pack('<d', float(frame['time'])) and float(clock['signed_dterror_s']) <= 1e-14 and clock['dterror_interval_empty'] == '0', 'Actual time/signed interval differs')
    return raw, clocks, b[:1800, [0, 2]], normal[:1800, [0, 2]], mk[:1800], before


def cubic(rr2):
    """Float32 source expression pattern; CUDA fast-math/FMA bit identity is not claimed."""
    hh = float(H); a1 = 10/(math.pi*7); a2double = a1/(hh*hh); a2 = np.float32(a2double); aa = a1/(hh*hh*hh)
    a24, c1, d1, c2 = map(np.float32, (.25*a2double, -3*aa, 9*aa/4, -3*aa/4))
    rr2 = np.float32(rr2); r = np.float32(np.sqrt(rr2)); q = np.float32(r/H)
    if r > H:
        t = np.float32(np.float32(2)-q); t2 = np.float32(t*t)
        return float(np.float32(a24*np.float32(t2*t))), float(np.float32(np.float32(c2*t2)/r))
    q2 = np.float32(q*q)
    w = np.float32(a2*np.float32(np.float32(1)+np.float32(np.float32(np.float32(.75)*q)-np.float32(1.5))*q2))
    fac = np.float32(0) if rr2 == 0 else np.float32(np.float32(np.float32(c1*q)+np.float32(d1*q2))/r)
    return float(w), float(fac)


def det3(m):
    a,b,c,d,e,f,g,h,i = m.ravel()
    return float(a*e*i+b*f*g+c*d*h-g*e*c-h*f*a-i*d*b)


def support(tree, soil, js, ids, at, original):
    ix = [k for k in sorted(tree.query_ball_point(at, SEARCH)) if np.float32(np.dot(at-soil[k], at-soil[k])) <= R2]
    m = np.zeros((3,3)); rhs = np.zeros(3); sumwab = submerged = 0.; nearest = None; nearest2 = math.inf; ties = 0; positive = 0
    for k in ix:  # Native-ID order is deterministic, not the unavailable GPU cell order.
        d = at-soil[k]; rr2 = float(np.dot(d,d)); w0, fac = cubic(rr2)
        vol = VOL0*float(js[k]); w = w0*vol; grad = fac*d*vol; row = np.array([w, grad[0], grad[1]])
        m += np.outer(row, np.r_[1., d]); rhs += row*float(js[k])
        sumwab += w; submerged -= vol*float(np.dot(d, fac*d)); positive += w0 > 0
        if rr2 < nearest2: nearest2, nearest, ties = rr2, k, 1
        elif rr2 == nearest2: ties += 1
    det = det3(m); active = submerged > 0 or sumwab >= 0  # Actual mDBC-Threshold=0.
    good = active and sumwab > 0 and math.isfinite(det) and abs(det) >= 1e-3
    out = dict(nodes=len(ix), positive_W_nodes=int(positive), sumwab=sumwab, submerged=submerged,
               det=det, cond_inf=float(np.linalg.cond(m, np.inf)),
               cond_hscaled_inf=float(np.linalg.cond(np.diag([1,float(H),float(H)])@m@np.diag([1,1/float(H),1/float(H)]), np.inf)),
               min_J=float(js[ix].min()) if ix else None, max_J=float(js[ix].max()) if ix else None,
               nearest_id=int(ids[nearest]) if nearest is not None else None, nearest_ties=ties,
               nearest_distance_m=math.sqrt(nearest2) if nearest is not None else None,
               geometry_gate=bool(good), Jfit=None, Jfit_saturated=None)
    if good:  # Never invert a fit below the unchanged original determinant gate.
        q = np.linalg.inv(m)@rhs
        jf = float(js[nearest]-np.dot(q[1:], at-soil[nearest])+np.dot(q[1:], at-original))
        out.update(Jfit=jf, Jfit_saturated=bool(math.isfinite(jf) and jf > SOLID0))
    return out, nearest


def clean(v):
    if isinstance(v, dict): return {k:clean(x) for k,x in v.items()}
    if isinstance(v, list): return [clean(x) for x in v]
    return None if isinstance(v, float) and not math.isfinite(v) else v


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native', type=Path, required=True); p.add_argument('--normals', type=Path, required=True)
    p.add_argument('--out-prefix', type=Path, default=T/'figures'/TAG); a = p.parse_args()
    paths = {k:Path(str(a.out_prefix)+s) for k,s in dict(csv='.csv', plot='.png', check='.check.json').items()}
    need(a.out_prefix.parent.is_dir() and not any(q.exists() for q in paths.values()), 'Existing outputs protected; fresh prefix required')
    started = time.perf_counter(); raw, clocks, b, normal, mk, before = load(a.native, a.normals)
    rows, summaries = [], []
    for part, frame in enumerate(raw):
        soil = np.asarray(frame['Posd'][1800:][:,[0,2]]); js = np.asarray(frame['PoroVolumeRatio'][1800:]); ids = np.asarray(frame['Idp'][1800:]); tree = cKDTree(soil)
        local = []
        for slot, (at, bn) in enumerate(zip(b, normal)):
            ix = sorted(tree.query_ball_point(at, SEARCH)); d = at-soil[ix]; rr = np.sum(d*d, axis=1); df = d.astype(np.float32)
            rf = np.float32(df[:,0]*df[:,0]+df[:,1]*df[:,1]); rc = rr.astype(np.float32)
            direct = (rr <= R2)&(rr >= LOWER); cast = (rc <= R2)&(rc >= LOWER); components = (rf <= R2)&(rf >= LOWER)
            if not np.any(direct|cast|components): continue
            gp = at+bn; first, nearest = support(tree, soil, js, ids, gp, gp)
            retry = None; centre = gp.copy()
            if not first['geometry_gate'] and nearest is not None and np.any(gp-soil[nearest] != 0):
                centre = gp-(gp-soil[nearest]); retry, _ = support(tree, soil, js, ids, centre, gp)
            final = retry if retry is not None else first
            row = dict(part=part, time_s=float(frame['time']), completed_step=int(clocks[part]['completed_step']), native_id=slot, mk=int(mk[slot]),
                       B_x_m=float(at[0]), B_z_m=float(at[1]), normal_x_m=float(bn[0]), normal_z_m=float(bn[1]), GP_x_m=float(gp[0]), GP_z_m=float(gp[1]),
                       B_double_nodes=int(direct.sum()), B_cast_rr2_nodes=int(cast.sum()), B_cast_component_nodes=int(components.sum()),
                       active_proxy=True, retry_attempted=retry is not None, retry_x_m=float(centre[0]), retry_z_m=float(centre[1]),
                       retry_shift_m=float(np.linalg.norm(centre-gp)), final_geometry_gate=final['geometry_gate'], final_Jfit_saturated=final['Jfit_saturated'])
            row.update({'primary_'+k:v for k,v in first.items()})
            row.update({'retry_'+k:(retry[k] if retry is not None else None) for k in first})
            rows.append(row); local.append(row)
        summaries.append(dict(part=part, time_s=float(frame['time']), active_proxy_count=len(local), inactive_proxy_count=1800-len(local),
                              primary_geometry_failed=sum(not r['primary_geometry_gate'] for r in local), retries=sum(r['retry_attempted'] for r in local),
                              final_geometry_failed=sum(not r['final_geometry_gate'] for r in local), final_Jfit_invalid=sum(r['final_Jfit_saturated'] is False for r in local),
                              nearest_tie_rows=sum(r['primary_nearest_ties'] > 1 for r in local)))
    need(rows and len(summaries) == 11, 'Empty or incomplete geometry diagnostic')
    with paths['csv'].open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    finalrows = [r for r in rows if r['part'] == 10]; finalsoil = raw[-1]['Posd'][1800:]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    ax[0].scatter(finalsoil[:,0], finalsoil[:,2], s=1, c='.75', label='saved soil')
    for key, color, marker, label in (('primary_geometry_gate','tab:orange','o','primary weak, retried'), ('final_geometry_gate','tab:red','x','final weak')):
        q = [r for r in finalrows if not r[key]]
        ax[0].scatter([r['GP_x_m'] for r in q], [r['GP_z_m'] for r in q], c=color, marker=marker, s=28, label=f'{label}: {len(q)}')
    ax[0].set(xlabel='x [m]', ylabel='z [m]', title='Last saved GP support risks', aspect='equal'); ax[0].legend(fontsize=8); ax[0].grid(alpha=.2)
    x = [r['time_s'] for r in summaries]
    for key, label in (('active_proxy_count','B support proxy'), ('primary_geometry_failed','primary weak'), ('final_geometry_failed','after one retry weak')):
        ax[1].plot(x, [r[key] for r in summaries], marker='o', markersize=3, label=label)
    ax[1].set(xlabel='Actual saved time [s]', ylabel='Wall samples', title='Eleven saved states, not failed substage'); ax[1].legend(fontsize=8); ax[1].grid(alpha=.2)
    fig.suptitle('Cubic float-kernel geometry diagnostic; no native C/Ace or exact GPU replay', fontsize=10)
    with paths['plot'].open('xb') as f: fig.savefig(f, format='png', dpi=170)
    plt.close(fig)
    need(all(stat(e['path']) == e for e in before), 'Consumed saved data changed')
    result = dict(stage=TAG, passed=True, frames=11, rows=len(rows), h_float=float(H), kernel_radius_squared=R2, determinant_limit=1e-3,
                  saved_state_summaries=summaries, source_stats=before, output_stats=[stat(paths[k]) for k in ('csv','plot')],
                  elapsed_s=time.perf_counter()-started, original_saved_data_modified=False, initialized_full_normals_used=True,
                  active_is_proximity_proxy_not_wetness=True, GPU_PosCell_and_cell_order_available=False, CUDA_fast_math_bit_equivalence=False,
                  native_C_or_total_Ace_available=False, stage1_C_or_Ace_replayed=False, exact_failed_stage_or_ID_identified=False,
                  solver_invocations=0, decoder_invocations=0, SHA_scans=0, physical_acceptance=False)
    with paths['check'].open('x', encoding='utf-8') as f: json.dump(clean(result), f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(clean(result), allow_nan=False))


if __name__ == '__main__': main()
