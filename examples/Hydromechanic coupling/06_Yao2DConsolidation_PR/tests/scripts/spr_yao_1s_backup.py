"""Explicit accepted 1-s evidence inventory; no raw output or unrelated staging."""
import json
from pathlib import Path
import subprocess
from spr_yao_short import TESTS,CASE,REPO,bound


def main():
    manifest=TESTS/'logs/spr_yao_1s_backup_r1.manifest.json';assert not manifest.exists()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()=='7fda9ffe8c3ee657fe7d5279f9f35565f199719c'
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=REPO).strip()
    assert not subprocess.check_output(['git','diff','--name-only','--','src/source'],cwd=REPO).strip()
    visual=TESTS/'logs/spr_yao_cpu_gpu_1s_r1.visual.json';v=json.loads(visual.read_text());assert v['passed'] and v['visual_inspected']
    for item in v['evidence']:assert bound(item['path'])['sha256']==item['sha256']
    paths=[CASE/'README.md',TESTS/'README.md',TESTS/'notes/spr_yao_1s_r1.md',REPO/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml',Path(__file__).resolve()]
    paths += list((TESTS/'scripts').glob('spr_yao_1s_*.py'))
    paths += list((TESTS/'configs').glob('spr_yao_cpu_gpu_1s_r1*'))+list((TESTS/'configs').glob('xspr_yao_cpu_gpu_1s_r1*'))
    paths += list((TESTS/'logs').glob('spr_yao_cpu_gpu_1s_r1*'))+list((TESTS/'figures').glob('spr_yao_cpu_gpu_1s_r1*'))
    paths=sorted(set(p.resolve() for p in paths if p.is_file()))
    assert all('outputs' not in p.relative_to(REPO).parts and p.suffix not in ('.exe','.bi4','.dll') for p in paths)
    entries=[dict(relative_path=p.relative_to(REPO).as_posix(),**bound(p)) for p in paths]
    data=dict(base='7fda9ffe8c3ee657fe7d5279f9f35565f199719c',scope='Reviewed bounded 1-s evidence/docs only; no production source or raw/binary cloud backup',
        files=entries,allowed_stage=[e['relative_path'] for e in entries]+[manifest.relative_to(REPO).as_posix()])
    with manifest.open('x',encoding='utf8') as f:json.dump(data,f,indent=2)
    print(json.dumps(dict(files=len(entries),bytes=sum(p.stat().st_size for p in paths),manifest=str(manifest)),indent=2))


if __name__=='__main__':main()
