#!/bin/bash 

#./xCaseImapctForces3D_slope45_linux64_GPU.sh
#if [ $? -ne 0 ] ; then fail; fi
./xCaseImapctForces3D_slope50_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseImapctForces3D_slope55_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseImapctForces3D_slope60_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseImapctForces3D_slope65_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi