function v = toNumericColumn(x)

    % Caso 1: già numerico
    if isnumeric(x)
        v = x(:);
        v = v(~isnan(v));
        return
    end

    % Caso 2: cell array
    if iscell(x)
        mask = cellfun(@(y) isnumeric(y) && isscalar(y) && ~isnan(y), x);
        v = cell2mat(x(mask));
        v = v(:);
        return
    end

    % Caso 3: altro tipo → scarta
    v = [];
end