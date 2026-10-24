"""Old 18 plane operators plus baseline/new one-dimensional native 0-ULP runs."""
from pathlib import Path
import json
import re
import subprocess
import numpy as np
from mdbc_gpu_vector_run import read, bound, verify
from formal_release_sequence import CASE, TESTS, REPO
from k5_guard_probe import native

TAG="spr_planes_regression_r1"


def invoke(command,log):
    with log.open("xb") as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW,cwd=REPO/"bin/windows")
    assert result.returncode==0,(command[0],log)


def main():
    receipt=TESTS/"logs"/(TAG+".check.json");assert not receipt.exists()
    build=TESTS/"logs/mdbc_vector_planes_r1rel.build.json";b=read(build);verify(b['inputs']+b['runtime']+b['resolved_compile_link_inputs'])
    prepared=read(TESTS/"logs/mdbc_plane_r2.prepare.json")
    exe=TESTS/"outputs/mdbc_vector_planes_r1rel/mdbc_vector.exe"
    result=dict(passed=False,planes=[],native_pairs=[],inputs=[bound(__file__),bound(build)])
    try:
        for v in prepared['variants']:
            name=TAG+'_'+v['geometry']+'_s'+str(v['slip_mode']);out=TESTS/'outputs'/name
            assert not out.exists()
            values=[v['dimension'],v['slip_mode'],v['native_count'],v['wall_count'],v['wall_roi_count']]+[x for row in v['rotation'] for x in row]
            command=[str(exe)]+[str(x) for x in values]+['-cpu','-ompthreads:1',('-mdbc','-mdbc_noslip','-mdbc_freeslip')[v['slip_mode']-1],v['prefix'],str(out),'-dirdataout','data','-sv:none']
            invoke(command,TESTS/'logs'/(name+'.log'))
            done=read(out/'vector_complete.json');assert done['passed']
            result['planes'].append(dict(name=name,metrics=done,outputs=[bound(p) for p in out.iterdir() if p.is_file()]))
        for enabled in (0,1):
            name=TAG+'_oneplane_'+str(enabled);definition=TESTS/'configs'/(name+'_Def.xml');folder=TESTS/'outputs'/(name+'_input');prefix=folder/name
            assert not definition.exists() and not folder.exists()
            text=(CASE/'CaseTerzaghiConsolidation_q0_PR_full_k1em4_Def.xml').read_text(encoding='utf8')
            for key,value in [('TimeMax','.03'),('TimeOut','.001'),('SoilBoundaryDerivativeSPR',str(enabled))]:
                text,n=re.subn(r'(<parameter key="'+key+r'" value=")[^"]*(")',lambda m:m[1]+value+m[2],text);assert n==1
            definition.write_text(text,encoding='utf8');folder.mkdir()
            invoke([str(REPO/'bin/windows/GenCase_win64.exe'),str(definition.with_suffix('')),str(prefix),'-save:all'],TESTS/'logs'/(name+'.gencase.log'))
            outputs=[]
            for label,program in [('old',TESTS/'outputs/spr_planes_base/DualSPHysics5.2CPU_win64.exe'),('new',REPO/'bin/windows/DualSPHysics5.2CPU_win64.exe')]:
                out=TESTS/'outputs'/(name+'_'+label);assert not out.exists()
                invoke([str(program),'-cpu','-ompthreads:1',str(prefix),str(out),'-dirdataout','data','-svres'],TESTS/'logs'/(name+'_'+label+'.log'))
                outputs.append(out)
            parts=sorted((outputs[0]/'data').glob('Part_*.bi4'))
            assert len(parts)==31 and len(list((outputs[1]/'data').glob('Part_*.bi4')))==31
            for i in range(31):
                a,b=native(outputs[0],i),native(outputs[1],i)
                assert np.array_equal(a.id,np.arange(40,1040)) and a.shape==b.shape
                nums=a.select_dtypes('number').columns
                assert a[nums].to_numpy(dtype='<f8').tobytes()==b[nums].to_numpy(dtype='<f8').tobytes(),(enabled,i)
                assert a.drop(columns=nums).equals(b.drop(columns=nums))
            result['native_pairs'].append(dict(spr_enabled=enabled,frames=31,native_ids=1000,actual_final_time_s=float(a.time_s.iloc[0]),all_native_fields_0ulp=True,programs=[bound(TESTS/'outputs/spr_planes_base/DualSPHysics5.2CPU_win64.exe'),bound(REPO/'bin/windows/DualSPHysics5.2CPU_win64.exe')],definition=bound(definition),outputs=[bound(p) for out in outputs for p in out.rglob('*') if p.is_file()]))
            print('ONE-PLANE SPR',enabled,'0 ULP',flush=True)
        result['passed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
