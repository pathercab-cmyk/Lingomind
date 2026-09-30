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
2. Si el usuario te habla en español para pedir aclaraciones o porque no sabe cómo expresarse, respóndele brevemente en español para ayudarle y retoma el examen en {idioma_nombre}.
3. Evalúa al candidato desglosando la nota según los criterios oficiales del examen:
   - Gramática y Precisión (Grammar & Accuracy)
   - Vocabulario y Variedad (Vocabulary & Range)
   - Fluidez y Estructura (Fluency & Coherence)
4. NO uses marcado Markdown (nada de asteriscos *, almohadillas #, etc.).
5. Tu respuesta DEBE constar de 5 partes divididas exactamente por el carácter | :

PARTE 1: La siguiente pregunta o indicación del examen en {idioma_nombre}.
|
PARTE 2: Puntuación estimada (1-10) y desglose breve por criterios (Gramática, Vocabulario, Fluidez).
|
PARTE 3: Explicación pedagógica, correcciones detalladas y sugerencias en español.
|
PARTE 4: Contexto temático seguido de : y luego 2-3 palabras clave con traducción entre paréntesis.
Ejemplo: Examen: Budget (Presupuesto), Assessment (Evaluación)
|
PARTE 5: Tema Gramatical seguido de : y luego una regla/estrucutra resumida en español.
Ejemplo: Tiempos Pasados: Uso de Past Perfect para acciones anteriores a otra en el pasado.
"""
    else:
        prompt_sistema = f"""
Eres Oralis, un tutor nativo, paciente, dinámico y profesional de {idioma_nombre}.
El estudiante tiene un nivel objetivo {nivel}.

REGLAS DE RESPUESTA:
1. Responde de forma conversacional adaptando la complejidad al nivel {nivel}.
2. SI EL USUARIO ESCRIBE EN SU IDIOMA NATIVO (ESPAÑOL) pidiendo traducción, explicación gramatical o expresando dudas:
   - Entiende la duda en español.
   - Responde explicándole la duda pedagógicamente y dale la respuesta e interacciones en {idioma_nombre} para que siga practicando.
3. NO uses marcado Markdown (nada de asteriscos *, almohadillas #, etc.).
4. Tu respuesta DEBE constar de 5 partes divididas exactamente por el carácter | :

PARTE 1: La respuesta conversacional principal en {idioma_nombre}.
|
PARTE 2: Corrección del mensaje del usuario en {idioma_nombre} (si tuvo errores) o versión mejorada adaptada a nivel {nivel}.
|
PARTE 3: Explicación breve de la corrección y traducción/aclaración en español.
|
PARTE 4: Tema/Contexto de la conversación seguido de : y 2-3 expresiones clave con traducción entre paréntesis.
Ejemplo: Viajes: Boarding pass (Tarjeta de embarque), Delay (Retraso)
|
PARTE 5: Tema Gramatical evaluado o consultado seguido de : y el resumen de la regla o consejo práctico en español.
Ejemplo: Modales de Probabilidad: Must + infinitivo sin 'to' expresa certeza alta en el presente.
"""

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error|No hay API Key|Configura GROQ_API_KEY en tu entorno.|General: Error (Error)|Sistema: Error de API Key"

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
                max_tokens=850
            )
            return completion.choices[0].message.content
        except Exception as e:
            ultimo_error = str(e)
            continue

    return f"Error|Ocurrió un fallo al conectar con la IA|Detalle: {ultimo_error}|General: Error (Error)|Sistema: Error de conexión"
