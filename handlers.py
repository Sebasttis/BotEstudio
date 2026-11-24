import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from database import (
    guardar_apunte,
    obtener_apuntes,
    obtener_apunte,
    borrar_apunte,
    buscar_apuntes,
)

from ai_service import preguntar
from study_history import guardar_interaccion

logger = logging.getLogger(__name__)

LIMITE_TELEGRAM = 4000

MODOS_GUARDAR = {
    "guardar_materia",
    "guardar_titulo",
    "guardar_contenido",
}


# ==========================================
# UTILIDADES
# ==========================================

def limpiar_estado(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("modo", None)
    context.user_data.pop("nuevo_apunte", None)


async def editar(consulta, texto, markup=None):
    """Edita el mensaje del botón sin fallar si no cambió."""
    try:
        await consulta.edit_message_text(
            texto[:LIMITE_TELEGRAM],
            reply_markup=markup,
        )
    except BadRequest as error:
        if "not modified" not in str(error).lower():
            raise


def id_desde_callback(opcion: str):
    try:
        return int(opcion.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


# ==========================================
# TECLADOS
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


def teclado_apuntes(apuntes):
    filas = [
        [
            InlineKeyboardButton(
                f"📖 #{a['id']} {a['titulo'][:30]}",
                callback_data=f"ver:{a['id']}",
            )
        ]
        for a in apuntes
    ]

    filas.append([
        InlineKeyboardButton(
            "📝 Nuevo apunte",
            callback_data="guardar",
        ),
        InlineKeyboardButton(
            "🏠 Menú",
            callback_data="inicio",
        ),
    ])

    return InlineKeyboardMarkup(filas)


# ==========================================
# VISTAS DE APUNTES
# ==========================================

def vista_lista_apuntes(usuario_id):
    apuntes = obtener_apuntes(usuario_id)

    if not apuntes:
        return (
            "📚 MIS APUNTES\n\n"
            "Todavía no tienes apuntes guardados.\n\n"
            "Pulsa «Guardar apunte» o usa /guardar para comenzar.",
            teclado_principal(),
        )

    lineas = ["📚 TUS APUNTES (los 10 más recientes)\n"]

    for apunte in apuntes:
        lineas.append(
            f"#{apunte['id']} — {apunte['materia']}\n"
            f"📌 {apunte['titulo']}\n"
        )

    lineas.append(
        "Toca un apunte para leerlo completo o borrarlo.\n"
        "También puedes usar /buscar palabra."
    )

    return "\n".join(lineas), teclado_apuntes(apuntes)


def vista_apunte(apunte):
    texto = (
        f"📖 APUNTE #{apunte['id']}\n\n"
        f"📚 Materia: {apunte['materia']}\n"
        f"📌 Título: {apunte['titulo']}\n"
        f"🗓 Guardado: {str(apunte['fecha'])[:16]}\n\n"
        f"{apunte['contenido']}"
    )

    teclado = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🗑 Borrar",
                callback_data=f"borrar:{apunte['id']}",
            ),
        ],
        [
            InlineKeyboardButton(
                "📚 Mis apuntes",
                callback_data="apuntes",
            ),
            InlineKeyboardButton(
                "🏠 Menú",
                callback_data="inicio",
            ),
        ],
    ])

    return texto[:LIMITE_TELEGRAM], teclado


# ==========================================
# GUARDAR APUNTES (flujo guiado)
# ==========================================

TEXTO_GUARDAR = (
    "📝 NUEVO APUNTE\n\n"
    "Paso 1 de 3: ¿De qué materia es?\n\n"
    "Ejemplo: Lógica\n\n"
    "💡 También puedes enviarlo todo junto:\n"
    "Materia | Título | Contenido\n\n"
    "Usa /cancelar para salir."
)


def iniciar_guardado(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["modo"] = "guardar_materia"
    context.user_data["nuevo_apunte"] = {}


async def finalizar_guardado(
    mensaje,
    context,
    usuario_id,
    materia,
    titulo,
    contenido,
):
    try:
        apunte_id = guardar_apunte(
            usuario_id,
            materia,
            titulo,
            contenido,
        )
    except Exception:
        logger.exception("Error guardando apunte")

        await mensaje.reply_text(
            "⚠️ No pude guardar el apunte. "
            "Inténtalo de nuevo con /guardar.",
            reply_markup=teclado_principal(),
        )
        return

    limpiar_estado(context)

    await mensaje.reply_text(
        f"✅ APUNTE GUARDADO (#{apunte_id})\n\n"
        f"📚 Materia: {materia}\n"
        f"📌 Título: {titulo}\n\n"
        "Lo usaré como contexto cuando tu pregunta se "
        "relacione con él.",
        reply_markup=teclado_principal(),
    )


async def procesar_guardado(
    mensaje,
    context,
    usuario_id,
    modo,
    texto,
):
    datos = context.user_data.setdefault("nuevo_apunte", {})

    if modo == "guardar_materia":
        # Formato rápido: Materia | Título | Contenido
        partes = [p.strip() for p in texto.split("|", 2)]

        if len(partes) == 3:
            if not all(partes):
                await mensaje.reply_text(
                    "⚠️ Los tres campos deben tener texto.\n\n"
                    "Materia | Título | Contenido"
                )
                return

            await finalizar_guardado(
                mensaje, context, usuario_id, *partes
            )
            return

        datos["materia"] = texto[:100]
        context.user_data["modo"] = "guardar_titulo"

        await mensaje.reply_text(
            f"✅ Materia: {datos['materia']}\n\n"
            "Paso 2 de 3: ¿Cuál es el título del apunte?"
        )

    elif modo == "guardar_titulo":
        datos["titulo"] = texto[:150]
        context.user_data["modo"] = "guardar_contenido"

        await mensaje.reply_text(
            f"✅ Título: {datos['titulo']}\n\n"
            "Paso 3 de 3: escribe el contenido del apunte."
        )

    else:
        await finalizar_guardado(
            mensaje,
            context,
            usuario_id,
            datos.get("materia", "General"),
            datos.get("titulo", "Sin título"),
            texto,
        )


# ==========================================
# INICIO
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    limpiar_estado(context)

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
# COMANDOS DE APUNTES
# ==========================================

async def guardar_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    iniciar_guardado(context)
    await update.effective_message.reply_text(TEXTO_GUARDAR)


async def apuntes_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    texto, markup = vista_lista_apuntes(update.effective_user.id)

    await update.effective_message.reply_text(
        texto,
        reply_markup=markup,
    )


async def apunte_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message

    if not context.args or not context.args[0].isdigit():
        await mensaje.reply_text("Uso: /apunte 3")
        return

    apunte = obtener_apunte(
        update.effective_user.id,
        int(context.args[0]),
    )

    if not apunte:
        await mensaje.reply_text("No encontré ese apunte.")
        return

    texto, markup = vista_apunte(apunte)
    await mensaje.reply_text(texto, reply_markup=markup)


async def borrar_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message

    if not context.args or not context.args[0].isdigit():
        await mensaje.reply_text("Uso: /borrar 3")
        return

    borrado = borrar_apunte(
        update.effective_user.id,
        int(context.args[0]),
    )

    await mensaje.reply_text(
        "🗑 Apunte borrado." if borrado
        else "No encontré ese apunte."
    )


async def buscar_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    mensaje = update.effective_message
    consulta = " ".join(context.args).strip()

    if not consulta:
        await mensaje.reply_text("Uso: /buscar proposiciones")
        return

    resultados = buscar_apuntes(
        update.effective_user.id,
        consulta,
        limite=8,
        min_letras=3,
    )

    if not resultados:
        await mensaje.reply_text(
            "No encontré apuntes con esas palabras."
        )
        return

    await mensaje.reply_text(
        f"🔎 Resultados para «{consulta}»:",
        reply_markup=teclado_apuntes(resultados),
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
    usuario_id = consulta.from_user.id

    # ---------- Acciones sobre un apunte concreto ----------

    if opcion.startswith("ver:"):
        apunte_id = id_desde_callback(opcion)
        apunte = (
            obtener_apunte(usuario_id, apunte_id)
            if apunte_id is not None else None
        )

        if not apunte:
            await editar(
                consulta,
                "⚠️ Ese apunte ya no existe.",
                teclado_principal(),
            )
            return

        texto, markup = vista_apunte(apunte)
        await editar(consulta, texto, markup)
        return

    if opcion.startswith("borrar:"):
        apunte_id = id_desde_callback(opcion)

        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "✅ Sí, borrar",
                callback_data=f"borrar_si:{apunte_id}",
            ),
            InlineKeyboardButton(
                "↩️ Cancelar",
                callback_data=f"ver:{apunte_id}",
            ),
        ]])

        await editar(
            consulta,
            f"¿Seguro que quieres borrar el apunte "
            f"#{apunte_id}?\n\nNo se puede deshacer.",
            markup,
        )
        return

    if opcion.startswith("borrar_si:"):
        apunte_id = id_desde_callback(opcion)

        borrado = (
            borrar_apunte(usuario_id, apunte_id)
            if apunte_id is not None else False
        )

        texto, markup = vista_lista_apuntes(usuario_id)
        aviso = (
            "🗑 Apunte borrado.\n\n" if borrado
            else "⚠️ Ese apunte ya no existía.\n\n"
        )

        await editar(consulta, aviso + texto, markup)
        return

    # ---------- Menú ----------

    if opcion == "preguntar":
        limpiar_estado(context)
        context.user_data["modo"] = "preguntar"

        await editar(
            consulta,
            "💬 HACER UNA PREGUNTA\n\n"
            "Escribe tu pregunta y te responderé "
            "con una explicación clara y paso a paso.\n\n"
            "Puedes preguntar sobre matemáticas, lógica, "
            "programación y otros temas de estudio.\n\n"
            "✍️ Escribe tu pregunta en el chat.\n\n"
            "Usa /cancelar para cancelar.",
        )

    elif opcion == "imagen":
        limpiar_estado(context)

        await editar(
            consulta,
            "📷 RESOLVER CON FOTO\n\n"
            "1. Toma una foto del ejercicio o selecciónala "
            "desde tu galería.\n\n"
            "2. Adjunta la imagen en este chat.\n\n"
            "3. Si quieres, escribe una instrucción, por ejemplo:\n"
            "«Resuelve paso a paso y explica cada operación».\n\n"
            "💡 Procura que la foto tenga buena iluminación "
            "y que el enunciado se vea completo.\n\n"
            "Cuando envíes la imagen, comenzaré a analizarla.",
            teclado_principal(),
        )

    elif opcion == "pdf":
        limpiar_estado(context)

        await editar(
            consulta,
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
            teclado_principal(),
        )

    elif opcion == "guardar":
        iniciar_guardado(context)
        await editar(consulta, TEXTO_GUARDAR)

    elif opcion == "apuntes":
        limpiar_estado(context)
        texto, markup = vista_lista_apuntes(usuario_id)
        await editar(consulta, texto, markup)

    elif opcion == "historial":
        limpiar_estado(context)

        await editar(
            consulta,
            "🕘 MI HISTORIAL\n\n"
            "Pulsa el comando /historial para consultar "
            "tus ejercicios y respuestas guardadas.\n\n"
            "Si todavía no has analizado ejercicios, "
            "haz una pregunta o envía una foto o un PDF.",
            teclado_principal(),
        )

    elif opcion == "ayuda":
        limpiar_estado(context)

        await editar(
            consulta,
            "❓ AYUDA DEL TUTOR\n\n"
            "💬 Preguntar: escribe tu duda para la IA.\n"
            "📷 Foto: envía una imagen de un ejercicio.\n"
            "📄 PDF: adjunta un documento PDF.\n\n"
            "📝 APUNTES\n"
            "/guardar — Guardar un apunte nuevo.\n"
            "/apuntes — Ver tus apuntes.\n"
            "/apunte 3 — Leer el apunte #3.\n"
            "/buscar palabra — Buscar en tus apuntes.\n"
            "/borrar 3 — Borrar el apunte #3.\n\n"
            "🕘 /historial — Tus consultas anteriores.\n"
            "/start — Abrir el menú.\n"
            "/cancelar — Cancelar una acción.",
            teclado_principal(),
        )

    elif opcion == "inicio":
        limpiar_estado(context)

        await editar(
            consulta,
            "🏠 MENÚ PRINCIPAL\n\n"
            "¿Qué quieres estudiar hoy?",
            teclado_principal(),
        )


# ==========================================
# CANCELAR
# ==========================================

async def cancelar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    limpiar_estado(context)

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

    if not mensaje or not mensaje.text or not update.effective_user:
        return

    usuario_id = update.effective_user.id
    texto = mensaje.text.strip()

    modo = context.user_data.get("modo")

    # Guardando un apunte (flujo guiado)
    if modo in MODOS_GUARDAR:
        await procesar_guardado(
            mensaje, context, usuario_id, modo, texto
        )
        return

    # Consultar a la IA
    await mensaje.reply_text(
        "🤔 Estoy preparando tu respuesta. Un momento..."
    )
    await mensaje.chat.send_action(ChatAction.TYPING)

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
                for apunte in apuntes
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

        # Guardar en el historial (un fallo aquí no debe
        # impedir que el estudiante reciba su respuesta).
        try:
            guardar_interaccion(
                user_id=usuario_id,
                tipo="texto",
                pregunta=texto,
                respuesta=respuesta,
            )
        except Exception:
            logger.exception("Error guardando historial")

        if apuntes:
            usados = ", ".join(
                f"#{a['id']} {a['titulo']}" for a in apuntes
            )
            respuesta += f"\n\n📎 Apuntes usados: {usados}"

        context.user_data.pop("modo", None)

        # Telegram limita cada mensaje de texto.
        partes_respuesta = [
            respuesta[i:i + LIMITE_TELEGRAM]
            for i in range(0, len(respuesta), LIMITE_TELEGRAM)
        ]

        for indice, parte in enumerate(partes_respuesta):
            es_ultimo = indice == len(partes_respuesta) - 1

            await mensaje.reply_text(
                parte,
                reply_markup=(
                    teclado_principal() if es_ultimo else None
                ),
            )

    except Exception:
        logger.exception("Error al responder con IA")

        await mensaje.reply_text(
            "⚠️ No pude generar tu respuesta en este momento.\n\n"
            "Comprueba la conexión y la configuración de la IA "
            "e inténtalo nuevamente.",
            reply_markup=teclado_principal(),
        )