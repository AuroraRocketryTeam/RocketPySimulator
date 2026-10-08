function flight_result = export_flight_data(flight_setting, flight_data, time)
    global dispersion_input_file dispersion_output_file
    % Importa o ricarica il modulo Python
    mod = py.importlib.import_module('export_flight_data');
    mod = py.importlib.reload(mod);

    % Chiama la funzione Python
    flight_result = mod.export_flight_data(flight_setting, flight_data, time,dispersion_input_file,dispersion_output_file);
end