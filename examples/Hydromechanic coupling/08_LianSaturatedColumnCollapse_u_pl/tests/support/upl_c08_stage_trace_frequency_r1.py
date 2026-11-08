"""Descriptive frequencies of sealed C08 stage data, not a coupled spectrum proof."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import pandas as pd

T=Path(__file__).resolve().parents[1]
TAG='upl_c08_stage_trace_frequency_r1'
SOURCE=T/'figures/upl_c08_stage_trace_terms_r2_window_steps.csv'
PARENT=T/'figures/upl_c08_stage_trace_terms_r2_window.check.json'

def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args()
 if not args.execution_authorized:raise RuntimeError('Root review required')
 prefix=T/'figures'/TAG
 if list(prefix.parent.glob(prefix.name+'*')):raise RuntimeError('Existing derived results preserved')
 parent=json.loads(PARENT.read_text(encoding='utf-8'));before=[stat(SOURCE),stat(PARENT),stat(__file__),stat(T/'notes'/(TAG+'.md'))]
 assert parent['passed'] and parent['profile']=='window'
 assert next(e for e in parent['files'] if Path(e['path']).resolve()==SOURCE.resolve())==before[0]
 data=pd.read_csv(SOURCE,float_precision='round_trip',usecols=['native_id','nstep','tau_s','p_full_prepond_Pa'])
 rows=[];growth=[]
 for identity in (5809,4956,4959):
  own=[]
  for lo,hi in ((.619,.621),(.625,.627),(.635,.637)):
   d=data[(data.native_id==identity)&(data.tau_s>=lo)&(data.tau_s<hi)]
   times=d.tau_s.to_numpy();p=d.p_full_prepond_Pa.to_numpy();assert len(p)>2 and np.all(np.diff(d.nstep)==1) and np.all(np.diff(times)>0)
   dt=float(np.diff(times).mean());centered=p-p.mean();rms=float(np.sqrt(np.mean(centered**2)))
   spectrum=np.abs(np.fft.rfft(centered*np.hanning(len(p))));frequencies=np.fft.rfftfreq(len(p),dt)
   peak=1+int(np.argmax(spectrum[1:]));frequency=float(frequencies[peak]);y=2*math.pi*frequency*dt
   gain=math.sqrt(1+y**4/4);rate=math.log1p(y**4/4)/(2*dt)
   row=dict(native_id=identity,requested_start_s=lo,requested_end_s=hi,first_actual_tau_s=float(times[0]),last_actual_tau_s=float(times[-1]),actual_center_tau_s=float(times.mean()),samples=len(p),actual_mean_dt_s=dt,p_prepond_mean_Pa=float(p.mean()),demeaned_RMS_Pa=rms,Hann_peak_Hz=frequency,FFT_bin_width_Hz=float(frequencies[1]),hypothetical_undamped_midpoint_gain_per_step=gain,hypothetical_undamped_midpoint_log_growth_per_s=rate)
   rows.append(row);own.append(row)
  early,late=own[0],own[-1]
  growth.append(dict(native_id=identity,early_RMS_Pa=early['demeaned_RMS_Pa'],late_RMS_Pa=late['demeaned_RMS_Pa'],RMS_ratio=late['demeaned_RMS_Pa']/early['demeaned_RMS_Pa'],center_gap_s=late['actual_center_tau_s']-early['actual_center_tau_s'],descriptive_local_RMS_log_growth_per_s=math.log(late['demeaned_RMS_Pa']/early['demeaned_RMS_Pa'])/(late['actual_center_tau_s']-early['actual_center_tau_s'])))
 files=[]
 for suffix,table in (('_windows.csv',rows),('_growth.csv',growth)):
  path=Path(str(prefix)+suffix)
  with path.open('x',encoding='utf-8',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
  files.append(stat(path))
 assert all(stat(e['path'])==e for e in before)
 result=dict(stage=TAG,passed=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,source_field='actual full-step pressure before ponding',FFT='demeaned actual consecutive samples, Hann window, largest nonzero rFFT bin; no zero padding',RMS='demeaned unwindowed actual values',hypothetical_midpoint_comparison='isolated undamped pure-imaginary mode at observed peak frequency; not actual coupled eigenvalues',growth_is_not_fitted_eigenvalue=True,consumed=before,files=files)
 with Path(str(prefix)+'.check.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(growth))

if __name__=='__main__':main()
