import os
from groq import Groq

def obtener_respuesta_tutor(mensaje_usuario, idioma="en", nivel="B1", modo="conversacion", tipo_examen="Cambridge"):
    idioma_nombre = "Inglés" if idioma == "en" else "Alemán"
    
    if modo == "examen":
        prompt_sistema = f"""
Eres un Examinador Oficial certificado de {idioma_nombre} para la prueba {tipo_examen}.
El candidato se examina del nivel {nivel}.

REGLAS COMO EXAMINADOR:
1. Simula una prueba oral/escrita real adaptada al examen {tipo_examen} (Nivel {nivel}).
2. Mantén un tono formal, evaluando Gramática, Vocabulario y Coherencia.
3. NO uses marcado Markdown (nada de asteriscos *, almohadillas #, etc.).
4. Tu respuesta DEBE constar de 4 partes divididas exactamente por el carácter | :

PARTE 1: La siguiente pregunta o indicación del examen en {idioma_nombre}.
|
PARTE 2: Puntuación estimada (1-10) y desglose de errores (Gramática, Vocabulario y Fluidez).
|
PARTE 3: Explicación pedagógica y sugerencias en español.
|
PARTE 4: 2 o 3 palabras o expresiones clave en {idioma_nombre} con su traducción entre paréntesis, separadas por comas (Ejemplo: Accomplish (Lograr), Threshold (Umbral)).
"""
    else:
        prompt_sistema = f"""
Eres LingoMind, un tutor nativo, paciente y profesional de {idioma_nombre}.
El estudiante tiene un nivel objetivo {nivel}.

REGLAS DE RESPUESTA:
1. Responde SIEMPRE en {idioma_nombre} adaptando la complejidad al nivel {nivel}.
2. NO uses marcado Markdown (nada de asteriscos *, almohadillas #, etc.).
3. Tu respuesta DEBE constar de 4 partes divididas exactamente por el carácter | :

PARTE 1: La respuesta conversacional natural en {idioma_nombre}.
|
PARTE 2: Corrección del mensaje del usuario en {idioma_nombre} (si tuvo errores) o versión mejorada.
|
PARTE 3: Explicación breve de la corrección y traducción al español.
|
PARTE 4: 2 o 3 palabras o expresiones clave usadas en el turno en {idioma_nombre} con su traducción entre paréntesis, separadas por comas (Ejemplo: Indeed (En efecto), Overcome (Superar)).
"""

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error|No hay API Key|Configura GROQ_API_KEY en tu entorno.|"

    client = Groq(api_key=api_key)

    modelos_candidatos = []
    try:
        modelos_data = client.models.list().data
        for m in modelos_data:
            m_id = str(m.id).lower() if hasattr(m, 'id') else str(m).lower()
            if not any(x in m_id for x in ["whisper", "guard", "vision"]):
                modelos_candidatos.append(m.id if hasattr(m, 'id') else str(m))
    except Exception:
        pass

    if not modelos_candidatos:
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
                temperature=0.6,
                max_tokens=700
            )
            return completion.choices[0].message.content
        except Exception as e:
            ultimo_error = str(e)
            continue

    return f"Error|Ocurrió un fallo al conectar con la IA|Detalle: {ultimo_error}|"
    rror: {ultimo_error}"
