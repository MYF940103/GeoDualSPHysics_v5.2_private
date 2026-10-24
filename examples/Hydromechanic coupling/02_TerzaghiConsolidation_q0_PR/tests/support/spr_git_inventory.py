"""Explicit backup allowlist for this SPR task; inventory only, no Git writes."""
from pathlib import Path
from collections import Counter
import json
import subprocess
from spr_planes_run import TESTS,REPO,bound


def main():
    receipt=TESTS/'logs/spr_delivery_backup_r1.manifest.json';assert not receipt.exists()
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=REPO).strip(),'Preserve an existing user index'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    assert head=='e696271b1200e667f27646c58886044d4791b944'
    paths={REPO/'src/source'/x for x in ('JSphCpu.cpp','JSphCpu.h','JSphCpuSingle.cpp','JSphGpu.cpp','JSphGpu.h','JSphGpuSingle.cpp','JSphGpu_ker.cu','JSphGpu_ker.h')}
    paths.add(REPO/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml')
    y=REPO/'examples/Hydromechanic coupling/06_Yao2DConsolidation_PR/tests'
    paths.update([TESTS/'README.md',y/'README.md',y.parent/'README.md'])
    allowed={'.cpp','.h','.ps1','.py','.bat','.xml','.json','.log','.md','.csv','.png'}
    for root,prefix in ((TESTS,'spr'),(y,'spr_yao')):
        for category in ('configs','support' if root==TESTS else 'scripts','notes','logs','figures'):
            folder=root/category
            for p in folder.iterdir():
                if not p.is_file() or p.suffix.lower() not in allowed:continue
                if not (p.name.startswith(prefix) or (category=='configs' and p.name.startswith('x'+prefix))):continue
                if p.name.endswith('_final.csv'):continue  # Native raw dumps are reproducible, not plot-source tables.
                assert p.stat().st_size<20*1024*1024,('Review unexpectedly large backup item',p)
                paths.add(p)
    paths.update(y/'scripts'/x for x in ('build_read_meta.ps1','build_read_native.ps1','read_meta_fixed.cpp','read_native_fixed.cpp'))
    required=[y/'logs/spr_yao_gpu_post03_r1.audit_r1.json',y/'logs/spr_yao_gpu_post03_r1.visual.json',TESTS/'logs/spr_gpu_delivery_r1.check.json']
    assert all(json.loads(p.read_text())['passed'] for p in required)
    files=[]
    for p in sorted(paths):
        assert p.is_file() and (p==REPO or REPO in p.parents) and 'outputs' not in p.relative_to(REPO).parts
        item=bound(p);item.update(relative=p.relative_to(REPO).as_posix(),bytes=p.stat().st_size);files.append(item)
    result=dict(base_head=head,scope='Short-verified static convex planar SPR candidate; not full 2-D physical release',
        files=files,raw_outputs_executables_and_unrelated_changes_excluded=True,source_files=8,
        total_bytes=sum(x['bytes'] for x in files),evidence=[bound(p) for p in required])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(files=len(files),megabytes=result['total_bytes']/1024**2,extensions=dict(Counter(Path(x['relative']).suffix for x in files))),indent=2))


if __name__=='__main__':main()
