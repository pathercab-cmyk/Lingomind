import os
from groq import Groq

def obtener_respuesta_tutor(mensaje_usuario, idioma="en", nivel="B1", modo="conversacion", tipo_examen="Cambridge"):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error|Falta API Key|Configura GROQ_API_KEY en Render.|General: Error|Sistema: Error API"

    client = Groq(api_key=api_key)

    # Nombres oficiales de producción en la API de Groq
    modelos_disponibles = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ]

    for modelo in modelos_disponibles:
        try:
            completion = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": f"Eres un tutor de idioma {idioma} nivel {nivel}."},
                    {"role": "user", "content": mensaje_usuario}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            return completion.choices[0].message.content
        except Exception:
            # Si el modelo falla o cambia de nombre, prueba con el siguiente automáticamente
            continue

    return "Error|Fallo de conexión|No se pudo obtener respuesta de ningún modelo de Groq.|General: Error|Sistema: Sin servicio"
