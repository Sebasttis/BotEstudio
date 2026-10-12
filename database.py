
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "estudio.db"


def conectar():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row

    return conexion


def inicializar_bd():
    with conectar() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS apuntes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                materia TEXT NOT NULL,
                titulo TEXT NOT NULL,
                contenido TEXT NOT NULL,
                fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def guardar_apunte(usuario_id, materia, titulo, contenido):
    with conectar() as conexion:
        conexion.execute("""
            INSERT INTO apuntes
                (usuario_id, materia, titulo, contenido)
            VALUES (?, ?, ?, ?)
        """, (usuario_id, materia, titulo, contenido))


def obtener_apuntes(usuario_id, limite=10):
    with conectar() as conexion:
        cursor = conexion.execute("""
            SELECT id, materia, titulo, contenido, fecha
            FROM apuntes
            WHERE usuario_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (usuario_id, limite))

        return cursor.fetchall()


def buscar_apuntes(usuario_id, pregunta):
    palabras = {
        palabra.lower().strip(".,;:¿?¡!()")
        for palabra in pregunta.split()
        if len(palabra) >= 4
    }

    if not palabras:
        return []

    resultados = []

    with conectar() as conexion:
        cursor = conexion.execute("""
            SELECT id, materia, titulo, contenido, fecha
            FROM apuntes
            WHERE usuario_id = ?
            ORDER BY id DESC
            LIMIT 100
        """, (usuario_id,))

        for apunte in cursor.fetchall():
            texto = (
                apunte["materia"] + " " +
                apunte["titulo"] + " " +
                apunte["contenido"]
            ).lower()

            coincidencias = sum(
                1 for palabra in palabras if palabra in texto
            )

            if coincidencias:
                resultados.append((coincidencias, apunte))

    resultados.sort(key=lambda resultado: resultado[0], reverse=True)

    return [apunte for _, apunte in resultados[:3]]
