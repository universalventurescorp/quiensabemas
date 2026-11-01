-- Base D1 "quiensabemas" de la web de salas.
CREATE TABLE IF NOT EXISTS grupos (
  codigo  TEXT PRIMARY KEY,
  sala    TEXT NOT NULL,
  creado  INTEGER NOT NULL,
  inicio  INTEGER,            -- ms en que alguien tocó EMPEZAR (al oír «¡YA!»)
  pausa   INTEGER,            -- ms en que se pausó (NULL si corre)
  pausado INTEGER NOT NULL DEFAULT 0,  -- ms acumulados en pausa
  ajuste  INTEGER NOT NULL DEFAULT 0   -- ms de corrección manual de sincronía
);
CREATE TABLE IF NOT EXISTS jugadores (
  id       TEXT PRIMARY KEY,
  codigo   TEXT NOT NULL REFERENCES grupos(codigo),
  apodo    TEXT NOT NULL,
  fama     INTEGER NOT NULL DEFAULT 0, -- aceptó salir en el Salón de la fama
  puntos   INTEGER NOT NULL DEFAULT 0,
  aciertos INTEGER NOT NULL DEFAULT 0,
  ultima   INTEGER NOT NULL DEFAULT 0, -- última pregunta reportada
  act      INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS jugadores_codigo ON jugadores(codigo);
CREATE INDEX IF NOT EXISTS grupos_sala ON grupos(sala);
