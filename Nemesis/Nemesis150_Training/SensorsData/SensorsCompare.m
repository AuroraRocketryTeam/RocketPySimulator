close,clear,clc


% Read CATS log 
logCATS = readmatrix("SensorsData\logCATS.csv");

log_time = (logCATS(:,2) - 20180)/10; % time is in decisecons (1 dsec = 0.1 sec) and starts from 20180 dsec
log_altitude = logCATS(:,7); % altitudeitude
log_vz = logCATS(:,8);       % vertical velocity

Lt = log_time;
Lalt = log_altitude;
Lvz = log_vz;

% Read RocketPy simulation (n=300) log
logPy_vz = readmatrix("SensorsData\vz_mean.csv");
logPy_altitude = readmatrix("SensorsData\altitude_mean.csv");
logPy_az = readmatrix("SensorsData\az_mean.csv");

vz_time = logPy_vz(:,1); % time step for vz
vz = logPy_vz(:,2); % vz

az_time = logPy_az(:,1); % time step for az
az = logPy_az(:,2); % az

altitude_time = logPy_altitude(:,1); % time step for altitude
altitude = logPy_altitude(:,2); % altitude


% The burnout time can be clearly see from the video is ~5.3s
% this confirms what is written in the motor specs

% Plot altitude over time
figure;
plot(Lt, Lalt, "-b");
hold on;
plot(altitude_time, altitude, "-k")
xlabel('Time [s]');
ylabel('Altitude [m]');
title('Altitude over Time');
theme('light')
legend('CATS','RocketPy')
grid on;


% Plot vertical velocity over time
figure;
plot(Lt, Lvz, "-r");
hold on; 
plot(vz_time, vz, '-k')
xlabel('Time [s]');
ylabel('Vertical Velocity [m/s]');
title('Vertical Velocity over Time');
theme('light')
legend('CATS','RocketPy')
grid on;



%% VERTICAL ACCELERATION
% Correct time intervals by removing the link=2 measurements

log_link = logCATS(:,1);
[index] = find(log_link == 2);

% remove link=2 cells
log_time(index) = [];
log_vz(index) = [];

% Vertical Acceleration

az_nonFiltered = gradient(log_vz,log_time); % non-filtered

% filtered (median) 
vzFiltered = medfilt1(log_vz, 9);
azFiltered = gradient(vzFiltered,log_time); % gradient


% Plot Vertical Acceleration
figure; 
%plot(log_time,az_nonFiltered,'g') % dati non filtrati
%hold on;
plot(log_time,azFiltered,'g') % median
hold on;
plot(az_time, az, 'k') % rocketpy
xlabel('Time [s]');
ylabel('Vertical Acceleration [m/s^2]');
title('Vertical Acceleration over Time')
theme('light')
legend('median', 'RocketPy')
grid on;




