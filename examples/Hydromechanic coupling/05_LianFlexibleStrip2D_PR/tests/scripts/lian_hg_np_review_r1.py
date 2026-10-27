"""Review native-ID HG operator regressions and the separate frozen oscillator."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from lian_release_r1 import TESTS, REPO, bound, utc, write_json

TAG='lian_hg_np_review_r1'


def verify_hashes(items):
    # PowerShell build manifests store SHA only; native manifests also store size.
    for e in items:
        current=bound(e['path'])
        assert current['sha256'].lower()==e['sha256'].lower(),e['path']
        if 'bytes' in e:assert current['bytes']==e['bytes'],e['path']


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    source=[bound(__file__)];checks={}
    for label,count in [('control',42),('release',58),('debug',58)]:
        p=TESTS/'logs'/f'lian_hg_np_{label}_r1.check.json';s=json.loads(p.read_text())
        assert s['passed'] and len(s['passed_cases'])==count and 'RTX 3050' in s['device']
        assert s['double_relative_plus_absolute_tolerance']==1e-8 and s['gpu_cache_required_max_ulp']==0
        assert all(m['max_error_over_limit']<=1 for m in s['metrics'].values())
        checks[label]=s;source.append(bound(p))
    logs=TESTS/'logs'
    old=logs/'lian_hg_np_control_r1.check.periodic.csv'
    new=logs/'lian_hg_np_release_r1.check.periodic.csv'
    assert bound(old)['sha256']==bound(new)['sha256']
    source.extend([bound(old),bound(new)])
    for config,label in [('Release','control_r1'),('Release','bounded_r1'),('Debug','bounded_r1')]:
        manifest=logs/f'lian_hg_np_{config}_{label}.build.json'
        b=json.loads(manifest.read_text(encoding='utf-8-sig'));assert b['built']
        assert bound(b['executable'])['sha256'].lower()==b['executable_sha256'].lower()
        verify_hashes(b['runtime']);source.append(bound(manifest))
        # Original source/object paths are mutable build inputs. Preserve the old
        # receipt, and verify changed old sources from the separately frozen copy.
        if label=='bounded_r1':verify_hashes(b['inputs'])
    frozen=json.loads((logs/'lian_hg_np_control_r1.snapshot.json').read_text(encoding='utf-8-sig'))
    for e in frozen:assert bound(e['Path'])['sha256'].lower()==e['Hash'].lower()
    source.append(bound(logs/'lian_hg_np_control_r1.snapshot.json'))
    mem=logs/'lian_hg_np_debug_r2.memcheck.log';text=mem.read_text(encoding='utf-16')
    assert 'ERROR SUMMARY: 0 errors' in text and '0 bytes leaked in 0 allocations' in text
    source.append(bound(mem))
    energy_path=TESTS/'figures/lian_hg_np_energy_r1.csv'
    energy=pd.read_csv(energy_path,float_precision='round_trip')
    assert len(energy)==129 and energy.step.tolist()==list(range(129))
    assert energy.energy_ratio.between(.999,1.001).all()
    assert abs((energy.kinetic+energy.potential-energy.total_energy)).max()<1e-15
    assert 'PASS frozen bounded oscillator' in (logs/'lian_hg_np_energy_r1.log').read_text(encoding='utf-16')
    source.extend([bound(energy_path),bound(logs/'lian_hg_np_energy_r1.log'),
        bound(logs/'lian_hg_energy_Release_bounded_r1.build.json')])
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    axes[0].plot(energy.time_s,energy.energy_ratio,color='#28618e',label='Total / initial energy')
    for limit in [.999,1.001]:axes[0].axhline(limit,color='#353535',ls='--')
    axes[0].set(xlabel='Isolated oscillator time (s)',ylabel='Energy ratio',ylim=(.9989,1.0011))
    for key,color,line in [('kinetic','#ae692c','--'),('potential','#28618e','-')]:
        axes[1].plot(energy.time_s,energy[key],color=color,ls=line,label=key)
    axes[1].set(xlabel='Isolated oscillator time (s)',ylabel='Frozen-operator energy')
    for ax in axes:ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Bounded HG stiffness: independent velocity-Verlet oscillator, 96 fixed native nodes\n'
        'NOT the production SPH/history integrator; no coupled Lian or full-cycle energy acceptance.')
    png=TESTS/'figures'/(TAG+'_energy.png');assert not png.exists();fig.savefig(png,dpi=170);plt.close(fig)
    current=[bound(REPO/'src/source'/n) for n in ['JSphHourglassCpu.cpp','JSphHourglassCpu.h',
        'JSphHourglassGpu.cpp','JSphHourglassGpu_ker.cu','JSphHourglassGpu_ker.h','JSphCpuSingle.cpp','JSphGpuSingle.cpp']]
    write_json(receipt,dict(passed=True,visual_review_passed=False,utc=utc(),sources=source,
        candidate_sources=current,artifacts=[bound(png),bound(energy_path)],
        old_periodic_cpu_gpu_snapshot0ulp=True,periodic_snapshot_sha256=bound(old)['sha256'],
        old_cases=42,new_cases_each_configuration=58,new_bounded_cases=16,gpu_debug_memcheck_errors=0,
        bounded_affine_rate_abs=checks['release']['metrics']['bounded_affine_zero_rate']['max_abs_error'],
        dense_gpu_rate_abs=checks['release']['metrics']['dense_gpu_rate']['max_abs_error'],
        frozen_energy_min_ratio=float(energy.energy_ratio.min()),frozen_energy_max_ratio=float(energy.energy_ratio.max()),
        physical_accepted=False,runtime_Lian_tested=False,
        limitations=['Snapshot0ULP is frozen old/new Release CPU/GPU operator states, not a physical case rerun.',
            'The oscillator uses real HG stiffness on frozen geometry with its own velocity-Verlet integrator.',
            'Neither operator virtual work nor isolated oscillator energy proves coupled SPH/history energy stability.',
            'Static 2D elastic small-rotation fresh native set only; no plasticity/3D/large rotation/HG restart claim.']))
    print('PASS old42/new58 + memcheck + frozen energy; runtime Lian pending',flush=True)


if __name__=='__main__':main()
