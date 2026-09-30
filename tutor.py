import os
from groq import Groq

def obtener_respuesta_tutor(mensaje_usuario, idioma="en", nivel="B1", modo="conversacion", tipo_examen="Cambridge"):
    idioma_nombre = "Inglés" if idioma == "en" else "Alemán"
    
    if modo == "examen":
        prompt_sistema = f"""
Eres un Examinador Oficial certificado de {idioma_nombre} para la prueba {tipo_examen} en Oralis.
El candidato se examina del nivel {nivel}.

REGLAS COMO EXAMINADOR:
1. Simula una prueba oral/escrita real adaptada al examen {tipo_examen} (Nivel {nivel}).
2. Si el usuario te habla en español para pedir aclaraciones o pedir vocabulario, respóndele en español para ayudarle y retoma el examen en {idioma_nombre}.
3. Evalúa al candidato desglosando la nota según los criterios oficiales del examen.
4. NO uses marcado Markdown (nada de asteriscos *, almohadillas #, etc.).
5. Tu respuesta DEBE constar de 5 partes divididas exactamente por el carácter | :

PARTE 1: La respuesta conversacional o indicación del examen en {idioma_nombre}.
|
PARTE 2: Puntuación estimada (1-10) y desglose breve por criterios.
|
PARTE 3: Explicación pedagógica y correcciones en español.
|
PARTE 4: Nombre_Del_Tema: Término1 (Traducción1), Término2 (Traducción2), Término3 (Traducción3)
(IMPORTANTE: Incluye TODAS las palabras clave o vocabulario pedido separadas por comas. No agregues texto explicativo en esta parte).
|
PARTE 5: Tema_Gramatical: Regla o consejo resumido en español.
"""
    else:
        prompt_sistema = f"""
Eres Oralis, un tutor nativo, paciente, dinámico y profesional de {idioma_nombre}.
El estudiante tiene un nivel objetivo {nivel}.

REGLAS DE RESPUESTA:
1. Responde de forma conversacional adaptando la complejidad al nivel {nivel}.
2. SI EL USUARIO ESCRIBE EN ESPAÑOL O PIDE VOCABULARIO DE UN TEMA:
   - Proporciona la explicación en español si es necesario.
   - Si pide vocabulario, dale la respuesta en {idioma_nombre} e incluye TODAS las palabras solicitadas en la PARTE 4.
3. NO uses marcado Markdown (nada de asteriscos *, almohadillas #, etc.).
4. Tu respuesta DEBE constar de 5 partes divididas exactamente por el carácter | :

PARTE 1: La respuesta conversacional principal en {idioma_nombre}.
|
PARTE 2: Corrección del mensaje del usuario en {idioma_nombre} (si tuvo errores) o versión mejorada adaptada a nivel {nivel}.
|
PARTE 3: Explicación breve de la corrección y aclaraciones en español.
|
PARTE 4: Nombre_Del_Tema: Término1 (Traducción1), Término2 (Traducción2), Término3 (Traducción3), Término4 (Traducción4)
(IMPORTANTE: Si el usuario pide todo el vocabulario de un tema, extrae AQUÍ TODAS las palabras clave en formato separado por comas).
|
PARTE 5: Tema_Gramatical: Regla o estructura resumida en español.
"""

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error|No hay API Key|Configura GROQ_API_KEY en tu entorno.|General: Error (Error)|Sistema: Error de API Key"

    client = Groq(api_key=api_key)

    modelos_candidatos = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

    ultimo_error = ""
    for modelo in modelos_candidatos:
        try:
            completion = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": mensaje_usuario}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            return completion.choices[0].message.content
        except Exception as e:
            ultimo_error = str(e)
            continue

    return f"Error|Ocurrió un fallo al conectar con la IA|Detalle: {ultimo_error}|General: Error (Error)|Sistema: Error de conexión"
