"""Build-only retry after a diagnosed C++ helper name collision; preserve r1."""
from pathlib import Path
import c08_h18_storage_rhs_r1_build as base

def main():
    t=base.T
    original=(t/'support/c08_h18_storage_rhs_r1.cpp').read_bytes()
    replacement=(t/'support/c08_h18_storage_rhs_r2.cpp').read_bytes()
    base.m.need(original.count(b'Gamma(')==3 and original.count(b'c08_h18_storage_rhs_r1')==3
        and replacement==original.replace(b'Gamma(',b'RoundoffGamma(').replace(b'c08_h18_storage_rhs_r1',b'c08_h18_storage_rhs_r2'),
        'Only diagnosed name/output-tag correction admitted')
    failed=base.m.read(base.L/'c08_h18_storage_rhs_r1.build.json')
    call=base.m.read(base.L/'c08_h18_storage_rhs_r1.compile.call.json')
    base.m.need(not failed['passed'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==2,
        'Preserved actual r1 compile2 evidence required')
    base.TAG='c08_h18_storage_rhs_r2'
    base.OUT=t/'outputs'/(base.TAG+'_build')
    base.CPP=t/'support'/(base.TAG+'.cpp')
    base.NOTE=t/'notes'/(base.TAG+'.md')
    base.main()

if __name__=='__main__':main()
