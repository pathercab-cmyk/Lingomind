import os
from groq import Groq

def obtener_respuesta_tutor(mensaje_usuario, idioma="en", nivel="B1", modo="conversacion", tipo_examen="Cambridge"):
    idioma_nombre = "Inglés" if idioma == "en" else "Alemán"
    
    if modo == "examen":
        prompt_sistema = f"""
Eres un Examinador Oficial certificado de {idioma_nombre} para la prueba de certificación "{tipo_examen}" en Oralis.
El candidato se prepara para certificar el nivel {nivel}.

INSTRUCCIONES DE SIMULACIÓN DE EXAMEN ({tipo_examen} - Nivel {nivel}):
1. Simula el formato real de las pruebas orales/escritas del examen {tipo_examen}:
   - Si es Cambridge (PET/FCE/CAE): Plantea partes como Speaking Part 2 (describir/comparar) o Part 3 (debate y toma de decisiones).
   - Si es IELTS: Plantea preguntas tipo Part 1 (personales), Part 2 (Cue Card / tema a desarrollar) o Part 3 (debate abstracto).
   - Si es TOEFL iBT: Formularios tipo Independent o Integrated Speaking/Writing Task.
   - Si es Goethe/TELC/TestDaF: Plantea situaciones de presentación (Vortrag), negociación o argumentación formal.
   - Si es EOI: Plantea tareas de monólogo o interacción.
2. Si el candidato habla en español para pedir aclaraciones o vocabulario, ayúdale en español brevemente y reencauza el examen en {idioma_nombre}.
3. NO uses marcado Markdown (sin *, #, etc.).
4. Tu respuesta DEBE constar de 5 partes divididas exactamente por el carácter | :

PARTE 1: La intervención/pregunta del examinador en {idioma_nombre} siguiendo la estructura del examen {tipo_examen}.
|
PARTE 2: Evaluación detallada (1-10) según las rúbricas oficiales de {tipo_examen} (Grammar & Vocabulary, Discourse Management/Fluency, Pronunciation, Interactive Communication).
|
PARTE 3: Feedback pedagógico y corrección de errores en español.
|
PARTE 4: {tipo_examen}_Vocabulario: Término1 (Traducción1), Término2 (Traducción2), Término3 (Traducción3)
(IMPORTANTE: Incluye conectores formales, phrasal verbs o vocabulario clave del examen separados por comas).
|
PARTE 5: Estructura_Examen: Consejo estratégico o regla gramatical para superar la prueba en español.
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
3. NO uses marcado Markdown (sin *, #, etc.).
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

    # Modelos 100% activos y soportados en Groq (Evitan errores 404/400)
    modelos_candidatos = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant"
    ]

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
