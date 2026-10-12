
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from database import inicializar_bd
from handlers import start, menu_button, handle_text, cancelar
from media_handlers import recibir_imagen, recibir_pdf, historial


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)


async def ayuda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.effective_message.reply_text(
        "Soy tu asistente de estudio.\n\n"
        "/start - Abrir el menú\n"
        "/ayuda - Ver los comandos\n"
        "/cancelar - Cancelar la acción actual\n"
        "/historial - Consultar ejercicios guardados"
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "No se encontró TELEGRAM_BOT_TOKEN. "
            "Revisa el archivo .env."
        )

    inicializar_bd()

    app = Application.builder().token(TOKEN).build()

    # Comandos principales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(CommandHandler("historial", historial))

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

    print("Asistente de estudio iniciado.")
    print("Abre Telegram y envía /start a tu bot.")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
