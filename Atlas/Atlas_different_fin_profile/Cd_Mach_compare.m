close,clear,clc

hex = readmatrix("Atlas\Atlas_v1.0_hex\Hexagonal_power_on.CSV");
hexblunt = readmatrix("Atlas\Atlas_v1.0_hex_blunt\Hexagonal_blunt_base_power_on.CSV");
square = readmatrix("Atlas\Atlas_v1.0_square\square_power_on.CSV");

Mach = hex(:,1); % mach number
Cd_hex = hex(:,2); % hexagonal profile cd

Cd_hexblunt = hexblunt(:,2); % hexagonal blunt profile cd

Cd_square = square(:,2); % square profile cd

figure;

plot(Mach,Cd_hex, 'r')
hold on;
plot(Mach,Cd_hexblunt, 'b')
hold on;
plot(Mach,Cd_square, 'g')
grid on
xlabel('Mach number')
ylabel('Cd')
legend('hexagonal','hexagonal blunt','square')