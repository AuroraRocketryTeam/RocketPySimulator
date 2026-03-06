function export_flight_error(settings_list)
    global dispersion_error_file

    for i = 1:numel(settings_list)
        % Converto il contenuto della cell in stringa leggibile
        str_to_write = evalc('disp(settings_list)');  
        fprintf(dispersion_error_file, "%s\n", str_to_write);
    end
end