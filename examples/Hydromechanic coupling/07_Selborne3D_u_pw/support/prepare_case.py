"""Reproduce the configuration-only Selborne package. Never starts a solver.

Run once in an empty case directory. Existing deliverables are not overwritten.
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / '03_RetrogressiveSlopeFailure_u_pw/CaseRetroSlope_u_pw_prestress_Def.xml'


def save(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as f:
        f.write(text)


def node(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})


def box(parent, origin, size):
    b = node(parent, 'drawbox')
    node(b, 'boxfill').text = 'solid'
    node(b, 'point', **dict(zip('xyz', origin)))
    node(b, 'size', **dict(zip('xyz', size)))


def prism(parent, polygon, y0, y1, seed):
    polygon = list(reversed(polygon))
    node(parent, 'setdrawmode', mode='full')
    b = node(parent, 'drawprism')
    for y in (y0, y1):
        for x, z in polygon:
            node(b, 'point', x=x, y=y, z=z)
    fill = node(parent, 'fillprism', **dict(zip('xyz', seed)))
    for y in (y0, y1):
        for x, z in polygon:
            node(fill, 'point', x=x, y=y, z=z)
    node(fill, 'modefill').text = 'void'


def geometry():
    g = ET.Element('geometry')
    pre = node(g, 'predefinition')
    for key, value in [('Dp', '0.5'), ('Length', '56'), ('Width', '25'), ('BaseH', '6'), ('SlopeH', '9'), ('CrestX', '18'), ('ToeX', '36')]:
        node(pre, 'newvarcte', **{key: value})
    node(pre, 'newvar', Hdp='Dp/2')
    d = node(g, 'definition', dp='#Dp', units_comment='metres (m)')
    node(d, 'pointmin', x='#-4*Dp', y='#-4*Dp', z='#-4*Dp')
    node(d, 'pointmax', x='#Length+4*Dp', y='#Width+4*Dp', z='#BaseH+SlopeH+4*Dp')
    cmds = node(g, 'commands')
    # Actual mDBC surfaces lie half a lattice interval inside boundary centres.
    normals = node(cmds, 'list', name='GeometryForNormals')
    node(normals, 'setactive', drawpoints='0', drawshapes='1')
    node(normals, 'setshapemode').text = 'actual | bound'
    # Open inward-facing planes avoid spurious normals from closed slab ends.
    planes = [
        [('#-4*Dp','#-4*Dp','#Hdp'),('#Length+4*Dp','#-4*Dp','#Hdp'),('#Length+4*Dp','#Width+4*Dp','#Hdp'),('#-4*Dp','#Width+4*Dp','#Hdp')],
        [('#Hdp','#-4*Dp','#-4*Dp'),('#Hdp','#Width+4*Dp','#-4*Dp'),('#Hdp','#Width+4*Dp','#BaseH+SlopeH+Dp'),('#Hdp','#-4*Dp','#BaseH+SlopeH+Dp')],
        [('#Length-Hdp','#Width+4*Dp','#-4*Dp'),('#Length-Hdp','#-4*Dp','#-4*Dp'),('#Length-Hdp','#-4*Dp','#BaseH+Dp'),('#Length-Hdp','#Width+4*Dp','#BaseH+Dp')],
        [('#Length+4*Dp','#Hdp','#-4*Dp'),('#-4*Dp','#Hdp','#-4*Dp'),('#-4*Dp','#Hdp','#BaseH+SlopeH+Dp'),('#Length+4*Dp','#Hdp','#BaseH+SlopeH+Dp')],
        [('#-4*Dp','#Width-Hdp','#-4*Dp'),('#Length+4*Dp','#Width-Hdp','#-4*Dp'),('#Length+4*Dp','#Width-Hdp','#BaseH+SlopeH+Dp'),('#-4*Dp','#Width-Hdp','#BaseH+SlopeH+Dp')],
    ]
    for mk, points in enumerate(planes):
        node(normals, 'setmkbound', mk=mk)
        quad=node(normals, 'drawquadri')
        for point in points:
            node(quad, 'point', **dict(zip('xyz',point)))
    node(normals, 'shapeout', file='hdp')
    node(normals, 'resetdraw')
    main = node(cmds, 'mainlist')
    node(main, 'runlist', name='GeometryForNormals')
    node(main, 'setdrawmode', mode='full')
    node(main, 'setshapemode').text = 'actual | bound'
    # Four lattice layers; side blocks do not overwrite the base block.
    node(main, 'setmkbound', mk=0)
    box(main, ('#-3*Dp', '#-3*Dp', '#-3*Dp'), ('#Length+6*Dp', '#Width+6*Dp', '#3*Dp'))
    node(main, 'setmkbound', mk=1)
    box(main, ('#-3*Dp', '#-3*Dp', '#Dp'), ('#3*Dp', '#Width+6*Dp', '#BaseH+SlopeH-Dp'))
    node(main, 'setmkbound', mk=2)
    box(main, ('#Length', '#-3*Dp', '#Dp'), ('#3*Dp', '#Width+6*Dp', '#BaseH-Dp'))
    # Side-wall profiles follow the slope; there is no wall on the exposed top.
    side = [('#Dp', '#Dp'), ('#Length-Dp', '#Dp'), ('#Length-Dp', '#BaseH'), ('#ToeX', '#BaseH'), ('#CrestX', '#BaseH+SlopeH'), ('#Dp', '#BaseH+SlopeH')]
    for mk, y0, y1 in [(3, '#-3*Dp', '0'), (4, '#Width', '#Width+3*Dp')]:
        node(main, 'setmkbound', mk=mk)
        prism(main, side, y0, y1, ('10', '#-Dp' if mk==3 else '#Width+Dp', '3'))
    node(main, 'setmkfluid', mk=0)
    box(main, ('#Dp', '#Dp', '#Dp'), ('#Length-2*Dp', '#Width-2*Dp', '#BaseH-Dp'))
    node(main, 'setmkfluid', mk=1)
    upper = [('#Dp', '#BaseH+Dp'), ('#ToeX-2*Dp', '#BaseH+Dp'), ('#CrestX', '#BaseH+SlopeH'), ('#Dp', '#BaseH+SlopeH')]
    prism(main, upper, '#Dp', '#Width-Dp', ('10', '12.5', '10'))
    node(main, 'shapeout', file='')
    return g


def make_xml(stage):
    root = ET.parse(SOURCE).getroot()
    root.insert(0, ET.Comment(' CONFIGURATION PREPARATION ONLY. Global soil below is a geometry-export placeholder, NOT a two-material simulation. Read support/model_spec.json and code_change_plan.md. Solver launch is blocked by BAT until material mapping and basal pore-pressure boundary are implemented. '))
    cd = root.find('casedef')
    cd.find('constantsdef/rhop0').set('value', '2054')
    cd.find('constantsdef/rhop0').set('comment', 'Saturated mixture: (1-0.38)*2700+0.38*1000; NOT grain density')
    cd.find('constantsdef/rhopgradient').set('value', '1')
    old = cd.find('geometry')
    idx = list(cd).index(old)
    cd.remove(old)
    cd.insert(idx, geometry())
    special = root.find('execution/special')
    special.clear()
    soil = node(special, 'soils')
    soil.append(ET.Comment(' Current parser supports ONE global material only. Upper-layer values here are placeholders. BOTH real layer specifications are in support/model_spec.json. '))
    for key, val in [('phi',24),('coh',15000),('dlt',0),('phi_r',13),('coh_r',500),('n_phi',0 if stage=='prestress' else 5),('n_coh',0 if stage=='prestress' else 5),('SoilTriggerFos',1),('ModulusE','20e6'),('PRvs',0.33)]:
        node(soil, key, value=val)
    hydro = node(special, 'hydromechanics')
    for key, val in [('HydroMech',1),('HydroMechInitMode','FreeSurface' if stage=='prestress' else 'None'),('PoreWaterRho',1000),('PoreWaterBulkModulus','2e8'),('Porosity',0.38),('HydraulicConductivity','1e-3'),('PoreDtSafety',0.1),('PoreShepardRegularization',0),('PoreShepardInterval',40),('PoreMdbcInterpolationMode',0)]:
        node(hydro, key, value=val)
    hydro.find('PoreWaterBulkModulus').set('comment', 'Provisional numerical Kw from case03, NOT a Table 5 material parameter; sensitivity check required')
    hydro.append(ET.Comment(' Failure requires basal DELTA p=110000*min(t_stage/10,1) Pa on x=[0,24], y=[0,25], z=0. NOT implemented by externalload. See specification; no fake XML option is used. '))
    node(special, 'drainage', mode='drained')
    slip = node(special, 'mdbcslip')
    for mk in range(5):
        node(slip, 'bound', mkbound=mk, slipmode=2 if mk==0 else 3, comment='Fixed no-slip base' if mk==0 else 'Undrained mechanical roller approximation')
    params = root.find('execution/parameters')
    updates = {'SavePosDouble':1,'DPCtes':1,'SlipMode':3,'NoPenetration':1,'SoilDamping':1 if stage=='prestress' else 0,'DensityDT':0,'DtFixed':0,'DtMin':'1e-9','TimeMax':20 if stage=='prestress' else 100,'TimeOut':0.5,'PartsOutMax':0.001,'RhopOutMin':1400,'RhopOutMax':2800}
    comments = {'DPCtes':'3D circumscribed DP; differs from paper SMP mapping, see model notes','TimeMax':'Provisional horizon; convergence/failure must be assessed, not assumed','DtFixed':'Adaptive mechanical and hydraulic stability limits; do not copy MPM dt=1e-3','SoilDamping':'Gravity relaxation only; disabled in failure','DensityDT':'Disabled pending heterogeneous-interface verification','DtMin':'Small lower clamp for high conductivity; validate reported diffusion dt','PartsOutMax':'Abort on excessive particle loss','SlipMode':'Side-wall free-slip; base overridden by mdbcslip'}
    for p in params.findall('parameter'):
        key=p.get('key')
        if key in updates:
            p.set('value',str(updates[key]))
            p.set('comment',comments.get(key,'Selborne preparation setting; see README'))
    sd=params.find('simulationdomain')
    sd.find('posmin').attrib.update(x='default - 2',y='default - 2',z='default - 2')
    sd.find('posmax').attrib.update(x='default + 10',y='default + 2',z='default + 5')
    ET.indent(root, space='    ')
    return '<?xml version="1.0" encoding="UTF-8" ?>\n'+ET.tostring(root,encoding='unicode')+'\n'


def main():
    for stage in ('prestress','failure'):
        save(ROOT / f'CaseSelborne3D_u_pw_{stage}_Def.xml', make_xml(stage))
    spec = {
        'status':'PREPARATION_ONLY_SOLVER_BLOCKED',
        'source':'FSM-MPM section 4.3, Fig.12, Table 5 (PDF pp.12-15)',
        'coordinates':'x from high left boundary toward downhill; y transverse; z upward; base z=0',
        'geometry':{'length_m':56,'width_m':25,'base_height_m':6,'slope_height_m':9,'crest_x_m':18,'toe_x_m':36,'initial_dp_m':0.5,'target_dp_m':0.2,'lower_volume_m3':8400,'upper_volume_m3':6075},
        'shared':{'grain_density_kg_m3':2700,'water_density_kg_m3':1000,'mixture_density_kg_m3':2054,'porosity':0.38,'hydraulic_conductivity_m_s':0.001,'E_Pa':20000000,'nu':0.33,'dilation_deg':0,'tensile_strength_Pa':0},
        'materials':[
            {'mkfluid':0,'name':'Unweathered Gault clay','phi_peak_deg':26,'phi_residual_deg':15,'cohesion_peak_Pa':25000,'cohesion_residual_Pa':500,'n_phi':0.5,'n_coh':0.5},
            {'mkfluid':1,'name':'Weathered Gault clay','phi_peak_deg':24,'phi_residual_deg':13,'cohesion_peak_Pa':15000,'cohesion_residual_Pa':500,'n_phi':5,'n_coh':5}
        ],
        'basal_loading':{'status':'REQUIRES_CODE_CHANGE','mkbound':0,'physical_region':{'x':[0,24],'y':[0,25],'z':0},'quantity':'increment relative to equilibrated prestress basal pressure','delta_p_Pa':110000,'ramp_s':10,'hold_after_ramp':True,'clock':'failure stage elapsed time; zero at restart','outside_region':'impermeable','solid':'fixed throughout'},
        'prestress':{'softening':False,'strength':'peak values of each layer, no artificial cohesion increase','end':'require kinetic energy, velocity, force balance and pore-pressure settling; 20 s is only a draft horizon'},
        'failure':{'restart':'inherit geometry, ids, material tags, velocity, effective stress, kplastic, PorePress, PorePress0 and mDBC normals','SoilTriggerFos':1,'softening':True,'duration_s_provisional':100},
        'numerical_assumptions':{'Kw_Pa':200000000,'DPCtes':1,'constitutive_match':'current 3D DP is not paper SMP-DP; confirm plastic strain measure before transferring softening coefficients','tension_cutoff':'zero tensile strength must be audited; no XML option claimed','excavation_history':'omitted, following FSM-MPM; Morikawa explicitly includes it'}
    }
    save(ROOT/'support/model_spec.json',json.dumps(spec,indent=2,ensure_ascii=False)+'\n')
    geometry_bat='''@echo off
setlocal
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "tests\support\check_geometry.ps1"
set "rc=%errorlevel%"
popd
pause
exit /b %rc%
'''
    save(ROOT/'xCheckSelborne3D_geometry_win64_CPU.bat',geometry_bat.replace('\n','\r\n'))
    for stage in ('prestress','failure'):
        bat=f'''@echo off
setlocal
pushd "%~dp0"
echo Selborne 3D {stage}: PREPARATION ONLY - SOLVER NOT STARTED.
echo Current solver uses one global SoilCte; mkfluid does not select materials.
echo A regional basal pore-pressure ramp is also missing.
echo Read README.md and support\code_change_plan.md before enabling this stage.
echo Double-click xCheckSelborne3D_geometry_win64_CPU.bat for GenCase checks.
popd
pause
exit /b 2
'''
        save(ROOT/f'xCaseSelborne3D_u_pw_{stage}_win64_CPU.bat',bat.replace('\n','\r\n'))


if __name__=='__main__':
    main()
