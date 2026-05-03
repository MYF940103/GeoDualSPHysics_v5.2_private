##Plot comparison between numerical and experiment results
##Test on Octave

A=dlmread('./CaseImapctForces3D_slope45_out/GaugesForce_Force1.csv',';');
theta=45;
mag=(-cosd(theta)*A(:,3)-cosd(90-theta)*A(:,5));%45
plot(A(:,1),mag,'r')
hold on
A=dlmread('./CaseImapctForces3D_slope50_out/GaugesForce_Force1.csv',';');
theta=50;
mag=(-cosd(theta)*A(:,3)-cosd(90-theta)*A(:,5));%50
plot(A(:,1),mag,'g')
A=dlmread('./CaseImapctForces3D_slope55_out/GaugesForce_Force1.csv',';');
theta=55;
mag=(-cosd(theta)*A(:,3)-cosd(90-theta)*A(:,5));%55
plot(A(:,1),mag,'b')
A=dlmread('./CaseImapctForces3D_slope60_out/GaugesForce_Force1.csv',';');
theta=60;
mag=(-cosd(theta)*A(:,3)-cosd(90-theta)*A(:,5));%60
plot(A(:,1),mag,'m');
A=dlmread('./CaseImapctForces3D_slope65_out/GaugesForce_Force1.csv',';');
theta=65;
mag=(-cosd(theta)*A(:,3)-cosd(90-theta)*A(:,5));%65
plot(A(:,1),mag,'k');

C=csvread('./Impact_force_exp.csv');
plot(C(:,1),C(:,2),'--r')
plot(C(:,3),C(:,4),'--g')
plot(C(:,5),C(:,6),'--b')
plot(C(:,7),C(:,8),'--m')
plot(C(:,9),C(:,10),'--k')
xlabel('Time(s)');ylabel('Forces(N)');
##legend('3Dcase1','3Dcase2','exp','other simulation','Location','SouthEast')
axis([0 2 0 800])
set(gca,'Fontname','Times New Roman')
set(gca,'Fontsize',12)
