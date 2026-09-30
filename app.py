import os
from flask import Flask, request, jsonify
from groq import Groq
from gtts import gTTS

app = Flask(__name__)

# Inicializar el cliente de Groq utilizando la variable de entorno GROQ_API_KEY
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

@app.route("/", methods=["GET"])
def home():
    return "Servidor activo y escuchando."

@app.route("/evaluar", methods=["POST"])
def evaluar():
    try:
        data = request.json or {}
        prompt_usuario = data.get("prompt", "")

        if not prompt_usuario:
            return jsonify({"error": "No se recibió texto para evaluar."}), 400

        # Llamada a la API de Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres Oralis, un tutor experto en evaluación de idiomas. "
                        "Analiza la respuesta del estudiante y proporciona retroalimentación "
                        "detallada sobre gramática, vocabulario y sugerencias de mejora."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt_usuario,
                }
            ],
            model="llama-3.3-70b-versatile",
        )

        respuesta_texto = chat_completion.choices[0].message.content

        return jsonify({"respuesta": respuesta_texto})

    except Exception as e:
        return jsonify({
            "error": "No se pudo procesar la evaluación en este momento.",
            "detalle": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
