
import sqlite3
import os
from datetime import datetime


RUTA_DB = os.path.join("data", "estudio.db")


def conectar():
    os.makedirs("data", exist_ok=True)

    conexion = sqlite3.connect(RUTA_DB)
    conexion.execute("""
        CREATE TABLE IF NOT EXISTS historial_estudio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            pregunta TEXT NOT NULL,
            respuesta TEXT NOT NULL,
            fecha TEXT NOT NULL
        )
    """)
    conexion.commit()

    return conexion


def guardar_interaccion(
    user_id: int,
    tipo: str,
    pregunta: str,
    respuesta: str
):
    conexion = conectar()

    try:
        conexion.execute("""
            INSERT INTO historial_estudio
            (user_id, tipo, pregunta, respuesta, fecha)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            tipo,
            pregunta,
            respuesta,
            datetime.now().isoformat(timespec="seconds")
        ))

        conexion.commit()
    finally:
        conexion.close()


def consultar_historial(user_id: int, limite: int = 10):
    conexion = conectar()

    try:
        cursor = conexion.execute("""
            SELECT id, tipo, pregunta, respuesta, fecha
            FROM historial_estudio
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limite))

        return cursor.fetchall()
    finally:
        conexion.close()
