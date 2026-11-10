"""Acceso a datos con SQLite. Todo el SQL de la aplicación vive en este módulo.

Esquema (dos tablas relacionadas):
    proyectos (1) ──< calculos (N)
Al eliminar un proyecto se eliminan sus cálculos (ON DELETE CASCADE).

Todas las consultas son parametrizadas con '?': nunca se concatenan cadenas.
"""
import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).resolve().parent.parent / "datos" / "cimentaciones.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS proyectos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL UNIQUE,
    ubicacion  TEXT,
    creado     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calculos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id  INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    descripcion  TEXT NOT NULL,
    fecha        TEXT NOT NULL,
    entradas     TEXT NOT NULL,   -- JSON con DatosCimentacion
    resultados   TEXT NOT NULL,   -- JSON con ResultadoCimentacion
    cumple       INTEGER NOT NULL -- 1 cumple / 0 no cumple
);
"""


def conectar(ruta=RUTA_DB):
    """Abre la conexión, activa llaves foráneas y crea las tablas si no existen."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Flet ejecuta los eventos en hilos distintos al principal; la app es de un
    # solo usuario, así que se permite usar la conexión desde esos hilos.
    con = sqlite3.connect(ruta, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con
