"""Decode one sealed bounded job once; no solver or automatic follow-on."""
import argparse
from pathlib import Path
import mdbc_partition_components_r3 as e
from upl_c08_plane_run_r1 import SPECS,PRE,POLICY
T=Path(__file__).resolve().parents[1];L=T/'logs'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=tuple(SPECS));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Reviewed single native read required')
    stem,conf,backend,nopen,updates,cadence,*_=SPECS[a.action];tag='upl_c08_plane_'+stem+'_r1';out=T/'outputs'/tag;native=out/'native';receipt=L/(tag+'.native.json')
    e.need(not native.exists() and not receipt.exists() and not (L/(tag+'.native.call.json')).exists(),'Existing/partial native read protected')
    rp=L/(tag+'.run.json');r=e.read(rp);cp=L/(tag+'.call.json');c=e.read(cp)
    e.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged'] and r['actual_steps']==4000000+updates and r['saved_frames']==updates//cadence,'Sealed actual solver required')
    e.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and not c['ownership_errors'],'Actual owned solver/tool exits required')
    e.need(Path(c['actual_solver']['exe']).samefile(r['program']['path']),'Actual target executable differs')
    bp=L/'upl_c08_plane_native_r1.build.json';b=e.read(bp);e.need(b['passed'] and b['consumed_stats_unchanged'],'Closed native reader build required')
    program=Path(e.bind(b['program'])['path']);plan=out/'planned_steps.csv'
    before=[e.stat(x) for x in (Path(__file__),rp,cp,bp,plan,PRE,PRE.parent/'Part_Head.ibi4')]+r['consumed']+[r['Run_out'],r['Run_csv'],*r['PARTs']]+b['consumed']+[b['program']]
    e.need(all(e.stat(x['path'])==x for x in before),'Consumed build/input/outputs changed')
    call=e.invoke(tag+'.native',[str(program),'--read','psi0',backend,str(out/'data'),str(PRE),str(4000000+updates),str(updates//cadence),str(int(nopen)),str(plan),str(native)],T.parent)
    d=e.read(native/'completion.json');e.need(d['passed'] and d['samples']==updates//cadence and d['completed_steps']==4000000+updates and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6800,'Native coverage differs')
    e.need(d['NoPenOn_argument']==nopen and (not nopen or d['DynamicNoPenetrationPolicy']==POLICY),'Native contact policy differs')
    e.need(all(e.stat(x['path'])==x for x in before),'Consumed files changed while reading')
    e.save(receipt,dict(stage=tag,passed=True,actual_call=call,consumed=before,completion=e.stat(native/'completion.json'),outputs=[e.stat(p) for p in sorted(native.iterdir()) if p.is_file()],consumed_stats_unchanged=True,physical_acceptance=False,SHA_scans=0))
    print('NATIVE_PASSED',receipt,flush=True)
if __name__=='__main__':main()
