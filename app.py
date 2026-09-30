import os
import io
import asyncio
from flask import Flask, render_template, request, jsonify, send_file
import edge_tts
from tutor import obtener_respuesta_tutor

app = Flask(__name__)

# Mapeo de voces neurales ultra-naturales
VOICES = {
    'en': 'en-US-JennyNeural',
    'de': 'de-DE-KatjaNeural'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    mensaje = data.get('mensaje', '')
    idioma = data.get('idioma', 'en')
    nivel = data.get('nivel', 'B1')
    modo = data.get('modo', 'conversacion')
    tipo_examen = data.get('tipo_examen', 'Cambridge')

    respuesta_raw = obtener_respuesta_tutor(mensaje, idioma, nivel, modo, tipo_examen)
    partes = respuesta_raw.split('|')

    respuesta = partes[0].strip() if len(partes) > 0 else "Error al procesar la respuesta."
    correccion = partes[1].strip() if len(partes) > 1 else ""
    explicacion = partes[2].strip() if len(partes) > 2 else ""
    vocabulario = partes[3].strip() if len(partes) > 3 else ""

    return jsonify({
        'respuesta': respuesta,
        'correccion': correccion,
        'explicacion': explicacion,
        'vocabulario': vocabulario
    })

@app.route('/tts', methods=['POST'])
def tts():
    data = request.get_json()
    texto = data.get('texto', '')
    idioma = data.get('idioma', 'en')
    
    voice = VOICES.get(idioma, 'en-US-JennyNeural')

    async def generate_audio():
        communicate = edge_tts.Communicate(texto, voice)
        mp3_fp = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_fp.write(chunk["data"])
        mp3_fp.seek(0)
        return mp3_fp

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_stream = loop.run_until_complete(generate_audio())
        return send_file(audio_stream, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
