from flask import Flask, render_template, request, jsonify, send_file
from tutor import obtener_respuesta_tutor
import edge_tts
import asyncio
import io

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    datos = request.get_json()
    mensaje = datos.get("mensaje", "")
    idioma = datos.get("idioma", "en")
    nivel = datos.get("nivel", "B1")
    modo = datos.get("modo", "conversacion")
    tipo_examen = datos.get("tipo_examen", "Cambridge Main Suite")

    respuesta_raw = obtener_respuesta_tutor(
        mensaje_usuario=mensaje,
        idioma=idioma,
        nivel=nivel,
        modo=modo,
        tipo_examen=tipo_examen
    )

    partes = respuesta_raw.split("|")
    if len(partes) >= 5:
        return jsonify({
            "respuesta": partes[0].strip(),
            "correccion": partes[1].strip(),
            "explicacion": partes[2].strip(),
            "vocabulario": partes[3].strip(),
            "gramatica": partes[4].strip()
        })
    else:
        return jsonify({
            "respuesta": respuesta_raw,
            "correccion": "",
            "explicacion": "",
            "vocabulario": "",
            "gramatica": ""
        })

@app.route("/tts", methods=["POST"])
def tts():
    datos = request.get_json()
    texto = datos.get("texto", "")
    idioma = datos.get("idioma", "en")

    voice = "en-US-AvaNeural" if idioma == "en" else "de-DE-KillianNeural"

    async def generate_audio():
        communicate = edge_tts.Communicate(texto, voice)
        out = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                out.write(chunk["data"])
        out.seek(0)
        return out

    try:
        audio_data = asyncio.run(generate_audio())
        return send_file(audio_data, mimetype="audio/mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
