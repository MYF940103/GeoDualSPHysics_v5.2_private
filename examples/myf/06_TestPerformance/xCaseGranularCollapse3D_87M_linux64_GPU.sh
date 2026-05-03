

# "name" and "dirout" are named according to the testcase

export name=CaseGranularCollapse3D_87M
export dirout=${name}_out
export diroutdata=${dirout}/data

# "executables" are renamed and called from their directory
export dirbin=../../bin/linux
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${dirbin}
export gencase="${dirbin}/GenCase_linux64"
export dualsphysicscpu="${dirbin}/DualSPHysics5.2CPU_linux64"
export dualsphysicsgpu="${dirbin}/DualSPHysics5.2_linux64"
export boundaryvtk="${dirbin}/BoundaryVTK_linux64"
export partvtk="${dirbin}/PartVTK_linux64"
export partvtkout="${dirbin}/PartVTKOut_linux64"
export measuretool="${dirbin}/MeasureTool_linux64"
export isosurface="${dirbin}/IsoSurface_linux64"
export floatinginfo="${dirbin}/FloatingInfo_linux64"
export tovtk="${dirbin}/ToVTK_linux64"

${gencase} ${name}_Def ${dirout}/${name} -save:all

${dualsphysicsgpu} -gpu ${dirout}/${name} ${dirout} -dirdataout data -svres

export dirout2=${dirout}/particles
${tovtk} -dirin ${diroutdata} -filexml ${dirout}/${name}.xml -savevtk ${dirout2}/PartFluid