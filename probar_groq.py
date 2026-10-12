
import asyncio
from ai_service import preguntar


async def main():
    pregunta = (
        "Explícame paso a paso cómo resolver "
        "el límite de (x² - 4)/(x - 2) "
        "cuando x tiende a 2."
    )

    respuesta = await preguntar(pregunta)
    print(respuesta)


if __name__ == "__main__":
    asyncio.run(main())
