import os
from groq import Groq

def obtener_respuesta_tutor(mensaje_usuario, idioma="en", nivel="B1", modo="conversacion", tipo_examen="Cambridge"):
    mAP_IDIOMAS = {
        "en": "Inglés",
        "de": "Alemán",
        "fr": "Francés",
        "it": "Italiano",
        "pt": "Portugués",
        "zh": "Chino Mandarín",
        "ja": "Japonés",
        "ru": "Ruso",
        "es": "Español para Extranjeros (ELE)"
    }
    
    idioma_nombre = mAP_IDIOMAS.get(idioma, "Inglés")
    
    if modo == "examen":
        prompt_sistema = f"""
Eres un Examinador Oficial certificado de {idioma_nombre} para la prueba "{tipo_examen}" en el ámbito universitario (Instituto de Idiomas / US). Nivel objetivo: {nivel}.
NO uses marcado Markdown (sin *, #).
Tu respuesta DEBE constar de 5 partes divididas exactamente por el carácter | :
PARTE 1: Intervención en {idioma_nombre}.
|
PARTE 2: Evaluación (1-10) según rúbricas oficiales.
|
PARTE 3: Feedback pedagógico en español.
|
PARTE 4: {tipo_examen}_Vocabulario: Término1 (Traducción1), Término2 (Traducción2)
|
PARTE 5: Estructura_Examen: Consejo estratégico en español.
"""
    else:
        prompt_sistema = f"""
Eres Oralis, tutor nativo de {idioma_nombre} nivel {nivel}.
NO uses marcado Markdown (sin *, #).
Tu respuesta DEBE constar de 5 partes divididas exactamente por el carácter | :
PARTE 1: Respuesta conversacional en {idioma_nombre}.
|
PARTE 2: Corrección/mejora de la frase del usuario en {idioma_nombre}.
|
PARTE 3: Explicación breve en español.
|
PARTE 4: Tema_Vocabulario: Término1 (Traducción1), Término2 (Traducción2)
|
PARTE 5: Tema_Gramatical: Regla o estructura en español.
"""

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error|Falta API Key|Configura GROQ_API_KEY en Render.|General: Error|Sistema: Sin API Key"

    client = Groq(api_key=api_key)

    # Modelo activo validado en tu panel de Groq
    modelo_activo = "qwen/qwen3.8-27b"

    try:
        completion = client.chat.completions.create(
            model=modelo_activo,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": mensaje_usuario}
            ],
            temperature=0.5,
            max_tokens=1000
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error|Fallo de Groq|{str(e)}|General: Error|Sistema: Error de API"
