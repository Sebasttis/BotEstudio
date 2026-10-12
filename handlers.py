
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from database import (
    guardar_apunte,
    obtener_apuntes,
    buscar_apuntes,
)

from ai_service import preguntar


# ==========================================
# MENU PRINCIPAL
# ==========================================

def teclado_principal():
    botones = [
        [
            InlineKeyboardButton(
                "💬 Hacer una pregunta",
                callback_data="preguntar",
            ),
        ],
        [
            InlineKeyboardButton(
                "📷 Resolver con foto",
                callback_data="imagen",
            ),
            InlineKeyboardButton(
                "📄 Analizar PDF",
                callback_data="pdf",
            ),
        ],
        [
            InlineKeyboardButton(
                "📝 Guardar apunte",
                callback_data="guardar",
            ),
            InlineKeyboardButton(
                "📚 Mis apuntes",
                callback_data="apuntes",
            ),
        ],
        [
            InlineKeyboardButton(
                "🕘 Mi historial",
                callback_data="historial",
            ),
            InlineKeyboardButton(
                "❓ Ayuda",
                callback_data="ayuda",
            ),
        ],
    ]

    return InlineKeyboardMarkup(botones)


# ==========================================
# INICIO
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop("modo", None)

    texto = (
        "¡Hola! 👋 Bienvenido a tu Tutor Académico.\n\n"
        "🎓 Estoy aquí para ayudarte a estudiar.\n\n"
        "¿Qué puedes hacer conmigo?\n\n"
        "💬 Hacer preguntas y recibir explicaciones.\n"
        "📷 Enviar una foto de un ejercicio.\n"
        "📄 Adjuntar un PDF para analizarlo.\n"
        "📝 Guardar tus apuntes de clase.\n"
        "📚 Consultar tus apuntes guardados.\n"
        "🕘 Revisar tu historial de ejercicios.\n\n"
        "Selecciona una opción del menú para comenzar."
    )

    await update.effective_message.reply_text(
        texto,
        reply_markup=teclado_principal(),
    )


# ==========================================
# BOTONES DEL MENU
# ==========================================

async def menu_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    consulta = update.callback_query
    await consulta.answer()

    opcion = consulta.data

    # Hacer preguntas con IA
    if opcion == "preguntar":
        context.user_data["modo"] = "preguntar"

        await consulta.edit_message_text(
            "💬 HACER UNA PREGUNTA\n\n"
            "Escribe tu pregunta y te responderé "
            "con una explicación clara y paso a paso.\n\n"
            "Puedes preguntar sobre matemáticas, lógica, "
            "programación y otros temas de estudio.\n\n"
            "✍️ Escribe tu pregunta en el chat.\n\n"
            "Usa /cancelar para cancelar.",
        )

    # Resolver mediante una fotografía
    elif opcion == "imagen":
        context.user_data.pop("modo", None)

        await consulta.edit_message_text(
            "📷 RESOLVER CON FOTO\n\n"
            "1. Toma una foto del ejercicio o selecciónala "
            "desde tu galería.\n\n"
            "2. Adjunta la imagen en este chat.\n\n"
            "3. Si quieres, escribe una instrucción, por ejemplo:\n"
            "«Resuelve paso a paso y explica cada operación».\n\n"
            "💡 Procura que la foto tenga buena iluminación "
            "y que el enunciado se vea completo.\n\n"
            "Cuando envíes la imagen, comenzaré a analizarla.",
            reply_markup=teclado_principal(),
        )

    # Analizar documentos PDF
    elif opcion == "pdf":
        context.user_data.pop("modo", None)

        await consulta.edit_message_text(
            "📄 ANALIZAR UN PDF\n\n"
            "1. En el chat, pulsa el icono del clip 📎.\n\n"
            "2. Selecciona «Archivo» o «Documento».\n\n"
            "3. Escoge el PDF que quieres estudiar y envíalo.\n\n"
            "4. Si deseas, escribe qué necesitas:\n"
            "• Explicar los temas.\n"
            "• Resolver los ejercicios.\n"
            "• Preparar una guía de estudio.\n"
            "• Resumir el contenido.\n\n"
            "📌 Si el PDF es un documento escaneado, "
            "puede que necesitemos reconocimiento de texto (OCR).",
            reply_markup=teclado_principal(),
        )

    # Guardar apuntes
    elif opcion == "guardar":
        context.user_data["modo"] = "guardar"

        await consulta.edit_message_text(
            "📝 GUARDAR UN APUNTE\n\n"
            "Envía la información con este formato:\n\n"
            "Materia | Título | Contenido\n\n"
            "Ejemplo:\n"
            "Lógica | Proposiciones | Una proposición "
            "es un enunciado que puede ser verdadero o falso.\n\n"
            "Separa los tres campos con el símbolo |.\n\n"
            "Usa /cancelar para salir.",
        )

    # Consultar apuntes
    elif opcion == "apuntes":
        usuario_id = consulta.from_user.id
        apuntes = obtener_apuntes(usuario_id)

        if not apuntes:
            texto = (
                "📚 MIS APUNTES\n\n"
                "Todavía no tienes apuntes guardados.\n\n"
                "Pulsa «Guardar apunte» para comenzar."
            )
        else:
            lineas = ["📚 TUS APUNTES GUARDADOS\n"]

            for apunte in apuntes:
                lineas.append(
                    f"#{apunte['id']} — {apunte['materia']}\n"
                    f"📌 {apunte['titulo']}\n"
                    f"{apunte['contenido'][:300]}\n"
                )

            texto = "\n".join(lineas)
            texto = texto[:4000]

        await consulta.edit_message_text(
            texto,
            reply_markup=teclado_principal(),
        )

    # Historial de ejercicios
    elif opcion == "historial":
        context.user_data.pop("modo", None)

        await consulta.edit_message_text(
            "🕘 MI HISTORIAL\n\n"
            "Pulsa el comando /historial para consultar "
            "tus ejercicios y respuestas guardadas.\n\n"
            "Si todavía no has analizado ejercicios, "
            "envía una foto o un PDF para comenzar.",
            reply_markup=teclado_principal(),
        )

    # Ayuda
    elif opcion == "ayuda":
        context.user_data.pop("modo", None)

        await consulta.edit_message_text(
            "❓ AYUDA DEL TUTOR\n\n"
            "💬 Preguntar: escribe tu duda para la IA.\n\n"
            "📷 Resolver con foto: selecciona esta opción "
            "y después envía una imagen.\n\n"
            "📄 Analizar PDF: selecciona esta opción y "
            "adjunta un documento PDF.\n\n"
            "📝 Guardar apunte: almacena tus notas.\n\n"
            "📚 Mis apuntes: consulta tus notas guardadas.\n\n"
            "🕘 Mi historial: consulta /historial.\n\n"
            "/start — Abrir el menú.\n"
            "/cancelar — Cancelar una acción.",
            reply_markup=teclado_principal(),
        )

    # Volver al menú
    elif opcion == "inicio":
        context.user_data.pop("modo", None)

        await consulta.edit_message_text(
            "🏠 MENÚ PRINCIPAL\n\n"
            "¿Qué quieres estudiar hoy?",
            reply_markup=teclado_principal(),
        )


# ==========================================
# CANCELAR
# ==========================================

async def cancelar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.pop("modo", None)

    await update.effective_message.reply_text(
        "Acción cancelada. Puedes elegir otra opción.",
        reply_markup=teclado_principal(),
    )


# ==========================================
# MENSAJES DE TEXTO
# ==========================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message

    if not mensaje or not mensaje.text:
        return

    usuario_id = update.effective_user.id
    texto = mensaje.text.strip()

    modo = context.user_data.get("modo")

    # Guardar un apunte
    if modo == "guardar":
        partes = texto.split("|", 2)

        if len(partes) != 3 or not all(
            parte.strip() for parte in partes
        ):
            await mensaje.reply_text(
                "⚠️ El formato es incorrecto.\n\n"
                "Usa este formato:\n"
                "Materia | Título | Contenido"
            )
            return

        materia, titulo, contenido = [
            parte.strip() for parte in partes
        ]

        guardar_apunte(
            usuario_id,
            materia,
            titulo,
            contenido,
        )

        context.user_data.pop("modo", None)

        await mensaje.reply_text(
            f"✅ APUNTE GUARDADO\n\n"
            f"📚 Materia: {materia}\n"
            f"📌 Título: {titulo}",
            reply_markup=teclado_principal(),
        )
        return

    # Consultar a la IA
    await mensaje.reply_text(
        "🤔 Estoy preparando tu respuesta. Un momento..."
    )

    try:
        apuntes = buscar_apuntes(usuario_id, texto)

        # Si existen apuntes relacionados, se incluyen
        # como contexto para que la IA los tenga en cuenta.
        if apuntes:
            contexto_apuntes = "\n\n".join(
                (
                    f"Materia: {apunte['materia']}\n"
                    f"Título: {apunte['titulo']}\n"
                    f"Contenido: {apunte['contenido'][:1500]}"
                )
                for apunte in apuntes[:3]
            )

            consulta_ia = (
                f"Pregunta del estudiante:\n{texto}\n\n"
                f"Apuntes relacionados del estudiante:\n"
                f"{contexto_apuntes}\n\n"
                "Responde la pregunta paso a paso. "
                "Utiliza los apuntes si son pertinentes, "
                "y aclara si contienen algún error."
            )
        else:
            consulta_ia = texto

        respuesta = await preguntar(consulta_ia)

        context.user_data.pop("modo", None)

        # Telegram limita cada mensaje de texto.
        partes_respuesta = [
            respuesta[i:i + 4000]
            for i in range(0, len(respuesta), 4000)
        ]

        for indice, parte in enumerate(partes_respuesta):
            es_ultimo = indice == len(partes_respuesta) - 1

            await mensaje.reply_text(
                parte,
                reply_markup=(
                    teclado_principal() if es_ultimo else None
                ),
            )

    except Exception as error:
        print(f"Error al responder con IA: {error}")

        await mensaje.reply_text(
            "⚠️ No pude generar tu respuesta en este momento.\n\n"
            "Comprueba la conexión y la configuración de la IA "
            "e inténtalo nuevamente.",
            reply_markup=teclado_principal(),
        )
