from contextlib import closing
from datetime import datetime

# Usa la MISMA base de datos que los apuntes (ruta absoluta),
# así no depende de desde qué carpeta ejecutes el bot.
from database import conectar


def _asegurar_tabla(conexion):
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


def guardar_interaccion(
    user_id: int,
    tipo: str,
    pregunta: str,
    respuesta: str
):
    with closing(conectar()) as conexion:
        _asegurar_tabla(conexion)

        with conexion:
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


def consultar_historial(user_id: int, limite: int = 10):
    with closing(conectar()) as conexion:
        _asegurar_tabla(conexion)

        cursor = conexion.execute("""
            SELECT id, tipo, pregunta, respuesta, fecha
            FROM historial_estudio
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limite))

        return cursor.fetchall()