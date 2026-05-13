from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


COMMON_PARAMS = """      <parameter key="SavePosDouble" value="0" />
      <parameter key="DPCtes" value="3" />
      <parameter key="Boundary" value="1" />
      <parameter key="SlipMode" value="1" />
      <parameter key="StepAlgorithm" value="2" />
      <parameter key="Kernel" value="2" />
      <parameter key="ViscoTreatment" value="1" />
      <parameter key="Visco" value="1.0" />
      <parameter key="DensityDT" value="0" />
      <parameter key="Shifting" value="0" />
      <parameter key="RigidAlgorithm" value="1" />
      <parameter key="CoefDtMin" value="0.01" />
      <parameter key="#DtIni" value="0.000001" />
      <parameter key="#DtMin" value="0.00000001" />
      <parameter key="DtAllParticles" value="0" />
      <parameter key="TimeMax" value="{time_max}" />
      <parameter key="TimeOut" value="0.00025" />
      <parameter key="PartsOutMax" value="1" />
      <parameter key="RhopOutMin" value="500" />
      <parameter key="RhopOutMax" value="3000" />
      <simulationdomain>
        <posmin x="-0.08" y="-0.08" z="-0.03" />
        <posmax x="0.08" y="0.08" z="0.13" />
      </simulationdomain>
      <parameter key="HydromechCoupling" value="1" />
      <parameter key="PorePressureModel" value="1" />
      <parameter key="PorePressureBoundaryOperator" value="0" />
      <parameter key="HydraulicElevationSource" value="0" />
      <parameter key="PorePressureInit" value="0" />
      <parameter key="PorePressureTopDrained" value="0" />
      <parameter key="PorePressureBottomNoFlux" value="0" />
      <parameter key="SavePorePressure" value="1" />
      <parameter key="PorePressureDtSafety" value="0.20" />
      <parameter key="InitialStressMode" value="1" />
      <parameter key="InitialEffectiveStressIso" value="50" />
      <parameter key="InitialEffectiveStressTargetMk" value="-1" />
      <parameter key="PorePressureFeedback" value="{feedback}" />
      <parameter key="PorePressureFeedbackStartTime" value="0.003" />
      <parameter key="PorePressureFeedbackRampEndTime" value="0.0045" />
      <parameter key="PorePressureFeedbackScale" value="1" />
      <parameter key="SavePorePressureFeedbackDiagnostics" value="1" />
      <parameter key="PorePressureFeedbackDiagInterval" value="1" />
      <parameter key="PorePressureFeedbackLimiterMode" value="0" />
      <parameter key="PorePressureFeedbackRelaxation" value="0" />
      <parameter key="PorePressureFeedbackMaxAccel" value="0" />
      <parameter key="PorePressureFeedbackMaxAccelRatio" value="0" />
      <parameter key="PorePressureFeedbackUseClassFilter" value="{feedback_class_filter}" />
      <parameter key="PorePressureFeedbackExcludeCaps" value="0" />
      <parameter key="PorePressureFeedbackExcludeEdges" value="0" />
      <parameter key="PorePressureFeedbackExcludeConfinementTargets" value="0" />
      <parameter key="PorePressureFeedbackInteriorOnly" value="{feedback_interior_only}" />
      <parameter key="HydraulicGravityX" value="0" />
      <parameter key="HydraulicGravityY" value="0" />
      <parameter key="HydraulicGravityZ" value="-9.81" />
      <parameter key="PorePressureFeedbackMode" value="1" />
      <parameter key="PorePressureFeedbackOperator" value="1" />
      <parameter key="HydromechDamping" value="1" />
      <parameter key="HydromechDampingXi" value="0.05" />
      <parameter key="PorePressureShepard" value="1" />
      <parameter key="PorePressureShepardInterval" value="10" />
      <parameter key="PorePressureShepardMode" value="1" />
      <parameter key="FlexibleConfiningStress" value="{flex_conf}" />
      <parameter key="ConfiningStressP0" value="50" />
      <parameter key="ConfiningStressRampStart" value="0" />
      <parameter key="ConfiningStressRampEnd" value="0.001" />
      <parameter key="ConfiningStressTargetMk" value="-1" />
      <parameter key="ConfiningStressMode" value="0" />
      <parameter key="ConfiningStressGradientMode" value="0" />
      <parameter key="FlexibleConfiningStressFiDiagnostic" value="1" />
      <parameter key="ConfiningStressFiThreshold" value="0.70" />
      <parameter key="SaveConfiningStressDiagnostics" value="1" />
      <parameter key="ConfiningStressGeometry" value="1" />
      <parameter key="ConfiningStressCylinderCenterX" value="0" />
      <parameter key="ConfiningStressCylinderCenterY" value="0" />
      <parameter key="ConfiningStressCylinderCenterZ" value="0" />
      <parameter key="ConfiningStressCylinderAxisX" value="0" />
      <parameter key="ConfiningStressCylinderAxisY" value="0" />
      <parameter key="ConfiningStressCylinderAxisZ" value="1" />
      <parameter key="ConfiningStressCylinderRadius" value="0.03" />
      <parameter key="ConfiningStressCylinderHeight" value="0.10" />
      <parameter key="ConfiningStressCapExclusionLength" value="0.015" />
      <parameter key="ConfiningStressEdgeExclusionLength" value="0.015" />
      <parameter key="ConfiningStressUseFiSelector" value="1" />
      <parameter key="ConfiningStressUseLateralSelector" value="1" />"""


def build_xml(name, title, params, accinput=False):
    acc = ""
    if accinput:
        acc = """      <accinputs>
        <accinput mkfluid="1">
          <time start="0.0048" end="0.006" />
          <acccentre x="0" y="0" z="0" />
          <globalgravity value="1" />
          <acctimesfile value="TriaxialAxialAcc_T4k.csv" />
        </accinput>
      </accinputs>
"""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<case app="GenCase v5.0.197 (18-07-2020)" date="{title}">
  <casedef>
    <constantsdef>
      <gravity x="0" y="0" z="0" comment="Mechanical body gravity disabled" units_comment="m/s^2" />
      <rhop0 value="2100" comment="Reference bulk density" units_comment="kg/m^3" />
      <hswl value="0" auto="true" comment="Maximum still water level" units_comment="metres (m)" />
      <gamma value="7" comment="Polytropic constant" />
      <speedsystem value="0" auto="true" comment="Maximum system speed" />
      <coefsound value="20" comment="Coefficient to multiply speedsystem" />
      <speedsound value="20" auto="false" comment="Explicit non-zero sound speed" />
      <hdp value="1.8" comment="h=hdp*dp" />
      <cflnumber value="0.2" comment="Coefficient to multiply dt" />
    </constantsdef>
    <mkconfig boundcount="240" fluidcount="9" />
    <geometry>
      <predefinition>
        <newvarcte R="0.03" />
        <newvarcte Hcyl="0.10" />
        <newvarcte Dp="0.01" />
      </predefinition>
      <definition dp="#Dp" units_comment="metres (m)">
        <pointmin x="-0.08" y="-0.08" z="-0.03" />
        <pointmax x="0.08" y="0.08" z="0.13" />
      </definition>
      <commands>
        <mainlist>
          <setshapemode>dp | bound</setshapemode>
          <setdrawmode mode="full" />
          <setmkfluid mk="0" />
          <drawcylinder radius="#R">
            <point x="0" y="0" z="0" />
            <point x="0" y="0" z="#Hcyl-Dp" />
          </drawcylinder>
          <setmkfluid mk="1" name="AxialLoadLayer" />
          <drawcylinder radius="#R">
            <point x="0" y="0" z="#Hcyl-Dp" />
            <point x="0" y="0" z="#Hcyl" />
          </drawcylinder>
          <shapeout file="" />
        </mainlist>
      </commands>
    </geometry>
  </casedef>
  <execution>
    <special>
      <soils>
        <SoilConstitutiveModel value="0" comment="Linear elastic skeleton diagnostic" />
        <phi value="33" comment="Ignored by linear elastic mode" />
        <coh value="10e3" comment="Ignored by linear elastic mode" />
        <dlt value="0" comment="Dilatancy angle" />
        <ModulusE value="2e6" comment="Young modulus" />
        <PRvs value="0.3" comment="Poisson ratio" />
        <Porosity0 value="0.3" comment="Porosity" />
        <HydraulicConductivity value="1e-8" comment="Hydraulic conductivity [m/s]" />
        <WaterBulkModulus value="2e8" comment="Water bulk modulus [Pa]" />
        <WaterDensity value="1000" comment="Water density [kg/m3]" />
      </soils>
{acc}    </special>
    <parameters>
{params}
    </parameters>
  </execution>
</case>
"""


CASES = [
    ("CaseT4k_InitialStressOnly_FeedbackOff", "T4k initial hydrostatic effective stress only, feedback off",
     dict(time_max="0.006", feedback="0", feedback_class_filter="0", feedback_interior_only="0", flex_conf="0"), False),
    ("CaseT4k_InitialStressPlusConf_FeedbackOff", "T4k initial effective stress plus selected flexible confinement, feedback off",
     dict(time_max="0.006", feedback="0", feedback_class_filter="0", feedback_interior_only="0", flex_conf="1"), False),
    ("CaseT4k_InitialStressPlusConf_FeedbackDelayed", "T4k initial effective stress plus selected flexible confinement, delayed interior feedback",
     dict(time_max="0.006", feedback="1", feedback_class_filter="1", feedback_interior_only="1", flex_conf="1"), False),
    ("CaseT4k_InitialStressPlusConf_AxialSmoke", "T4k optional axial smoke after initial effective stress and delayed feedback",
     dict(time_max="0.006", feedback="1", feedback_class_filter="1", feedback_interior_only="1", flex_conf="1"), True),
]


BAT_TEMPLATE = """@echo off
setlocal
set dirbin=..\\..\\..\\..\\..\\bin\\windows
set gencase="%dirbin%\\GenCase_win64.exe"
set dualsphysicscpu="%dirbin%\\DualSPHysics5.2CPU_win64.exe"
set name={name}
set dirout=%name%_out
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\\%name% -save:all
if not "%ERRORLEVEL%" == "0" exit /b 1
%dualsphysicscpu% -cpu %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx -svres
if not "%ERRORLEVEL%" == "0" exit /b 1
echo T4k CPU Release completed for %name%.
exit /b 0
"""


def main():
    for name, title, values, axial in CASES:
        params = COMMON_PARAMS.format(**values)
        (ROOT / f"{name}_Def.xml").write_text(build_xml(name, title, params, axial), encoding="utf-8")
        (ROOT / f"xRun_{name}_win64_CPU_release.bat").write_text(BAT_TEMPLATE.format(name=name), encoding="utf-8")
    (ROOT / "TriaxialAxialAcc_T4k.csv").write_text(
        "#Time;LinearAccX;LinearAccY;LinearAccZ;AngularAccX;AngularAccY;AngularAccZ\n"
        "0;0;0;0;0;0;0\n"
        "0.0048;0;0;0;0;0;0\n"
        "0.0052;0;0;-0.2;0;0;0\n"
        "0.006;0;0;-0.2;0;0;0\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
