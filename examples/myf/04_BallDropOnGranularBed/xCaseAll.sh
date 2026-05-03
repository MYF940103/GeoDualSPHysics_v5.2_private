#!/bin/bash 

./xCaseBallDrop3D_vel1.12_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseBallDrop3D_vel1.87_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseBallDrop3D_vel3.03_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseBallDrop3D_vel3.3_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseBallDrop3D_vel3.63_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi