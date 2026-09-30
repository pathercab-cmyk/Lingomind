import os
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# Inicializar cliente de Groq leyendo la variable de entorno
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

@app.route("/evaluar", methods=["POST"])
def evaluar():
    try:
        data = request.json
        prompt_usuario = data.get("prompt", "")

        # Llamada a Groq (usando un modelo como llama-3.3-70b-versatile o llama3-8b-8192)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Eres un tutor de idiomas. Evalúa el texto del estudiante.",
                },
                {
                    "role": "user",
                    "content": prompt_usuario,
                }
            ],
            model="llama-3.3-70b-versatile",
        )

        respuesta = chat_completion.choices[0].message.content
        return jsonify({"respuesta": respuesta})

    except Exception as e:
        return jsonify({
            "error": "No se pudo procesar la evaluación detallada en este momento.",
            "detalle": str(e)
        }), 500
