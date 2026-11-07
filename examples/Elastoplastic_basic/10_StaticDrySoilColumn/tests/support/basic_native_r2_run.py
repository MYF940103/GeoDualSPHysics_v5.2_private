"""Decode each newly closed basic run once; preserve native binary stress precision."""
import argparse,json
from pathlib import Path
from basic_material_r1 import context,need,read,stat,save,invoke
a=argparse.ArgumentParser();a.add_argument('case',choices=['column','collapse']);a.add_argument('window',choices=['short','full']);a.add_argument('mode',choices=['old','new']);x=a.parse_args();c,t,stem,short,full,soil,fixed=context(x.case)
tag='basic_material_'+x.window+'_'+x.mode+'_CPU_r1';rp=t/'logs'/(tag+'.run.json');r=read(rp);need(r['passed'] and r['consumed_stats_unchanged'],'Run must be closed safe before decoder')
_,t10,*_=context('column');bp=t10/'logs/basic_native_r2.build.json';b=read(bp);need(b['passed'] and stat(b['program']['path'])==b['program'],'Closed unchanged native reader required')
out=t/'outputs'/(tag+'_native_r2');check=t/'logs'/(tag+'.native_r2.check.json');need(not out.exists() and not check.exists(),'Fresh single native decode required');before=[stat(rp),stat(bp),b['program']]
record=dict(passed=False,source_run=stat(rp),reader_build=stat(bp),physical_acceptance=False)
try:
    call=invoke(t,tag+'.native_r2',[b['program']['path'],str(t/'outputs'/tag/'data'),str(soil),str(fixed),str(r['saved_frames']),str(out)],c)
    d=read(out/'completion.json');need(d['passed'] and d['samples']==r['saved_frames'] and d['soil']==soil and d['fixed']==fixed and d['no_exclusions'],'Native coverage/finite/fixed guards failed')
    need(all(stat(e['path'])==e for e in before),'Reader/run binding changed');record.update(passed=True,actual_call=call,completion=d,consumed_stats_unchanged=True,files=[stat(f) for f in out.iterdir() if f.is_file()])
except Exception as e:record['first_failure']=str(e)
save(check,record);print(json.dumps({k:v for k,v in record.items() if k not in ('files','actual_call')},indent=2));need(record['passed'],'Native checks failed; preserve without retry')
