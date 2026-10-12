
import os
import base64
import re
import asyncio
from io import BytesIO

from dotenv import load_dotenv
from groq import AsyncGroq
from pypdf import PdfReader

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

MODELO_TEXTO = os.getenv(
    "GROQ_TEXT_MODEL",
    "openai/gpt-oss-120b"
)

MODELO_VISION = os.getenv(
    "GROQ_VISION_MODEL",
    "qwen/qwen3.8-27b"
)

if not API_KEY:
    raise ValueError(
        "Falta GROQ_API_KEY en el archivo .env"
    )

cliente = AsyncGroq(api_key=API_KEY)


# Instrucciones para que la IA genere respuestas
# fáciles de leer en Telegram.
INSTRUCCIONES = """
Eres un tutor académico en español para un estudiante
universitario principiante.

Explica con paciencia, claridad y paso a paso.

Cuando resuelvas ejercicios:
1. Identifica qué pide el enunciado.
2. Explica la regla que debes aplicar.
3. Desarrolla el procedimiento paso a paso.
4. Explica por qué se realiza cada operación.
5. Comprueba el resultado cuando sea posible.

FORMATO OBLIGATORIO:
- Utiliza texto sencillo y compatible con Telegram.
- No utilices fórmulas en formato LaTeX.
- No escribas fórmulas entre $$, \\( \\) o \\[ \\].
- No uses comandos como \\lim, \\frac o \\cdot.
- Escribe las operaciones matemáticas en texto legible.
- Utiliza símbolos Unicode cuando sea posible:
  −, ×, ÷, →, ², ³, ≤, ≥.
- Organiza las respuestas con títulos cortos.
- Numera los pasos del procedimiento.
- Deja espacios entre las secciones.
- Usa listas cuando ayuden a comprender.
- No uses tablas complejas.
- Termina los ejercicios con:
  RESPUESTA FINAL: resultado
- No escribas etiquetas Markdown innecesarias.
- No inventes información si la imagen no se entiende.
- Si falta información, indícalo claramente.

Ejemplo del formato esperado:

EJERCICIO: límite de una función.

1. Regla que se aplica
Explica la propiedad que permite resolverlo.

2. Sustitución
Escribe la expresión reemplazando la variable.

3. Procedimiento
Desarrolla las operaciones en orden.

4. Respuesta final
Indica el resultado y compruébalo cuando sea posible.
"""


def limpiar_respuesta(texto: str) -> str:
    """
    Elimina formatos que pueden verse mal en Telegram
    y convierte algunos comandos matemáticos comunes.
    """

    # Quitar delimitadores matemáticos.
    texto = re.sub(r"\$\$(.*?)\$\$", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"\\\[(.*?)\\\]", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"\\\((.*?)\\\)", r"\1", texto, flags=re.DOTALL)

    # Convertir fracciones sencillas: \frac{a}{b} -> a/b
    # Repite para permitir fracciones sencillas anidadas.
    patron_fraccion = re.compile(
        r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}"
    )

    for _ in range(5):
        texto_nuevo = patron_fraccion.sub(r"(\1)/(\2)", texto)
        if texto_nuevo == texto:
            break
        texto = texto_nuevo

    # Comandos matemáticos frecuentes.
    reemplazos = {
        r"\lim": "límite",
        r"\to": "→",
        r"\rightarrow": "→",
        r"\cdot": "·",
        r"\times": "×",
        r"\div": "÷",
        r"\pm": "±",
        r"\infty": "∞",
        r"\leq": "≤",
        r"\le": "≤",
        r"\geq": "≥",
        r"\ge": "≥",
        r"\neq": "≠",
        r"\pi": "π",
        r"\sqrt": "√",
        r"\approx": "≈",
        r"\%": "%",
        r"\,": " ",
        r"\;": " ",
        r"\quad": " ",
        r"\left": "",
        r"\right": "",
        r"\displaystyle": "",
    }

    for original, nuevo in reemplazos.items():
        texto = texto.replace(original, nuevo)

    # Convertir potencias comunes: x^{2} -> x².
    potencias = {
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
    }

    def convertir_potencia(coincidencia):
        exponente = coincidencia.group(1)

        if exponente in potencias:
            return potencias[exponente]

        return "^(" + exponente + ")"

    texto = re.sub(
        r"\^\{([^{}]+)\}",
        convertir_potencia,
        texto,
    )

    # Quitar llaves sobrantes de expresiones sencillas.
    texto = texto.replace("{", "").replace("}", "")

    # Eliminar negritas Markdown para que no se vean **.
    texto = texto.replace("**", "")
    texto = texto.replace("__", "")

    # Eliminar encabezados Markdown como ### Título.
    texto = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", texto)

    # Eliminar bloques de código Markdown.
    texto = texto.replace("```", "")
    texto = texto.replace("`", "")

    # Reducir líneas vacías excesivas.
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    
    # Eliminar signos de dólar usados como delimitadores matemáticos.
    texto = texto.replace("$", "")


    return texto.strip()


async def preguntar(texto: str) -> str:
    """Responde preguntas escritas por el estudiante."""

    respuesta = await cliente.chat.completions.create(
        model=MODELO_TEXTO,
        messages=[
            {
                "role": "system",
                "content": INSTRUCCIONES,
            },
            {
                "role": "user",
                "content": texto,
            },
        ],
        temperature=0.3,
        max_completion_tokens=2000,
    )

    contenido = (
        respuesta.choices[0].message.content
        or "No pude generar una respuesta."
    )

    return limpiar_respuesta(contenido)


async def analizar_imagen(
    datos: bytes,
    mime_type: str,
    pregunta: str = "Resuelve y explica el ejercicio paso a paso."
) -> str:
    """Envía una imagen al modelo compatible con visión."""

    imagen_base64 = base64.b64encode(datos).decode("utf-8")

    respuesta = await cliente.chat.completions.create(
        model=MODELO_VISION,
        messages=[
            {
                "role": "system",
                "content": INSTRUCCIONES,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": pregunta,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{mime_type};base64,"
                                f"{imagen_base64}"
                            )
                        },
                    },
                ],
            },
        ],
        temperature=0.2,
        max_completion_tokens=2500,
    )

    contenido = (
        respuesta.choices[0].message.content
        or "No pude interpretar la imagen."
    )

    return limpiar_respuesta(contenido)


async def analizar_pdf(
    datos: bytes,
    nombre: str,
    pregunta: str = "Resume y explica el documento paso a paso."
) -> str:
    """Analiza un PDF por fragmentos para reducir el consumo de tokens."""

    try:
        lector = PdfReader(BytesIO(datos))

        if lector.is_encrypted:
            return (
                "El PDF está protegido. "
                "Envíame una versión sin contraseña."
            )

        paginas = []

        for numero, pagina in enumerate(lector.pages, start=1):
            texto = pagina.extract_text() or ""

            if texto.strip():
                paginas.append(
                    f"Página {numero}:\n{texto.strip()}"
                )

        contenido = "\n\n".join(paginas)

        if not contenido.strip():
            return (
                "No pude extraer texto de este PDF. "
                "Puede ser un documento escaneado. "
                "Necesitamos OCR para reconocer su contenido."
            )

        # Dividir el texto en fragmentos pequeños.
        tamano_fragmento = 3000
        fragmentos = [
            contenido[i:i + tamano_fragmento]
            for i in range(0, len(contenido), tamano_fragmento)
        ]

        # Evitar consumir demasiados tokens en un documento enorme.
        max_fragmentos = 15
        total_original = len(fragmentos)
        fragmentos = fragmentos[:max_fragmentos]

        resultados = []

        for indice, fragmento in enumerate(fragmentos, start=1):
            # Esperar entre solicitudes para reducir la presión
            # sobre el límite de tokens por minuto.
            if indice > 1:
                await asyncio.sleep(20)

            print(
                f"Analizando fragmento {indice} "
                f"de {len(fragmentos)} del PDF: {nombre}"
            )

            respuesta = await cliente.chat.completions.create(
                model=MODELO_TEXTO,
                messages=[
                    {
                        "role": "system",
                        "content": INSTRUCCIONES,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Documento: {nombre}\n"
                            f"Fragmento: {indice} de "
                            f"{len(fragmentos)}\n\n"
                            f"Solicitud del estudiante: {pregunta}\n\n"
                            "Analiza solamente el contenido de este "
                            "fragmento. Explica los conceptos importantes "
                            "y resuelve los ejercicios que aparezcan, "
                            "paso a paso. Sé claro y conciso. "
                            "No inventes contenido que no esté presente.\n\n"
                            f"CONTENIDO:\n{fragmento}"
                        ),
                    },
                ],
                temperature=0.3,
                max_completion_tokens=500,
            )

            resultado = (
                respuesta.choices[0].message.content
                or "No se obtuvo respuesta para este fragmento."
            )

            resultados.append(
                f"PARTE {indice}\n\n"
                f"{limpiar_respuesta(resultado)}"
            )

        respuesta_final = (
            f"📄 ANÁLISIS DEL DOCUMENTO: {nombre}\n\n"
            + "\n\n--------------------\n\n".join(resultados)
        )

        if total_original > max_fragmentos:
            respuesta_final += (
                "\n\n⚠️ El documento es muy extenso. "
                f"Se analizaron {max_fragmentos} de "
                f"{total_original} fragmentos. "
                "Envía el resto del documento por partes "
                "para completar el análisis."
            )

        return respuesta_final

    except Exception as error:
        print(f"Error analizando PDF: {error}")

        return (
            "⚠️ No pude completar el análisis del PDF.\n\n"
            "Puede deberse al límite temporal de Groq, "
            "a un problema de conexión o a un documento inválido. "
            "Espera un momento y vuelve a intentarlo."
        )

