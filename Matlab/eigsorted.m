function [vals_sorted, vecs_sorted] = eigsorted(cov)
    % Calcola autovalori e autovettori di una matrice simmetrica
    [vecs, vals_matrix] = eig(cov);        % eig restituisce autovettori e matrice diagonale di autovalori
    vals = diag(vals_matrix);              % estrai autovalori come vettore

    % Ordina gli autovalori in ordine decrescente
    [vals_sorted, order] = sort(vals, 'descend');

    % Riordina gli autovettori in base all'ordine degli autovalori
    vecs_sorted = vecs(:, order);
end