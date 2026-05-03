#!/bin/bash 

./xCaseCubeSlidingSlope_kfric0.0_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseCubeSlidingSlope_kfric0.1_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseCubeSlidingSlope_kfric0.3_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi
./xCaseCubeSlidingSlope_kfric0.6_linux64_GPU.sh
if [ $? -ne 0 ] ; then fail; fi