"""Build only one standalone numeric-core fixture and closed Decimal references. Never run it."""
import argparse
import csv
import math
import os
import struct
import subprocess
from decimal import Decimal, Context, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction
from pathlib import Path
import c08_h18_hg_energy_memory_r1_build as prior

m,T,L,S=prior.m,prior.T,prior.L,prior.S
TAG='c08_h18_hg_numeric_r1'
CPP,HDR,NOTE=T/'support'/(TAG+'.cpp'),T/'support'/(TAG+'.hpp'),T/'notes'/(TAG+'.md')
OUT=T/'outputs'/(TAG+'_build');BASE=L/'c08_h18_hg_energy_memory_r1.build.json'
STAGE=L/'c08_h18_plastic_hg_stage_r1.check.json'
REVIEW=L/'c08_h18_as03n255_full3_review_r1.check.json'
NATIVE=L/'c08_h18_as03n255_full3_native_r1.check.json'
RAW=T/'outputs/c08_h18_as03n255_full3_r1/native_r1'
GAMMA=T/'outputs/c08_h18_plastic_hg_stage_r1/stage_nodes.csv'

def same(a,b):return str(Path(a).resolve()).casefold()==str(Path(b).resolve()).casefold()
def seal(path,entries):
    q=[x for x in entries if same(path,x['path'])]
    m.need(q and all(x==q[0] for x in q),'Unique old seal absent/conflicting: '+str(path));return m.bind(q[0])

# Reference-only directed Decimal interval arithmetic. No libm sine/cosine or
# Windows long-double precision is assumed. All operations round outward.
DOWN=Context(prec=100,rounding=ROUND_FLOOR,Emin=-999999,Emax=999999)
UP=Context(prec=100,rounding=ROUND_CEILING,Emin=-999999,Emax=999999)
ZERO=Decimal(0);ONE=Decimal(1)
def add(a,b):return DOWN.add(a[0],b[0]),UP.add(a[1],b[1])
def neg(a):return a[1].copy_negate(),a[0].copy_negate()
def mul(a,b):
    return min(DOWN.multiply(x,y) for x in a for y in b),max(UP.multiply(x,y) for x in a for y in b)
def divint(a,n):
    d=Decimal(n);return DOWN.divide(a[0],d),UP.divide(a[1],d)
def tail_add(a,error):return DOWN.subtract(a[0],error),UP.add(a[1],error)
def sincos(theta):
    m.need(theta[0]==theta[1] and theta[0].copy_abs()<Decimal(7),'Exact closed angle in reference range required')
    square=mul(theta,theta);st=theta;ct=(ONE,ONE);ss=st;cs=ct
    for n in range(1,129):
        st=neg(divint(mul(st,square),(2*n)*(2*n+1)));ss=add(ss,st)
        ct=neg(divint(mul(ct,square),(2*n-1)*(2*n)));cs=add(cs,ct)
    sn=divint(mul(st,square),258*259);cn=divint(mul(ct,square),257*258)
    sb=max(x.copy_abs() for x in sn);cb=max(x.copy_abs() for x in cn)
    # For |theta|<7 these alternating terms are decreasing after n=128;
    # the first omitted exact term bounds the entire remaining tail.
    return tail_add(ss,sb),tail_add(cs,cb),sb,cb

def rounded(interval):
    center=UP.divide(UP.add(interval[0],interval[1]),Decimal(2));value=float(center)
    exact=Decimal.from_float(value)
    err=max(ZERO,UP.subtract(exact,interval[0]),UP.subtract(interval[1],exact))
    upper=math.nextafter(float(err),math.inf)
    return value,upper

def point_reference(angles,steps):
    exact=sum((Fraction.from_float(angles[i%len(angles)]) for i in range(steps)),Fraction())
    theta=(DOWN.divide(Decimal(exact.numerator),Decimal(exact.denominator)),UP.divide(Decimal(exact.numerator),Decimal(exact.denominator)))
    m.need(theta[0]==theta[1],'Closed binary64 angle sum must be exactly representable at Decimal100')
    sine,cosine,stail,ctail=sincos(theta)
    x=add(mul((Decimal('0.125'),)*2,cosine),neg(mul((Decimal('-0.25'),)*2,sine)))
    z=add(mul((Decimal('0.125'),)*2,sine),mul((Decimal('-0.25'),)*2,cosine))
    xv,xe=rounded(x);zv,ze=rounded(z)
    return dict(angle=str(theta[0]),x=xv,z=zv,xe=xe,ze=ze,
                sine_lo=str(sine[0]),sine_hi=str(sine[1]),cosine_lo=str(cosine[0]),cosine_hi=str(cosine[1]),
                sine_omitted_term_upper=str(stail),cosine_omitted_term_upper=str(ctail))

def references(path):
    base=math.ldexp(float.fromhex('0x1.921fb54442d18p+2'),-10)
    rows=[]
    for name,angles in (('constant',[base]),('variable_reverse',[base*x for x in (-.25,1.25,1.5,1.5)])):
        m.need(all(abs(a*.5)<.005 for a in angles),'Each declared half angle must remain in the shared helper range')
        full,quarter=point_reference(angles,1024),point_reference(angles,256)
        bits=[format(struct.unpack('<Q',struct.pack('<d',a))[0],'016x') for a in angles]
        q=dict(sequence=name,steps=1024,period=len(angles),**{'angle'+str(i)+'_bits':bits[i] if i<len(bits) else '' for i in range(4)},
            exact_double_angle_sum_decimal=full['angle'],x_reference=repr(full['x']),z_reference=repr(full['z']),
            x_reference_error=repr(full['xe']),z_reference_error=repr(full['ze']),
            quarter_exact_double_angle_sum_decimal=quarter['angle'],quarter_x_reference=repr(quarter['x']),quarter_z_reference=repr(quarter['z']),
            quarter_x_reference_error=repr(quarter['xe']),quarter_z_reference_error=repr(quarter['ze']))
        for prefix,data in (('full_',full),('quarter_',quarter)):
            for key in ('sine_lo','sine_hi','cosine_lo','cosine_hi','sine_omitted_term_upper','cosine_omitted_term_upper'):q[prefix+key]=data[key]
        rows.append(q)
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return dict(Decimal_precision=100,directed_rounding=True,Taylor_highest_index=128,
                tail='first omitted alternating term after decreasing terms',
                exact_input='Fraction.from_float of each actual binary64 full angle',
                reference_output_error='directed Decimal interval plus binary64 reference quantization',
                sequences=2,steps_per_sequence=1024,quarter_check_step=256,
                initial_e=[.125,-.25],physical_clock=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    m.need(p.parse_args().execution_authorized,'Independent root build admission required; component is never automatic')
    receipt=L/(TAG+'.build.json');labels=[TAG+'.compile',TAG+'.link']
    m.need(not OUT.exists() and not receipt.exists() and all(not (L/(q+ext)).exists() for q in labels for ext in ('.call.json','.log')),'Existing complete/partial build protected')
    consumed,calls=[],[]
    try:
        base,stage,review,native=map(m.read,(BASE,STAGE,REVIEW,NATIVE))
        m.need(base['passed'] and base['configuration']=='DebugCPU' and base['consumed_stats_unchanged']
               and base['actual_link_objects']==1 and base['physical_objects_compiled']==base['retained_physical_objects']==0,
               'Actual standalone precise DebugCPU/CRT recipe required')
        m.need(stage['passed'] and stage['consumed_stats_unchanged'] and stage['component_invocations']==1
               and stage['actual_updates']==8 and stage['solver_invocations']==stage['reader_invocations']==0,
               'Completed actual bounded CPU-stage component required')
        sd,sc,sb=[m.bind(stage[k]) for k in ('completion','actual_call','build')]
        done,call,stagebuild=m.read(sd['path']),m.read(sc['path']),m.read(sb['path'])
        m.need(done['passed'] and done['source_parts']==[38,76] and done['stage_node_rows']==60000
               and done['manual_OFF_CPU22_equivalent_field_checks']==220000
               and done['material_sigma_kappa_scalar_bit_checks']==420000
               and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,
               'Actual matched material/OFF proof and owned exit required')
        m.need(review['analysis_complete'] and review['consumed_stats_unchanged'] and review['actual_samples']==301
               and native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations']==1,
               'Original sealed full301 review/native required')
        consumed=[m.stat(q) for q in (Path(__file__),CPP,HDR,NOTE,BASE,STAGE,REVIEW,NATIVE,Path(prior.__file__))]+[sd,sc,sb]
        consumed.append(seal(GAMMA,stage['files']))
        consumed += [seal(RAW/q,review['consumed']) for q in ('typed22.bin','typed22_layout.csv','clocks.csv','completion.json')]
        consumed += [m.bind(native[k]) for k in ('actual_call','native_completion','metadata','reader_build')]
        consumed.append(m.bind(stagebuild['header']))
        ccpath,lcpath=L/'c08_h18_hg_energy_memory_r1.compile.call.json',L/'c08_h18_hg_energy_memory_r1.link.call.json'
        cc,lc=m.read(ccpath),m.read(lcpath)
        m.need(all(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure'] is None for q in (cc,lc)),
               'Actual original CRT compiler/linker recipes required')
        consumed += [m.stat(q) for q in (ccpath,lcpath,cc['program'],lc['program'])]
        oldout=Path(base['program']['path']).parent;oldcpp=Path(base['source']['path'])
        args=[str(CPP) if q==str(oldcpp) else q.replace(str(oldout),str(OUT)) for q in cc['arguments']]
        m.need(args.count(str(CPP))==1 and not any(q.startswith('/I') for q in args)
               and all(q in args for q in ('/Od','/MTd','/RTC1','/fp:precise','/std:c++17')),
               'One shared precise value-expression recipe required; no physical include path')
        exe=OUT/'C08H18HgNumericR1.exe'
        linkargs=['/OUT:'+str(exe),'/NOLOGO','/DEBUG','/PDB:'+str(OUT/'entry.pdb'),'/SUBSYSTEM:CONSOLE','/MACHINE:X64',str(OUT/'entry.obj')]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode==0,'Original MSVC environment unavailable')
        env={k.upper():v for k,v in os.environ.items()}
        env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION']=='14.36.32532','Original MSVC ABI differs');env.pop('CL',None);env.pop('_CL_',None)
        m.verify(consumed);OUT.mkdir();refpath=OUT/'rotation_reference.csv';reference_method=references(refpath);consumed.append(m.stat(refpath))
        calls.append(m.invoke(labels[0],[str(cc['program']),*args],S/'VS',env))
        dep=m.read(OUT/'dependencies.json')['Data'];includes={Path(q).resolve() for q in dep['Includes']}
        m.need(Path(dep['Source']).resolve()==CPP.resolve() and HDR.resolve() in includes
               and all(not q.is_relative_to((S/'source').resolve()) for q in includes)
               and all(q==HDR.resolve() for q in includes if q.is_relative_to(T.resolve())),
               'Standalone core unexpectedly consumed physical/other private project headers')
        calls.append(m.invoke(labels[1],[str(lc['program']),*linkargs],S/'VS',env));m.verify(consumed)
        m.save(receipt,dict(stage=TAG+'.build',passed=True,configuration='DebugCPU',source=m.stat(CPP),header=m.stat(HDR),note=m.stat(NOTE),program=m.stat(exe),
            actual_stage_check=m.stat(STAGE),actual_stage_completion=sd,actual_stage_call=sc,actual_stage_header=stagebuild['header'],
            source_native=m.stat(NATIVE),source_review=m.stat(REVIEW),gamma_input=m.stat(GAMMA),rotation_reference=m.stat(refpath),reference_method=reference_method,
            original_CRT_build=m.stat(BASE),dependencies=m.stat(OUT/'dependencies.json'),actual_link_objects=1,new_entry_objects=1,
            retained_physical_objects=0,physical_objects_compiled=0,project_libraries_linked=0,runtime_copies=0,
            same_template_value_algorithm=True,Audit_and_Fast_instantiated=True,old_stage_assets_changed=False,public_source_changed=False,
            fixed_input_only=True,rotation_helper_range_only=True,private_State_short_spin_guard_retained=True,
            physical_updates=0,material_calls=0,Darcy_calls=0,compile_invocations=1,link_invocations=1,component_invocations=0,
            solver_invocations=0,reader_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False,
            no_automatic_component_or_solver=True,calls=calls,consumed=consumed,consumed_stats_unchanged=True))
    except Exception as error:
        if not receipt.exists():m.save(receipt,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=consumed,
            partial_outputs_preserved=True,component_invocations=0,solver_invocations=0,reader_invocations=0,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=='__main__':main()
