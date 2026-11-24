import re
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "estudio.db"

# Palabras muy comunes que no sirven para buscar apuntes.
PALABRAS_COMUNES = {
    "como", "cual", "cuales", "donde", "cuando", "para", "sobre",
    "paso", "pasos", "explica", "explicame", "resuelve", "resolver",
    "ejercicio", "ejercicios", "quiero", "puedes", "favor", "esto",
    "esta", "este", "estos", "entre", "desde", "hasta", "tengo",
    "hacer", "dime", "ayuda", "ayudame",
}


def conectar():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row

    return conexion


def inicializar_bd():
    with closing(conectar()) as conexion:
        with conexion:
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
            conexion.execute("""
                CREATE INDEX IF NOT EXISTS idx_apuntes_usuario
                ON apuntes (usuario_id)
            """)


def _normalizar(texto):
    """Minúsculas y sin tildes: 'Lógica' -> 'logica'."""
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(
        c for c in texto if unicodedata.category(c) != "Mn"
    )


def guardar_apunte(usuario_id, materia, titulo, contenido):
    """Guarda un apunte y devuelve su id."""
    with closing(conectar()) as conexion:
        with conexion:
            cursor = conexion.execute("""
                INSERT INTO apuntes
                    (usuario_id, materia, titulo, contenido)
                VALUES (?, ?, ?, ?)
            """, (usuario_id, materia, titulo, contenido))

            return cursor.lastrowid


def obtener_apuntes(usuario_id, limite=10):
    with closing(conectar()) as conexion:
        cursor = conexion.execute("""
            SELECT id, materia, titulo, contenido, fecha
            FROM apuntes
            WHERE usuario_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (usuario_id, limite))

        return cursor.fetchall()


def obtener_apunte(usuario_id, apunte_id):
    """Devuelve un apunte del usuario o None."""
    with closing(conectar()) as conexion:
        cursor = conexion.execute("""
            SELECT id, materia, titulo, contenido, fecha
            FROM apuntes
            WHERE id = ? AND usuario_id = ?
        """, (apunte_id, usuario_id))

        return cursor.fetchone()


def borrar_apunte(usuario_id, apunte_id):
    """Borra un apunte. Devuelve True si existía."""
    with closing(conectar()) as conexion:
        with conexion:
            cursor = conexion.execute("""
                DELETE FROM apuntes
                WHERE id = ? AND usuario_id = ?
            """, (apunte_id, usuario_id))

            return cursor.rowcount > 0


def buscar_apuntes(usuario_id, pregunta, limite=3, min_letras=4):
    """Busca apuntes relacionados con un texto (ignora tildes)."""
    palabras = {
        palabra
        for palabra in re.findall(r"\w+", _normalizar(pregunta))
        if len(palabra) >= min_letras
        and palabra not in PALABRAS_COMUNES
    }

    if not palabras:
        return []

    resultados = []

    with closing(conectar()) as conexion:
        cursor = conexion.execute("""
            SELECT id, materia, titulo, contenido, fecha
            FROM apuntes
            WHERE usuario_id = ?
            ORDER BY id DESC
            LIMIT 200
        """, (usuario_id,))

        for apunte in cursor.fetchall():
            texto = _normalizar(
                f"{apunte['materia']} {apunte['titulo']} "
                f"{apunte['contenido']}"
            )

            coincidencias = sum(
                1 for palabra in palabras if palabra in texto
            )

            if coincidencias:
                resultados.append((coincidencias, apunte))

    # Más coincidencias primero; a igualdad, el más reciente.
    resultados.sort(key=lambda r: r[0], reverse=True)

    return [apunte for _, apunte in resultados[:limite]]