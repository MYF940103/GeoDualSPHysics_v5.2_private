#!/usr/bin/env python3
"""Generate T4q explicit platen boundary XML/BAT smoke cases."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent


BASE_PARAMS = {
    "R": "0.03",
    "Hcyl": "0.10",
    "PlateH": "0.02",
    "Dp": "0.01",
}


CASES = [
    {
        "name": "CaseT4q_PlatenGeometry_NoLoad",
        "date": "T4q explicit platen geometry check, no platen motion",
        "time_max": "0.001",
        "top_motion": False,
        "lateral_confinement": False,
    },
    {
        "name": "CaseT4q_TopVelocity_NoConfinement",
        "date": "T4q top prescribed-velocity platen smoke, no lateral confinement",
        "time_max": "0.0015",
        "top_motion": True,
        "lateral_confinement": False,
    },
    {
        "name": "CaseT4q_TopVelocity_LateralConfinement",
        "date": "T4q top prescribed-velocity platen with lateral flexible confinement",
        "time_max": "0.0015",
        "top_motion": True,
        "lateral_confinement": True,
    },
]


def motion_block(active: bool) -> str:
    if not active:
        return ""
    return """    <motion>
      <objreal ref=\"1\">
        <begin mov=\"1\" start=\"0\" finish=\"0.0015\" />
        <mvrect id=\"1\" duration=\"0.0015\">
          <vel x=\"0\" y=\"0\" z=\"-0.005\" units_comment=\"m/s\" />
        </mvrect>
      </objreal>
    </motion>
"""


def confinement_params(active: bool) -> str:
    if not active:
        return """      <parameter key=\"FlexibleConfiningStress\" value=\"0\" />
      <parameter key=\"SaveConfiningStressDiagnostics\" value=\"0\" />
      <parameter key=\"CapConfiningStress\" value=\"0\" />
"""
    return """      <parameter key=\"FlexibleConfiningStress\" value=\"1\" />
      <parameter key=\"ConfiningStressP0\" value=\"50\" />
      <parameter key=\"ConfiningStressRampStart\" value=\"0\" />
      <parameter key=\"ConfiningStressRampEnd\" value=\"0.0005\" />
      <parameter key=\"ConfiningStressTargetMk\" value=\"-1\" />
      <parameter key=\"ConfiningStressMode\" value=\"0\" />
      <parameter key=\"ConfiningStressGradientMode\" value=\"0\" />
      <parameter key=\"FlexibleConfiningStressFiDiagnostic\" value=\"1\" />
      <parameter key=\"ConfiningStressFiThreshold\" value=\"0.70\" />
      <parameter key=\"SaveConfiningStressDiagnostics\" value=\"1\" />
      <parameter key=\"ConfiningStressGeometry\" value=\"1\" />
      <parameter key=\"ConfiningStressCylinderCenterX\" value=\"0\" />
      <parameter key=\"ConfiningStressCylinderCenterY\" value=\"0\" />
      <parameter key=\"ConfiningStressCylinderCenterZ\" value=\"0\" />
      <parameter key=\"ConfiningStressCylinderAxisX\" value=\"0\" />
      <parameter key=\"ConfiningStressCylinderAxisY\" value=\"0\" />
      <parameter key=\"ConfiningStressCylinderAxisZ\" value=\"1\" />
      <parameter key=\"ConfiningStressCylinderRadius\" value=\"0.03\" />
      <parameter key=\"ConfiningStressCylinderHeight\" value=\"0.10\" />
      <parameter key=\"ConfiningStressCapExclusionLength\" value=\"0.015\" />
      <parameter key=\"ConfiningStressEdgeExclusionLength\" value=\"0.015\" />
      <parameter key=\"ConfiningStressUseFiSelector\" value=\"1\" />
      <parameter key=\"ConfiningStressUseLateralSelector\" value=\"1\" />
      <parameter key=\"ConfiningStressLateralSelectorStartTime\" value=\"0\" />
      <parameter key=\"CapConfiningStress\" value=\"0\" />
"""


def xml_text(case: dict[str, object]) -> str:
    name = str(case["name"])
    return f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<case app=\"GenCase v5.0.197 (18-07-2020)\" date=\"{case['date']}\">
  <casedef>
    <constantsdef>
      <gravity x=\"0\" y=\"0\" z=\"0\" comment=\"Mechanical body gravity disabled\" units_comment=\"m/s^2\" />
      <rhop0 value=\"2100\" comment=\"Reference bulk density\" units_comment=\"kg/m^3\" />
      <hswl value=\"0\" auto=\"true\" comment=\"Maximum still water level\" units_comment=\"metres (m)\" />
      <gamma value=\"7\" comment=\"Polytropic constant\" />
      <speedsystem value=\"0\" auto=\"true\" comment=\"Maximum system speed\" />
      <coefsound value=\"20\" comment=\"Coefficient to multiply speedsystem\" />
      <speedsound value=\"20\" auto=\"false\" comment=\"Explicit non-zero sound speed\" />
      <hdp value=\"1.8\" comment=\"h=hdp*dp\" />
      <cflnumber value=\"0.2\" comment=\"Coefficient to multiply dt\" />
    </constantsdef>
    <mkconfig boundcount=\"240\" fluidcount=\"9\" />
    <geometry>
      <predefinition>
        <newvarcte R=\"{BASE_PARAMS['R']}\" />
        <newvarcte Hcyl=\"{BASE_PARAMS['Hcyl']}\" />
        <newvarcte PlateH=\"{BASE_PARAMS['PlateH']}\" />
        <newvarcte Dp=\"{BASE_PARAMS['Dp']}\" />
      </predefinition>
      <definition dp=\"#Dp\" units_comment=\"metres (m)\">
        <pointmin x=\"-0.08\" y=\"-0.08\" z=\"-0.04\" />
        <pointmax x=\"0.08\" y=\"0.08\" z=\"0.14\" />
      </definition>
      <commands>
        <mainlist>
          <setshapemode>real | bound</setshapemode>
          <setdrawmode mode=\"full\" />
          <setmkbound mk=\"2\" name=\"BottomPlaten\" />
          <drawcylinder radius=\"#R\">
            <point x=\"0\" y=\"0\" z=\"#-PlateH\" />
            <point x=\"0\" y=\"0\" z=\"#-Dp/2\" />
          </drawcylinder>
          <setmkbound mk=\"1\" name=\"TopPlaten\" />
          <drawcylinder radius=\"#R\">
            <point x=\"0\" y=\"0\" z=\"#Hcyl+Dp/2\" />
            <point x=\"0\" y=\"0\" z=\"#Hcyl+PlateH\" />
          </drawcylinder>
          <setshapemode>dp | bound</setshapemode>
          <setdrawmode mode=\"full\" />
          <setmkfluid mk=\"0\" name=\"Specimen\" />
          <drawcylinder radius=\"#R\">
            <point x=\"0\" y=\"0\" z=\"0\" />
            <point x=\"0\" y=\"0\" z=\"#Hcyl\" />
          </drawcylinder>
          <shapeout file=\"\" />
        </mainlist>
      </commands>
    </geometry>
{motion_block(bool(case['top_motion']))}  </casedef>
  <execution>
    <special>
      <soils>
        <SoilConstitutiveModel value=\"0\" comment=\"Linear elastic skeleton diagnostic\" />
        <phi value=\"33\" comment=\"Ignored by linear elastic mode\" />
        <coh value=\"10e3\" comment=\"Ignored by linear elastic mode\" />
        <dlt value=\"0\" comment=\"Dilatancy angle\" />
        <ModulusE value=\"2e6\" comment=\"Young modulus\" />
        <PRvs value=\"0.3\" comment=\"Poisson ratio\" />
        <Porosity0 value=\"0.3\" comment=\"Porosity\" />
        <HydraulicConductivity value=\"1e-8\" comment=\"Hydraulic conductivity [m/s]\" />
        <WaterBulkModulus value=\"2e8\" comment=\"Water bulk modulus [Pa]\" />
        <WaterDensity value=\"1000\" comment=\"Water density [kg/m3]\" />
      </soils>
    </special>
    <parameters>
      <parameter key=\"SavePosDouble\" value=\"0\" />
      <parameter key=\"DPCtes\" value=\"3\" />
      <parameter key=\"Boundary\" value=\"1\" />
      <parameter key=\"SlipMode\" value=\"1\" />
      <parameter key=\"StepAlgorithm\" value=\"2\" />
      <parameter key=\"Kernel\" value=\"2\" />
      <parameter key=\"ViscoTreatment\" value=\"1\" />
      <parameter key=\"Visco\" value=\"1.0\" />
      <parameter key=\"ViscoBoundFactor\" value=\"1\" />
      <parameter key=\"DensityDT\" value=\"0\" />
      <parameter key=\"Shifting\" value=\"0\" />
      <parameter key=\"RigidAlgorithm\" value=\"1\" />
      <parameter key=\"CoefDtMin\" value=\"0.01\" />
      <parameter key=\"#DtIni\" value=\"0.000001\" />
      <parameter key=\"#DtMin\" value=\"0.00000001\" />
      <parameter key=\"DtAllParticles\" value=\"0\" />
      <parameter key=\"TimeMax\" value=\"{case['time_max']}\" />
      <parameter key=\"TimeOut\" value=\"0.00025\" />
      <parameter key=\"PartsOutMax\" value=\"1\" />
      <parameter key=\"RhopOutMin\" value=\"500\" />
      <parameter key=\"RhopOutMax\" value=\"3000\" />
      <simulationdomain>
        <posmin x=\"-0.08\" y=\"-0.08\" z=\"-0.04\" />
        <posmax x=\"0.08\" y=\"0.08\" z=\"0.14\" />
      </simulationdomain>
      <parameter key=\"HydromechCoupling\" value=\"1\" />
      <parameter key=\"PorePressureModel\" value=\"1\" />
      <parameter key=\"PorePressureBoundaryOperator\" value=\"0\" />
      <parameter key=\"HydraulicElevationSource\" value=\"0\" />
      <parameter key=\"PorePressureInit\" value=\"0\" />
      <parameter key=\"PorePressureTopDrained\" value=\"0\" />
      <parameter key=\"PorePressureBottomNoFlux\" value=\"0\" />
      <parameter key=\"SavePorePressure\" value=\"1\" />
      <parameter key=\"PorePressureDtSafety\" value=\"0.20\" />
      <parameter key=\"InitialStressMode\" value=\"0\" />
      <parameter key=\"PorePressureFeedback\" value=\"0\" />
      <parameter key=\"PorePressureFeedbackScale\" value=\"1\" />
      <parameter key=\"SavePorePressureFeedbackDiagnostics\" value=\"0\" />
      <parameter key=\"HydraulicGravityX\" value=\"0\" />
      <parameter key=\"HydraulicGravityY\" value=\"0\" />
      <parameter key=\"HydraulicGravityZ\" value=\"-9.81\" />
      <parameter key=\"PorePressureFeedbackMode\" value=\"1\" />
      <parameter key=\"PorePressureFeedbackOperator\" value=\"1\" />
      <parameter key=\"HydromechDamping\" value=\"1\" />
      <parameter key=\"HydromechDampingXi\" value=\"0.05\" />
      <parameter key=\"PorePressureShepard\" value=\"1\" />
      <parameter key=\"PorePressureShepardInterval\" value=\"10\" />
      <parameter key=\"PorePressureShepardMode\" value=\"1\" />
{confinement_params(bool(case['lateral_confinement']))}    </parameters>
  </execution>
</case>
"""


def bat_text(case: dict[str, object]) -> str:
    name = str(case["name"])
    return f"""@echo off
setlocal
set dirbin=..\\..\\..\\..\\..\\bin\\windows
set gencase=\"%dirbin%\\GenCase_win64.exe\"
set dualsphysicscpu=\"%dirbin%\\DualSPHysics5.2CPU_win64.exe\"
set name={name}
set dirout=%name%_out
if exist %dirout% rd /s /q %dirout%
%gencase% %name%_Def %dirout%\\%name% -save:all
if not \"%ERRORLEVEL%\" == \"0\" exit /b 1
%dualsphysicscpu% -cpu %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx -svres
if not \"%ERRORLEVEL%\" == \"0\" exit /b 1
echo T4q CPU Release completed for %name%.
exit /b 0
"""


def main() -> None:
    for case in CASES:
        name = str(case["name"])
        with (ROOT / f"{name}_Def.xml").open("w", newline="\n") as f:
            f.write(xml_text(case))
        with (ROOT / f"xRun_{name}_win64_CPU_release.bat").open("w", newline="\n") as f:
            f.write(bat_text(case))


if __name__ == "__main__":
    main()
