function settings_list = flight_settings(params, total_number)
    % FLIGHT_SETTINGS Genera un array di flight settings basati sui parametri

    settings_list = cell(total_number,1);
    i = 1;

    while i <= total_number
        keys = fieldnames(params);
        flight_setting = struct();

        for k = 1:numel(keys)
            key = keys{k};
            val = params.(key);

            if isnumeric(val) && numel(val) == 2
                % Distribuzione normale
                flight_setting.(key) = normrnd(val(1), val(2));
            else
                % Distribuzione discreta
                idx = randi(numel(val));
                flight_setting.(key) = val(idx);
            end
        end

        % Filtra valori non realistici
        if flight_setting.lag_rec < 0 || flight_setting.lag_se < 0
            continue
        end

        settings_list{i} = flight_setting;
        i = i + 1;
    end
end