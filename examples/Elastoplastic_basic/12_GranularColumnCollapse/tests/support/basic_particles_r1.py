"""Official PartVTK export of the completed new basic collapse run only."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'10_StaticDrySoilColumn/tests/support'))
from basic_material_r1 import R,context,need,read,stat,save,invoke
a=argparse.ArgumentParser();a.add_argument('window',choices=['short','full']);x=a.parse_args();c,t,stem,*_=context('collapse');tag='basic_material_'+x.window+'_new_CPU_r1';run=t/'outputs'/tag;rp=t/'logs'/(tag+'.run.json');np=t/'logs'/(tag+'.native_r2.check.json');r=read(rp);n=read(np);need(r['passed'] and n['passed'],'Closed completed new run/native required');target=run/'particles';check=t/'logs'/(tag+'.particles_r1.check.json');need(not target.exists() and not check.exists(),'Fresh particles export required')
program=R/'bin/windows/PartVTK_win64.exe';xml=t/'outputs'/(tag+'_seed')/(stem+'.xml');inputs=[stat(program),stat(R/'bin/windows/DsphConfig.xml'),stat(rp),stat(np),stat(xml)]+[stat(run/'data'/f'Part_{i:04d}.bi4') for i in range(r['saved_frames'])]
argv=[str(program),'-dirin',str(run/'data'),'-filexml',str(xml),'-savevtk',str(target/'PartFluid'),'-onlytype:-all,fluid','-vars:-all,+idp,+mk,+vel,+rhop,+press,+SigmaState_kk,+SigmaState_ij,+Sigma_kk,+Sigma_ij,+Kplastic','-threads:1']
result=dict(passed=False,source_run=stat(rp),source_native=stat(np),window=x.window,raw_native_modified=False,solver_invocations=0,SHA_scans=0)
try:
    call=invoke(t,tag+'.particles_r1',argv,c);files=sorted(target.glob('PartFluid_*.vtk'));need(len(files)==r['saved_frames'],'Expected every completed frame');head=files[0].read_bytes();precision={}
    for name in ('SigmaState_kk','SigmaState_ij','Sigma_kk','Sigma_ij','Kplastic','Vel','Rhop','Press'):
        where=head.find(name.encode());need(where>=0,'Requested VTK field absent: '+name);precision[name]=head[where:head.find(b'\n',where)].decode('ascii',errors='replace')
    need(b'POINTS 2500 ' in head,'All2500soil points required');need(all(stat(e['path'])==e for e in inputs),'Postprocessing changed a consumed input')
    text='# Completed new basic granular collapse visualization\n\nThis is the '+('.1 s startup, not the full1 s result' if x.window=='short' else 'complete1 s result')+'. Run: `'+tag+'`. All '+str(len(files))+' actual saved frames and2500soil points per frame were exported by official PartVTK v5.0.206; `PartFluid_*.vtk` is the ParaView series. Original BI4/native exports remain unchanged.\n\nCoordinates are the original saved float32 positions. `Vel`, `Rhop`, `Kplastic`, and legacy `Sigma_kk/ij` retain their declared display types. `SigmaState_kk/ij` is included from native double stress; inspect the field declarations below for actual VTK storage. Offdiagonal order is xy,yz,xz. `Press` is the dry WCSPH EOS pressure derived by PartVTK, NOT pore-water pressure. This dry case has no pore equation.\n\n```text\n'+'\n'.join(precision.values())+'\n```\n\nNo interpolation, smoothing, new solver, equilibrium claim or physical acceptance threshold is introduced.\n'
    with (target/'README.md').open('x',encoding='utf-8') as f:f.write(text)
    result.update(passed=True,actual_call=call,frames=len(files),soil_points_per_frame=2500,VTK_field_declarations=precision,consumed=inputs,consumed_stats_unchanged=True,files=[stat(p) for p in files],README=stat(target/'README.md'))
except Exception as e:result['first_failure']=str(e)
save(check,result);print(json.dumps({k:v for k,v in result.items() if k not in ('files','consumed','actual_call')},indent=2));need(result['passed'],'PartVTK failed; preserve first evidence')
