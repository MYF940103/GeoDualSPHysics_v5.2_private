"""Old/new real GPU programs: four single-plane SPR/HG paths, fresh 0.03 s."""
from pathlib import Path
import json
import re
import subprocess
import numpy as np
from spr_planes_run import TESTS,REPO,bound
from k5_guard_probe import native


def invoke(command,log):
    with log.open('xb') as stream:child=subprocess.run(command,cwd=REPO/'bin/windows',stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
    assert child.returncode==0,(command[0],log)


def main():
    tag='spr_gpu_paths_r1';receipt=TESTS/'logs'/(tag+'.check.json');assert not receipt.exists()
    case=TESTS.parent;old=TESTS/'outputs/spr_gpu_planes_base/DualSPHysics5.2_GEO_win64.exe';new=REPO/'bin/windows/DualSPHysics5.2_GEO_win64.exe'
    result=dict(passed=False,inputs=[bound(__file__),bound(old),bound(new)],pairs=[])
    try:
        for enabled in (0,1):
            for xi in ('0','.1'):
                name=tag+'_s'+str(enabled)+'_hg'+('0' if xi=='0' else '1');definition=TESTS/'configs'/(name+'_Def.xml');generated=TESTS/'outputs'/(name+'_input');prefix=generated/name
                assert not definition.exists() and not generated.exists()
                text=(case/'CaseTerzaghiConsolidation_q0_PR_full_k1em4_Def.xml').read_text(encoding='utf8')
                for key,value in [('TimeMax','.03'),('TimeOut','.001'),('SoilBoundaryDerivativeSPR',str(enabled)),('SoilHourglassXi',xi)]:
                    text,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],text);assert n==1
                with definition.open('x',encoding='utf8') as stream:stream.write(text)
                generated.mkdir();invoke([str(REPO/'bin/windows/GenCase_win64.exe'),str(definition.with_suffix('')),str(prefix),'-save:all'],TESTS/'logs'/(name+'.gencase.log'))
                outputs=[]
                for label,exe in [('old',old),('new',new)]:
                    out=TESTS/'outputs'/(name+'_'+label);assert not out.exists()
                    invoke([str(exe),'-gpu','-stable',str(prefix),str(out),'-dirdataout','data','-svres'],TESTS/'logs'/(name+'_'+label+'.log'));outputs.append(out)
                assert all(len(list((p/'data').glob('Part_*.bi4')))==31 for p in outputs)
                for i in range(31):
                    a,b=native(outputs[0],i),native(outputs[1],i);assert np.array_equal(a.id,np.arange(40,1040)) and a.shape==b.shape
                    fields=a.select_dtypes('number').columns
                    assert a[fields].to_numpy(dtype='<f8').tobytes()==b[fields].to_numpy(dtype='<f8').tobytes(),(name,i)
                    assert a.drop(columns=fields).equals(b.drop(columns=fields))
                result['pairs'].append(dict(spr=enabled,xi=xi,frames=31,soil_native_ids=1000,all_fields_0ulp=True,actual_final_time_s=float(a.time_s.iloc[0]),owned_exits_verified=True,
                    definition=bound(definition),outputs=[bound(p) for base in outputs+[generated] for p in base.rglob('*') if p.is_file()]))
                print(name,'31 native frames 0 ULP',flush=True)
        for item in result['inputs']:assert bound(item['path'])['sha256']==item['sha256']
        result['passed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
