"""Bounded static FS3 counterfactual; one frozen read-only PART decoder, no solver."""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import csv
import ctypes
import hashlib
import io
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

T = Path(__file__).resolve().parents[1]
TAG = 'upl_cryer_fs_audit_r1'
NAME = 'CaseCryerProblem_PR_symc_nu030'
FOLDER = T.parent / (NAME + '_out')
CHECK = T / 'logs' / (TAG + '.check.json')
CALL = T / 'logs' / (TAG + '.reader.call.json')
CSV = T / 'figures' / (TAG + '.csv')
NOTE = T / 'notes' / (TAG + '.json')
PRIOR_SHA = 'b67debe21b06b020852ae381b9cbae418291bc11ce29ef2a913bac2b4743a042'
READER_SHA = '5d8fbeadc5f5b953eff85457c1bff690e22afc06a345d6d752113a1fa8f52502'
COLUMNS = 'time_s saved_step id x y z vx vy vz rho pressure sigma_xx sigma_yy sigma_zz sigma_xy sigma_yz sigma_xz kplastic load_ax load_ay load_az fstype normal_x normal_y normal_z load_available position_double stress_double mass dp h native_count nout has_dterror dterror_s'.split()
F32 = np.float32
ALMOSTZERO = F32(1e-18)


def need(ok, message):
    if not bool(ok):
        raise RuntimeError(message)


def entry(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def readjson(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def bounded_cpu():
    need(os.name == 'nt', 'This owner requires the reviewed Windows decoder environment')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    process = kernel.GetCurrentProcess()
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.GetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
    kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    allowed, system = ctypes.c_size_t(), ctypes.c_size_t()
    need(kernel.SetPriorityClass(process, 0x4000), 'Cannot select BELOW_NORMAL priority')
    need(kernel.GetProcessAffinityMask(process, ctypes.byref(allowed), ctypes.byref(system)), 'Cannot read CPU affinity')
    chosen = allowed.value & -allowed.value
    need(chosen and kernel.SetProcessAffinityMask(process, chosen), 'Cannot select one allowed logical CPU')
    return chosen


def seed_boundary(path):
    raw = Path(path).read_bytes()
    need(b'BINARY\nDATASET POLYDATA\nPOINTS 8 float\n' in raw, 'Unexpected frozen boundary VTK schema')
    def values(marker, dtype, count):
        need(raw.count(marker) == 1, 'Nonunique frozen VTK field: ' + repr(marker))
        return np.frombuffer(raw, dtype=dtype, count=count, offset=raw.index(marker) + len(marker)).copy()
    xyz = values(b'POINTS 8 float\n', '>f4', 24).astype('f8').reshape(8, 3)
    ids = values(b'SCALARS Idp unsigned_int\nLOOKUP_TABLE default\n', '>u4', 8)
    vel = values(b'Vel 3 8 float\n', '>f4', 24)
    rho = values(b'Rhop 1 8 float\n', '>f4', 8).astype('f8')
    kinds = values(b'Type 1 8 unsigned_char\n', 'u1', 8)
    need(np.array_equal(ids, np.arange(8)) and np.all(vel == 0) and np.all(kinds == 0), 'Seed dummy IDs/stationarity/type changed')
    need(np.isfinite(xyz).all() and np.isfinite(rho).all() and np.all(rho > 0), 'Invalid seed boundary fields')
    return xyz, rho


def umbrella(dr, ids, normal, h, radius2):
    """CPU float3D arithmetic model; sorted-ID witness, not historical cell/FMA replay."""
    n = normal.astype('f4')
    norm2 = F32(F32(n[0] * n[0] + n[1] * n[1]) + n[2] * n[2])
    result = dict(umbrella_checked=False, normal_norm2=float(norm2), normal_norm2_minus_cut=float(norm2) - float(F32(1e-12)),
                  umbrella_witness_id=None, umbrella_witness_branch=None, umbrella_found=False,
                  min_abs_far_rrq_minus_h=None, min_abs_near_angle_minus_cut=None, min_abs_branch_rr2_minus_2h2=None)
    if norm2 <= F32(1e-12):
        return result
    result['umbrella_checked'] = True
    d = dr.astype('f4')
    rr2 = F32(F32(d[:, 0] * d[:, 0] + d[:, 1] * d[:, 1]) + d[:, 2] * d[:, 2])
    keep = (rr2 <= radius2) & (rr2 >= ALMOSTZERO)
    d, rr2, ids = d[keep], rr2[keep], ids[keep]
    if not len(ids):
        return result
    split = F32(F32(F32(2) * h) * h)
    result['min_abs_branch_rr2_minus_2h2'] = float(np.min(np.abs(rr2.astype('f8') - float(split))))
    far = rr2 > split
    found = np.zeros(len(ids), dtype=bool)
    if far.any():
        q = F32(-d[far] - F32(h * n))
        q2 = F32(F32(q[:, 0] * q[:, 0] + q[:, 1] * q[:, 1]) + q[:, 2] * q[:, 2])
        rrq = np.sqrt(q2).astype('f4')
        result['min_abs_far_rrq_minus_h'] = float(np.min(np.abs(rrq.astype('f8') - float(h))))
        found[far] = rrq < h
    if (~far).any():
        near = d[~far]
        reciprocal = F32(F32(1) / np.sqrt(rr2[~far]).astype('f4'))
        dot = F32(F32(-near[:, 0] * n[0] - near[:, 1] * n[1]) - near[:, 2] * n[2])
        cosine = np.clip(F32(dot * reciprocal), F32(-1), F32(1))
        angle = np.arccos(cosine.astype('f8')).astype('f4')
        cut = F32(.785398)
        result['min_abs_near_angle_minus_cut'] = float(np.min(np.abs(angle.astype('f8') - float(cut))))
        found[~far] = angle < cut
    if found.any():
        witness = int(np.flatnonzero(found)[0])
        result.update(umbrella_found=True, umbrella_witness_id=int(ids[witness]), umbrella_witness_branch='far_q_inside' if far[witness] else 'near_angle')
    return result


def run():
    need(not any(p.exists() for p in (CHECK, CALL, CSV)), 'Fresh outputs required; old evidence is never overwritten')
    inputs = []
    def bind(expected):
        actual = entry(expected['path'])
        need(actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'].lower(), 'Bound input changed: ' + actual['path'])
        if not any(e['path'].casefold() == actual['path'].casefold() for e in inputs):
            inputs.append(actual)
        return Path(actual['path'])
    result = dict(stage=TAG, passed=False, physical_acceptance=False, solver_started=False, build_invoked=False,
                  decoder_invocations=0, workers=1, decoder_PosDiv_exported=False, fs_threshold_reconstructed=False,
                  counterfactual_static_mask_only=True, historical_GPU_0ULP_replay=False, legacy_OFF_modified=False,
                  correction_or_new_trajectory_admitted=False, inputs=inputs, files=[], failure=None)
    try:
        affinity = bounded_cpu()
        prior_path = T / 'logs' / 'cryer_full_native_r1.check.json'
        prior_e = entry(prior_path)
        need(prior_e['sha256'] == PRIOR_SHA, 'Frozen native summary check changed')
        bind(prior_e)
        prior = readjson(prior_path)
        need(prior['passed'] and prior['initial35_passed'] and prior['native_safety_passed'] and prior['checked_frames'] == 1065, 'Missing retained native-summary qualification')
        manifest = readjson(bind(prior['inputs_manifest']))
        def retained(path):
            matches = [e for e in manifest['inputs'] if Path(e['path']).resolve() == Path(path).resolve()]
            need(len(matches) == 1, 'Missing/nonunique retained file: ' + str(path))
            return bind(matches[0])
        cloud_entries = [e for e in prior['artifacts'] if Path(e['path']).name == 'cryer_full_native_r1_initial_cloud.csv']
        need(len(cloud_entries) == 1, 'Missing retained initial cloud')
        cloud_path = bind(cloud_entries[0])
        runtime = retained(FOLDER / (NAME + '.xml'))
        part = retained(FOLDER / 'data' / 'Part_0000.bi4')
        boundary = retained(FOLDER / (NAME + '_Bound.vtk'))
        reader = bind(prior['reader_program'])
        need(prior['reader_program']['sha256'].lower() == READER_SHA and prior['reader'] == prior['reader_program'], 'Wrong frozen native decoder')
        bind(prior['reader_source'])
        bind(entry(__file__)); bind(entry(NOTE))
        args = [str(reader), str(part.parent), '0']
        started = datetime.now(timezone.utc).isoformat()
        child = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        result['decoder_invocations'] = 1
        call = dict(program=prior['reader_program'], arguments=args[1:], started_utc=started, ended_utc=datetime.now(timezone.utc).isoformat(),
                    direct_native_call=True, owned_call_exited=True, exit_code=int(child.returncode), exit_code_from_owned_subprocess=True,
                    parent_and_child_affinity_mask=affinity, priority='BELOW_NORMAL', thread_environment={k: os.environ[k] for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')},
                    stdout_bytes=len(child.stdout), stdout_saved=False, stderr=child.stderr.decode('utf-8', errors='replace'), solver_invoked=False)
        seal(CALL, call)
        result['reader_call'] = entry(CALL)
        need(type(child.returncode) is int and child.returncode == 0, 'Owned read-only decoder failed')
        a = pd.read_csv(io.BytesIO(child.stdout), dtype='f8', float_precision='round_trip')
        del child
        cloud = pd.read_csv(cloud_path, float_precision='round_trip')
        need(list(a) == COLUMNS and len(a) == len(cloud) == 37173, 'Native/cloud schema or row count changed')
        ids = a.id.to_numpy(dtype='i8')
        need(np.array_equal(a.id, np.arange(8, 37181)) and np.array_equal(cloud.id, ids), 'Native material IDs changed')
        x = a[['x', 'y', 'z']].to_numpy(copy=True)
        x0 = cloud[['x0', 'y0', 'z0']].to_numpy(dtype='f8')
        need(np.array_equal(x.view('u8'), x0.view('u8')), 'Native XYZ not bit-identical to retained cloud')
        for native, saved in (('rho', 'rho0'), ('mass', 'mass0')):
            need(np.array_equal(a[native].to_numpy().view('u8'), cloud[saved].to_numpy(dtype='f8').view('u8')), 'Native/cloud ' + native + ' changed')
        fs = a.fstype.to_numpy(dtype='i8')
        need(np.array_equal(a.fstype, fs) and np.array_equal(cloud.fstype0, fs), 'Native initial FSType changed')
        need(np.all(a.time_s == 0) and np.all(a.saved_step == 0) and np.all(a.native_count == 37181), 'Not the retained initial PART')
        normal = a[['normal_x', 'normal_y', 'normal_z']].to_numpy()
        need(np.isfinite(x).all() and np.isfinite(normal).all() and np.all(a.rho > 0) and np.all(a.mass > 0), 'Invalid fields used by neighbor audit')
        xml = ET.parse(runtime).getroot()
        particles = xml.find('./execution/particles'); constants = xml.find('./execution/constants')
        need(particles is not None and constants is not None and particles.attrib['np'] == '37181' and particles.attrib['nb'] == '8', 'Runtime particle metadata changed')
        need(particles.find('fixed').attrib['begin'] == '0' and particles.find('fixed').attrib['count'] == '8' and particles.find('fluid').attrib['begin'] == '8' and particles.find('fluid').attrib['count'] == '37173', 'Runtime native blocks changed')
        dp = float(constants.find('dp').attrib['value']); h = F32(float(constants.find('h').attrib['value']))
        mass = F32(float(constants.find('massfluid').attrib['value']))
        need(np.all(a.dp == dp) and np.all(a.h.astype('f4') == h) and np.all(a.mass == float(mass)), 'Runtime/native dp/h/mass changed')
        bx, brho = seed_boundary(boundary)
        origin = float(xml.find('./execution/uservars/varnum[@name="dummyb"]').attrib['value'])
        corners = np.array([[origin + i * dp, origin + j * dp, origin + k * dp] for i in (0, 1) for j in (0, 1) for k in (0, 1)], dtype='f4').astype('f8')
        need(np.array_equal(bx[np.lexsort(bx.T[::-1])], corners), 'Actual seed dummy points differ from the runtime cube metadata')
        radius = F32(F32(2) * h); radius2 = F32(radius * radius)
        query_radius = float(np.sqrt(np.nextafter(radius2, F32(np.inf)))) * (1 + 16 * np.finfo('f4').eps)
        dummy_gap = min(float(np.sqrt(np.sum((x - p) ** 2, axis=1)).min()) for p in bx)
        need(dummy_gap > query_radius, 'Frozen seed dummy enters actual soil support')
        allx = np.vstack((x, bx)); allids = np.r_[ids, np.arange(8)]
        volumes = np.r_[a.mass.to_numpy() / a.rho.to_numpy(), float(F32(float(constants.find('massbound').attrib['value']))) / brho]
        need(np.isfinite(volumes).all() and np.all(volumes > 0), 'Nonpositive neighbor quadrature volume')
        tree = cKDTree(allx)
        coefficient = float(F32(F32(4) / F32(3))) * 3.141592
        old_nzero = F32(coefficient * float(radius2) * float(radius2) / (dp * dp * dp))
        alternative_nzero = F32(coefficient * float(radius2) * float(radius) / (dp * dp * dp))
        changed = candidates = kept3 = zero_neighbors3 = 0
        before = {str(k): int(np.count_nonzero(fs == k)) for k in np.unique(fs)}; after = dict(before)
        with CSV.open('x', encoding='utf-8', newline='') as stream:
            writer = None
            for i in range(len(ids)):
                selected = np.asarray(tree.query_ball_point(x[i], query_radius, workers=1), dtype='i8')
                selected = selected[np.argsort(allids[selected], kind='stable')]
                dr = x[i] - allx[selected]
                rr2 = ((dr[:, 0] * dr[:, 0] + dr[:, 1] * dr[:, 1]) + dr[:, 2] * dr[:, 2]).astype('f4')
                valid = (rr2 <= radius2) & (rr2 >= ALMOSTZERO) & (volumes[selected] > 0)
                count = int(valid.sum()); dummy_count = int(np.count_nonzero(valid & (allids[selected] < 8)))
                need(dummy_count == 0, 'Unexpected actual dummy neighbor')
                old_ratio = F32(old_nzero / F32(count)) if count else None
                alternative_ratio = F32(alternative_nzero / F32(count)) if count else None
                candidate = bool(fs[i] == 3 and count > 0 and not alternative_ratio < F32(.4))
                cf = int(fs[i])
                u = umbrella(dr, allids[selected], normal[i], h, radius2) if candidate else dict(umbrella_checked=False, normal_norm2=None, normal_norm2_minus_cut=None, umbrella_witness_id=None, umbrella_witness_branch=None, umbrella_found=False, min_abs_far_rrq_minus_h=None, min_abs_near_angle_minus_cut=None, min_abs_branch_rr2_minus_2h2=None)
                if candidate:
                    candidates += 1; cf = 0 if u['umbrella_found'] else 2
                    after['3'] -= 1; after[str(cf)] = after.get(str(cf), 0) + 1
                    changed += int(cf == 0)
                elif fs[i] == 3:
                    kept3 += int(count > 0); zero_neighbors3 += int(count == 0)
                row = dict(id=int(ids[i]), x0_m=float(x[i, 0]), y0_m=float(x[i, 1]), z0_m=float(x[i, 2]), actual_fstype=int(fs[i]), positive_volume_neighbors=count, dummy_neighbors=dummy_count,
                           cpu_R4_nzero=float(old_nzero), numerator_only_R3_nzero=float(alternative_nzero),
                           cpu_R4_ratio=None if old_ratio is None else float(old_ratio), numerator_only_R3_ratio=None if alternative_ratio is None else float(alternative_ratio),
                           R4_ratio_minus_cut=None if old_ratio is None else float(old_ratio) - float(F32(.4)), R3_ratio_minus_cut=None if alternative_ratio is None else float(alternative_ratio) - float(F32(.4)),
                           closest_abs_support_rr2_minus_R2=float(np.min(np.abs(rr2.astype('f8') - float(radius2)))),
                           native_normal_x=float(normal[i, 0]), native_normal_y=float(normal[i, 1]), native_normal_z=float(normal[i, 2]),
                           pre_threshold_lt_1p8_logically_inferred=bool(fs[i] == 3 and count > 0), native_fs_threshold_available=False,
                           counterfactual_umbrella_candidate=candidate, counterfactual_fstype=cf, counterfactual_active_surface=bool(cf in (2, 3)), **u)
                if writer is None:
                    writer = csv.DictWriter(stream, fieldnames=list(row)); writer.writeheader()
                writer.writerow(row)
        result.update(passed=True, initial_XYZ_ID_rho_mass_FSType_match=True, native_rows=len(ids), native_count=37181,
                      seed_dummy_ids=list(range(8)), seed_dummy_positions_m=bx.tolist(), seed_dummy_to_soil_min_distance_m=dummy_gap,
                      h_m=float(h), dp_m=dp, kernel_support_m=float(radius), kernel_support_squared_m2=float(radius2),
                      cpu_R4_nzero=float(old_nzero), numerator_only_R3_nzero=float(alternative_nzero), original_FSType_counts=before,
                      counterfactual_FSType_counts=after, original_FS3_positive_neighbors_retained3=kept3, original_FS3_zero_neighbors=zero_neighbors3,
                      counterfactual_umbrella_candidates=candidates, counterfactual_active_mask_removed=changed, CSV_rows=len(ids),
                      scope='Only actual FS3 with positive counted neighbors; FS0/1/2 unchanged. No PosDiv reconstruction, no physical or trajectory conclusion.')
    except Exception as exc:
        result.update(passed=False, failure=type(exc).__name__ + ': ' + str(exc))
    finally:
        try:
            for e in inputs:
                need(entry(e['path']) == e, 'Consumed input changed during audit: ' + e['path'])
            result['consumed_inputs_unchanged'] = True
        except Exception as exc:
            result.update(passed=False, consumed_inputs_unchanged=False, postcheck_failure=str(exc))
        result['files'] = [entry(p) for p in (CALL, CSV) if p.exists()]
        seal(CHECK, result)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='One read-only decoder and static FS3 geometry audit after root review')
    args = parser.parse_args()
    if not args.run:
        parser.print_help()
    else:
        raise SystemExit(run())
