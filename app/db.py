"""Acceso a datos con SQLite. Todo el SQL de la aplicación vive en este módulo.

Esquema (dos tablas relacionadas):
    proyectos (1) ──< calculos (N)
Al eliminar un proyecto se eliminan sus cálculos (ON DELETE CASCADE).

Todas las consultas son parametrizadas con '?': nunca se concatenan cadenas.
"""
import json
import sqlite3
from datetime import datetime
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


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------------------- proyectos
def obtener_o_crear_proyecto(con, nombre, ubicacion=""):
    """Retorna el id del proyecto con ese nombre; lo crea si no existe."""
    fila = con.execute("SELECT id FROM proyectos WHERE nombre = ?", (nombre,)).fetchone()
    if fila:
        return fila["id"]
    cur = con.execute(
        "INSERT INTO proyectos (nombre, ubicacion, creado) VALUES (?, ?, ?)",
        (nombre, ubicacion, _ahora()),
    )
    con.commit()
    return cur.lastrowid


def listar_proyectos(con):
    """Lista de proyectos con el número de cálculos de cada uno."""
    return con.execute(
        """SELECT p.id, p.nombre, p.ubicacion, p.creado, COUNT(c.id) AS n_calculos
           FROM proyectos p LEFT JOIN calculos c ON c.proyecto_id = p.id
           GROUP BY p.id ORDER BY p.nombre"""
    ).fetchall()


def eliminar_proyecto(con, proyecto_id):
    """Elimina un proyecto y, en cascada, todos sus cálculos."""
    con.execute("DELETE FROM proyectos WHERE id = ?", (proyecto_id,))
    con.commit()


# ---------------------------------------------------------------- cálculos
def guardar_calculo(con, proyecto_id, descripcion, entradas, resultados, cumple):
    """Guarda un cálculo. ``entradas`` y ``resultados`` son diccionarios."""
    cur = con.execute(
        """INSERT INTO calculos (proyecto_id, descripcion, fecha, entradas, resultados, cumple)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (proyecto_id, descripcion, _ahora(), json.dumps(entradas),
         json.dumps(resultados), int(cumple)),
    )
    con.commit()
    return cur.lastrowid


def buscar_calculos(con, texto=""):
    """Lista los cálculos cuyo proyecto o descripción contienen ``texto``.

    Con texto vacío retorna todos, del más reciente al más antiguo.
    """
    patron = f"%{texto.strip()}%"
    return con.execute(
        """SELECT c.id, p.nombre AS proyecto, c.descripcion, c.fecha, c.cumple
           FROM calculos c JOIN proyectos p ON p.id = c.proyecto_id
           WHERE p.nombre LIKE ? OR c.descripcion LIKE ?
           ORDER BY c.id DESC""",
        (patron, patron),
    ).fetchall()


def obtener_calculo(con, calculo_id):
    """Retorna un diccionario con el cálculo completo, o None si no existe."""
    fila = con.execute(
        """SELECT c.*, p.nombre AS proyecto, p.ubicacion
           FROM calculos c JOIN proyectos p ON p.id = c.proyecto_id
           WHERE c.id = ?""",
        (calculo_id,),
    ).fetchone()
    if fila is None:
        return None
    calculo = dict(fila)
    calculo["entradas"] = json.loads(calculo["entradas"])
    calculo["resultados"] = json.loads(calculo["resultados"])
    return calculo


def eliminar_calculo(con, calculo_id):
    """Elimina un cálculo por su id."""
    con.execute("DELETE FROM calculos WHERE id = ?", (calculo_id,))
    con.commit()
