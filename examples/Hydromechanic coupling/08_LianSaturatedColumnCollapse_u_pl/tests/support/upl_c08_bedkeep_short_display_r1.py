"""Display-only adapter for three sealed short-review CSVs; never recomputes native data."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

T=Path(__file__).resolve().parents[1];F=T/'figures';TAG='upl_c08_bedkeep_short_display_r1';SOURCE='upl_c08_bedkeep_short_review_r1'
def need(b,s):
    if not b:raise RuntimeError(s)
def stat(p):
    p=p.resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def number(v):return format(float(v),'.11g')

def load(phase,before):
    prefix=F/(SOURCE+'_'+phase);cp=Path(str(prefix)+'.check.json');c=json.loads(cp.read_text(encoding='utf-8'));before.append(stat(cp))
    need(c['passed'] and c['stage']==SOURCE and c['phase']==phase and not c['physical_acceptance'],'Closed original phase review required')
    values={}
    for leaf in ('history','matched'):
        p=Path(str(prefix)+'_'+leaf+'.csv');entry=next(e for e in c['files'] if Path(e['path']).samefile(p));need(stat(p)==entry,'Original bound phase CSV changed');before.append(entry);values[leaf]=table(p)
    expected=1 if phase=='smoke' else 3;need(len(values['history'])==2*expected and len(values['matched'])==expected and c['actual_common_step_time_pairs']==expected,'Original phase row coverage differs')
    if phase=='smoke':need(c['CPU_GPU_budget_applied'] and c['CPU_GPU_pressure_budget_Pa']==5 and c['CPU_GPU_material_budget_mm']==.005,'Original smoke budget declaration differs')
    elif phase=='off':
        need(c['keepfalse_full22_layout_and_clock_file_byte_exact'] and c['signed_dterror_compared_in_exact_clock_file'],'Original OFF exact control not passed')
        p=Path(str(prefix)+'_byte_exact.csv');entry=next(e for e in c['files'] if Path(e['path']).samefile(p));need(stat(p)==entry,'Bound OFF exactness table changed');before.append(entry);need(all(q['byte_exact']=='True' for q in table(p)),'Original exactness table contains a difference')
    else:need(c['keeptrue_vs_old_is_descriptive'] and not c['CPU_GPU_budget_applied'],'SHORT remains descriptive between boundary operators')
    return values

def smoke(values,path):
    rows={r['case']:r for r in values['history']};need(set(rows)=={'CPU','GPU'} and abs(float(rows['CPU']['time_s'])-float(rows['GPU']['time_s']))<=1e-14,'Original smoke backend/actual time differs');cpu,gpu=rows['CPU'],rows['GPU'];paired=values['matched'][0]
    specs=(('p_RMS_Pa','Pore pressure RMS [Pa]'),('total_stress_Frobenius_RMS_Pa','Total stress Frobenius RMS [Pa]'),('mean_material_settlement_double_PRE_mm','Mean material settlement from PRE [mm]'),('speed_max_m_s','Maximum speed [m/s]'),('min_soil_z_m','Minimum soil z [m]'),('max_kappa','Maximum plastic history'),('J_min','Minimum J'),('J_max','Maximum J'))
    cells=[[label,number(cpu[key]),number(gpu[key]),number(float(gpu[key])-float(cpu[key]))] for key,label in specs]
    fig,axs=plt.subplots(2,1,figsize=(13,7),layout='constrained',gridspec_kw={'height_ratios':[3,1.35]});axs[0].axis('off');axs[1].axis('off')
    q=axs[0].table(cellText=cells,colLabels=['Native-history statistic','CPU Debug','GPU Debug','GPU - CPU statistic'],cellLoc='right',colWidths=[.40,.20,.20,.20],loc='center');q.auto_set_font_size(False);q.set_fontsize(10);q.scale(1,1.8)
    paircells=[['RMS of per-ID pressure difference [Pa]',number(paired['pressure_RMS_difference_Pa']),'5 Pa'],['Maximum per-ID material XYZ difference [mm]',number(paired['material_XYZ_max_difference_mm']),'0.005 mm']]
    q=axs[1].table(cellText=paircells,colLabels=['Original paired smoke metric (different from subtracting RMS statistics)','Actual value','Original budget'],cellLoc='right',colWidths=[.68,.20,.12],loc='center');q.auto_set_font_size(False);q.set_fontsize(10);q.scale(1,1.8)
    fig.suptitle('KeepBedOverlap smoke: 6805 IDs, 5000 soil, completed step '+cpu['completed_step']+'\nActual tau='+format(float(cpu['tau_s']),'.17g')+' s; tables use the existing sealed CSVs, no axis offset',fontsize=12)
    fig.savefig(path,dpi=160);plt.close(fig)

def history(phase,values,path):
    labels=('OLD','OFF') if phase=='off' else ('OLD','SHORT');names={'OLD':'retained AS + plane, keep=false','OFF':'new build, keep=false','SHORT':'new build, keep=true (five bed IDs)'}
    groups={label:sorted((r for r in values['history'] if r['case']==label),key=lambda r:int(r['part'])) for label in labels};need(all(len(r)==3 for r in groups.values()),'Only the three actual saved points are plotted')
    ticks=[float(r['tau_s']) for r in groups[labels[0]]];need(all([int(r['completed_step']) for r in rr]==[4004000,4008000,4012000] and all(abs(float(r['tau_s'])-ticks[i])<=1e-14 for i,r in enumerate(rr)) for rr in groups.values()),'Actual matched step/tau points differ; no interpolation')
    specs=(('p_RMS_Pa','Pore pressure RMS [kPa]',.001),('total_stress_Frobenius_RMS_Pa','Total stress Frobenius RMS [kPa]',.001),('mean_material_settlement_double_PRE_mm','Mean material settlement from PRE [mm]',1),('speed_max_m_s','Maximum speed [m/s]',1),('min_soil_z_m','Minimum soil z [mm]',1000),('max_kappa','Maximum plastic history',1))
    fig,axs=plt.subplots(2,3,figsize=(14,7.5),layout='constrained')
    for ax,(key,title,scale) in zip(axs.flat,specs):
        for label in labels:
            rr=groups[label];old=label=='OLD';ax.plot([float(r['tau_s']) for r in rr],[float(r[key])*scale for r in rr],ls='--' if old else '-',color='.4' if old else 'C0',marker='x' if old else 'o',markerfacecolor='none',ms=6,label=names[label])
        # Tick locations remain actual scalar-clock tau; only their text is rounded for display.
        ax.set_xticks(ticks,['0.01','0.02','0.03']);ax.set_xlim(ticks[0]-.0007,ticks[-1]+.0007);formatter=ScalarFormatter(useOffset=False);formatter.set_scientific(False);ax.yaxis.set_major_formatter(formatter);ax.set(title=title,xlabel='Actual tau [s], labels rounded to 0.01');ax.grid(alpha=.25);ax.legend(fontsize=7)
    text='Default-off proof: original typed22/layout/clocks byte exact, including signed diagnostics.' if phase=='off' else 'Different boundary operators: descriptive changes, no 5 Pa / 0.005 mm comparison gate.'
    fig.suptitle('KeepBedOverlap '+phase+' — three actual saved states\n'+text,fontsize=12);fig.savefig(path,dpi=160);plt.close(fig)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one display-only invocation');need(not list(F.glob(TAG+'*')),'Existing display products/partial work protected')
    before=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md'))];phases={p:load(p,before) for p in ('smoke','off','short')};files=[]
    for phase,v in phases.items():
        p=F/(TAG+'_'+phase+'_display.png');smoke(v,p) if phase=='smoke' else history(phase,v,p);files.append(p)
    need(all(stat(Path(e['path']))==e for e in before),'Original sealed CSV/check changed during display')
    result=dict(stage=TAG,passed=True,display_only=True,original_reviews_reexecuted=False,original_data_and_PNGs_overwritten=False,smoke_is_numeric_table=True,smoke_difference_is_GPU_minus_CPU_statistic=True,paired_pressure_RMS_is_separately_labelled=True,actual_tau_used_as_tick_locations=True,three_tick_labels=['0.01','0.02','0.03'],axis_offset_disabled=True,no_interpolation_smoothing_clipping_or_fitting=True,native_binary_reads=0,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False,consumed=before,files=[stat(p) for p in files])
    with (F/(TAG+'.check.json')).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('BEDKEEP_DISPLAY_COMPLETED',F/(TAG+'.check.json'),flush=True)

if __name__=='__main__':main()
