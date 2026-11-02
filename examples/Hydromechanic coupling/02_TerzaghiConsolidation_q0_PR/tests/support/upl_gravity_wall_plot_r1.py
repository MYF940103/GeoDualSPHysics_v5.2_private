"""Plot already checked scientific regression pairs; no native solver or interpolation."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

T = Path(__file__).resolve().parents[1]
OUT = T/'figures'/'upl_gravity_wall_summary_r1.png'
TABLE = T/'figures'/'upl_gravity_wall_summary_r1.csv'
CHECK = T/'logs'/'upl_gravity_wall_plot_r1.check.json'


def entry(path):
    return {'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    if any(path.exists() for path in (OUT,TABLE,CHECK)):
        raise ValueError('Retained plot/table/check protected')
    fig, axes = plt.subplots(3,2,figsize=(10,8),sharex=True)
    inputs, summaries = [], []
    rows = [('pressure_RMS_over_Pstar','Pressure RMS / Pstar [ppm]'),('velocity_RMS_over_A','Velocity XYZ RMS / A [ppm]'),('u_RMS_over_Ustar','Material u XYZ RMS / Ustar [ppm]')]
    styles = [('half','-','Half-step difference'),('frame_c','--','Gravity frame vs g0: coarse'),('frame_h',':','Gravity frame vs g0: half')]
    for col,model in enumerate(('constant','variable')):
        for pair,style,label in styles:
            prefix = 'upl_gravity_wall_'+model+'_'+pair+'_r2'
            proof_path = T/'logs'/(prefix+'.check.json')
            proof = json.loads(proof_path.read_text(encoding='utf-8-sig'))
            if proof['passed'] is not True or not all(proof['gates'].values()) or proof['physical_acceptance'] is not False:
                raise ValueError('Passed bounded pair required')
            path = T/'figures'/(prefix+'.csv')
            bound = next(item for item in proof['files'] if Path(item['path']).resolve()==path.resolve())
            if entry(path) != bound:
                raise ValueError('Checked history changed')
            inputs.extend((entry(proof_path),entry(path)))
            with path.open(encoding='utf-8-sig',newline='') as stream:
                data=list(csv.DictReader(stream))
            time=np.asarray([float(row['time_s']) for row in data])
            if not np.array_equal(time,np.arange(257)*2.0**-23):
                raise ValueError('All257 actual dyadic times required')
            for row,(key,ylabel) in enumerate(rows):
                value=np.asarray([float(item[key]) for item in data])*1e6
                if not np.isfinite(value).all() or (value>100).any():
                    raise ValueError('Original100ppm gate failed')
                axes[row,col].plot(time*1e6,value,style,label=label,lw=1.6)
                axes[row,col].set_ylabel(ylabel)
                axes[row,col].grid(alpha=.25)
                axes[row,col].set_ylim(bottom=0)
            summaries.append([model,pair,proof['max_pressure_RMS_Pa'],proof['max_velocity_RMS_over_A'],proof['max_material_u_RMS_over_Ustar'],proof['max_material_u_mm'],proof['max_body_gravity_RMS_over_A']])
        axes[0,col].set_title('Constant k' if model=='constant' else 'Smooth k(J), manufactured Ck = 2^-13')
        axes[-1,col].set_xlabel('Actual saved time [microseconds]')
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Private CPU tangential-gravity wall regression\nPrior normalized limit: 100 ppm (above displayed ranges); not physical-case acceptance',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.94))
    fig.savefig(OUT,dpi=180)
    plt.close(fig)
    with TABLE.open('x',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['model','pair','max_pressure_RMS_Pa','max_velocity_RMS_over_A','max_material_u_RMS_over_Ustar','max_material_u_mm','max_body_gravity_RMS_over_A'])
        writer.writerows(summaries)
    for item in inputs:
        if entry(Path(item['path'])) != item:
            raise ValueError('Plot input changed during read')
    with CHECK.open('x',encoding='utf-8') as stream:
        json.dump({'passed':True,'stage':'upl_gravity_wall_plot_r1','inputs':inputs,'files':[entry(OUT),entry(TABLE)],'no_interpolation_smoothing_or_native_data_edits':True,'physical_acceptance':False},stream,indent=2,allow_nan=False)
        stream.write('\n')


if __name__=='__main__':
    main()
