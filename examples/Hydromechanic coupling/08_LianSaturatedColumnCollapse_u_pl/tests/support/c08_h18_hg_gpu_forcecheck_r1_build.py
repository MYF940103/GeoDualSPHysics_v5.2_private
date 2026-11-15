"""Build only one CRT CPU check entry and a mechanically closed GPU-order core. Never run it."""
import argparse
import difflib
import os
import subprocess
from pathlib import Path
import c08_h18_hg_numeric_r1_build as prior

m,T,L,S=prior.m,prior.T,prior.L,prior.S
TAG='c08_h18_hg_gpu_forcecheck_r1'
CPP,NOTE=T/'support'/(TAG+'.cpp'),T/'notes'/(TAG+'.md')
OUT=T/'outputs'/(TAG+'_build')
CORE=OUT/(TAG+'_core.hpp')
BASE=L/'c08_h18_hg_numeric_r1.build.json'
CHECK=L/'c08_h18_hg_numeric_r1.check.json'

PT='''static std::vector<V> ApplyPT(const Graph& g,const std::vector<V>& y){
  Need(y.size()==g.rows.size(),"HG adjoint input extent differs");const size_t n=g.x.size();std::vector<M> z(n),t(n);std::vector<V> out(n),q(g.rows.size());std::vector<size_t> begin(n+1,0);
  for(const auto& r:g.rows)begin[r.i+1]++;for(size_t i=0;i<n;i++)begin[i+1]+=begin[i];
  for(size_t k=0;k<g.rows.size();k++){const auto& r=g.rows[k];z[r.i]=z[r.i]+Outer(y[k],r.d);}
  for(size_t i=0;i<n;i++)t[i]=RightInverse(z[i],g.moment[i]);
  for(size_t k=0;k<g.rows.size();k++){const auto& r=g.rows[k];q[k]=y[k]-r.a*Mul(t[r.i],r.d);}
  for(size_t i=0;i<n;i++){V force;for(size_t k=begin[i];k<begin[i+1];k++){const auto& r=g.rows[k];auto at=std::lower_bound(g.rows.begin()+begin[r.j],g.rows.begin()+begin[r.j+1],unsigned(i),[](const Row& row,unsigned j){return row.j<j;});Need(at!=g.rows.begin()+begin[r.j+1]&&at->j==i,"HG reference graph lacks true reverse row");const size_t rev=size_t(at-g.rows.begin());force=force-q[k]+q[rev];}out[i]=-force;}return out;
}
'''
MOMENT='  for(const auto& r:g.rows){auto& m=g.moment[r.i];'
SORT='  std::sort(g.rows.begin(),g.rows.end(),[](const Row& a,const Row& b){return a.i<b.i||(a.i==b.i&&a.j<b.j);});\n'
OLD_REVERSE='g.rows.push_back({j,i,-d,g.volume[i]*w,D,radius,w});'
NEW_REVERSE='g.rows.push_back({j,i,g.x[j]-g.x[i],g.volume[i]*w,D,radius,w});'

def change(source):
    m.need(source.count('c08num')==2 and 'c08gpucheck' not in source,'Exactly two original namespace tokens required')
    m.need(source.count(MOMENT)==source.count(OLD_REVERSE)==1 and SORT not in source,'Unique original graph/moment anchors required')
    begin=source.index('static std::vector<V> ApplyPT(')
    end=source.index('static B ClipTime',begin)
    oldpt=source[begin:end]
    m.need(source.count(oldpt)==1 and oldpt.startswith('static std::vector<V> ApplyPT(')
           and oldpt.endswith('return out;\n}\n'),'Exact original complete PT body required')
    changed=source.replace('c08num','c08gpucheck').replace(OLD_REVERSE,NEW_REVERSE,1).replace(MOMENT,SORT+MOMENT,1)
    m.need(changed.count(oldpt)==1,'Original PT changed outside the prescribed body')
    changed=changed.replace(oldpt,PT,1)
    m.need(changed.count(PT)==changed.count(SORT)==changed.count(NEW_REVERSE)==1
           and changed.count('c08gpucheck')==2,'Each prescribed transformation must occur exactly once')
    inverse=changed.replace(PT,oldpt,1).replace(SORT,'',1).replace(NEW_REVERSE,OLD_REVERSE,1).replace('c08gpucheck','c08num')
    m.need(inverse.encode('utf-8')==source.encode('utf-8'),'Inverse transform must recover every original byte')
    return changed,dict(namespace_tokens=2,reverse_row=1,canonical_row_sort=1,PT_body=1,
                        inverse_original_all_bytes=True,
                        old_PT=oldpt,new_PT=PT,inserted_sort=SORT,old_reverse=OLD_REVERSE,new_reverse=NEW_REVERSE)

def same(a,b):return str(Path(a).resolve()).casefold()==str(Path(b).resolve()).casefold()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    m.need(p.parse_args().execution_authorized,'Independent root build admission required')
    receipt=L/(TAG+'.build.json');labels=[TAG+'.compile',TAG+'.link']
    m.need(not OUT.exists() and not receipt.exists() and all(not (L/(q+ext)).exists() for q in labels for ext in ('.call.json','.log')),
           'Existing successful/failed/partial output is protected')
    consumed,calls=[],[]
    try:
        base,check=m.read(BASE),m.read(CHECK)
        m.need(base['passed'] and base['configuration']=='DebugCPU' and base['consumed_stats_unchanged']
               and base['actual_link_objects']==base['new_entry_objects']==1
               and base['physical_objects_compiled']==base['retained_physical_objects']==base['project_libraries_linked']==0,
               'Actually passed standalone CRT numeric build required')
        m.need(check['passed'] and check['all_common_bits_exact'] and check['retained_actual_force_bits']==20000
               and check['actual_owned_exits']==[0,0] and check['solver_invocations']==check['reader_invocations']==0
               and same(check['build']['path'],BASE),'Passed numerical implementation check required')
        header=m.bind(base['header']);oldexe=m.bind(base['program']);oldcpp=m.bind(base['source'])
        m.bind(check['build']);component_call=m.bind(check['actual_call']);completion=m.bind(check['completion'])
        ccseal,lcseal=base['calls'];ccpath,lcpath=Path(m.bind(ccseal)['path']),Path(m.bind(lcseal)['path'])
        cc,lc=m.read(ccpath),m.read(lcpath)
        m.need(all(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure'] is None for q in (cc,lc)),
               'Actual original CL/link handles and exits required')
        m.need(cc['stage']=='c08_h18_hg_numeric_r1.compile' and lc['stage']=='c08_h18_hg_numeric_r1.link',
               'Exact numeric compiler/link recipe stages required')
        consumed=[m.stat(q) for q in (Path(__file__),CPP,NOTE,BASE,CHECK,Path(prior.__file__),Path(m.__file__),ccpath,lcpath,cc['program'],lc['program'])]
        consumed += [header,oldexe,oldcpp,component_call,completion,m.bind(cc['log']),m.bind(lc['log'])]
        text=Path(header['path']).read_bytes().decode('utf-8');generated,proof=change(text)
        oldout=Path(oldexe['path']).parent
        args=[str(CPP) if q==str(Path(oldcpp['path'])) else q.replace(str(oldout),str(OUT)) for q in cc['arguments']]
        m.need(args.count(str(CPP))==1 and not any(q.lower().startswith('/i') for q in args)
               and all(q in args for q in ('/Od','/MTd','/RTC1','/fp:precise','/std:c++17'))
               and args.count('/sourceDependencies')==1
               and sum(q.lower().startswith('/fo') for q in args)==sum(q.lower().startswith('/fd') for q in args)==1,
               'One unchanged precise Debug CRT entry recipe required')
        args.append('/I'+str(OUT))
        exe=OUT/'C08H18HgGpuForcecheckR1.exe';linkargs=[];nout=0
        for q in lc['arguments']:
            if q.lower().startswith('/out:'):
                m.need(same(q[5:],oldexe['path']),'Original numeric link target differs');q='/OUT:'+str(exe);nout+=1
            else:q=q.replace(str(oldout),str(OUT))
            linkargs.append(q)
        objects=[Path(q).resolve() for q in linkargs if q.lower().endswith('.obj')]
        m.need(nout==1 and objects==[(OUT/'entry.obj').resolve()]
               and not any(q.lower().endswith('.lib') or q.lower().startswith('/libpath:') for q in linkargs),
               'Exactly one entry object with only implicit CRT libraries required')
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode==0,'Original MSVC environment unavailable')
        env={k.upper():v for k,v in os.environ.items()}
        env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC ABI differs');env.pop('CL',None);env.pop('_CL_',None)
        m.verify(consumed);OUT.mkdir()
        with CORE.open('xb') as f:f.write(generated.encode('utf-8'))
        proofpath=OUT/'source_diff_proof.json';diffpath=OUT/'source.diff'
        proof.update(original_header=header,generated_header=m.stat(CORE),original_bytes=len(text.encode('utf-8')),
                     generated_bytes=len(generated.encode('utf-8')),value_change_scope='directed row subtraction/order and receiver-gather PT only',
                     Audit_arithmetic_LS_ExactStep_Rotate_State_other_bytes_preserved=True,
                     degree_lambda_accumulation_original_order=True,physical_updates=0)
        m.save(proofpath,proof)
        with diffpath.open('x',encoding='utf-8',newline='') as f:
            f.write(''.join(difflib.unified_diff(text.splitlines(True),generated.splitlines(True),fromfile=str(header['path']),tofile=str(CORE))))
        consumed += [m.stat(q) for q in (CORE,proofpath,diffpath)]
        m.verify(consumed)
        calls.append(m.invoke(labels[0],[str(cc['program']),*args],S/'VS',env))
        dep=m.read(OUT/'dependencies.json')['Data'];includes={Path(q).resolve() for q in dep['Includes']}
        m.need(Path(dep['Source']).resolve()==CPP.resolve() and CORE.resolve() in includes
               and all(not q.is_relative_to(S.resolve()) for q in includes)
               and all(q==CORE.resolve() for q in includes if q.is_relative_to(T.resolve())),
               'Entry consumed a public/other private project header instead of the generated core')
        calls.append(m.invoke(labels[1],[str(lc['program']),*linkargs],S/'VS',env));m.verify(consumed)
        m.save(receipt,dict(stage=TAG+'.build',passed=True,configuration='DebugCPU',source=m.stat(CPP),note=m.stat(NOTE),program=m.stat(exe),
            original_numeric_build=m.stat(BASE),original_numeric_check=m.stat(CHECK),original_header=header,generated_header=m.stat(CORE),
            source_diff_proof=m.stat(proofpath),source_diff=m.stat(diffpath),inverse_original_all_bytes=True,transformation_counts=dict(namespace_tokens=2,reverse_row=1,canonical_row_sort=1,PT_body=1),
            dependencies=m.stat(OUT/'dependencies.json'),actual_link_objects=1,new_entry_objects=1,retained_physical_objects=0,
            physical_objects_compiled=0,project_libraries_linked=0,runtime_copies=0,compile_invocations=1,link_invocations=1,
            component_invocations=0,solver_invocations=0,reader_invocations=0,GPU_actions=0,public_source_changed=False,old_assets_changed=False,
            future_GPU_snapshot_consumed=False,component_output_created=False,no_automatic_component=True,
            SHA_scans=0,physical_acceptance=False,calls=calls,consumed=consumed,consumed_stats_unchanged=True))
    except Exception as error:
        if not receipt.exists():m.save(receipt,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=consumed,
            partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,reader_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=='__main__':main()

