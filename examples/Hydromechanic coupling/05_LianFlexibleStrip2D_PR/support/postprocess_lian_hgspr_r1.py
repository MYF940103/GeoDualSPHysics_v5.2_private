"""Returned server HG+SPR run: native audit and material observables, no solver."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd

CASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE/'tests/scripts'))
from lian_release_r1 import native, bound, write_json, utc, READER
from postprocess_lian_release import weights
from lian_hg_short_r1 import hg_stats

TAG = 'lian_hgspr100_r1'
FOLDER = CASE/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out'
OUT = CASE/'figures'
LOG = CASE/'tests/logs'
SNAPSHOTS = [0, 10, 20, 60, 300, 1000, 2000]


def read(part):
    a = native(FOLDER, part)
    return part, a


def analyze():
    OUT.mkdir(exist_ok=True)
    receipt = LOG/(TAG+'.check.json')
    history_path = OUT/(TAG+'_history.csv')
    assert not receipt.exists() and not history_path.exists(), 'Never overwrite retained analysis'
    started = time.perf_counter()
    files = sorted((FOLDER/'data').glob('Part_*.bi4'))
    assert [p.name for p in files] == [f'Part_{i:04d}.bi4' for i in range(2001)]
    text = (FOLDER/'Run.out').read_text(errors='replace')
    assert 'Finished execution (code=0)' in text and 'NVIDIA RTX A6000' in text
    hg = hg_stats(text)
    assert hg['steps'] == 10000000
    initial = native(FOLDER, 0)
    assert len(initial) == initial.id.nunique() == 20301
    assert initial.pressure.eq(0).all()
    ids = initial.id.to_numpy()
    xyz = initial[['x', 'y', 'z']].to_numpy()
    probes = {'A': weights(initial, 0., 10.), 'B': weights(initial, 1.25, 8.75)}
    stencil = {name: [dict(native_id=int(ids[k]), x0_m=float(initial.x.iloc[k]),
        z0_m=float(initial.z.iloc[k]), weight=w) for k,w in points] for name,points in probes.items()}
    masks = {'left_normal': (np.isclose(initial.x, 0, atol=1e-9, rtol=0), 'x'),
        'right_normal': (np.isclose(initial.x, 20, atol=1e-9, rtol=0), 'x'),
        'bottom_normal': (np.isclose(initial.z, 0, atol=1e-9, rtol=0), 'z'),
        'bottom_tangent': (np.isclose(initial.z, 0, atol=1e-9, rtol=0), 'x')}
    rows, failures, sources, artifacts = [], [], [], []
    for p in [Path(__file__), READER, CASE/'support/paper_observables.json',
        CASE/'support/postprocess_lian_release.py', CASE/'tests/scripts/lian_release_r1.py',
        CASE/'tests/scripts/lian_hg_short_r1.py', FOLDER/'Run.out', FOLDER/'Run.csv',
        FOLDER/'data/Part_Head.ibi4', CASE/'CaseLianFlexibleStrip2D_PR_release_Def.xml',
        CASE/'support/server_manifest.json']:
        sources.append(bound(p))

    def save_csv(label, frame):
        p = OUT/(TAG+'_'+label+'.csv')
        assert not p.exists()
        frame.to_csv(p, index=False, float_format='%.17g')
        artifacts.append(bound(p))

    def inspect(part, a):
        t = float(a.time_s.iloc[0])
        dt = 1e-5
        source_time = max(0., t-dt)
        contact = a.x.abs().le(1.25)
        drained = a.fstype.isin([2, 3]) & ~contact
        active = source_time >= 1 and t > 0
        force = float(-(a.mass*a.load_az).sum())
        expected = 13000*min(1., source_time)
        checks = dict(ids=len(a)==20301 and np.array_equal(a.id, ids),
            finite=bool(np.isfinite(a.to_numpy()).all()), positive_density=bool(a.rho.gt(0).all()),
            elastic=bool(a.kplastic.eq(0).all()), no_exclusion=bool(a.nout.eq(0).all()),
            double_position_stress=bool(a.position_double.eq(1).all() and a.stress_double.eq(1).all()),
            load_observed=bool(a.load_available.eq(1).all()),
            geometry=bool(a.x.between(-.1,20.1).all() and a.z.between(-.1,10.1).all()),
            natural_step=bool(part==0 or (a.has_dterror.eq(1).all() and a.dterror_s.le(1e-14).all())),
            actual_time=abs(t-part*.05)<=1.1e-5,
            drainage=bool(not active or (drained.any() and a.pressure[drained].eq(0).all())),
            resultant=abs(force-expected)<.002,
            mass_h_dp=bool(np.array_equal(a[['mass','h','dp']],initial[['mass','h','dp']])))
        failures.extend(dict(part=part, actual_time_s=t, guard=k) for k,v in checks.items() if not v)
        assert checks['ids'] and checks['finite'], 'Cannot safely map malformed native data'
        displacement = a[['x','y','z']].to_numpy()-xyz
        total = a[['sigma_xx','sigma_yy','sigma_zz']].to_numpy()-a.pressure.to_numpy()[:,None]
        w = a[a.id.eq(1744)].iloc[0]
        row = dict(part=part, time_s=t, saved_step=int(a.saved_step.iloc[0]), source_prior_time_s=source_time,
            pressure_min_pa=float(a.pressure.min()), pressure_max_pa=float(a.pressure.max()),
            pressure_mean_pa=float(a.pressure.mean()), pressure_rms_pa=float(np.sqrt(np.mean(a.pressure**2))),
            vmax_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()),
            total_sigma_zz_min_pa=float(total[:,2].min()), total_sigma_zz_max_pa=float(total[:,2].max()),
            total_sigma_zz_rms_pa=float(np.sqrt(np.mean(total[:,2]**2))),
            sigma_zz_effective_rms_pa=float(np.sqrt(np.mean(a.sigma_zz**2))),
            force_N_m=force, expected_force_N_m=expected,
            loaded_count=int(a.load_az.abs().gt(0).sum()), drainage_active=active,
            potential_drained_count=int(drained.sum()),
            drained_abs_max_pa=float(a.pressure[drained].abs().max()) if active else None,
            dterror_s=float(a.dterror_s.iloc[0]), rho_min_kg_m3=float(a.rho.min()), rho_max_kg_m3=float(a.rho.max()),
            displacement_max_mm=float(1000*np.linalg.norm(displacement,axis=1).max()),
            id1744_x_m=float(w.x), id1744_pressure_pa=float(w.pressure),
            id1744_load_az=float(w.load_az), id1744_fstype=int(w.fstype), id1744_contact=bool(abs(w.x)<=1.25))
        for name,points in probes.items():
            row[name+'_pressure_pa']=sum(weight*float(a.pressure.iloc[k]) for k,weight in points)
            row[name+'_settlement_mm']=1000*sum(weight*float(initial.z.iloc[k]-a.z.iloc[k]) for k,weight in points)
            row[name+'_ux_mm']=1000*sum(weight*float(a.x.iloc[k]-initial.x.iloc[k]) for k,weight in points)
        for name,(mask,col) in masks.items():
            row[name+'_max_mm']=1000*float(abs(a.loc[mask,col]-initial.loc[mask,col]).max())
        if part in SNAPSHOTS:
            fields=pd.DataFrame(dict(id=a.id,x0_m=initial.x,y0_m=initial.y,z0_m=initial.z,
                x_m=a.x,y_m=a.y,z_m=a.z,depth0_m=10-initial.z,pressure_pa=a.pressure,
                sigma_zz_effective_pa=a.sigma_zz,total_sigma_zz_pa=total[:,2],
                settlement_mm=-1000*displacement[:,2],ux_mm=1000*displacement[:,0],
                speed_m_s=np.linalg.norm(a[['vx','vy','vz']],axis=1),kplastic=a.kplastic,fstype=a.fstype))
            save_csv(f'field_{part:04d}',fields)
        if part==2000:
            profile=[]
            for z in np.unique(initial.z):
                points=weights(initial,1.25,z)
                profile.append(dict(z0_m=float(z),depth0_m=10-float(z),
                    z_m=sum(weight*float(a.z.iloc[k]) for k,weight in points),
                    ux_m=sum(weight*float(a.x.iloc[k]-initial.x.iloc[k]) for k,weight in points),
                    pressure_pa=sum(weight*float(a.pressure.iloc[k]) for k,weight in points)))
            save_csv('horizontal_profile',pd.DataFrame(profile))
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        for first in range(0,2001,8):
            for part,a in pool.map(read,range(first,min(first+8,2001))):
                rows.append(inspect(part,a))
            if first%80==0:
                write_json(LOG/(TAG+'.progress.json'),dict(stage='offline_native_review',checked_frames=len(rows),
                    total_frames=2001,actual_time_s=rows[-1]['time_s'],failures=len(failures),updated_utc=utc()))
                print('Native review',len(rows),'/2001; guards failed',len(failures),flush=True)
    history=pd.DataFrame(rows)
    save_csv('history',history)
    save_csv('guard_failures',pd.DataFrame(failures,columns=['part','actual_time_s','guard']))
    print('Seal raw native hashes',flush=True)
    sources.extend(bound(p) for p in sorted((FOLDER/'data').iterdir()) if p.is_file())
    selected=history[history.part.isin([10,20,60,300,1000,1500,2000])]
    save_csv('summary',selected)
    write_json(receipt,dict(passed=not failures,native_safety_passed=not failures,utc=utc(),
        visual_review_passed=False,paper_reference_accuracy_accepted=False,full_cycle_half_tested=False,
        frames=2001,native_soil_ids=20301,actual_final_time_s=rows[-1]['time_s'],
        final_saved_step=rows[-1]['saved_step'],hg=hg,paper_material_stencils=stencil,
        max_resultant_error_N_m=float(abs(history.force_N_m-history.expected_force_N_m).max()),
        native_pressure_min_pa=float(history.pressure_min_pa.min()),
        final_observables=rows[-1],guard_failure_count=len(failures),
        script_wall_seconds=time.perf_counter()-started,sources=sources,artifacts=artifacts,
        limitations=['Paper SPH/FEM are numerical references, not an analytical solution.',
            '13-node 1.3-m nodal resultant is 4% above the ideal 1.25-m strip; unchanged.',
            'Initial material IDs/weights define A/B and x0=1.25-m profile; no moving nearest-node probes.',
            'No 100-s half-step test; only previously retained bounded short evidence.',
            'Source-clock drainage is not fixed-grid aligned; 0.05-s output omits 0.01-0.05-s paper detail.']))
    print(receipt,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['analyze'])
    args=parser.parse_args()
    analyze()
