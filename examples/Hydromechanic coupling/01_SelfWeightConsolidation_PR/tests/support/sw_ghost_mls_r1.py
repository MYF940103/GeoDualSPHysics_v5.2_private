"""Offline fixed-wall MLS screen. No solver, build, integration, or acceptance.

CPU-double and GPU-packed-float arithmetic are IEEE/numpy surrogates, not actual
compiled CPU/CUDA bits or neighbor accumulation order. Periodic images reproduce
this case's uniform x-periodic cell only. The optional repair is an OFFLINE
comparison: retain W(0), use its zero gradient, and do not alter distances.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess

import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
READER = TESTS / 'outputs/sw_native_r1/ReadSelfWeightNative.exe'
SOURCES = [REPO / 'src/source' / name for name in [
    'JSph.cpp', 'JSphCpu.cpp', 'JSphGpu_ker.cu', 'JSphGpuSimple_ker.cu',
    'FunSphKernel.h', 'FunSphKernel_iker.h', 'JCellSearch_inline.h',
    'JCellSearch_iker.h', 'JBinaryData.h', 'JBinaryData.cpp', 'JPartDataBi4.cpp']]


def bound(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def metadata(path):
    """Parse only the root scalar block, following JBinaryData::OutItemBase/Value.

    No byte-name searching in array payloads. DatBool occupies a native int.
    The supported input is the retained little-endian JPartDataBi4 format.
    """
    data = Path(path).read_bytes()
    assert data.startswith(b'#FileJBD JPartDataBi4') and data[60] == 0
    offset = 64

    def get(fmt):
        nonlocal offset
        result = struct.unpack_from('<' + fmt, data, offset)
        offset += struct.calcsize('<' + fmt)
        return result[0] if len(result) == 1 else result

    def text():
        nonlocal offset
        size = get('I')
        assert 0 <= size <= len(data) - offset
        result = data[offset:offset + size].decode('utf8')
        offset += size
        return result

    size = get('I'); item_end = offset + size
    assert text() == '\nITEM\n' and text() == 'JPartDataBi4'
    get('i'); get('i'); text(); text()  # hide flags and formatting strings
    arrays, items, scalar_bytes = get('I'), get('I'), get('I')
    assert offset == item_end and scalar_bytes > 0
    scalar_end = offset + scalar_bytes
    assert text() == '\nVALUES'
    count = get('I'); values = {}; types = {}
    formats = {2: 'i', 3: 'b', 4: 'B', 5: 'h', 6: 'H', 7: 'i', 8: 'I',
               9: 'q', 10: 'Q', 11: 'f', 12: 'd', 20: 'iii', 21: 'III',
               22: 'fff', 23: 'ddd'}
    for _ in range(count):
        name, datatype = text(), get('i')
        assert name not in values and (datatype == 1 or datatype in formats)
        values[name] = text() if datatype == 1 else get(formats[datatype])
        types[name] = datatype
        assert offset <= scalar_end
    assert offset == scalar_end
    for name in ['MapPosMin', 'MapPosMax', 'PeriXinc']:
        assert types[name] == 23
    assert types['PeriMode'] == 7 and values['PeriMode'] == 1
    return values, dict(root_arrays=arrays, root_items=items, root_values=count,
                        scalar_start=item_end, scalar_end=scalar_end)


def vtk_points(path):
    data = Path(path).read_bytes()
    match = re.search(rb'\nPOINTS (\d+) (float|double)\n', data)
    assert data.startswith(b'# vtk DataFile') and b'\nBINARY\n' in data and match
    count = int(match[1]); kind = match[2].decode()
    points = np.frombuffer(data, dtype='>f4' if kind == 'float' else '>f8',
                           count=3 * count, offset=match.end()).astype(float).reshape(-1, 3)
    return data, points, kind


def ghost_geometry(path):
    data, positions, kind = vtk_points(path)
    count = len(positions)
    assert count == 40 and kind == 'double'
    def array(pattern, dtype, size):
        match = re.search(pattern, data); assert match
        return np.frombuffer(data, dtype=dtype, count=size, offset=match.end()).copy()
    ids = array(rb'SCALARS Idp unsigned_int\nLOOKUP_TABLE default\n', '>u4', count)
    normals = array(rb'\nNormal 3 40 float\n', '>f4', count * 3).astype(float).reshape(-1, 3)
    assert np.array_equal(np.sort(ids), np.arange(40)) and np.isfinite(normals).all()
    order = np.argsort(ids)
    return positions[order], normals[order]


def packed(points, origin, size):
    distance = points - origin
    cells = np.maximum((distance / size).astype(np.int64), 0)
    remainder = (distance - float(size) * cells).astype(np.float32)
    return cells, remainder


def kernel(rr2, h, awen, bwen, repair):
    radius = np.sqrt(rr2, dtype=np.float32)
    q = (radius / np.float32(h)).astype(np.float32)
    w1 = (np.float32(1) - np.float32(.5) * q).astype(np.float32)
    w2 = (w1 * w1).astype(np.float32)
    with np.errstate(divide='ignore', invalid='ignore'):
        fac = ((((bwen * q).astype(np.float32) * w2).astype(np.float32)
                * w1).astype(np.float32) / radius).astype(np.float32)
    wab = (((awen * (q + q + np.float32(1))).astype(np.float32)
            * w2).astype(np.float32) * w2).astype(np.float32)
    if repair:
        fac[rr2 == 0] = np.float32(bwen / np.float32(h))
    return wab, fac


def selftest():
    rr = np.array([0., .0001], dtype=np.float32)
    raw, rawfac = kernel(rr, .018, np.float32(1719.), np.float32(-477572.), False)
    fixed, fixedfac = kernel(rr, .018, np.float32(1719.), np.float32(-477572.), True)
    assert np.array_equal(raw, fixed) and raw[0] > 0 and np.isnan(rawfac[0])
    assert np.isfinite(fixedfac).all() and rawfac[1] == fixedfac[1]
    return dict(passed=True, files_written=False, programs_started=False)


def matrix_row(index, ghosts, cloud, rho, excess, p0, origin, size, h, mass, model, repair):
    if model == 'cpu_double':
        displacement = ghosts[index] - cloud
        rr2 = np.sum(displacement * displacement, axis=1).astype(np.float32)
    else:
        gc, gr = packed(ghosts[index:index + 1], origin, size)
        pc, pr = packed(cloud, origin, size)
        displacement = (gr[0] - pr + np.float32(size) * (gc[0] - pc).astype(np.float32)).astype(np.float32)
        rr2 = np.sum(displacement * displacement, axis=1, dtype=np.float32)
    mask = (rr2 <= np.float32(size * size)) & (rho > 0)
    d, r2 = displacement[mask].astype(float), rr2[mask]
    wab, fac = kernel(r2, h, np.float32(.557 / h**2), np.float32(-2.7852 / h**3), repair)
    volume = (np.float32(mass) / rho[mask].astype(np.float32)).astype(np.float32).astype(float)
    weight = wab.astype(float) * volume
    with np.errstate(invalid='ignore'):
        grad = fac.astype(float)[:, None] * d * volume[:, None]
        matrix = np.array([[weight.sum(), (d[:, 0] * weight).sum(), (d[:, 2] * weight).sum()],
                           [grad[:, 0].sum(), (d[:, 0] * grad[:, 0]).sum(), (d[:, 2] * grad[:, 0]).sum()],
                           [grad[:, 2].sum(), (d[:, 0] * grad[:, 2]).sum(), (d[:, 2] * grad[:, 2]).sum()]])
        rhs = np.array([(weight * excess[mask]).sum(),
                        (grad[:, 0] * excess[mask]).sum(), (grad[:, 2] * excess[mask]).sum()])
        determinant = float(np.linalg.det(matrix))
    use_mls = abs(determinant) >= 1e-3
    estimated_excess = float(np.linalg.solve(matrix, rhs)[0]) if use_mls else float(rhs[0] / matrix[0, 0])
    return dict(bound_id=index, model=model, zero_gradient_repair=repair, neighbor_count=int(mask.sum()),
                minimum_rr2_m2=float(r2.min()), coincident_count=int((r2 == 0).sum()),
                nonfinite_fac_count=int((~np.isfinite(fac)).sum()), matrix_finite=bool(np.isfinite(matrix).all()),
                determinant=determinant, determinant_finite=bool(np.isfinite(determinant)),
                branch='MLS' if use_mls else 'zero_order', sum_weights=float(matrix[0, 0]),
                estimated_excess_pa=estimated_excess, estimated_pressure_pa=float(np.float32(p0[index] + estimated_excess)))


def run(args):
    assert args.part >= 0 and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_]*', args.output)
    job = Path(args.job).resolve(); reader = Path(args.reader).resolve()
    output = TESTS / 'figures' / (args.output + '.csv')
    check = TESTS / 'logs' / (args.output + '.check.json')
    assert job.is_dir() and not output.exists() and not check.exists()
    native_path = job / 'data' / f'Part_{args.part:04d}.bi4'
    geometry_path, domain_path = job / 'CfgInit_NormalsGhost.vtk', job / 'CfgInit_Domain.vtk'
    inputs = [bound(p) for p in [__file__, reader, TESTS / 'support/read_selfweight_native_r1.cpp',
                                native_path, geometry_path, domain_path] + SOURCES]
    decode = subprocess.run([str(reader), str(job / 'data'), str(args.part)], capture_output=True, check=True)
    a = pd.read_csv(io.BytesIO(decode.stdout), float_precision='round_trip')
    assert len(a) == 1040 and len(a.columns) == 38 and np.array_equal(a.id, np.arange(1040))
    assert np.isfinite(a.to_numpy(dtype=float)).all() and a.rho.gt(0).all()
    assert a.is_boundary.iloc[:40].eq(1).all() and a.is_boundary.iloc[40:].eq(0).all()
    meta, header = metadata(native_path)
    h, mass = float(meta['H']), float(meta['MassFluid'])
    size = float(np.float32(2 * h)); origin = np.array(meta['MapPosMin']); origin[0] -= size
    increment = np.array(meta['PeriXinc'])
    assert increment[0] == meta['MapPosMin'][0] - meta['MapPosMax'][0]
    assert np.array_equal(increment[1:], [0., 0.]) and abs(increment[0] + .1) < 1e-15
    positions, normals = ghost_geometry(geometry_path)
    assert np.array_equal(positions, a[['x', 'y', 'z']].to_numpy()[:40])
    _, domain, domain_kind = vtk_points(domain_path); assert len(domain) % 8 == 0
    box_minima = domain.reshape(-1, 8, 3).min(axis=1)
    tolerance = 3 * np.maximum(np.abs(np.spacing(box_minima.astype(np.float32))).astype(float), 1e-12)
    assert ((abs(box_minima - origin) <= tolerance).all(axis=1)).any()
    soil = a.iloc[40:]; xyz = soil[['x', 'y', 'z']].to_numpy(); ghosts = positions + normals
    cloud = np.concatenate([xyz + shift * increment for shift in [-1, 0, 1]])
    rho = np.tile(soil.rho.to_numpy(), 3)
    excess = np.tile(soil.pressure.to_numpy() - soil.porepress0.to_numpy(), 3)
    rows = []
    for model in ['cpu_double', 'gpu_packed_float']:
        for repair in [False, True]:
            for i in range(40):
                row = matrix_row(i, ghosts, cloud, rho, excess, a.porepress0.to_numpy(), origin, size, h, mass, model, repair)
                row.update(time_s=float(a.time_s.iloc[0]), saved_step=int(a.saved_step.iloc[0]),
                           observed_pressure_pa=float(a.pressure.iloc[i]), observed_p0_pa=float(a.porepress0.iloc[i]),
                           observed_excess_native_pa=float(a.excess_native.iloc[i]))
                rows.append(row)
    assert all(bound(r['path']) == r for r in inputs), 'An input changed during offline analysis'
    with output.open('x', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    summaries = [dict(model=model, zero_gradient_repair=repair,
                      mls_count=sum(r['branch'] == 'MLS' for r in rows if r['model'] == model and r['zero_gradient_repair'] == repair),
                      nonfinite_determinant_count=sum(not r['determinant_finite'] for r in rows if r['model'] == model and r['zero_gradient_repair'] == repair))
                 for model in ['cpu_double', 'gpu_packed_float'] for repair in [False, True]]
    clean = [{k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.items()} for r in rows]
    result = dict(analysis_completed=True, physical_acceptance=False, solver_started=False,
                  surrogate_not_actual_compiled_bits=True, periodic_scope='fixed axis-X case01 only; explicit native images',
                  limitations=['numpy reductions/solve are not production accumulation/inversion or GPU FMA',
                               'saved state is not necessarily a pre/post-Shepard event state',
                               'initial geometry cannot alone prove the dynamic cause'],
                  inputs=inputs, native_metadata_header=header, map_real_min=meta['MapPosMin'], map_padded_min=origin.tolist(),
                  domain_vtk_point_storage=domain_kind, domain_box_minima=box_minima.tolist(), poscellsize=size,
                  time_s=float(a.time_s.iloc[0]), part=args.part, summaries=summaries, rows=clean, csv=bound(output))
    with check.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(check=str(check), summaries=summaries), allow_nan=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selftest', action='store_true', help='Read-only synthetic zero-radius test; no reader or files')
    parser.add_argument('--job', help='Existing native job output directory; no solver is run')
    parser.add_argument('--part', type=int, help='Existing native PART index')
    parser.add_argument('--reader', default=str(READER))
    parser.add_argument('--output', help='Fresh analysis tag: tests/figures/TAG.csv and tests/logs/TAG.check.json')
    args = parser.parse_args()
    if args.selftest:
        assert args.job is None and args.part is None and args.output is None
        print(json.dumps(selftest()))
    elif args.job is None and args.part is None and args.output is None:
        parser.print_help()
    else:
        assert args.job is not None and args.part is not None and args.output is not None
        run(args)
