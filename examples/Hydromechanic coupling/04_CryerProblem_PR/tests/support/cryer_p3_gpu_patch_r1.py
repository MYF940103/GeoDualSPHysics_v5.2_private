"""Create/verify the four-file Cryer P3 GPU source delta (no objects or programs)."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

T=Path(__file__).resolve().parents[1]
BASE=T/'outputs/upl_tpi_cryer_gpu_r2_source/source'
CANDIDATE=T/'outputs/cryer_p3_gpu_r2_source'
PATCH=T/'support/cryer_p3_gpu_r2.patch'
MANIFEST=T/'notes/cryer_p3_gpu_patch_r1.json'
FILES=('JSphGpu.cpp','JSphGpuSingle.cpp','upl_tpi_cryer_gpu_r1.h','upl_tpi_m0_dt_r2.h')

def digest(data):return hashlib.sha256(data).hexdigest()

def apply_to_copy(base,destination,manifest):
    if destination.exists():raise FileExistsError(destination)
    destination.mkdir(parents=True)
    for item in manifest['files']:
        name=item['path']
        if name not in FILES:raise ValueError(name)
        old=base/name
        if item['base_sha256'] is None:
            if old.exists():raise FileExistsError(old)
            continue
        if digest(old.read_bytes())!=item['base_sha256']:raise ValueError('Different base '+name)
        shutil.copyfile(old,destination/name)
    # Apply outside any parent's worktree; core.autocrlf must not rewrite the LF patch.
    subprocess.run(['git','-C',str(destination),'init','-q'],check=True)
    args=['git','-C',str(destination),'-c','core.autocrlf=false','apply','--whitespace=nowarn']
    subprocess.run([*args,'--check',str(PATCH)],check=True)
    subprocess.run([*args,str(PATCH)],check=True)
    for item in manifest['files']:
        p=destination/item['path'];lf=p.read_bytes()
        if digest(lf)!=item['candidate_lf_sha256']:raise ValueError('Patch LF mismatch '+p.name)
        # The retained Windows compiler inputs use CRLF for these four files only.
        compiled=lf.replace(b'\n',b'\r\n')
        if digest(compiled)!=item['compiled_source_sha256']:raise ValueError('Compiler input mismatch '+p.name)
        p.write_bytes(compiled)

def generate():
    if PATCH.exists() or MANIFEST.exists():raise FileExistsError(PATCH)
    patch=[];files=[]
    for leaf in FILES:
        old=BASE/leaf;new=CANDIDATE/leaf
        before=old.read_bytes() if old.exists() else b''
        after=new.read_bytes();lf=after.replace(b'\r\n',b'\n')
        assert b'\r' not in before and b'\r' not in lf and lf.replace(b'\n',b'\r\n')==after
        a=('a/'+leaf).encode();b=('b/'+leaf).encode()
        patch.append(b'diff --git '+a+b' '+b+b'\n')
        if not old.exists():patch.append(b'new file mode 100644\n')
        patch+=list(difflib.diff_bytes(difflib.unified_diff,before.splitlines(True),lf.splitlines(True),
                                        fromfile=a if old.exists() else b'/dev/null',tofile=b))
        files.append(dict(path=leaf,base_sha256=digest(before) if old.exists() else None,candidate_lf_sha256=digest(lf),compiled_source_sha256=digest(after)))
    data=b''.join(patch)
    with PATCH.open('xb') as f:f.write(data)
    manifest=dict(base='tests/outputs/upl_tpi_cryer_gpu_r2_source/source',candidate='tests/outputs/cryer_p3_gpu_r2_source',
                  patch=str(PATCH.relative_to(T)).replace('\\','/'),patch_bytes=len(data),patch_sha256=digest(data),files=files,
                  scope='Four source files; untouched CUDA operators from the original XYZ Cryer baseline. No object or executable archived.')
    with tempfile.TemporaryDirectory(prefix='cryer_patch_proof_') as tmp:
        apply_to_copy(BASE,Path(tmp)/'source',manifest)
    manifest['verified_git_apply_and_compiled_source_bytes']=True
    with MANIFEST.open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2)
    print(PATCH,len(data))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--generate',action='store_true')
    ap.add_argument('--base',type=Path,default=BASE)
    ap.add_argument('--destination',type=Path)
    args=ap.parse_args()
    if args.generate:generate()
    else:
        if not args.destination:ap.error('--destination must name a new directory')
        m=json.loads(MANIFEST.read_text())
        if digest(PATCH.read_bytes())!=m['patch_sha256']:raise ValueError('Different patch')
        apply_to_copy(args.base,args.destination,m)

