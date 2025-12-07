USE tfg;
DELETE FROM tickets_clasificados
WHERE modelo_version = 'SVM_v1.1';
INSERT INTO tickets_clasificados (
    id_ticket,
    id_tipo_predicho,
    score_predicho,
    modelo_version,
    fecha_inferencia
)
SELECT
    f.id_ticket,
    dt.id_tipo,
    NULL,
    'SVM_v1.1',
    NOW()
FROM stg_predicciones p
JOIN f_tickets f
      ON f.ticket_code = p.id_ticket
JOIN d_tipo dt
      ON dt.codigo = p.pred_cat;