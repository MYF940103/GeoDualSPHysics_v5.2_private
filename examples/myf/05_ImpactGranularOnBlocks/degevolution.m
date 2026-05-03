##Test on Octave
clear
A=dlmread('./CaseDamBreak3Cubes_out/ChronoExchange_mkbound_52.csv');
% Input data
time=A(:,2);
velx=A(:,11);
radovt=A(:,18);%in axis of y

%DO integral
distancex=cumtrapz(time, velx);
rad=cumtrapz(time, radovt);

%output degree
deg=-rad2deg(rad)+90;
plot(time,deg,'k');hold on

B=[0.1006	90
0.15023	90
0.20049	90
0.25076	88.3452
0.29967	74.58217
0.35065	30.72619
0.40173	3.4459
0.45271	0
0.50153	0
];

C=[0.09988	90
0.15023	90
0.20049	90
0.25148	82.66522
0.30183	77.85909
0.35137	41.62191
0.40245	23.08006
0.45127	0
0.50153	0
];

plot(B(:,1),B(:,2),'-or');
scatter(C(:,1),C(:,2),'square');


