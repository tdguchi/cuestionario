-- Tabla para configuraciones de puntuación
CREATE TABLE IF NOT EXISTS scoring_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT UNIQUE,  -- NULL para configuración global
    base_score REAL NOT NULL DEFAULT 0.0,
    correct_value REAL NOT NULL DEFAULT 1.0,
    incorrect_penalty REAL NOT NULL DEFAULT 0.25,
    blank_penalty REAL NOT NULL DEFAULT 0.0
);

-- Insertar configuración global por defecto
INSERT INTO scoring_config (subject, base_score, correct_value, incorrect_penalty, blank_penalty)
VALUES (NULL, 0.0, 1.0, 0.25, 0.0);
