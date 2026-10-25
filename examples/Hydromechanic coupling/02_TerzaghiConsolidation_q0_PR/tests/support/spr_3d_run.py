"""Fresh 3-D production-step pulse; gated native checks, no formal writes."""
import argparse
from decimal import Decimal
from pathlib import Path
import json
import subprocess
import time
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from spr_planes_run import TESTS,REPO,bound


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend',choices=['cpu','gpu'],default='cpu')
    p.add_argument('--geometry',choices=['edge3','corner3'],default='edge3')
    p.add_argument('--slip',type=int,choices=[2,3],default=3)
    p.add_argument('--debug',action='store_true');p.add_argument('--tag',default='spr_3d_r1')
    p.add_argument('--gpu-build',default='spr_3d_Release_r2')
    a=p.parse_args();assert a.tag.replace('_','').isalnum() and not(a.debug and a.backend!='cpu')
    tag=f'{a.tag}_{a.geometry}_s{a.slip}_{a.backend}'+('_debug' if a.debug else '')
    status=TESTS/'logs'/(tag+'.status.json');assert not status.exists()
    build=TESTS/'logs'/('spr_3d_DebugCPU_r1.build.json' if a.debug else 'spr_3d_ReleaseCPU_r1.build.json' if a.backend=='cpu' else a.gpu_build+'.build.json')
    b=json.loads(build.read_text(encoding='utf-8-sig'));exe=Path(b['executable'])
    assert bound(exe)['sha256']==b['executable_sha256']
    # Reuse authoritative project build provenance, rather than compiling another algorithm.
    for item in b['inputs']+b.get('runtime',[]):assert bound(item['path'])['sha256']==item['sha256'],item['path']
    result=dict(passed=False,status='running',backend=a.backend,geometry=a.geometry,slip_mode=a.slip,
        production_source_changed=False,physical_acceptance=False,inputs=[bound(__file__),bound(build),bound(exe),bound(TESTS/'notes/spr_3d_r1.md')],runs=[])
    def publish():
        temporary=status.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2),encoding='utf8');temporary.replace(status)
    publish();frames=[]
    try:
        for phase,dt,stride in ([('c','.000001',10)] if a.debug else [('c','.000001',10),('h','.0000005',20)]):
            name=tag+'_'+phase;definition=TESTS/'configs'/f'spr_3d_r1_{a.geometry}_s{a.slip}_{phase}_Def.xml'
            root=ET.parse(definition).getroot();assert root.find('execution/parameters/parameter[@key="DtFixed"]').get('value')==dt
            assert root.find('execution/parameters/parameter[@key="SoilBoundaryDerivativeSPR"]').get('value')=='1'
            duration=Decimal('.00002' if a.debug else '.002');steps=int(duration/Decimal(dt));samples=steps//stride+1
            generated=TESTS/'outputs'/(name+'_input');out=TESTS/'outputs'/name
            log=TESTS/'logs'/(name+'.log');genlog=TESTS/'logs'/(name+'.gencase.log')
            assert not any(x.exists() for x in (generated,out,log,genlog));generated.mkdir();prefix=generated/name
            with genlog.open('xb') as stream:subprocess.run([str(REPO/'bin/windows/GenCase_win64.exe'),str(definition.with_suffix('')),str(prefix),'-save:all'],stdout=stream,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            flags=['-cpu','-ompthreads:1'] if a.backend=='cpu' else ['-gpu','-stable']
            command=[str(exe),str(steps),str(stride),*flags,str(prefix),str(out),'-dirdataout','data','-sv:none']
            result['stage']=name;result['active_input']=bound(definition);result['command']=command;publish()
            started=time.perf_counter()
            with log.open('xb') as stream:
                process=subprocess.Popen(command,cwd=exe.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                result['owned_pid']=process.pid;result['owned_exited']=False;publish()
                try:code=process.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    process.terminate();process.wait(timeout=20);raise RuntimeError('Owned pulse exceeded bounded runtime')
            elapsed=time.perf_counter()-started;result['owned_exited']=True;publish()
            assert code==0,(name,'Solver/observer exit',code)
            done=json.loads((out/'pulse_complete.json').read_text());assert done['completed'] and done['steps']==steps
            assert abs(done['actual_time_s']-float(duration))<1e-11 and done['dt_s']==float(dt)
            assert done['max_fixed_dt_minus_mechanical_limit_s']<=0 and done['pore_dt_limit_s']>=float(dt)
            f=pd.read_csv(out/'pulse.csv',float_precision='round_trip').sort_values(['step','id']).reset_index(drop=True)
            initial=f[f.step.eq(0)];n=len(initial);assert n==(1600 if a.geometry=='edge3' else 1000)
            assert len(f)==samples*n and f.id.nunique()==n and not f.duplicated(['step','id']).any()
            assert np.isfinite(f.to_numpy()).all() and f.rho.gt(0).all() and f.kplastic.eq(0).all()
            assert f.x.gt(0).all() and f.z.gt(0).all() and (a.geometry!='corner3' or f.y.gt(0).all())
            assert np.array_equal(f.id.to_numpy().reshape(samples,n),np.tile(initial.id.to_numpy(),(samples,1)))
            actual=f.time_s.to_numpy().reshape(samples,n);assert abs(actual-np.arange(samples)[:,None]*float(dt)*stride).max()<1e-11
            energy=pd.read_csv(out/'energy.csv',float_precision='round_trip');assert len(energy)==samples and np.isfinite(energy.to_numpy()).all()
            ratio=float(energy.total_J.max()/energy.total_J.iloc[0]);assert ratio<=1.1,(name,'Energy guard',ratio)
            record=dict(name=name,exit_code=code,owned_pid=process.pid,owned_exited=True,completion=done,soil_count=n,samples=samples,
                energy_ratio_max=ratio,observed_wall_s=elapsed,definition=bound(definition),log=bound(log),gencase_log=bound(genlog),
                outputs=[bound(x) for x in out.iterdir() if x.is_file()],generated_inputs=[bound(x) for x in generated.iterdir() if x.is_file()])
            result['runs'].append(record);frames.append(f);publish();print(name,'native gates passed; wall seconds',elapsed,flush=True)
        if not a.debug:
            c,h=frames;n=len(c[c.step.eq(0)]);assert np.array_equal(c.id,h.id) and abs(c.time_s-h.time_s).max()<1e-11
            dp=(c.pressure.to_numpy()-h.pressure.to_numpy()).reshape(201,n)
            movement=np.linalg.norm(c[['x','y','z']].to_numpy()-h[['x','y','z']].to_numpy(),axis=1).reshape(201,n)*1000
            stress=((c.pressure-c.szz)-(h.pressure-h.szz)).to_numpy().reshape(201,n)
            table=pd.DataFrame(dict(time_s=c.time_s.to_numpy()[::n],pressure_rms_pa=np.sqrt(np.mean(dp*dp,axis=1)),material_max_mm=movement.max(axis=1),total_stress_rms_pa=np.sqrt(np.mean(stress*stress,axis=1))))
            pair=dict(pressure_rms_max_pa=float(table.pressure_rms_pa.max()),material_displacement_max_mm=float(table.material_max_mm.max()),total_stress_rms_max_pa=float(table.total_stress_rms_pa.max()))
            result['half']=pair;assert pair['pressure_rms_max_pa']<=.5 and pair['material_displacement_max_mm']<=1e-5,pair
            csv=TESTS/'figures'/(tag+'_half.csv');table.to_csv(csv,index=False,mode='x');result['outputs']=[bound(csv)]
            fig,axes=plt.subplots(1,3,figsize=(12,3.7),layout='constrained')
            for ax,column,label in zip(axes,['pressure_rms_pa','material_max_mm','total_stress_rms_pa'],['Pressure RMS difference (Pa)','3-D material displacement difference (mm)','Vertical total-stress RMS difference (Pa)']):
                ax.plot(table.time_s*1000,table[column],color='#2166a5');ax.set(xlabel='Actual time (ms)',ylabel=label);ax.grid(alpha=.2)
            fig.suptitle(f'3-D {a.geometry}, SlipMode={a.slip}, {a.backend}: independent half step; HG/NoPen off')
            png=TESTS/'figures'/(tag+'_half.png');assert not png.exists();fig.savefig(png,dpi=150);plt.close(fig);result['outputs'].append(bound(png))
            print('HALF',pair,flush=True)
        for item in result['inputs']:assert bound(item['path'])['sha256']==item['sha256'],'Input changed during run'
        result.update(passed=True,status='completed_pending_visual_review',stage='gates_passed')
    except BaseException as error:
        result.update(status='rejected_or_interrupted',error=repr(error));raise
    finally:publish()


if __name__=='__main__':main()
