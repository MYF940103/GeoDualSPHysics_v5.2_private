"""Local immutable short-verified candidate, not a Git/cloud backup."""
from pathlib import Path
import json
import shutil
from spr_planes_run import TESTS,REPO,bound


def main():
    out=TESTS/'outputs/spr_planes_cpu_gpu_short_verified';receipt=TESTS/'logs/spr_planes_cpu_gpu_short_verified.snapshot.json'
    assert not out.exists() and not receipt.exists()
    checks=[TESTS/'logs'/(x+'.check.json') for x in ('spr_gpu_delivery_r1','spr_gpu_paths_r2','spr_gpu_scope_r1')]
    y=REPO/'examples/Hydromechanic coupling/06_Yao2DConsolidation_PR/tests'
    checks += [y/'logs/spr_yao_gpu_load_grid10_r2.review.json',y/'logs/spr_yao_gpu_load_grid10_r2.visual.json']
    assert all(json.loads(p.read_text())['passed'] for p in checks)
    sources=['JSphCpu.h','JSphCpu.cpp','JSphCpuSingle.cpp','JSphGpu.h','JSphGpu.cpp','JSphGpuSingle.cpp','JSphGpu_ker.h','JSphGpu_ker.cu']
    files=[REPO/'src/source'/x for x in sources]+[REPO/'bin/windows'/x for x in ('DualSPHysics5.2CPU_win64.exe','DualSPHysics5.2CPU_win64_debug.exe','DualSPHysics5.2_GEO_win64.exe','DualSPHysics5.2_win64_debug.exe')]
    out.mkdir();saved=[]
    for source in files:
        target=out/source.name;shutil.copy2(source,target);a,b=bound(source),bound(target);assert a['sha256']==b['sha256'];saved.append(dict(source=a,retained=b))
    with receipt.open('x',encoding='utf8') as stream:json.dump(dict(local_snapshot=True,cloud_backup=False,physical_acceptance=False,
        scope='Static convex multi-plane operator/pulse/Yao .1-s candidate only; formal 1-D results unchanged',
        inputs=[bound(__file__)]+[bound(x) for x in checks],files=saved),stream,indent=2)
    print('Frozen',len(saved),'source/program files locally; no Git mutation')


if __name__=='__main__':main()
