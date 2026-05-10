#!/usr/bin/env python3
"""Lightweight stress-path extractor for the reduced triaxial smoke output.

This script estimates mean effective stress p' and deviatoric stress q from the
saved Sigma_kk/Sigma_ij fields. It is intentionally simple and intended for
smoke inspection, not final paper-quality postprocessing.
"""
import argparse
import csv
import math
from pathlib import Path

def f(row, key, default=math.nan):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default

def read_rows(path):
    rows = []
    with path.open(newline='') as fp:
        for row in csv.DictReader(fp, delimiter=';'):
            if row.get('Idp'):
                rows.append(row)
    return rows

def frame_metrics(path, z0_min=None, z0_max=None):
    rows = read_rows(path)
    vals = []
    zs = []
    vels = []
    for r in rows:
        sxx, syy, szz = f(r, 'Sigma_kk.x'), f(r, 'Sigma_kk.y'), f(r, 'Sigma_kk.z')
        sxy, sxz, syz = f(r, 'Sigma_ij.x'), f(r, 'Sigma_ij.y'), f(r, 'Sigma_ij.z')
        # GeoDualSPHysics soil stresses are compression-negative in the current DP path.
        p_eff = -(sxx + syy + szz) / 3.0
        dev = [sxx + p_eff, syy + p_eff, szz + p_eff]
        j2 = 0.5 * (dev[0]**2 + dev[1]**2 + dev[2]**2) + sxy**2 + sxz**2 + syz**2
        q = math.sqrt(max(0.0, 3.0 * j2))
        vals.append((p_eff, q, f(r, 'PorePress'), f(r, 'ExcessPorePress')))
        z = f(r, 'Pos.z [m]')
        if math.isfinite(z):
            zs.append(z)
        vx, vy, vz = f(r, 'Vel.x [m/s]'), f(r, 'Vel.y [m/s]'), f(r, 'Vel.z [m/s]')
        if math.isfinite(vx) and math.isfinite(vy) and math.isfinite(vz):
            vels.append(math.sqrt(vx * vx + vy * vy + vz * vz))
    if not vals:
        return None
    n = len(vals)
    means = [sum(v[i] for v in vals) / n for i in range(4)]
    zmin, zmax = min(zs), max(zs)
    axial_strain = 0.0
    if z0_min is not None and z0_max is not None and z0_max > z0_min:
        axial_strain = ((zmax - zmin) - (z0_max - z0_min)) / (z0_max - z0_min)
    return {
        'frame': path.stem.replace('PartCsv_', ''),
        'count': n,
        'p_eff_mean': means[0],
        'q_mean': means[1],
        'porepress_mean': means[2],
        'excess_mean': means[3],
        'z_min': zmin,
        'z_max': zmax,
        'axial_strain_proxy': axial_strain,
        'velocity_max': max(vels) if vels else math.nan,
        'velocity_mean': sum(vels) / len(vels) if vels else math.nan,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', default='CaseUndrainedTriaxial_PR_Smoke_out/data')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    path = Path(args.path)
    files = sorted(path.glob('PartCsv_*.csv')) if path.is_dir() else [path]
    if not files:
        print('no PartCsv files')
        return 1

    first_rows = read_rows(files[0])
    z0 = [f(r, 'Pos.z [m]') for r in first_rows if math.isfinite(f(r, 'Pos.z [m]'))]
    z0_min, z0_max = min(z0), max(z0)
    records = [frame_metrics(p, z0_min, z0_max) for p in files]
    records = [r for r in records if r]
    if not records:
        print('no rows')
        return 1

    if args.out:
        with Path(args.out).open('w', newline='') as fp:
            writer = csv.DictWriter(fp, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

    last = records[-1]
    print('frame,count,p_eff_mean,q_mean,porepress_mean,excess_mean,axial_strain_proxy,velocity_max')
    print('{frame},{count},{p_eff_mean},{q_mean},{porepress_mean},{excess_mean},{axial_strain_proxy},{velocity_max}'.format(**last))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
