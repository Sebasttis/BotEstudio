import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from database import inicializar_bd
from handlers import (
    start,
    menu_button,
    handle_text,
    cancelar,
    guardar_cmd,
    apuntes_cmd,
    apunte_cmd,
    borrar_cmd,
    buscar_cmd,
)
from media_handlers import recibir_imagen, recibir_pdf, historial


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.effective_message.reply_text(
        "Soy tu asistente de estudio.\n\n"
        "/start - Abrir el menú\n"
        "/ayuda - Ver los comandos\n"
        "/cancelar - Cancelar la acción actual\n"
        "/historial - Consultar ejercicios guardados\n\n"
        "Apuntes:\n"
        "/guardar - Guardar un apunte nuevo\n"
        "/apuntes - Ver tus apuntes\n"
        "/apunte 3 - Leer el apunte #3\n"
        "/buscar palabra - Buscar en tus apuntes\n"
        "/borrar 3 - Borrar el apunte #3"
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    """Registra cualquier error no controlado en la consola."""
    logger.error(
        "Error no controlado",
        exc_info=context.error,
    )


async def post_init(app: Application):
    """Crea el menú de comandos que aparece al escribir /."""
    await app.bot.set_my_commands([
        BotCommand("start", "Abrir el menú"),
        BotCommand("guardar", "Guardar un apunte"),
        BotCommand("apuntes", "Ver mis apuntes"),
        BotCommand("buscar", "Buscar en mis apuntes"),
        BotCommand("historial", "Mi historial"),
        BotCommand("ayuda", "Ver los comandos"),
        BotCommand("cancelar", "Cancelar la acción actual"),
    ])


def main():
    if not TOKEN:
        raise RuntimeError(
            "No se encontró TELEGRAM_BOT_TOKEN. "
            "Revisa el archivo .env."
        )

    inicializar_bd()

    app = (
        Application.builder()
        .token(TOKEN)
        # Procesa varios mensajes a la vez: un PDF largo
        # ya no bloquea al resto del bot.
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    # Comandos principales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(CommandHandler("historial", historial))

    # Comandos de apuntes
    app.add_handler(CommandHandler("guardar", guardar_cmd))
    app.add_handler(CommandHandler("apuntes", apuntes_cmd))
    app.add_handler(CommandHandler("apunte", apunte_cmd))
    app.add_handler(CommandHandler("borrar", borrar_cmd))
    app.add_handler(CommandHandler("buscar", buscar_cmd))

    # Botones del menú
    app.add_handler(
        CallbackQueryHandler(menu_button)
    )

    # Recepción de fotografías
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            recibir_imagen
        )
    )

    # Recepción de documentos PDF
    app.add_handler(
        MessageHandler(
            filters.Document.PDF,
            recibir_pdf
        )
    )

    # Mensajes de texto normales
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    app.add_error_handler(error_handler)

    print("Asistente de estudio iniciado.")
    print("Abre Telegram y envía /start a tu bot.")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()