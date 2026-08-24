-- Consulta 1: Agregación -- total de tickets por área
SELECT a.nombre AS area, COUNT(*) AS total_tickets
FROM tickets t
JOIN areas a ON t.id_area = a.id_area
GROUP BY a.nombre
ORDER BY total_tickets DESC;

-- Consulta 2: Join de tres tablas -- tickets con su área y su usuario
SELECT t.codigo, u.nombre AS usuario, a.nombre AS area, t.prioridad, t.estado
FROM tickets t
JOIN usuarios u ON t.id_usuario = u.id_usuario
JOIN areas a ON t.id_area = a.id_area
ORDER BY t.codigo;

-- Consulta 3: Tickets reabiertos, de más a menos reaperturas
SELECT codigo, reaperturas
FROM tickets
WHERE reaperturas > 0
ORDER BY reaperturas DESC;