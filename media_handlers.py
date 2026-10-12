
import logging

from telegram import Update
from telegram.ext import ContextTypes
from study_history import consultar_historial
from ai_service import analizar_imagen, analizar_pdf
from study_history import guardar_interaccion

logger = logging.getLogger(__name__)

MAX_ARCHIVO = 10 * 1024 * 1024  # 10 MB


async def recibir_imagen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    mensaje = update.effective_message

    if not mensaje or not mensaje.photo:
        return

    foto = mensaje.photo[-1]

    if foto.file_size and foto.file_size > MAX_ARCHIVO:
        await mensaje.reply_text(
            "La imagen supera los 10 MB. "
            "Envíame una imagen más pequeña."
        )
        return

    await mensaje.reply_text(
        "Estoy leyendo la imagen y analizando el ejercicio..."
    )

    try:
        archivo = await context.bot.get_file(foto.file_id)
        datos = bytes(await archivo.download_as_bytearray())

        pregunta = mensaje.caption or (
            "Lee el ejercicio de la imagen y resuélvelo "
            "paso a paso. Explica las operaciones."
        )

        respuesta = await analizar_imagen(
            datos,
            "image/jpeg",
            pregunta
        )

        guardar_interaccion(
            user_id=update.effective_user.id,
            tipo="imagen",
            pregunta=pregunta,
            respuesta=respuesta
        )

        # Telegram admite como máximo 4096 caracteres por mensaje.
        for inicio in range(0, len(respuesta), 4000):
            await mensaje.reply_text(
                respuesta[inicio:inicio + 4000]
            )

    except Exception:
        logger.exception("Error procesando imagen")
        await mensaje.reply_text(
            "No pude analizar la imagen. "
            "Comprueba que sea legible y que el modelo "
            "de visión esté habilitado en Groq."
        )


async def recibir_pdf(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    mensaje = update.effective_message
    documento = mensaje.document if mensaje else None

    if not documento:
        return

    if documento.file_size and documento.file_size > MAX_ARCHIVO:
        await mensaje.reply_text(
            "El PDF supera los 10 MB. "
            "Envíame una versión más pequeña."
        )
        return

    nombre = documento.file_name or "documento.pdf"

    await mensaje.reply_text(
        "Estoy leyendo el PDF. Esto puede tardar un momento..."
    )

    try:
        archivo = await context.bot.get_file(documento.file_id)
        datos = bytes(await archivo.download_as_bytearray())

        pregunta = mensaje.caption or (
            "Explica el contenido del PDF de forma sencilla. "
            "Identifica los conceptos importantes y, si hay "
            "ejercicios, explica cómo resolverlos."
        )

        respuesta = await analizar_pdf(
            datos,
            nombre,
            pregunta
        )

        guardar_interaccion(
            user_id=update.effective_user.id,
            tipo="pdf",
            pregunta=f"{nombre}: {pregunta}",
            respuesta=respuesta
        )

        for inicio in range(0, len(respuesta), 4000):
            await mensaje.reply_text(
                respuesta[inicio:inicio + 4000]
            )

    except Exception:
        logger.exception("Error procesando PDF")
        await mensaje.reply_text(
            "No pude leer el PDF. Comprueba que no esté "
            "protegido y que tenga texto seleccionable. "
            "Los documentos escaneados requieren OCR."
        )

        


async def historial(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    usuario = update.effective_user.id
    registros = consultar_historial(usuario, 10)

    if not registros:
        await update.effective_message.reply_text(
            "Todavía no tienes ejercicios guardados."
        )
        return

    for registro in registros:
        id_registro, tipo, pregunta, respuesta, fecha = registro

        texto = (
            f"Registro #{id_registro} | {tipo}\n"
            f"Fecha: {fecha}\n"
            f"Pregunta: {pregunta}\n\n"
            f"Respuesta:\n{respuesta}"
        )

        # Evita superar el límite de Telegram.
        for inicio in range(0, len(texto), 4000):
            await update.effective_message.reply_text(
                texto[inicio:inicio + 4000]
            )
