#!/usr/bin/env python3
"""Lightweight stress-path extractor for the reduced triaxial smoke output.

This script estimates mean effective stress p' and deviatoric stress q from the
saved Sigma_kk/Sigma_ij fields. It is intentionally simple and intended for
smoke inspection, not final paper-quality postprocessing.
"""
import csv, math, sys
from pathlib import Path

def f(row, key):
    return float(row[key])

def main(path):
    path = Path(path)
    rows = []
    with path.open(newline='') as fp:
        for row in csv.DictReader(fp, delimiter=';'):
            if row.get('Idp'):
                rows.append(row)
    vals = []
    for r in rows:
        sxx, syy, szz = f(r, 'Sigma_kk.x'), f(r, 'Sigma_kk.y'), f(r, 'Sigma_kk.z')
        sxy, sxz, syz = f(r, 'Sigma_ij.x'), f(r, 'Sigma_ij.y'), f(r, 'Sigma_ij.z')
        # GeoDualSPHysics soil stresses are compression-negative in the current DP path.
        p_eff = -(sxx + syy + szz) / 3.0
        dev = [sxx + p_eff, syy + p_eff, szz + p_eff]
        j2 = 0.5 * (dev[0]**2 + dev[1]**2 + dev[2]**2) + sxy**2 + sxz**2 + syz**2
        q = math.sqrt(max(0.0, 3.0 * j2))
        vals.append((p_eff, q, f(r, 'PorePress'), f(r, 'ExcessPorePress')))
    if not vals:
        print('no rows')
        return 1
    n = len(vals)
    means = [sum(v[i] for v in vals) / n for i in range(4)]
    print('count,p_eff_mean,q_mean,porepress_mean,excess_mean')
    print(f'{n},{means[0]},{means[1]},{means[2]},{means[3]}')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'CaseUndrainedTriaxial_PR_Smoke_out/data/PartCsv_0001.csv'))
