##Test on Octave
clear
A=dlmread('./CaseCubeSlidingSlope_kfric0.0_out/ChronoExchange_mkbound_2.csv');
% Input data
time=A(:,2);
theta=30;%degree slope angle
mu=0.0;%friction angle

distancex_=A(:,14)-A(2,14);%actual value of distancex
distancex_(1,1)=0;
distancez_=A(:,16)-A(2,16);
distancez_(1,1)=0;
distance=sqrt(distancex_.^2+distancez_.^2);


%analytical solution of the distance
d=0.5*9.81*(sind(theta)-mu*cosd(theta))*time.^2;

%output distance
plot(time,distance,'r');
hold on
scatter(time,d,'r');
axis([0 1 0 2])

A=dlmread('./CaseCubeSlidingSlope_kfric0.1_out/ChronoExchange_mkbound_2.csv');
% Input data
time=A(:,2);
theta=30;%degree slope angle
mu=0.1;%friction angle

distancex_=A(:,14)-A(2,14);%actual value of distancex
distancex_(1,1)=0;
distancez_=A(:,16)-A(2,16);
distancez_(1,1)=0;
distance=sqrt(distancex_.^2+distancez_.^2);


%analytical solution of the distance
d=0.5*9.81*(sind(theta)-mu*cosd(theta))*time.^2;

%output distance
plot(time,distance,'g');
scatter(time,d,'g');

A=dlmread('./CaseCubeSlidingSlope_kfric0.3_out/ChronoExchange_mkbound_2.csv');
% Input data
time=A(:,2);
theta=30;%degree slope angle
mu=0.3;%friction angle

distancex_=A(:,14)-A(2,14);%actual value of distancex
distancex_(1,1)=0;
distancez_=A(:,16)-A(2,16);
distancez_(1,1)=0;
distance=sqrt(distancex_.^2+distancez_.^2);


%analytical solution of the distance
d=0.5*9.81*(sind(theta)-mu*cosd(theta))*time.^2;

%output distance
plot(time,distance,'b');
scatter(time,d,'b');

A=dlmread('./CaseCubeSlidingSlope_kfric0.6_out/ChronoExchange_mkbound_2.csv');
% Input data
time=A(:,2);
theta=30;%degree slope angle
mu=0.6;%friction angle

distancex_=A(:,14)-A(2,14);%actual value of distancex
distancex_(1,1)=0;
distancez_=A(:,16)-A(2,16);
distancez_(1,1)=0;
distance=sqrt(distancex_.^2+distancez_.^2);


%analytical solution of the distance
d=0.*time;

%output distance
plot(time,distance,'m');
scatter(time,d,'m');
